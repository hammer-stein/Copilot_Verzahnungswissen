"""
interfaces.py – Abstrakte Schnittstellen (Protocols) für alle Systemkomponenten.

Definiert den Vertrag zwischen Pipeline-Logik und konkreten Implementierungen via
Python Protocol (PEP 544). Eine Klasse muss nicht explizit erben – es reicht,
die richtige Methode zu haben (structural subtyping / Duck Typing mit Typprüfung).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Protocol

from app.core.types import (
    Answer,
    Chunk,
    DocumentInfo,
    EmbeddedChunk,
    EmbeddingResult,
    RawDocument,
    RetrievedChunk,
    SearchResult,
)


class DocumentLoader(Protocol):
    """Liest eine Datei und gibt ein RawDocument zurück. Aktuelle Impl.: PDFLoader."""
    def load(self, file_path: Path) -> RawDocument: ...


class Chunker(Protocol):
    """Teilt ein RawDocument in Textsegmente (Chunks) auf. Impls.: SemanticChunker, RecursiveTextChunker."""
    def chunk(self, document: RawDocument) -> list[Chunk]: ...


class Embedder(Protocol):
    """
    Wandelt Texte in L2-normalisierte Vektoren um. Aktuelle Impl.: BGEM3Embedder.
    WICHTIG: Dieselbe Instanz muss für Indexierung UND Retrieval genutzt werden,
    damit Chunks und Fragen im gleichen Vektorraum liegen.
    """
    def embed(self, texts: list[str]) -> EmbeddingResult: ...


class CADAdapter(Protocol):
    """
    Liefert das vollständige GearParameters-JSON (Format: cad_processor/src/output_schema.py).
    Impls.: SyntheticCadJsonAdapter (Testdatensätze), CadProcessorClient (echte STEP-Analyse).
    """
    def extract(self, file_path: Optional[Path]) -> dict: ...


class VectorStore(Protocol):
    """Speichert, sucht und verwaltet EmbeddedChunks in einer Vektordatenbank. Aktuelle Impl.: QdrantStore."""
    def upsert(self, chunks: list[EmbeddedChunk]) -> None: ...

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        threshold: float,
        query_sparse_vector: Optional[dict] = None,
        use_hybrid: bool = False,
        hybrid_dense_weight: float = 0.7,
        hybrid_sparse_weight: float = 0.3,
    ) -> list[SearchResult]: ...

    def delete_by_doc_hash(self, doc_hash: str) -> None: ...

    def set_document_folder(self, doc_hash: str, folder: str) -> None: ...

    def set_document_title(self, doc_hash: str, title: str) -> None: ...

    def list_documents(self) -> list[DocumentInfo]: ...


ProgressCallback = Callable[[str], None]


class Retriever(Protocol):
    """Findet relevante Chunks für die Nutzerfrage. Aktuelle Impl.: HybridRetriever."""
    def retrieve(self, question: str, progress_callback: Optional[ProgressCallback] = None) -> list[RetrievedChunk]: ...


class AnswerGenerator(Protocol):
    """Generiert eine Antwort aus Frage + Chunks + CAD-Kontext via LLM. Aktuelle Impl.: OllamaAnswerGenerator."""
    def generate(
        self,
        *,
        question: str,
        chunks: list[RetrievedChunk],
        cad_metadata: dict,
        answer_format: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Answer: ...
