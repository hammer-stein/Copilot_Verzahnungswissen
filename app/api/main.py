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
import re
import threading
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
    request_id: Optional[str] = None  # Client-seitige ID für Live-Prozessstatus


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
    cad_previews_dir = storage_dir / "cad_previews"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    cad_previews_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = BASE_DIR / "logs" / "queries"
    logs_dir.mkdir(parents=True, exist_ok=True)

    process_lock = threading.Lock()
    process_runs: dict[str, dict[str, Any]] = {}

    def _default_process_steps() -> list[dict[str, str]]:
        return [
            {
                "key": "embedding",
                "agent": "embedding",
                "title": "Embedding",
                "content": f"Fragevektor via {config.embedder.model_name} vorbereiten.",
                "status": "pending",
            },
            {
                "key": "search",
                "agent": "retrieval",
                "title": "Chunk-Suche",
                "content": f"Vektorsuche mit Kosinus-Ähnlichkeit (Threshold {config.retriever.min_similarity:g}, top_k {config.retriever.top_k}).",
                "status": "pending",
            },
            {
                "key": "answer_generation",
                "agent": "solver",
                "title": "Antwortgenerierung",
                "content": f"Antwortentwurf via {config.answer_generator.model_name}.",
                "status": "pending",
            },
            {
                "key": "validation",
                "agent": "reviewer",
                "title": "Validierung",
                "content": f"Prüfung gegen CAD-Daten und Quellen via {config.answer_generator.model_name}.",
                "status": "pending" if config.answer_generator.enable_review else "skipped",
            },
            {
                "key": "improvement",
                "agent": "solver",
                "title": "Verbesserung",
                "content": f"Überarbeitung via {config.answer_generator.model_name}, falls die Prüfung Mängel findet.",
                "status": "pending" if (config.answer_generator.enable_review and config.answer_generator.max_revisions > 0) else "skipped",
            },
        ]

    def _ensure_process_run(request_id: str, *, questions: list[str]) -> None:
        with process_lock:
            process_runs[request_id] = {
                "request_id": request_id,
                "questions": questions,
                "status": "running",
                "steps": _default_process_steps(),
            }

    def _process_snapshot(request_id: Optional[str]) -> list[dict[str, str]]:
        if not request_id:
            return []
        with process_lock:
            run = process_runs.get(request_id)
            if not run:
                return []
            return [dict(step) for step in run.get("steps", [])]

    def _update_process(request_id: Optional[str], key: str, status: str, content: Optional[str] = None) -> None:
        if not request_id:
            return
        with process_lock:
            run = process_runs.get(request_id)
            if not run:
                return
            for step in run.get("steps", []):
                if step.get("key") == key:
                    step["status"] = status
                    if content:
                        step["content"] = content
                    break

    def _progress_for(request_id: Optional[str]):
        def progress(event: str) -> None:
            mapping = {
                "embedding_start": ("embedding", "running"),
                "embedding_done": ("embedding", "done"),
                "search_start": ("search", "running"),
                "search_done": ("search", "done"),
                "answer_generation_start": ("answer_generation", "running"),
                "answer_generation_done": ("answer_generation", "done"),
                "validation_start": ("validation", "running"),
                "validation_done": ("validation", "done"),
                "validation_skipped": ("validation", "skipped"),
                "improvement_start": ("improvement", "running"),
                "improvement_done": ("improvement", "done"),
                "improvement_skipped": ("improvement", "skipped"),
            }
            mapped = mapping.get(event)
            if mapped:
                _update_process(request_id, *mapped)
        return progress

    def _finish_process(request_id: Optional[str], status: str) -> None:
        if not request_id:
            return
        with process_lock:
            run = process_runs.get(request_id)
            if run:
                run["status"] = status

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

    @app.get("/cad/preview/{name}")
    async def cad_preview(name: str):
        """Liefert das aus einer hochgeladenen STEP-Datei erzeugte STL-Preview-Mesh."""
        if not re.fullmatch(r"[A-Za-z0-9_.-]+\.stl", name):
            raise HTTPException(status_code=404, detail="Unknown CAD preview.")
        preview_path = cad_previews_dir / name
        if not preview_path.exists():
            raise HTTPException(status_code=404, detail="CAD preview not found.")
        return FileResponse(preview_path, media_type="model/stl", filename=name)

    def _analyze_cad_with_preview(step_path: Path, preview_path: Path, original_filename: str) -> dict[str, Any]:
        result = components.cad_adapter.extract(step_path)
        if not isinstance(result, dict):
            raise RuntimeError("CAD adapter returned no metadata dictionary.")

        result = dict(result)
        result.setdefault("filename", original_filename or step_path.name)

        try:
            from app.implementations.cad_mesh_exporter import export_step_to_stl

            export_step_to_stl(step_path, preview_path)
            result["preview"] = {
                "format": "stl",
                "mesh_url": f"/cad/preview/{preview_path.name}",
                "source_filename": original_filename or step_path.name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:  # noqa: BLE001 - Preview ist optional, Parameteranalyse bleibt gültig.
            preview_path.unlink(missing_ok=True)
            logger.warning("cad_preview_generation_failed file=%s error=%s", step_path, exc)
            result["preview"] = {
                "format": "stl",
                "mesh_url": None,
                "source_filename": original_filename or step_path.name,
                "error": str(exc),
            }
        return result

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
        preview_name = f"{Path(tmp_name).stem}.stl"
        preview_path = cad_previews_dir / preview_name
        dest.write_bytes(await file.read())

        try:
            return await asyncio.to_thread(_analyze_cad_with_preview, dest, preview_path, file.filename or tmp_name)
        except Exception as e:
            logger.exception("cad_analysis_failed file=%s", dest)
            raise HTTPException(status_code=502, detail=f"CAD analysis failed: {e}")
        finally:
            dest.unlink(missing_ok=True)  # STEP-Datei nach Analyse wieder löschen

    @app.get("/ask/status/{request_id}")
    async def ask_status(request_id: str):
        """Live-Status einer laufenden /ask-Anfrage. Wird vom Frontend während der Generierung gepollt."""
        with process_lock:
            run = process_runs.get(request_id)
            if not run:
                return {"request_id": request_id, "status": "unknown", "steps": _default_process_steps()}
            return {
                "request_id": request_id,
                "status": run.get("status", "running"),
                "steps": [dict(step) for step in run.get("steps", [])],
            }

    async def _answer_one(question: str, cad_json: dict[str, Any], answer_format: Optional[str], request_id: Optional[str]) -> Answer:
        """
        Pipeline für eine einzelne Frage: Retrieval (Originalfrage) → Antwortgenerierung.
        Das CAD-JSON fließt erst in der Antwortstufe ein – das Retrieval arbeitet
        ausschließlich mit der Nutzerfrage.
        """
        progress = _progress_for(request_id)
        def _retrieve_with_optional_progress() -> list[Any]:
            try:
                return components.retriever.retrieve(question, progress_callback=progress)
            except TypeError as e:
                if "progress_callback" not in str(e):
                    raise
                return components.retriever.retrieve(question)

        chunks = await asyncio.to_thread(_retrieve_with_optional_progress)

        def _generate_with_optional_progress() -> Answer:
            try:
                return components.answer_generator.generate(
                    question=question,
                    chunks=chunks,
                    cad_metadata=cad_json,
                    answer_format=answer_format,
                    progress_callback=progress,
                )
            except TypeError as e:
                if "progress_callback" not in str(e):
                    raise
                return components.answer_generator.generate(
                    question=question,
                    chunks=chunks,
                    cad_metadata=cad_json,
                    answer_format=answer_format,
                )

        answer = await asyncio.to_thread(_generate_with_optional_progress)

        # Die Detail-Schritte des Generators (Solver/Reviewer) werden NICHT separat unter den
        # Ablauf gehängt, sondern in den passenden Ablauf-Schritt eingeschmolzen: Erläuterung +
        # echter Status (warnung="Hinweis", korrigiert) landen direkt bei Antwortgenerierung /
        # Validierung / Verbesserung. Nur der Orchestrator-Schritt bleibt separat erhalten.
        detail = list(answer.get("agent_trace", []))
        solver_contents: list[str] = []
        review_status = review_content = None
        improvement_status = improvement_content = None
        orchestrator_step = None
        for s in detail:
            ag, title = s.get("agent"), s.get("title", "")
            content, status = s.get("content", ""), s.get("status")
            if ag == "orchestrator":
                orchestrator_step = s  # "Recherche & Delegation" oder "Einzeldurchlauf (Fallback)"
            elif ag == "solver" and title.startswith("Lösung"):
                if content:
                    solver_contents.append(content)
            elif ag == "reviewer" and title == "Plausibilitätsprüfung":
                review_status, review_content = status, content
            elif title in ("Überarbeitete Antwort", "Korrigierte Antwort"):
                improvement_status, improvement_content = "korrigiert", content
            elif ag == "reviewer" and title == "Hinweis":
                improvement_status, improvement_content = "warnung", content

        snapshot = [step for step in _process_snapshot(request_id) if step.get("status") != "pending"]
        for step in snapshot:
            key = step.get("key")
            if key == "answer_generation" and solver_contents:
                step["content"] = " ".join(solver_contents)
            elif key == "validation" and review_status:
                step["status"] = review_status
                if review_content:
                    step["content"] = review_content
            elif key == "improvement" and improvement_status:
                step["status"] = improvement_status
                if improvement_content:
                    step["content"] = improvement_content

        process_steps = [{k: v for k, v in step.items() if k != "key"} for step in snapshot]
        merged = process_steps + ([orchestrator_step] if orchestrator_step else [])
        if merged:
            answer = dict(answer)
            answer["agent_trace"] = merged
        return answer

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
        request_id = (req.request_id or uuid.uuid4().hex).strip()
        _ensure_process_run(request_id, questions=questions)

        tasks = [_answer_one(q, cad, answer_format, request_id) for q in questions]
        try:
            answers = await asyncio.gather(*tasks)  # alle Fragen parallel verarbeiten
            _finish_process(request_id, "done")
        except Exception as e:
            _finish_process(request_id, "error")
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
