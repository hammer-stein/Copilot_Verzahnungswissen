"""
test_config.py – Prüft die Env-Variablen-Overrides von load_config.

Kernidee: Dieselbe config.yaml (lokale Defaults: eingebettetes Qdrant via `path`,
CAD-Stub) muss sich im Docker-Compose-Netz automatisch auf Server-/Service-Modus
umstellen, sobald die entsprechenden Env-Variablen gesetzt sind.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import load_config

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def test_local_defaults_use_embedded_qdrant_and_stub(monkeypatch):
    for var in ("QDRANT_HOST", "QDRANT_PORT", "CAD_PROCESSOR_URL", "OLLAMA_URL"):
        monkeypatch.delenv(var, raising=False)
    cfg = load_config(CONFIG_PATH)
    assert cfg.vector_store.path == "storage/qdrant"  # eingebetteter Modus lokal
    assert cfg.cad_adapter.implementation == "random_gear_stub"


def test_qdrant_host_env_forces_server_mode(monkeypatch):
    monkeypatch.setenv("QDRANT_HOST", "qdrant")
    monkeypatch.setenv("QDRANT_PORT", "6333")
    monkeypatch.delenv("CAD_PROCESSOR_URL", raising=False)
    cfg = load_config(CONFIG_PATH)
    assert cfg.vector_store.host == "qdrant"
    assert cfg.vector_store.port == 6333
    assert cfg.vector_store.path is None  # path deaktiviert → echter Qdrant-Server


def test_cad_processor_url_env_switches_to_http_adapter(monkeypatch):
    monkeypatch.setenv("CAD_PROCESSOR_URL", "http://cad_processor:8001")
    monkeypatch.delenv("QDRANT_HOST", raising=False)
    cfg = load_config(CONFIG_PATH)
    assert cfg.cad_adapter.implementation == "cad_processor_http"
    assert cfg.cad_adapter.url == "http://cad_processor:8001"


def test_ollama_url_env_override(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://host.docker.internal:11434")
    cfg = load_config(CONFIG_PATH)
    assert cfg.metadata_extractor.ollama_url == "http://host.docker.internal:11434"
