"""
ollama_client.py – HTTP-Client für die Ollama REST-API.

Kapselt alle HTTP-Aufrufe an den lokalen Ollama-Server (POST /api/generate).
Wird von OllamaMetadataExtractor (JSON-Ausgabe) und OllamaAnswerGenerator (Fließtext) genutzt.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx


class OllamaClient:
    """Synchroner HTTP-Client für Ollama. Wird via asyncio.to_thread() aus dem FastAPI-Event-Loop aufgerufen."""

    def __init__(self, *, base_url: str, timeout_s: int) -> None:
        """base_url ist z.B. "http://localhost:11434". timeout_s gilt für die gesamte Anfrage inkl. LLM-Generierung."""
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Sendet einen Prompt an Ollama und gibt den Antworttext zurück.
        stream=False bedeutet: Ollama wartet bis zur vollständigen Antwort und schickt sie als einen JSON-Response.
        """
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["num_predict"] = max_tokens  # Ollama nennt es "num_predict", nicht "max_tokens"

        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(f"{self.base_url}/api/generate", json=payload)
            r.raise_for_status()  # wirft Exception bei 4xx/5xx
            return str(r.json().get("response", "")).strip()

    def generate_json(
        self,
        *,
        model: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """
        Wie generate(), aber parst die Antwort als JSON.
        LLMs geben manchmal JSON mit erklärendem Text darum zurück – der Fallback
        sucht das erste { und letzte } und versucht diesen Bereich zu parsen.
        """
        text = self.generate(model=model, prompt=prompt, temperature=temperature, max_tokens=max_tokens)

        try:
            return json.loads(text)  # Normalfall: direkt valides JSON
        except Exception:
            # Fallback: JSON-Objekt aus umgebendem Text extrahieren
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start: end + 1])
            raise
