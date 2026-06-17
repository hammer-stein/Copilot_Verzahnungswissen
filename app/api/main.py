"""
api/main.py – FastAPI-Anwendung mit allen HTTP-Endpunkten.

Einstiegspunkt des Servers: create_app() lädt die Konfiguration, baut alle
Komponenten auf und registriert die Endpunkte /upload, /documents (+ /move),
/folders (CRUD), /ask, /cad/analyze, /cad/random, /cad/examples.

Anfrage-Fluss pro Frage (CAD-aware RAG):
  1. HybridRetriever sucht mit der Originalfrage in Qdrant
  2. AnswerGenerator beantwortet die Frage aus den Chunks + dem vollen CAD-JSON
     (das CAD-JSON fließt erst in der Antwortstufe ein, nicht ins Retrieval)
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.core.config import load_config
from app.core.factory import build_components
from app.core.folder_registry import FolderRegistry
from app.core.types import Answer
from app.core.utils import stable_json_dumps
from app.pipeline.indexer import KnowledgeBaseIndexer

logger = logging.getLogger(__name__)


# Pydantic-Modelle auf Modul-Ebene (nicht in create_app) – FastAPI-Anforderung für korrekte Validierung.
class AskRequest(BaseModel):
    questions: list[str] = Field(min_length=1)
    cad_metadata: dict[str, Any] = Field(default_factory=dict)  # volles GearParameters-JSON
    format: Optional[str] = None  # "kurz" | "standard" | "ausführlich" | "stichpunkte" | "tabellarisch"


class AskResponse(BaseModel):
    cad_metadata: dict[str, Any]
    answers: list[Answer]


class FolderRequest(BaseModel):
    name: str  # Ordnername zum Anlegen


class MoveRequest(BaseModel):
    folder: str = ""  # Zielordner ("" = aus Ordner entfernen / kein Ordner)


class TitleRequest(BaseModel):
    title: str  # Anzeigename eines Dokuments


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = BASE_DIR / "config.yaml"


def _setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def create_app(config_path: Path = DEFAULT_CONFIG_PATH) -> FastAPI:
    """
    Lädt die Konfiguration, baut alle Komponenten auf und erstellt die FastAPI-Anwendung.
    Wird einmalig beim Serverstart aufgerufen; alle Komponenten werden als Closure in den Endpunkten gehalten.
    """
    _setup_logging()

    if not config_path.exists():
        raise RuntimeError(f"Missing config file at {config_path}. Create one from config.example.yaml.")

    config = load_config(config_path)
    components = build_components(config, base_dir=BASE_DIR)  # ~10s wegen Embedder-Loading

    indexer = KnowledgeBaseIndexer(
        loader=components.loader,
        chunker=components.chunker,
        embedder=components.embedder,
        store=components.vector_store,
    )

    app = FastAPI(title="Modular RAG System", version="0.2.0")

    # CORS: alle Origins erlaubt für lokale Entwicklung
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def _no_cache_ui(request, call_next):
        """
        Verhindert, dass der Browser die GUI-Dateien (HTML/JS/CSS unter /ui/) cached.
        Sonst zeigt er nach Frontend-Änderungen alte Versionen, ohne dass ein Hard-Reload
        offensichtlich nötig wäre. Nur Entwicklungs-Komfort – keine API-Antworten betroffen.
        """
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/ui/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
        return response

    storage_dir = BASE_DIR / "storage"
    uploads_dir = storage_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = BASE_DIR / "logs" / "queries"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Ordner-Registry für die Organisation der Wissensbasis (inkl. leerer Ordner).
    folder_registry = FolderRegistry(storage_dir / "folders.json")

    # Design-System-GUI als statische Dateien einhängen. Die Copilot-App liegt unter
    # /ui/ui_kits/copilot/ und nutzt relative Pfade (../../styles.css, _ds_bundle.js …),
    # die so korrekt auf frontend/design-system/ aufgelöst werden.
    design_system_dir = BASE_DIR / "frontend" / "design-system"
    COPILOT_APP_PATH = "/ui/ui_kits/copilot/"
    if design_system_dir.exists():
        app.mount("/ui", StaticFiles(directory=design_system_dir, html=True), name="ui")

    @app.get("/")
    def root():
        """
        Leitet auf das Design-System-GUI weiter. Der Zeitstempel-Query erzwingt bei jedem
        Aufruf von '/' eine eindeutige index.html-URL – so umgeht der Browser zuverlässig
        eine evtl. veraltet gecachte Frontend-Version (häufige Ursache für „alte UI trotz
        Code-Änderung"). Fallback: altes Frontend, sonst Status.
        """
        if design_system_dir.exists():
            cache_bust = int(datetime.now(timezone.utc).timestamp())
            return RedirectResponse(url=f"{COPILOT_APP_PATH}?t={cache_bust}")
        frontend = BASE_DIR / "frontend" / "index.html"
        if frontend.exists():
            return FileResponse(frontend)
        return {"status": "ok"}

    @app.post("/upload")
    async def upload_pdf(file: UploadFile = File(...), folder: str = Form("")):
        """
        Nimmt eine PDF-Datei entgegen, speichert sie temporär und startet die Indexierungs-Pipeline.
        Optionaler Form-Parameter `folder` ordnet das Dokument einem UI-Ordner zu.
        asyncio.to_thread() verhindert, dass die synchrone Indexierung den Event-Loop blockiert.
        """
        original_name = Path(file.filename or "").name
        if not original_name.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF upload supported.")

        folder = (folder or "").strip()

        # Zeitstempel + UUID im Dateinamen verhindert Kollisionen bei gleichzeitigen Uploads
        tmp_name = f"{_utc_stamp()}_{uuid.uuid4().hex}{Path(original_name).suffix}"
        dest = uploads_dir / tmp_name

        content = await file.read()
        dest.write_bytes(content)

        try:
            info = await asyncio.to_thread(
                indexer.index_pdf, dest, file_name=original_name, folder=folder
            )
        except Exception as e:
            logger.exception("indexing_failed file=%s", dest)
            raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")

        if folder:
            await asyncio.to_thread(folder_registry.add, folder)  # Ordner sicher registrieren

        return info

    @app.get("/documents")
    async def list_documents():
        """Gibt alle indizierten Dokumente mit Chunk-Anzahl zurück."""
        try:
            return await asyncio.to_thread(indexer.list_documents)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/documents/{doc_hash}")
    async def delete_document(doc_hash: str):
        """Löscht alle Chunks eines Dokuments aus Qdrant anhand des doc_hash."""
        try:
            await asyncio.to_thread(indexer.delete_document, doc_hash)
            return {"status": "deleted", "doc_hash": doc_hash}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/documents/{doc_hash}/move")
    async def move_document(doc_hash: str, req: MoveRequest):
        """Verschiebt ein Dokument in einen anderen Ordner ("" = kein Ordner)."""
        folder = (req.folder or "").strip()
        try:
            if folder:
                await asyncio.to_thread(folder_registry.add, folder)
            await asyncio.to_thread(indexer.set_document_folder, doc_hash, folder)
            return {"status": "moved", "doc_hash": doc_hash, "folder": folder}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/documents/{doc_hash}/title")
    async def set_document_title(doc_hash: str, req: TitleRequest):
        """Setzt den sichtbaren Dokumenttitel für Bibliothek und Quellenangaben."""
        title = (req.title or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="Dokumenttitel darf nicht leer sein.")
        try:
            await asyncio.to_thread(indexer.set_document_title, doc_hash, title)
            return {"status": "renamed", "doc_hash": doc_hash, "title": title}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/folders")
    async def list_folders():
        """
        Liefert alle Ordnernamen: registrierte (inkl. leerer) plus solche, die aktuell
        von Dokumenten verwendet werden – als Vereinigungsmenge.
        """
        try:
            registered = await asyncio.to_thread(folder_registry.list)
            docs = await asyncio.to_thread(indexer.list_documents)
            in_use = {d.folder for d in docs if d.folder}
            names = sorted(set(registered) | in_use, key=str.casefold)
            return {"folders": names}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/folders")
    async def create_folder(req: FolderRequest):
        """Legt einen (leeren) Ordner an. Idempotent."""
        name = (req.name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Ordnername darf nicht leer sein.")
        try:
            folders = await asyncio.to_thread(folder_registry.add, name)
            return {"folders": folders}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/folders/{name}")
    async def delete_folder(name: str):
        """
        Entfernt einen Ordner. Enthaltene Dokumente werden NICHT gelöscht, sondern
        auf "kein Ordner" zurückgesetzt.
        """
        try:
            docs = await asyncio.to_thread(indexer.list_documents)
            for d in docs:
                if d.folder == name:
                    await asyncio.to_thread(indexer.set_document_folder, d.doc_hash, "")
            folders = await asyncio.to_thread(folder_registry.remove, name)
            return {"folders": folders}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/cad/examples")
    async def list_cad_examples():
        """Listet die verfügbaren synthetischen CAD-Testdatensätze (Dateinamen)."""
        files = await asyncio.to_thread(components.synthetic_cad_adapter.list_files)
        return {"files": [f.name for f in files]}

    @app.get("/cad/examples/{name}")
    async def get_cad_example(name: str):
        """Liefert einen bestimmten synthetischen CAD-Testdatensatz."""
        files = {f.name: f for f in components.synthetic_cad_adapter.list_files()}
        if name not in files:
            raise HTTPException(status_code=404, detail=f"Unknown CAD example: {name}")
        return await asyncio.to_thread(components.synthetic_cad_adapter.load_file, files[name])

    @app.get("/cad/random")
    async def random_cad():
        """Liefert einen zufälligen synthetischen CAD-Testdatensatz (Demo/Test)."""
        try:
            return await asyncio.to_thread(components.synthetic_cad_adapter.extract, None)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/cad/analyze")
    async def analyze_cad(file: UploadFile = File(...)):
        """
        Nimmt eine STEP-Datei entgegen und leitet sie an den konfigurierten CAD-Adapter
        weiter. Je nach Schalter (cad_adapter.implementation) wird die Datei echt vom
        cad_processor analysiert oder ein synthetischer Testdatensatz geliefert.
        Das Ergebnis ist direkt als cad_metadata für /ask verwendbar.
        """
        suffix = Path(file.filename).suffix.lower()
        if suffix not in (".step", ".stp"):
            raise HTTPException(status_code=400, detail="Only .step/.stp upload supported.")

        tmp_name = f"{_utc_stamp()}_{uuid.uuid4().hex}{suffix}"
        dest = uploads_dir / tmp_name
        dest.write_bytes(await file.read())

        try:
            return await asyncio.to_thread(components.cad_adapter.extract, dest)
        except Exception as e:
            logger.exception("cad_analysis_failed file=%s", dest)
            raise HTTPException(status_code=502, detail=f"CAD analysis failed: {e}")
        finally:
            dest.unlink(missing_ok=True)  # STEP-Datei nach Analyse wieder löschen

    async def _answer_one(question: str, cad_json: dict[str, Any], answer_format: Optional[str]) -> Answer:
        """
        Pipeline für eine einzelne Frage: Retrieval (Originalfrage) → Antwortgenerierung.
        Das CAD-JSON fließt erst in der Antwortstufe ein – das Retrieval arbeitet
        ausschließlich mit der Nutzerfrage.
        """
        chunks = await asyncio.to_thread(components.retriever.retrieve, question)
        return await asyncio.to_thread(
            components.answer_generator.generate,
            question=question,
            chunks=chunks,
            cad_metadata=cad_json,
            answer_format=answer_format,
        )

    @app.post("/ask", response_model=AskResponse)
    async def ask(req: AskRequest):
        """
        Beantwortet mehrere Fragen parallel via asyncio.gather().
        Jede Frage durchläuft Retrieval + LLM-Generierung mit CAD-Kontext.
        Das Ergebnis wird als JSON-Datei in logs/queries/ gespeichert.
        """
        questions = [q.strip() for q in req.questions if q.strip()]
        if not questions:
            raise HTTPException(status_code=400, detail="No questions provided.")

        cad = req.cad_metadata or {}
        answer_format = req.format or "standard"

        tasks = [_answer_one(q, cad, answer_format) for q in questions]
        try:
            answers = await asyncio.gather(*tasks)  # alle Fragen parallel verarbeiten
        except Exception as e:
            logger.exception("ask_failed")
            raise HTTPException(status_code=500, detail=str(e))

        # Anfrage als JSON-Log speichern (kein Konversationsgedächtnis, jede Anfrage isoliert)
        qid = uuid.uuid4().hex
        (logs_dir / f"{_utc_stamp()}_{qid}.json").write_text(
            stable_json_dumps({
                "questions": questions,
                "cad_metadata": cad,
                "format": answer_format,
                "answers": answers,
                "models": {
                    "embedder": config.embedder.model_name,
                    "answer_generator": config.answer_generator.model_name,
                },
            }),
            encoding="utf-8",
        )

        return AskResponse(cad_metadata=cad, answers=answers)

    return app


app = create_app()
