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
    Retriever,
    VectorStore,
)

# Hinweis: Die konkreten Implementierungen werden bewusst NICHT hier auf Modulebene
# importiert, sondern lazy in build_components(). So zieht ein Import von factory
# (z.B. durch Tests oder ASGI-Tooling) nicht die schweren Abhängigkeiten
# (sentence-transformers/torch, qdrant-client, pymupdf) nach sich, solange die
# Komponenten nicht tatsächlich gebaut werden.


class Components:
    """Einfacher Container für alle aufgebauten Systemkomponenten. Wird in main.py als Singleton gehalten."""
    def __init__(
        self,
        *,
        loader: DocumentLoader,
        chunker: Chunker,
        embedder: Embedder,
        cad_adapter: CADAdapter,
        synthetic_cad_adapter: CADAdapter,
        vector_store: VectorStore,
        retriever: Retriever,
        answer_generator: AnswerGenerator,
    ) -> None:
        self.loader = loader
        self.chunker = chunker
        self.embedder = embedder
        self.cad_adapter = cad_adapter
        self.synthetic_cad_adapter = synthetic_cad_adapter
        self.vector_store = vector_store
        self.retriever = retriever
        self.answer_generator = answer_generator


def build_components(config: AppConfig, *, base_dir: Path) -> Components:
    """
    Baut alle Systemkomponenten aus der validierten Konfiguration auf.
    Die Reihenfolge folgt den Abhängigkeiten: Embedder vor Chunker und Retriever,
    da beide dieselbe Instanz teilen müssen.
    """

    # Lazy-Importe: erst hier werden die schweren Abhängigkeiten geladen.
    from app.implementations.answer_generator_ollama import OllamaAnswerGenerator
    from app.implementations.cad_processor_client import CadProcessorClient
    from app.implementations.cad_processor_local import LocalCadProcessorAdapter
    from app.implementations.cad_synthetic_json import SyntheticCadJsonAdapter
    from app.implementations.chunker_recursive import RecursiveTextChunker
    from app.implementations.chunker_semantic import SemanticChunker
    from app.implementations.embedder_bge_m3 import BGEM3Embedder
    from app.implementations.pdf_loader_pymupdf import PDFLoader
    from app.implementations.qdrant_store import QdrantStore
    from app.implementations.retriever_hybrid import HybridRetriever

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

    # 4. CAD-Adapter – Schalter: synthetische Test-JSONs oder echter cad_processor-Service.
    #    Der Synthetik-Adapter wird immer mit aufgebaut, damit GET /cad/random
    #    unabhängig vom konfigurierten Hauptadapter Beispieldaten liefern kann.
    synthetic_cad_adapter = SyntheticCadJsonAdapter(
        data_dir=base_dir / config.cad_adapter.synthetic_data_dir,
    )
    cad_adapter: CADAdapter
    if config.cad_adapter.implementation == "synthetic_json":
        cad_adapter = synthetic_cad_adapter
    elif config.cad_adapter.implementation == "cad_processor_local":
        local_adapter = LocalCadProcessorAdapter(
            cad_processor_dir=base_dir / "cad_processor",
        )
        local_adapter.validate_available()
        cad_adapter = local_adapter
    elif config.cad_adapter.implementation == "cad_processor_http":
        cad_adapter = CadProcessorClient(
            url=config.cad_adapter.url,
            timeout_s=config.cad_adapter.timeout_s,
        )
    else:
        raise ValueError(f"Unknown cad_adapter: {config.cad_adapter.implementation}")

    # 5. Vektordatenbank – HTTP-Verbindung zu Qdrant
    if config.vector_store.implementation == "qdrant":
        vector_store: VectorStore = QdrantStore(
            host=config.vector_store.host,
            port=config.vector_store.port,
            collection_name=config.vector_store.collection_name,
            path=config.vector_store.path,
        )
    else:
        raise ValueError(f"Unknown vector_store: {config.vector_store.implementation}")

    # 6. Retriever – bekommt dieselbe embedder-Instanz wie der Chunker
    retriever: Retriever = HybridRetriever(
        embedder=embedder,  # geteilte Instanz – gleicher Vektorraum!
        store=vector_store,
        top_k=config.retriever.top_k,
        min_similarity=config.retriever.min_similarity,
        use_hybrid=config.retriever.use_hybrid,
        hybrid_dense_weight=config.retriever.hybrid_dense_weight,
        hybrid_sparse_weight=config.retriever.hybrid_sparse_weight,
        candidate_multiplier=config.retriever.candidate_multiplier,
    )

    # 7. Antwortgenerator – HTTP-Verbindung zu Ollama
    ag = config.answer_generator
    # Single-Pass-Generator IMMER bauen: er ist entweder die Antwortstrategie selbst oder dient
    # dem Multi-Agenten-Generator als robuster Fallback (garantierte Mindest-Antwortqualität).
    single_pass = OllamaAnswerGenerator(
        model_name=ag.model_name,
        base_url=ag.ollama_url,
        timeout_s=ag.timeout_s,
        prompt_path=(base_dir / config.domain.prompt_path),
        domain_name=config.domain.name,
        max_tokens=ag.max_tokens,
        temperature=ag.temperature,
    )

    if ag.implementation == "llama_ollama":
        answer_generator: AnswerGenerator = single_pass
    elif ag.implementation == "multi_agent":
        # Lazy-Importe analog zu oben: nur laden, wenn der Multi-Agenten-Modus aktiv ist.
        from app.implementations.answer_generator_multiagent import MultiAgentAnswerGenerator
        from app.implementations.ollama_client import OllamaClient
        from app.pipeline.agents.reviewer import ReviewerAgent
        from app.pipeline.agents.solver import SolverAgent

        client = OllamaClient(base_url=ag.ollama_url, timeout_s=ag.timeout_s)
        solver = SolverAgent(
            client=client,
            model_name=ag.model_name,
            prompt_path=(base_dir / ag.solver_prompt_path),
            domain_name=config.domain.name,
            max_tokens=ag.max_tokens,
            temperature=ag.temperature,
        )
        reviewer = ReviewerAgent(
            client=client,
            model_name=ag.model_name,
            prompt_path=(base_dir / ag.reviewer_prompt_path),
            domain_name=config.domain.name,
            max_tokens=ag.max_tokens,
            temperature=ag.review_temperature,  # streng/deterministisch
        )
        answer_generator = MultiAgentAnswerGenerator(
            solver=solver,
            reviewer=reviewer,
            fallback_generator=single_pass,
            enable_review=ag.enable_review,
            max_revisions=ag.max_revisions,
        )
    else:
        raise ValueError(f"Unknown answer_generator: {config.answer_generator.implementation}")

    return Components(
        loader=loader,
        chunker=chunker,
        embedder=embedder,
        cad_adapter=cad_adapter,
        synthetic_cad_adapter=synthetic_cad_adapter,
        vector_store=vector_store,
        retriever=retriever,
        answer_generator=answer_generator,
    )
