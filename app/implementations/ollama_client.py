"""
ollama_client.py – HTTP-Client für die Ollama REST-API.

Kapselt alle HTTP-Aufrufe an den lokalen Ollama-Server (POST /api/generate).
Wird von OllamaAnswerGenerator genutzt.
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
        response_format: Optional[str] = None,
    ) -> str:
        """
        Sendet einen Prompt an Ollama und gibt den Antworttext zurück.
        stream=False bedeutet: Ollama wartet bis zur vollständigen Antwort und schickt sie als einen JSON-Response.
        response_format="json" aktiviert Ollamas grammatik-gebundene Dekodierung: Das Modell kann dann
        nur noch syntaktisch gültiges JSON erzeugen (kein Text drumherum, keine kaputten Klammern/Strings).
        """
        # Sampling-Parameter MÜSSEN ins "options"-Objekt – auf Top-Level ignoriert Ollama sie stillschweigend.
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens  # Ollama nennt es "num_predict", nicht "max_tokens"

        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if options:
            payload["options"] = options
        if response_format:
            payload["format"] = response_format  # "json" → erzwingt gültiges JSON auf Dekodier-Ebene

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
        response_format: str = "json",
    ) -> Any:
        """
        Wie generate(), aber parst die Antwort als JSON. response_format="json" (Default) erzwingt
        bereits auf Ollama-Ebene gültiges JSON – das verhindert die häufigste Fehlerquelle kleiner
        Modelle (Text um das JSON, Markdown-Zäune, fehlende Kommas, unescapte Zeichen).
        Der Fallback unten (erstes { … letztes }) bleibt als zusätzliches Sicherheitsnetz erhalten.
        """
        text = self.generate(
            model=model, prompt=prompt, temperature=temperature,
            max_tokens=max_tokens, response_format=response_format,
        )

        try:
            return json.loads(text)  # Normalfall: direkt valides JSON
        except Exception:
            # Fallback: JSON-Objekt aus umgebendem Text extrahieren
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start: end + 1])
            raise
