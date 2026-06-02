"""
retriever_two_stage.py – Zweistufiger Retriever: Metadatenfilter + Vektorsuche.

Stage 1 baut aus den CAD-Parametern des aktuellen Bauteils einen deterministischen
Qdrant-Filter, der technisch unpassende Chunks ausschließt. Stage 2 sucht im
gefilterten Raum die semantisch ähnlichsten Chunks via Kosinus-Ähnlichkeit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.interfaces import Embedder, VectorStore
from app.core.schema import MetadataSchema, SchemaField, load_schema
from app.core.types import RetrievedChunk, SearchResult


class TwoStageRetriever:
    """Kombiniert deterministischen Metadatenfilter (Stage 1) mit semantischer Vektorsuche (Stage 2)."""

    def __init__(
        self,
        *,
        embedder: Embedder,
        store: VectorStore,
        schema_path: Path,
        stage1_strict: bool,
        stage1_relax_on_empty: bool,
        stage1_min_candidates: int,
        top_k: int,
        min_similarity: float,
        stage2_use_hybrid: bool = False,
        hybrid_dense_weight: float = 0.7,
        hybrid_sparse_weight: float = 0.3,
        reranker_enabled: bool = False,
        reranker_model: Optional[str] = None,
        reranker_candidate_multiplier: int = 5,
    ) -> None:
        """
        embedder muss dieselbe Instanz wie beim Indexieren sein (gleicher Vektorraum).
        stage1_relax_on_empty lockert Range-Filter schrittweise, wenn zu wenige Treffer gefunden werden.
        """
        self.embedder = embedder
        self.store = store
        self.schema_path = schema_path
        self.stage1_strict = stage1_strict
        self.stage1_relax_on_empty = stage1_relax_on_empty
        self.stage1_min_candidates = stage1_min_candidates
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.stage2_use_hybrid = stage2_use_hybrid
        self.hybrid_dense_weight = hybrid_dense_weight
        self.hybrid_sparse_weight = hybrid_sparse_weight
        self.reranker_enabled = reranker_enabled
        self.reranker_model = reranker_model
        self.reranker_candidate_multiplier = max(1, reranker_candidate_multiplier)
        self._reranker = None
        self._schema: Optional[MetadataSchema] = None  # lazy geladen

    @property
    def schema(self) -> MetadataSchema:
        """Lädt das Domänenschema beim ersten Aufruf aus der YAML-Datei (lazy, einmalig gecacht)."""
        if self._schema is None:
            self._schema = load_schema(self.schema_path)
        return self._schema

    def retrieve(self, question: str, cad_metadata: dict) -> list[RetrievedChunk]:
        """
        Bettet die Frage ein, baut den Stage-1-Filter aus CAD-Metadaten auf und
        sucht in Qdrant. Wenn zu wenige Treffer gefunden werden, werden Range-Filter
        mit Faktor 1.5x und 2.0x gelockert.
        """
        query_embedding = self.embedder.embed([question])
        qvec = query_embedding.dense_vectors[0]
        qsparse = query_embedding.sparse_vectors[0] if query_embedding.sparse_vectors else None
        candidate_k = self.top_k
        if self.stage2_use_hybrid or self.reranker_enabled:
            candidate_k = max(self.top_k * self.reranker_candidate_multiplier, self.stage1_min_candidates)

        # Stage 1: Filter mit vollem Strict-Modus (relax_factor=1.0)
        filter0 = _build_stage1_filter(self.schema, cad_metadata, relax_factor=1.0)
        hits = self._search(qvec, qsparse, filter0 if self.stage1_strict else {}, candidate_k)

        # Relax-Mechanismus: Range-Grenzen schrittweise lockern wenn zu wenig gefunden
        if self.stage1_relax_on_empty and self.stage1_strict and len(hits) < self.stage1_min_candidates:
            for factor in (1.5, 2.0):
                filt = _build_stage1_filter(self.schema, cad_metadata, relax_factor=factor)
                hits = self._search(qvec, qsparse, filt, candidate_k)
                if len(hits) >= self.stage1_min_candidates or hits:
                    break

        if self.reranker_enabled and hits:
            hits = self._rerank(question, hits)

        return [
            RetrievedChunk(chunk=h.chunk, metadata=h.metadata, similarity=h.score)
            for h in hits[: self.top_k]
        ]

    def _search(
        self,
        qvec: list[float],
        qsparse: Optional[dict[str, float]],
        filter_dict: dict,
        candidate_k: int,
    ) -> list[SearchResult]:
        return self.store.search(
            qvec,
            filter=filter_dict,
            top_k=candidate_k,
            threshold=self.min_similarity,
            query_sparse_vector=qsparse,
            use_hybrid=self.stage2_use_hybrid,
            hybrid_dense_weight=self.hybrid_dense_weight,
            hybrid_sparse_weight=self.hybrid_sparse_weight,
        )

    @property
    def reranker(self):
        if self._reranker is None:
            if not self.reranker_model:
                raise ValueError("reranker_enabled=True requires reranker_model.")
            from sentence_transformers import CrossEncoder

            self._reranker = CrossEncoder(self.reranker_model)
        return self._reranker

    def _rerank(self, question: str, hits: list[SearchResult]) -> list[SearchResult]:
        pairs = [(question, h.chunk.text) for h in hits]
        scores = [float(s) for s in self.reranker.predict(pairs)]
        reranked = [
            SearchResult(
                chunk=h.chunk,
                metadata=h.metadata,
                dense_score=h.dense_score,
                sparse_score=h.sparse_score,
                score=score,
            )
            for h, score in zip(hits, scores)
        ]
        return sorted(reranked, key=lambda h: h.score, reverse=True)


def _build_stage1_filter(schema: MetadataSchema, cad: dict, *, relax_factor: float) -> dict:
    """
    Baut das interne Filter-Dict aus CAD-Parametern und Schema-Feldern auf.
    Nur Felder mit filter_type werden berücksichtigt; fehlende CAD-Werte erzeugen keine Bedingung.
    or_empty=True stellt sicher, dass Chunks ohne Metadatenfeld nicht ausgeschlossen werden.
    """
    must: list[dict] = []
    for field in schema.filter_fields:
        if field.filter_type == "exact":
            v = cad.get(field.name)
            if v is None:
                continue
            must.append({"key": f"metadata.{field.name}", "match": v, "or_empty": True})
        elif field.filter_type == "set":
            v = cad.get(field.name)
            if v is None:
                continue
            must.append({"key": f"metadata.{field.name}", "contains": v, "or_empty": True})
        elif field.filter_type == "range":
            _append_range_filter(must, field, cad, relax_factor=relax_factor)
    return {"must": must}


def _append_range_filter(must: list[dict], field: SchemaField, cad: dict, *, relax_factor: float) -> None:
    """
    Fügt zwei Range-Bedingungen hinzu: chunk_min <= cad_value * relax UND chunk_max >= cad_value / relax.
    relax_factor > 1.0 erweitert den akzeptierten Bereich – Sicherheitsnetz bei seltenen Parameterwerten.
    """
    cad_value = cad.get(field.name)
    if cad_value is None:
        return

    # Range-Felder aus Schema oder Konvention ({name}_min / {name}_max)
    if not field.range_fields or len(field.range_fields) != 2:
        min_key, max_key = f"{field.name}_min", f"{field.name}_max"
    else:
        min_key, max_key = field.range_fields

    hi = float(cad_value) * float(relax_factor)   # obere Grenze für chunk_min
    lo = float(cad_value) / float(relax_factor)   # untere Grenze für chunk_max
    must.append({"key": f"metadata.{min_key}", "range": {"lte": hi}, "or_empty": True})
    must.append({"key": f"metadata.{max_key}", "range": {"gte": lo}, "or_empty": True})
