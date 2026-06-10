"""
factory.py – Komponentenaufbau (Dependency Injection) aus der Konfiguration.

Einziger Ort im System, an dem konkrete Implementierungen instanziiert werden.
Der Embedder wird als geteilte Instanz an Chunker und Retriever übergeben –
beide müssen im identischen Vektorraum arbeiten.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import AppConfig
from app.core.interfaces import (
    AnswerGenerator,
    CADAdapter,
    Chunker,
    DocumentLoader,
    Embedder,
    MetadataExtractor,
    Retriever,
    VectorStore,
)
from app.implementations.answer_generator_ollama import OllamaAnswerGenerator
from app.implementations.cad_processor_client import CadProcessorClient
from app.implementations.cad_random_gear import RandomGearGenerator
from app.implementations.chunker_recursive import RecursiveTextChunker
from app.implementations.chunker_semantic import SemanticChunker
from app.implementations.embedder_bge_m3 import BGEM3Embedder
from app.implementations.metadata_extractor_ollama import OllamaMetadataExtractor
from app.implementations.pdf_loader_pymupdf import PDFLoader
from app.implementations.qdrant_store import QdrantStore
from app.implementations.retriever_two_stage import TwoStageRetriever


class Components:
    """Einfacher Container für alle aufgebauten Systemkomponenten. Wird in main.py als Singleton gehalten."""
    def __init__(
        self,
        *,
        loader: DocumentLoader,
        chunker: Chunker,
        embedder: Embedder,
        metadata_extractor: MetadataExtractor,
        cad_adapter: CADAdapter,
        vector_store: VectorStore,
        retriever: Retriever,
        answer_generator: AnswerGenerator,
    ) -> None:
        self.loader = loader
        self.chunker = chunker
        self.embedder = embedder
        self.metadata_extractor = metadata_extractor
        self.cad_adapter = cad_adapter
        self.vector_store = vector_store
        self.retriever = retriever
        self.answer_generator = answer_generator


def build_components(config: AppConfig, *, base_dir: Path) -> Components:
    """
    Baut alle Systemkomponenten aus der validierten Konfiguration auf.
    Die Reihenfolge folgt den Abhängigkeiten: Embedder vor Chunker und Retriever,
    da beide dieselbe Instanz teilen müssen.
    """

    # 1. PDF-Loader – keine Abhängigkeiten
    loader: DocumentLoader = PDFLoader()

    # 2. Embedder – EINZIGE Instanz für Chunker und Retriever (~10s Ladezeit bei Start)
    embedder: Embedder
    if config.embedder.implementation == "bge_m3":
        embedder = BGEM3Embedder(
            model_name=config.embedder.model_name,
            device=config.embedder.device,
            max_length=config.embedder.max_length,
            use_sparse=config.embedder.use_sparse,
            batch_size=config.embedder.batch_size,
        )
    else:
        raise ValueError(f"Unknown embedder implementation: {config.embedder.implementation}")

    # 3. Chunker – SemanticChunker braucht den Embedder für Kosinusähnlichkeit
    chunker: Chunker
    if config.chunker.implementation == "semantic":
        chunker = SemanticChunker(
            embedder=embedder,  # geteilte Instanz!
            threshold=config.chunker.threshold,
            min_chunk_tokens=config.chunker.min_chunk_size,
            max_chunk_tokens=config.chunker.max_chunk_size,
            overlap_sentences=config.chunker.overlap_sentences,
        )
    elif config.chunker.implementation == "recursive":
        chunker = RecursiveTextChunker(
            min_chunk_tokens=config.chunker.min_chunk_size,
            max_chunk_tokens=config.chunker.max_chunk_size,
            overlap_sentences=config.chunker.overlap_sentences,
        )
    else:
        raise ValueError(f"Unknown chunker implementation: {config.chunker.implementation}")

    # 4. Metadaten-Extraktor – HTTP-Verbindung zu Ollama
    if config.metadata_extractor.implementation == "llama_ollama":
        metadata_extractor: MetadataExtractor = OllamaMetadataExtractor(
            model_name=config.metadata_extractor.model_name,
            base_url=config.metadata_extractor.ollama_url,
            timeout_s=config.metadata_extractor.timeout_s,
            max_retries=config.metadata_extractor.max_retries,
        )
    else:
        raise ValueError(f"Unknown metadata_extractor: {config.metadata_extractor.implementation}")

    # 5. CAD-Adapter – Zufalls-Stub (Demo) oder HTTP-Client zum cad_processor-Service
    cad_adapter: CADAdapter
    if config.cad_adapter.implementation == "random_gear_stub":
        cad_adapter = RandomGearGenerator()
    elif config.cad_adapter.implementation == "cad_processor_http":
        cad_adapter = CadProcessorClient(
            url=config.cad_adapter.url,
            timeout_s=config.cad_adapter.timeout_s,
        )
    else:
        raise ValueError(f"Unknown cad_adapter: {config.cad_adapter.implementation}")

    # 6. Vektordatenbank – HTTP-Verbindung zu Qdrant
    if config.vector_store.implementation == "qdrant":
        vector_store: VectorStore = QdrantStore(
            host=config.vector_store.host,
            port=config.vector_store.port,
            collection_name=config.vector_store.collection_name,
        )
    else:
        raise ValueError(f"Unknown vector_store: {config.vector_store.implementation}")

    # 7. Retriever – bekommt dieselbe embedder-Instanz wie der Chunker
    retriever: Retriever = TwoStageRetriever(
        embedder=embedder,  # geteilte Instanz – gleicher Vektorraum!
        store=vector_store,
        schema_path=(base_dir / config.domain.schema_path),
        stage1_strict=config.retriever.stage1_strict,
        stage1_relax_on_empty=config.retriever.stage1_relax_on_empty,
        stage1_min_candidates=config.retriever.stage1_min_candidates,
        top_k=config.retriever.stage2_top_k,
        min_similarity=config.retriever.stage2_min_similarity,
        stage2_use_hybrid=config.retriever.stage2_use_hybrid,
        hybrid_dense_weight=config.retriever.hybrid_dense_weight,
        hybrid_sparse_weight=config.retriever.hybrid_sparse_weight,
        reranker_enabled=config.retriever.reranker_enabled,
        reranker_model=config.retriever.reranker_model,
    )

    # 8. Antwortgenerator – HTTP-Verbindung zu Ollama (kann anderes Modell als Extraktor)
    if config.answer_generator.implementation == "llama_ollama":
        answer_generator: AnswerGenerator = OllamaAnswerGenerator(
            model_name=config.answer_generator.model_name,
            base_url=config.metadata_extractor.ollama_url,
            timeout_s=config.metadata_extractor.timeout_s,
            prompt_path=(base_dir / config.domain.prompt_path),
            domain_name=config.domain.name,
            max_tokens=config.answer_generator.max_tokens,
            temperature=config.answer_generator.temperature,
        )
    else:
        raise ValueError(f"Unknown answer_generator: {config.answer_generator.implementation}")

    return Components(
        loader=loader,
        chunker=chunker,
        embedder=embedder,
        metadata_extractor=metadata_extractor,
        cad_adapter=cad_adapter,
        vector_store=vector_store,
        retriever=retriever,
        answer_generator=answer_generator,
    )
