"""
api/main.py – FastAPI-Anwendung mit allen HTTP-Endpunkten.

Einstiegspunkt des Servers: create_app() lädt die Konfiguration, baut alle
Komponenten auf und registriert die Endpunkte /upload, /documents, /ask, /cad/random.
Der /ask-Endpunkt verarbeitet mehrere Fragen parallel via asyncio.gather().
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.config import load_config
from app.core.factory import build_components
from app.core.types import Answer
from app.core.utils import stable_json_dumps
from app.pipeline.indexer import KnowledgeBaseIndexer

logger = logging.getLogger(__name__)


# Pydantic-Modelle auf Modul-Ebene (nicht in create_app) – FastAPI-Anforderung für korrekte Validierung.
class AskRequest(BaseModel):
    questions: list[str] = Field(min_length=1)
    cad_metadata: dict[str, Any] = Field(default_factory=dict)


class AskResponse(BaseModel):
    cad_metadata: dict[str, Any]
    answers: list[Answer]


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = BASE_DIR / "config.yaml"


def _setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


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
        metadata_extractor=components.metadata_extractor,
        store=components.vector_store,
        schema_path=BASE_DIR / config.domain.schema_path,
    )

    app = FastAPI(title="Modular RAG System", version="0.1.0")

    # CORS: alle Origins erlaubt für lokale Entwicklung
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    storage_dir = BASE_DIR / "storage"
    uploads_dir = storage_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = BASE_DIR / "logs" / "queries"
    logs_dir.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def root():
        """Liefert das Frontend (index.html) oder einen Status-Response."""
        frontend = BASE_DIR / "frontend" / "index.html"
        if frontend.exists():
            return FileResponse(frontend)
        return {"status": "ok"}

    @app.post("/upload")
    async def upload_pdf(file: UploadFile = File(...)):
        """
        Nimmt eine PDF-Datei entgegen, speichert sie temporär und startet die Indexierungs-Pipeline.
        asyncio.to_thread() verhindert, dass die synchrone Indexierung den Event-Loop blockiert.
        """
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF upload supported.")

        # Zeitstempel + UUID im Dateinamen verhindert Kollisionen bei gleichzeitigen Uploads
        tmp_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}{Path(file.filename).suffix}"
        dest = uploads_dir / tmp_name

        content = await file.read()
        dest.write_bytes(content)

        try:
            info = await asyncio.to_thread(indexer.index_pdf, dest)
        except Exception as e:
            logger.exception("indexing_failed file=%s", dest)
            raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")

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

    @app.get("/cad/random")
    async def random_cad():
        """Liefert zufällige CAD-Metadaten vom RandomGearGenerator (Demo/Test)."""
        return await asyncio.to_thread(components.cad_adapter.extract, None)

    @app.post("/cad/analyze")
    async def analyze_cad(file: UploadFile = File(...)):
        """
        Nimmt eine STEP-Datei entgegen, leitet sie an den CAD-Adapter weiter
        (CadProcessorClient → cad_processor-Service) und gibt die gemappten
        CAD-Metadaten zurück – direkt als cad_metadata für /ask verwendbar.
        """
        suffix = Path(file.filename).suffix.lower()
        if suffix not in (".step", ".stp"):
            raise HTTPException(status_code=400, detail="Only .step/.stp upload supported.")

        tmp_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}{suffix}"
        dest = uploads_dir / tmp_name
        dest.write_bytes(await file.read())

        try:
            return await asyncio.to_thread(components.cad_adapter.extract, dest)
        except Exception as e:
            logger.exception("cad_analysis_failed file=%s", dest)
            raise HTTPException(status_code=502, detail=f"CAD analysis failed: {e}")
        finally:
            dest.unlink(missing_ok=True)  # STEP-Datei nach Analyse wieder löschen

    async def _answer_one(question: str, cad_metadata: dict[str, Any]) -> Answer:
        """Hilfsfunktion: führt Retrieval und Antwortgenerierung für eine einzelne Frage aus."""
        chunks = await asyncio.to_thread(components.retriever.retrieve, question, cad_metadata)
        return await asyncio.to_thread(
            components.answer_generator.generate,
            question=question,
            chunks=chunks,
            cad_metadata=cad_metadata,
        )

    @app.post("/ask", response_model=AskResponse)
    async def ask(req: AskRequest):
        """
        Beantwortet mehrere Fragen parallel via asyncio.gather().
        Jede Frage durchläuft Retrieval + LLM-Generierung; alle laufen gleichzeitig.
        Das Ergebnis wird als JSON-Datei in logs/queries/ gespeichert.
        """
        questions = [q.strip() for q in req.questions if q.strip()]
        if not questions:
            raise HTTPException(status_code=400, detail="No questions provided.")

        cad = req.cad_metadata or {}

        tasks = [_answer_one(q, cad) for q in questions]
        try:
            answers = await asyncio.gather(*tasks)  # alle Fragen parallel verarbeiten
        except Exception as e:
            logger.exception("ask_failed")
            raise HTTPException(status_code=500, detail=str(e))

        # Anfrage als JSON-Log speichern (kein Konversationsgedächtnis, jede Anfrage isoliert)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        qid = uuid.uuid4().hex
        (logs_dir / f"{ts}_{qid}.json").write_text(
            stable_json_dumps({
                "questions": questions,
                "cad_metadata": cad,
                "answers": answers,
                "models": {
                    "embedder": config.embedder.model_name,
                    "metadata_extractor": config.metadata_extractor.model_name,
                    "answer_generator": config.answer_generator.model_name,
                },
            }),
            encoding="utf-8",
        )

        return AskResponse(cad_metadata=cad, answers=answers)

    return app


app = create_app()
