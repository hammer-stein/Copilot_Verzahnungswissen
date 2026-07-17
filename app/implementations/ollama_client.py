"""
ollama_client.py – HTTP-Client für die Ollama REST-API.

Kapselt alle HTTP-Aufrufe an den lokalen Ollama-Server (POST /api/generate).
Wird von OllamaAnswerGenerator genutzt.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import httpx

# Reasoning-Modelle (z.B. qwen3, deepseek-r1) können ihre Denkspur als <think>…</think>
# in den Antworttext schreiben. Für den RAG-Fluss ist das Gift: Die Denkspur würde die
# ANTWORT:/URTEIL:-Parser verwirren und die Antwort im GUI vermüllen. Wird defensiv
# IMMER entfernt – bei Nicht-Reasoning-Modellen matcht das Muster schlicht nie.
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


def strip_think_block(text: str) -> str:
    """Entfernt <think>…</think>-Denkblöcke von Reasoning-Modellen aus dem Antworttext."""
    return _THINK_BLOCK_RE.sub("", text or "").strip()


class OllamaClient:
    """Synchroner HTTP-Client für Ollama. Wird via asyncio.to_thread() aus dem FastAPI-Event-Loop aufgerufen."""

    def __init__(self, *, base_url: str, timeout_s: int, think: Optional[bool] = None) -> None:
        """
        base_url ist z.B. "http://localhost:11434". timeout_s gilt für die gesamte Anfrage inkl. LLM-Generierung.
        think: Reasoning-Modus für Modelle wie qwen3 (None = Ollama-Default, False = aus).
        Für den RAG-Betrieb gehört er AUS – 2–3 LLM-Calls pro Frage mit Denkspur würden die
        Latenz vervielfachen, ohne dass kurze faktenbasierte Antworten davon profitieren.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.think = think

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
        if self.think is not None:
            payload["think"] = self.think  # Reasoning-Modus (qwen3 & Co.) explizit steuern

        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(f"{self.base_url}/api/generate", json=payload)
            if r.status_code == 400 and "think" in payload and "think" in r.text.lower():
                # Modell ohne Reasoning-Unterstützung (z.B. llama3.1) lehnt den think-Parameter
                # ab → einmalig ohne ihn wiederholen, damit ein Modellwechsel in der config.yaml
                # nicht an einer vergessenen think-Zeile scheitert.
                del payload["think"]
                r = client.post(f"{self.base_url}/api/generate", json=payload)
            r.raise_for_status()  # wirft Exception bei 4xx/5xx
            return strip_think_block(str(r.json().get("response", "")))

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
