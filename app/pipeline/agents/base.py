"""
base.py – Gemeinsame Basis für die LLM-Agenten des Multi-Agenten-Flows.

Kapselt das, was Solver und Reviewer teilen: das Rendern eines Prompt-Templates
(.format()-Platzhalter wie {DOMAIN}, {QUESTION} …) und den JSON-Aufruf gegen den
lokalen Ollama-Server. Bewusst zustandslos – passend zur „kein Konversationskontext"-
Vorgabe des Systems.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.implementations.ollama_client import OllamaClient


def as_str(value: Any) -> str:
    """Normalisiert einen vom LLM gelieferten Wert defensiv zu einem getrimmten String."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def as_str_list(value: Any) -> list[str]:
    """Normalisiert einen LLM-Wert zu einer Liste nicht-leerer Strings (Einzelwert wird gewrappt)."""
    if isinstance(value, list):
        return [s for s in (as_str(v) for v in value) if s]
    text = as_str(value)
    return [text] if text else []


class LlmAgent:
    """
    Basisklasse für einen einzelnen, zustandslosen LLM-Agenten.

    Lädt das Prompt-Template einmalig beim Start und liefert mit _generate_json()
    bereits geparstes JSON. Das eigentliche Prompt-Schema und die Ergebnis-Normalisierung
    legen die Unterklassen (SolverAgent, ReviewerAgent) fest.
    """

    def __init__(
        self,
        *,
        client: OllamaClient,
        model_name: str,
        prompt_path: Path,
        domain_name: str,
        max_tokens: int,
        temperature: float,
    ) -> None:
        self.client = client
        self.model_name = model_name
        self.prompt_template = prompt_path.read_text(encoding="utf-8")  # einmalig beim Start laden
        self.domain_name = domain_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _generate_json(self, **fields: str) -> Any:
        """
        Setzt die Felder in das Template ein ({DOMAIN} wird automatisch ergänzt) und ruft Ollama
        im JSON-Modus auf. generate_json() extrahiert auch ein in Fließtext eingebettetes JSON-Objekt.
        Wirft bei nicht parsebarer Antwort – die Fehlerbehandlung/der Fallback liegt im Aufrufer.
        """
        prompt = self.prompt_template.format(DOMAIN=self.domain_name, **fields)
        return self.client.generate_json(
            model=self.model_name,
            prompt=prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
