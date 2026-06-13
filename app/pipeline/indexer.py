"""
pipeline/indexer.py – Orchestriert den gesamten Indexierungsprozess.

Verbindet Loader, Chunker, Embedder und VectorStore zur Indexierungs-Pipeline:
PDF → Chunks → Embeddings → Qdrant. Wird von API-Endpunkt POST /upload aufgerufen.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.interfaces import Chunker, DocumentLoader, Embedder, VectorStore
from app.core.types import DocumentInfo, EmbeddedChunk

logger = logging.getLogger(__name__)


class KnowledgeBaseIndexer:
    """Orchestriert die Indexierungs-Pipeline von der PDF-Datei bis zum Qdrant-Eintrag."""

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

    def index_pdf(self, file_path: Path) -> DocumentInfo:
        """
        Vollständige Indexierungs-Pipeline für eine PDF-Datei:
        laden → chunken → einbetten → in Qdrant speichern.
        Gibt DocumentInfo mit chunk_count=0 zurück wenn keine Chunks erzeugt wurden.
        """
        logger.info("loading_document path=%s", file_path)
        doc = self.loader.load(file_path)

        logger.info("chunking_document doc_hash=%s pages=%d", doc.doc_hash, len(doc.pages))
        chunks = self.chunker.chunk(doc)
        logger.info("chunking_done doc_hash=%s chunks=%d", doc.doc_hash, len(chunks))

        if not chunks:
            return DocumentInfo(source_path=str(file_path), doc_hash=doc.doc_hash, chunk_count=0)

        logger.info("embedding_chunks doc_hash=%s count=%d", doc.doc_hash, len(chunks))
        embedding_result = self.embedder.embed([c.text for c in chunks])  # ein Batch für alle Chunks
        vectors = embedding_result.dense_vectors
        sparse_vectors = embedding_result.sparse_vectors or [None] * len(chunks)

        embedded: list[EmbeddedChunk] = [
            EmbeddedChunk(chunk=c, dense_vector=v, sparse_vector=sv, metadata={})
            for c, v, sv in zip(chunks, vectors, sparse_vectors)
        ]

        logger.info("upserting_chunks doc_hash=%s count=%d", doc.doc_hash, len(embedded))
        self.store.upsert(embedded)

        return DocumentInfo(source_path=str(file_path), doc_hash=doc.doc_hash, chunk_count=len(embedded))

    def delete_document(self, doc_hash: str) -> None:
        """Löscht alle Chunks eines Dokuments aus Qdrant anhand des doc_hash."""
        logger.info("delete_document doc_hash=%s", doc_hash)
        self.store.delete_by_doc_hash(doc_hash)

    def list_documents(self) -> list[DocumentInfo]:
        """Gibt alle indizierten Dokumente mit Chunk-Anzahl zurück (delegiert an VectorStore)."""
        return self.store.list_documents()
