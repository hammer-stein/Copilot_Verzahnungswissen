"""
types.py – Gemeinsame Datenstrukturen für die gesamte Pipeline.

Definiert alle Datencontainer, die zwischen den Komponenten ausgetauscht werden –
von der PDF-Datei bis zur fertigen Antwort. Alle Klassen sind frozen dataclasses
(unveränderlich) für Thread-Sicherheit bei parallelen Anfragen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Indexierungs-Datenstrukturen (Weg: PDF → Qdrant)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RawDocumentPage:
    """Einzelne Seite eines geladenen Dokuments. Erzeugt von PDFLoader, verarbeitet vom Chunker."""
    page_number: int  # 1-basiert
    text: str


@dataclass(frozen=True)
class RawDocument:
    """Vollständig geladenes Dokument mit allen Seiten. doc_hash dient als stabiler Dokumentenidentifikator."""
    source_path: str
    doc_hash: str   # SHA-256 der Datei – ermöglicht Deduplikation und Löschung
    pages: list[RawDocumentPage]


@dataclass(frozen=True)
class Chunk:
    """
    Einzelnes Textsegment aus einem Dokument. Atomare Wissenseinheit des Systems.
    Trägt Herkunftsinformationen (source_path, page_number, doc_hash) die bis in die Antwort erhalten bleiben.
    """
    text: str
    source_path: str
    page_number: int   # 1-basiert
    position: int      # monoton steigend innerhalb eines Dokuments
    doc_hash: str


@dataclass(frozen=True)
class EmbeddingResult:
    """Ergebnis eines Embedder-Aufrufs. dense_vectors[i] entspricht texts[i] des Eingabe-Batches."""
    dense_vectors: list[list[float]]
    sparse_vectors: Optional[list[dict[str, Any]]] = None  # aktuell nicht genutzt


@dataclass(frozen=True)
class EmbeddedChunk:
    """Chunk angereichert mit Embedding-Vektor und LLM-extrahierten Metadaten. Wird in Qdrant gespeichert."""
    chunk: Chunk
    dense_vector: list[float]
    sparse_vector: Optional[dict[str, Any]]
    metadata: dict[str, Any]  # z.B. {"verzahnungstyp": "Stirnrad", "modul_min": 2.0}


# ---------------------------------------------------------------------------
# Retrieval-Datenstrukturen (Weg: Frage → Antwort)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SearchResult:
    """Einzelnes Ergebnis aus Qdrant-Suche. Enthält rekonstruierten Chunk und Ähnlichkeits-Score."""
    chunk: Chunk
    metadata: dict[str, Any]
    dense_score: Optional[float]
    sparse_score: Optional[float]
    score: float  # finaler Score (aktuell = dense_score)


@dataclass(frozen=True)
class RetrievedChunk:
    """Vom Retriever ausgewählter Chunk, bereit für den AnswerGenerator."""
    chunk: Chunk
    metadata: dict[str, Any]
    similarity: float  # Kosinus-Ähnlichkeit zur Frage (0.0–1.0)


@dataclass(frozen=True)
class DocumentInfo:
    """Zusammenfassung eines indizierten Dokuments. Wird von GET /documents für das Frontend geliefert."""
    source_path: str
    doc_hash: str      # dient als Lösch-ID: DELETE /documents/{doc_hash}
    chunk_count: int
    file_name: str = ""  # ursprünglicher Dateiname (für die Anzeige in der UI)
    folder: str = ""     # Ordner zur Organisation der Wissensbasis ("" = kein Ordner)


# ---------------------------------------------------------------------------
# Ausgabe-Typen
# ---------------------------------------------------------------------------

class AnswerSource(TypedDict):
    """Eine Quellenangabe innerhalb einer Antwort. Referenziert via qid ([Q1], [Q2], ...) im Antworttext."""
    qid: str
    doc_hash: str
    source_path: str
    title: str
    page_number: int
    similarity: float
    text: str


class Answer(TypedDict):
    """Vollständige Antwort auf eine Frage. Erzeugt vom AnswerGenerator, direkt als JSON serialisiert."""
    question: str
    answer_text: str   # enthält Inline-Quellenverweise [Q1], [Q2], ...
    sources: list[AnswerSource]
