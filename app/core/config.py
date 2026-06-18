"""
config.py – Typisierte Konfigurationsmodelle für config.yaml.

Jede Klasse bildet einen Abschnitt der YAML-Datei ab und wird beim Start
durch Pydantic validiert. Fehler (z.B. unbekannte device-Werte) werden
frühzeitig abgefangen, nicht erst zur Laufzeit.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field


class DomainConfig(BaseModel):
    """Domänenspezifische Konfiguration – ändert sich beim Wechsel auf eine neue Fachdomäne (z.B. Lager)."""
    name: str           # Anzeigename, wird als {DOMAIN} in den LLM-Prompt eingesetzt
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
    batch_size: int = Field(default=4, ge=1)


class ChunkerConfig(BaseModel):
    """Wählt die Chunking-Strategie und deren Parameter. "semantic" = präziser, "recursive" = schneller."""
    implementation: Literal["semantic", "recursive"] = "semantic"
    threshold: float = 0.75       # nur für SemanticChunker: Ähnlichkeitsschwelle
    min_chunk_size: int = 100
    max_chunk_size: int = 512
    overlap_sentences: int = 1


class CADAdapterConfig(BaseModel):
    """
    Wählt die CAD-Datenquelle (Schalter synthetisch/echt):
    "synthetic_json"     = liest die synthetischen Testdatensätze aus synthetic_data_dir
    "cad_processor_http" = sendet STEP-Dateien an den cad_processor-Service (Port 8001)
    """
    implementation: Literal["synthetic_json", "cad_processor_http"]
    url: str = "http://localhost:8001"
    timeout_s: int = 120
    synthetic_data_dir: str = "test_verzahnung/cad_testdaten"


class VectorStoreConfig(BaseModel):
    """
    Verbindungsparameter für die Qdrant-Vektordatenbank.
    Ist `path` gesetzt, läuft Qdrant eingebettet (lokaler On-Disk-Modus, kein Docker/Server nötig);
    andernfalls wird per host/port mit einem laufenden Qdrant-Server verbunden.
    """
    implementation: Literal["qdrant"]
    host: str = "localhost"
    port: int = 6333
    path: Optional[str] = None  # z.B. "storage/qdrant" → eingebetteter Modus ohne Server
    collection_name: str = "knowledge_base"


class RetrieverConfig(BaseModel):
    """
    Steuert den Hybrid-Retriever: Dense-Vektorsuche, optional kombiniert mit
    lexikalischen Sparse-Scores (use_hybrid). candidate_multiplier bestimmt,
    wie viele Dense-Kandidaten vor dem Sparse-Reranking geholt werden.
    """
    top_k: int = 5
    min_similarity: float = 0.5
    use_hybrid: bool = True
    hybrid_dense_weight: float = 0.7
    hybrid_sparse_weight: float = 0.3
    candidate_multiplier: int = Field(default=8, ge=1)


class AnswerGeneratorConfig(BaseModel):
    """
    Konfiguration der Antwortgenerierung.

    implementation schaltet zwischen zwei Strategien (beide nutzen denselben Ollama-Server):
    "llama_ollama" = klassischer Single-Pass (ein LLM-Call).
    "multi_agent"  = leichtgewichtiger Fluss Orchestrator → Solver → Reviewer mit prüfbarem
                     Lösungsweg (agent_trace). Fällt bei Fehlern automatisch auf den Single-Pass zurück.
    """
    implementation: Literal["llama_ollama", "multi_agent"]
    model_name: str
    ollama_url: str = "http://localhost:11434"
    timeout_s: int = 120
    max_tokens: int = 800
    temperature: float = 0.2  # niedrig = faktenorientiert, deterministisch

    # --- nur für implementation == "multi_agent" relevant (Defaults halten bestehende config.yaml gültig) ---
    solver_prompt_path: str = "prompts/solver_prompt.txt"      # Prompt-Template des Lösungs-Agenten
    reviewer_prompt_path: str = "prompts/reviewer_prompt.txt"  # Prompt-Template des Review-Agenten
    enable_review: bool = True        # Review-Schritt aktiv (False = nur Solver, 1 LLM-Call)
    max_revisions: int = Field(default=1, ge=0)  # max. Solver-Revisionen, wenn der Reviewer ohne Korrektur beanstandet
    review_temperature: float = 0.0   # Reviewer streng/deterministisch


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
    Umgebungsvariablen überschreiben die Service-Adressen (für Docker Compose,
    wo Services über ihre Container-Namen statt localhost erreichbar sind).
    Dieselbe config.yaml funktioniert dadurch lokal (eingebettetes Qdrant + CAD-Stub)
    und im Compose-Netz (echter Qdrant-Server + cad_processor-Service):
    Sind die Service-Env-Variablen gesetzt, wird automatisch auf den Server-/Service-Modus
    umgeschaltet – auch wenn die Datei lokale Defaults (path, random_gear_stub) enthält.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    if os.getenv("QDRANT_HOST"):
        vs = raw.setdefault("vector_store", {})
        vs["host"] = os.environ["QDRANT_HOST"]
        vs["path"] = None  # Server-Modus erzwingen: eingebetteten On-Disk-Modus deaktivieren
        if os.getenv("QDRANT_PORT"):
            vs["port"] = int(os.environ["QDRANT_PORT"])
    if os.getenv("CAD_PROCESSOR_URL"):
        cad = raw.setdefault("cad_adapter", {})
        cad["url"] = os.environ["CAD_PROCESSOR_URL"]
        cad["implementation"] = "cad_processor_http"  # echten CAD-Service statt Stub nutzen
    if os.getenv("OLLAMA_URL"):
        raw.setdefault("answer_generator", {})["ollama_url"] = os.environ["OLLAMA_URL"]

    return AppConfig.model_validate(raw)
