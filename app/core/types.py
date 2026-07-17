"""
types.py – Gemeinsame Datenstrukturen für die gesamte Pipeline.

Definiert alle Datencontainer, die zwischen den Komponenten ausgetauscht werden –
von der Datei bis zur fertigen Antwort. Alle Klassen sind frozen dataclasses
(unveränderlich) für Thread-Sicherheit bei parallelen Anfragen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from typing_extensions import NotRequired, TypedDict


# ---------------------------------------------------------------------------
# Indexierungs-Datenstrukturen (Weg: Dokument → Qdrant)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RawDocumentPage:
    """Einzelne Seite eines geladenen Dokuments. Erzeugt von Loader, verarbeitet vom Chunker."""
    page_number: int  # 1-basiert
    text: str


@dataclass(frozen=True)
class RawDocument:
    """Vollständig geladenes Dokument mit allen Seiten. doc_hash ist der Identifikator."""
    source_path: str
    doc_hash: str   # SHA-256 der Datei – ermöglicht Deduplikation und Löschung
    pages: list[RawDocumentPage]
    doc_kind: str = "text"  # "text" (PDF/Fließtext) | "table" (CSV/Excel – 1 Zeile = 1 Datensatz)


@dataclass(frozen=True)
class Chunk:
    """Einzelnes Textsegment aus einem Dokument."""
    text: str
    source_path: str
    page_number: int
    position: int
    doc_hash: str


@dataclass(frozen=True)
class EmbeddingResult:
    """Ergebnis eines Embedder-Aufrufs."""
    dense_vectors: list[list[float]]
    sparse_vectors: Optional[list[dict[str, Any]]] = None


@dataclass(frozen=True)
class EmbeddedChunk:
    """Chunk angereichert mit Embedding-Vektor und Metadaten. Wird in Qdrant gespeichert."""
    chunk: Chunk
    dense_vector: list[float]
    sparse_vector: Optional[dict[str, Any]]
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Retrieval-Datenstrukturen
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SearchResult:
    """Einzelnes Ergebnis aus Qdrant-Suche."""
    chunk: Chunk
    metadata: dict[str, Any]
    dense_score: Optional[float]
    sparse_score: Optional[float]
    score: float


@dataclass(frozen=True)
class RetrievedChunk:
    """Vom Retriever ausgewählter Chunk, bereit für den AnswerGenerator."""
    chunk: Chunk
    metadata: dict[str, Any]
    similarity: float


@dataclass(frozen=True)
class DocumentInfo:
    """Zusammenfassung eines indizierten Dokuments für das Frontend."""
    source_path: str
    doc_hash: str
    chunk_count: int
    file_name: str = ""
    folder: str = ""


# ---------------------------------------------------------------------------
# Ausgabe-Typen
# ---------------------------------------------------------------------------

class AnswerSource(TypedDict):
    qid: str
    doc_hash: str
    source_path: str
    title: str
    page_number: int
    similarity: float
    text: str


class AgentStep(TypedDict):
    agent: str
    title: str
    content: str
    status: NotRequired[str]


class ReviewSummary(TypedDict):
    status: str
    summary: str
    issues: NotRequired[list[str]]


class Answer(TypedDict):
    question: str
    answer_text: str
    sources: list[AnswerSource]
    agent_trace: NotRequired[list[AgentStep]]
    review: NotRequired[ReviewSummary]
    # Zitier-Transparenz: abgerufene vs. tatsächlich zitierte Quellen (app/api/main.py)
    citation_stats: NotRequired[dict]