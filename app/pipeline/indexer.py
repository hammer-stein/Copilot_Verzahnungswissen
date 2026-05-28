"""
pipeline/indexer.py – Orchestriert den gesamten Indexierungsprozess.

Verbindet Loader, Chunker, Embedder, MetadataExtractor und VectorStore zur
Indexierungs-Pipeline: PDF → Chunks → Embeddings + Metadaten → Qdrant.
Wird von API-Endpunkt POST /upload aufgerufen.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from app.core.interfaces import Chunker, DocumentLoader, Embedder, MetadataExtractor, VectorStore
from app.core.schema import MetadataSchema, load_schema
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
        metadata_extractor: MetadataExtractor,
        store: VectorStore,
        schema_path: Path,
    ) -> None:
        """Alle Komponenten werden per Dependency Injection übergeben. Schema wird lazy geladen."""
        self.loader = loader
        self.chunker = chunker
        self.embedder = embedder
        self.metadata_extractor = metadata_extractor
        self.store = store
        self.schema_path = schema_path
        self._schema: Optional[MetadataSchema] = None

    @property
    def schema(self) -> MetadataSchema:
        """Lädt das Domänenschema beim ersten Aufruf (lazy, einmalig gecacht)."""
        if self._schema is None:
            self._schema = load_schema(self.schema_path)
        return self._schema

    def index_pdf(self, file_path: Path) -> DocumentInfo:
        """
        Vollständige Indexierungs-Pipeline für eine PDF-Datei:
        laden → chunken → Metadaten extrahieren → einbetten → in Qdrant speichern.
        Gibt DocumentInfo mit chunk_count=0 zurück wenn keine Chunks erzeugt wurden.
        """
        logger.info("loading_document path=%s", file_path)
        doc = self.loader.load(file_path)

        logger.info("chunking_document doc_hash=%s pages=%d", doc.doc_hash, len(doc.pages))
        chunks = self.chunker.chunk(doc)
        logger.info("chunking_done doc_hash=%s chunks=%d", doc.doc_hash, len(chunks))

        if not chunks:
            return DocumentInfo(source_path=str(file_path), doc_hash=doc.doc_hash, chunk_count=0)

        # Metadaten per LLM extrahieren und gegen Schema bereinigen
        meta_list: list[dict[str, Any]] = []
        for c in chunks:
            raw_meta = self.metadata_extractor.extract(c, self.schema) or {}
            meta_list.append(_sanitize_metadata(self.schema, raw_meta))

        logger.info("embedding_chunks doc_hash=%s count=%d", doc.doc_hash, len(chunks))
        vectors = self.embedder.embed([c.text for c in chunks]).dense_vectors  # ein Batch für alle Chunks

        # Chunks, Vektoren und Metadaten zu EmbeddedChunks zusammenführen
        embedded: list[EmbeddedChunk] = []
        for c, v, m in zip(chunks, vectors, meta_list):
            embedded.append(EmbeddedChunk(chunk=c, dense_vector=v, sparse_vector=None, metadata=m))

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


def _sanitize_metadata(schema: MetadataSchema, data: dict[str, Any]) -> dict[str, Any]:
    """
    Filtert LLM-Ausgaben auf erlaubte Schema-Felder. Verhindert, dass das LLM
    erfundene Felder in den Qdrant-Payload schreibt, die den Filter stören könnten.
    """
    # erlaubte Felder: Feldnamen + range_fields (z.B. modul_min, modul_max)
    allowed: set[str] = set()
    for f in schema.fields:
        allowed.add(f.name)
        if f.range_fields:
            allowed.update(f.range_fields)
        else:
            allowed.add(f"{f.name}_min")
            allowed.add(f"{f.name}_max")

    return {k: v for k, v in (data or {}).items() if k in allowed}
