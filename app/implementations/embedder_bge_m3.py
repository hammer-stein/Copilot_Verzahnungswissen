"""
embedder_bge_m3.py – Dense-Embedding mit BAAI/bge-m3 via sentence-transformers.

Implementiert das Embedder-Protokoll. Wird als EINZIGE Instanz sowohl beim Indexieren
(Chunks → Vektoren) als auch beim Retrieval (Frage → Vektor) verwendet, damit
beide im gleichen Vektorraum liegen.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from sentence_transformers import SentenceTransformer

from app.core.types import EmbeddingResult


class BGEM3Embedder:
    """Dense-Embedding-Wrapper für BAAI/bge-m3. Unterstützt CUDA, MPS (Apple Silicon) und CPU."""

    def __init__(
        self,
        *,
        model_name: str,
        device: str,
        max_length: int,
        use_sparse: bool,
        batch_size: int = 4,
    ) -> None:
        """
        Lädt das Modell in den Speicher – teuerste Operation beim Start (~5–15 Sekunden).
        use_sparse erzeugt zusätzlich einfache lexikalische Sparse-Vektoren für Hybrid-Search.
        """
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self.use_sparse = use_sparse
        self.batch_size = batch_size

        self._model = SentenceTransformer(model_name, device=device)  # lädt aus ~/.cache/huggingface/
        try:
            self._model.max_seq_length = max_length  # best-effort: nicht alle Backends unterstützen das
        except Exception:
            pass

    def embed(self, texts: list[str]) -> EmbeddingResult:
        """
        Wandelt eine Liste von Texten in L2-normalisierte Dense-Vektoren um (Batch-Verarbeitung).
        normalize_embeddings=True stellt sicher, dass die Kosinus-Ähnlichkeit in Qdrant korrekt ist.
        """
        vectors = self._model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,   # L2-Normalisierung: cosine(a,b) = a·b
            convert_to_numpy=False,       # PyTorch-Tensoren behalten
            show_progress_bar=False,
        )
        # Tensor → list[float] für JSON-Serialisierbarkeit und Qdrant-Kompatibilität
        dense_vectors: list[list[float]] = [list(map(float, v)) for v in vectors]
        sparse_vectors = [_lexical_sparse_vector(t) for t in texts] if self.use_sparse else None
        return EmbeddingResult(dense_vectors=dense_vectors, sparse_vectors=sparse_vectors)


_token_re = re.compile(r"[A-Za-zÄÖÜäöüß0-9_+-]+")


def _lexical_sparse_vector(text: str) -> dict[str, float]:
    """
    Erzeugt einen L2-normalisierten Bag-of-words-Vektor.
    Das ist keine echte BGE-M3-Sparse-Ausgabe, aber ein robuster lexikalischer Kanal
    für Normnummern, Werkstoffnamen und technische Kurzbegriffe ohne zusätzliche Dependencies.
    """
    tokens = [t.casefold() for t in _token_re.findall(text or "") if len(t) > 1]
    if not tokens:
        return {}

    counts = Counter(tokens)
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {term: float(count / norm) for term, count in counts.items()}
