"""
config.py – Typisierte Konfigurationsmodelle für config.yaml.

Jede Klasse bildet einen Abschnitt der YAML-Datei ab und wird beim Start
durch Pydantic validiert. Fehler (z.B. unbekannte device-Werte) werden
frühzeitig abgefangen, nicht erst zur Laufzeit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field


class DomainConfig(BaseModel):
    """Domänenspezifische Konfiguration – ändert sich beim Wechsel auf eine neue Fachdomäne (z.B. Lager)."""
    name: str           # Anzeigename, wird als {DOMAIN} in den LLM-Prompt eingesetzt
    schema_path: str    # Pfad zur Metadaten-Schema-YAML (z.B. "schemas/gears.yaml")
    prompt_path: str    # Pfad zum Antwort-Prompt-Template


class EmbedderConfig(BaseModel):
    """
    Konfiguration des Embedding-Modells. Ein Wechsel erfordert Neuindizierung,
    da alte Qdrant-Vektoren im anderen Vektorraum liegen würden.
    """
    implementation: Literal["bge_m3"]
    model_name: str
    device: Literal["cuda", "cpu", "mps"] = "cpu"
    use_sparse: bool = True
    max_length: int = 8192


class ChunkerConfig(BaseModel):
    """Wählt die Chunking-Strategie und deren Parameter. "semantic" = präziser, "recursive" = schneller."""
    implementation: Literal["semantic", "recursive"] = "semantic"
    threshold: float = 0.75       # nur für SemanticChunker: Ähnlichkeitsschwelle
    min_chunk_size: int = 100
    max_chunk_size: int = 512
    overlap_sentences: int = 1


class MetadataExtractorConfig(BaseModel):
    """Konfiguration des LLM-Aufrufs für die Metadatenextraktion pro Chunk."""
    implementation: Literal["llama_ollama"]
    model_name: str
    ollama_url: str = "http://localhost:11434"
    max_retries: int = 3
    timeout_s: int = 30


class CADAdapterConfig(BaseModel):
    """Wählt den CAD-Adapter. "random_gear_stub" generiert Zufallsdaten; zukünftig: "pythonocc"."""
    implementation: Literal["random_gear_stub"]


class VectorStoreConfig(BaseModel):
    """Verbindungsparameter für die Qdrant-Vektordatenbank."""
    implementation: Literal["qdrant"]
    host: str = "localhost"
    port: int = 6333
    collection_name: str = "knowledge_base"


class RetrieverConfig(BaseModel):
    """
    Steuert den zweistufigen Retriever: Stage-1-Filter (Metadaten) und Stage-2-Vektorsuche.
    stage1_relax_on_empty lockert Range-Filter schrittweise wenn zu wenige Treffer gefunden werden.
    """
    stage1_strict: bool = True
    stage1_relax_on_empty: bool = True
    stage1_min_candidates: int = 5     # unter diesem Wert wird der Filter gelockert
    stage2_top_k: int = 5
    stage2_min_similarity: float = 0.65
    stage2_use_hybrid: bool = True
    hybrid_dense_weight: float = 0.7
    hybrid_sparse_weight: float = 0.3
    reranker_enabled: bool = False
    reranker_model: Optional[str] = None


class AnswerGeneratorConfig(BaseModel):
    """Konfiguration des LLM-Aufrufs für die Antwortgenerierung."""
    implementation: Literal["llama_ollama"]
    model_name: str
    max_tokens: int = 800
    temperature: float = 0.2  # niedrig = faktenorientiert, deterministisch


class FrontendConfig(BaseModel):
    """Konfiguration des HTML-Frontends (alle Felder haben Standardwerte)."""
    default_question_fields: int = 3
    max_question_fields: int = 6
    show_metadata_panel: bool = True


class AppConfig(BaseModel):
    """Wurzel-Konfigurationsmodell – bildet die gesamte config.yaml ab."""
    domain: DomainConfig
    embedder: EmbedderConfig
    chunker: ChunkerConfig
    metadata_extractor: MetadataExtractorConfig
    cad_adapter: CADAdapterConfig
    vector_store: VectorStoreConfig
    retriever: RetrieverConfig
    answer_generator: AnswerGeneratorConfig
    frontend: FrontendConfig = Field(default_factory=FrontendConfig)


def load_config(path: Path) -> AppConfig:
    """
    Liest die YAML-Datei und validiert sie gegen AppConfig.
    yaml.safe_load verhindert Ausführung von Code in der YAML-Datei.
    Pydantic wirft ValidationError mit klarer Fehlermeldung bei ungültigen Werten.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(raw)
