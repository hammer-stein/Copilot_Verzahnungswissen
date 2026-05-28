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
from app.core.types import RetrievedChunk


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
        qvec = self.embedder.embed([question]).dense_vectors[0]

        # Stage 1: Filter mit vollem Strict-Modus (relax_factor=1.0)
        filter0 = _build_stage1_filter(self.schema, cad_metadata, relax_factor=1.0)
        hits = self.store.search(
            qvec,
            filter=filter0 if self.stage1_strict else {},  # stage1_strict=False = nur Vektorsuche
            top_k=self.top_k,
            threshold=self.min_similarity,
        )

        # Relax-Mechanismus: Range-Grenzen schrittweise lockern wenn zu wenig gefunden
        if self.stage1_relax_on_empty and self.stage1_strict and len(hits) < self.stage1_min_candidates:
            for factor in (1.5, 2.0):
                filt = _build_stage1_filter(self.schema, cad_metadata, relax_factor=factor)
                hits = self.store.search(qvec, filter=filt, top_k=self.top_k, threshold=self.min_similarity)
                if len(hits) >= self.stage1_min_candidates or hits:
                    break

        return [
            RetrievedChunk(chunk=h.chunk, metadata=h.metadata, similarity=h.score)
            for h in hits
        ]


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
