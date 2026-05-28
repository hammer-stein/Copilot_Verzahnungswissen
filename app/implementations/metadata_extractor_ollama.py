"""
metadata_extractor_ollama.py – LLM-basierte Metadatenextraktion via Ollama.

Implementiert das MetadataExtractor-Protokoll. Für jeden Chunk wird ein kleines LLM
aufgerufen, das aus dem Text domänenspezifische Metadaten (Verzahnungstyp, Modul, ...)
als JSON-Objekt extrahiert – Grundlage für den Stage-1-Filter im Retriever.
"""

from __future__ import annotations

from typing import Optional

from app.core.schema import MetadataSchema
from app.core.types import Chunk
from app.implementations.ollama_client import OllamaClient


class OllamaMetadataExtractor:
    """Extrahiert Metadaten aus Chunks via LLM-Aufruf. Bei Fehler wird ein leeres Dict zurückgegeben."""

    def __init__(self, *, model_name: str, base_url: str, timeout_s: int, max_retries: int) -> None:
        """model_name ist z.B. "llama3.2:3b" – ein kleines Modell reicht für JSON-Extraktion."""
        self.model_name = model_name
        self.max_retries = max_retries
        self.client = OllamaClient(base_url=base_url, timeout_s=timeout_s)

    def extract(self, chunk: Chunk, schema: MetadataSchema) -> dict:
        """
        Baut einen Prompt aus Schema-Beschreibung und Chunk-Text, ruft das LLM auf
        und gibt das geparste JSON zurück. Bei max_retries fehlgeschlagenen Versuchen
        wird {} zurückgegeben – der Chunk landet ohne Metadaten in Qdrant.
        """
        # Schema-Felder als Beschreibungszeilen für den Prompt aufbauen
        schema_lines = []
        for f in schema.fields:
            enum = f" enum={f.enum}" if f.enum else ""
            nullable = " nullable=true" if f.nullable else ""
            rng = f" range_fields={f.range_fields}" if f.range_fields else ""
            schema_lines.append(
                f"- {f.name}: type={f.type}{enum}{nullable}{rng}; "
                f"filter_type={f.filter_type}; {f.description or ''}".strip()
            )

        prompt = (
            "Du extrahierst Metadaten aus einem Text-Chunk.\n"
            "Gib AUSSCHLIESSLICH ein JSON-Objekt zurück (keine Erklärungen).\n"
            "Fülle nur Felder, die im Text explizit vorkommen. Sonst: null/unspecified oder Feld weglassen.\n\n"
            f"DOMÄNE: {schema.domain}\n"
            f"SCHEMA:\n{chr(10).join(schema_lines)}\n\n"
            f"HINWEIS:\n{schema.extraction_prompt_hint or ''}\n\n"
            f"CHUNK (Quelle: {chunk.source_path}, Seite {chunk.page_number}):\n{chunk.text}\n"
        )

        last_err: Optional[Exception] = None
        for _ in range(max(1, self.max_retries)):
            try:
                data = self.client.generate_json(
                    model=self.model_name,
                    prompt=prompt,
                    temperature=0.0,   # deterministisch – kein Raten
                    max_tokens=400,
                )
                if isinstance(data, dict):
                    return data
                return {}
            except Exception as e:
                last_err = e
                continue  # erneut versuchen bei ungültigem JSON

        return {}  # graceful degradation: Chunk wird ohne Metadaten gespeichert
