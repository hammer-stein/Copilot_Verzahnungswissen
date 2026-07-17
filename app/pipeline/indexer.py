"""
pipeline/indexer.py – Orchestriert den gesamten Indexierungsprozess.

Verbindet Loader, Chunker, Embedder und VectorStore zur Indexierungs-Pipeline:
Dokument → Chunks → Embeddings → Qdrant. Wird von API-Endpunkt POST /upload aufgerufen.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.interfaces import Chunker, DocumentLoader, Embedder, VectorStore
from app.core.types import DocumentInfo, EmbeddedChunk

logger = logging.getLogger(__name__)


class KnowledgeBaseIndexer:
    """Orchestriert die Indexierungs-Pipeline von der Datei bis zum Qdrant-Eintrag."""

    def __init__(
        self,
        *,
        loader: DocumentLoader,
        chunker: Chunker,
        embedder: Embedder,
        store: VectorStore,
    ) -> None:
        """Alle Komponenten werden per Dependency Injection übergeben."""
        self.loader = loader
        self.chunker = chunker
        self.embedder = embedder
        self.store = store

    def index_document(self, file_path: Path, *, file_name: str = "", folder: str = "") -> DocumentInfo:
        """
        Entscheidet basierend auf der Dateiendung, wie das Dokument verarbeitet wird.
        """
        suffix = file_path.suffix.lower()
        
        if suffix == ".pdf":
            return self.index_pdf(file_path, file_name=file_name, folder=folder)
        elif suffix in (".csv", ".xlsx", ".xls"):
            return self.index_tabular(file_path, file_name=file_name, folder=folder)
        else:
            raise ValueError(f"Kein passender Loader für Dateityp {suffix} gefunden.")

    def index_pdf(self, file_path: Path, *, file_name: str = "", folder: str = "") -> DocumentInfo:
        """Verarbeitet PDF-Dateien via Standard-Loader."""
        display_name = file_name or file_path.name
        logger.info("loading_pdf path=%s", file_path)
        doc = self.loader.load(file_path)
        return self._run_pipeline(doc, file_path, display_name, folder)

    def index_tabular(self, file_path: Path, *, file_name: str = "", folder: str = "") -> DocumentInfo:
        """Verarbeitet CSV/Excel via TabularLoader."""
        from app.implementations.tabular_loader_pandas import TabularLoader
        display_name = file_name or file_path.name
        logger.info("loading_tabular path=%s", file_path)
        
        # TabularLoader lädt Datei und gibt Doc-Objekt zurück
        loader = TabularLoader()
        doc = loader.load(file_path)
        return self._run_pipeline(doc, file_path, display_name, folder)

    def _run_pipeline(self, doc, file_path, display_name, folder) -> DocumentInfo:
        """Interne Methode, die das geladene Doc-Objekt chunkt, einbettet und speichert."""
        logger.info("chunking_document doc_hash=%s", doc.doc_hash)
        chunks = self.chunker.chunk(doc)
        
        if not chunks:
            return DocumentInfo(source_path=str(file_path), doc_hash=doc.doc_hash, chunk_count=0, file_name=display_name, folder=folder)

        embedding_result = self.embedder.embed([c.text for c in chunks])
        vectors = embedding_result.dense_vectors
        sparse_vectors = embedding_result.sparse_vectors or [None] * len(chunks)

        # doc_kind ("text" | "table") wandert in die Chunk-Metadaten → Qdrant-Payload,
        # damit der Retriever Tabellen-Dokumente beim Aggregat-Routing erkennen kann.
        doc_meta = {"file_name": display_name, "folder": folder, "doc_kind": getattr(doc, "doc_kind", "text")}
        embedded: list[EmbeddedChunk] = [
            EmbeddedChunk(chunk=c, dense_vector=v, sparse_vector=sv, metadata=dict(doc_meta))
            for c, v, sv in zip(chunks, vectors, sparse_vectors)
        ]

        self.store.upsert(embedded)
        return DocumentInfo(source_path=str(file_path), doc_hash=doc.doc_hash, chunk_count=len(embedded), file_name=display_name, folder=folder)

    # --- Die bestehenden Methoden für Folder/Title/Delete/List bleiben UNVERÄNDERT ---
    def set_document_folder(self, doc_hash: str, folder: str) -> None:
        self.store.set_document_folder(doc_hash, folder)

    def set_document_title(self, doc_hash: str, title: str) -> None:
        self.store.set_document_title(doc_hash, title)

    def delete_document(self, doc_hash: str) -> None:
        self.store.delete_by_doc_hash(doc_hash)

    def clear_all(self) -> None:
        """Löscht die gesamte Wissensbasis (alle Dokumente/Chunks)."""
        self.store.clear_all()

    def list_documents(self) -> list[DocumentInfo]:
        return self.store.list_documents()
    