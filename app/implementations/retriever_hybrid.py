"""
retriever_hybrid.py – Einstufiger Hybrid-Retriever (Dense + lexikalisch Sparse).

Bettet die Suchanfrage ein und sucht in Qdrant die semantisch ähnlichsten Chunks
via Kosinus-Ähnlichkeit. Bei use_hybrid=True wird der Dense-Score mit einem
lexikalischen Sparse-Score (Bag-of-words) gewichtet kombiniert – das verbessert
Treffer für Normnummern, Werkstoffbezeichnungen und technische Kurzbegriffe.

Das Retrieval arbeitet ausschließlich mit der Nutzerfrage. Die CAD-Parameter
fließen erst in der Antwortstufe (OllamaAnswerGenerator) als Kontext ein.
"""

from __future__ import annotations

from typing import Callable, Optional

from app.core.interfaces import Embedder, VectorStore
from app.core.types import RetrievedChunk

ProgressCallback = Callable[[str], None]


class HybridRetriever:
    """Semantische Vektorsuche mit optionalem Hybrid-Scoring. Zustandslos bis auf injizierte Komponenten."""

    def __init__(
        self,
        *,
        embedder: Embedder,
        store: VectorStore,
        top_k: int,
        min_similarity: float,
        use_hybrid: bool = True,
        hybrid_dense_weight: float = 0.7,
        hybrid_sparse_weight: float = 0.3,
        candidate_multiplier: int = 8,
    ) -> None:
        """
        embedder muss dieselbe Instanz wie beim Indexieren sein (gleicher Vektorraum).
        candidate_multiplier: bei Hybrid-Suche werden top_k * multiplier Dense-Kandidaten
        geholt, lokal mit Sparse-Scores nachsortiert und auf top_k gekürzt.
        """
        self.embedder = embedder
        self.store = store
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.use_hybrid = use_hybrid
        self.hybrid_dense_weight = hybrid_dense_weight
        self.hybrid_sparse_weight = hybrid_sparse_weight
        self.candidate_multiplier = max(1, candidate_multiplier)

    def retrieve(self, question: str, progress_callback: Optional[ProgressCallback] = None) -> list[RetrievedChunk]:
        """Bettet die Suchanfrage ein und gibt die top_k ähnlichsten Chunks zurück."""
        if progress_callback:
            progress_callback("embedding_start")
        embedding = self.embedder.embed([question])
        if progress_callback:
            progress_callback("embedding_done")
        qvec = embedding.dense_vectors[0]
        qsparse = embedding.sparse_vectors[0] if embedding.sparse_vectors else None

        candidate_k = self.top_k * self.candidate_multiplier if self.use_hybrid else self.top_k

        if progress_callback:
            progress_callback("search_start")
        hits = self.store.search(
            qvec,
            top_k=candidate_k,
            threshold=self.min_similarity,
            query_sparse_vector=qsparse,
            use_hybrid=self.use_hybrid,
            hybrid_dense_weight=self.hybrid_dense_weight,
            hybrid_sparse_weight=self.hybrid_sparse_weight,
        )
        if progress_callback:
            progress_callback("search_done")

        return [
            RetrievedChunk(chunk=h.chunk, metadata=h.metadata, similarity=h.score)
            for h in hits[: self.top_k]
        ]
