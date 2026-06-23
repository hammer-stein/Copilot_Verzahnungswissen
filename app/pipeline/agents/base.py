"""
base.py – Gemeinsame Basis für die LLM-Agenten des Multi-Agenten-Flows.

Kapselt das, was Solver und Reviewer teilen: das Rendern eines Prompt-Templates
(.format()-Platzhalter wie {DOMAIN}, {QUESTION} …) und den JSON-Aufruf gegen den
lokalen Ollama-Server. Bewusst zustandslos – passend zur „kein Konversationskontext"-
Vorgabe des Systems.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

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


_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


def parse_bullets(text: str) -> list[str]:
    """
    Zerlegt einen Abschnitt in Listenpunkte: Zeilen mit -, *, • oder '1.'/'1)'.
    Enthält der Abschnitt keine Aufzählungszeichen, wird jede nicht-leere Zeile ein Punkt.
    """
    if not text:
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    bullets = [_BULLET_RE.sub("", ln).strip() for ln in lines if _BULLET_RE.match(ln)]
    if bullets:
        return [b for b in bullets if b]
    return lines


def parse_labeled_sections(text: str, labels: list[str]) -> dict[str, str]:
    """
    Zerlegt LLM-Freitext in Abschnitte anhand von Label-Zeilen (z.B. "ANTWORT:").
    Robust für kleine Modelle: Label case-insensitive, Doppelpunkt optional, führende
    Markdown-Zeichen (*, #, >) erlaubt; Abschnittsinhalt darf mehrzeilig sein.
    Fehlende Labels ergeben einen leeren String. Text vor dem ersten Label wird verworfen.
    Gibt {LABEL_GROSS: inhalt} zurück.
    """
    # Führende Markdown-/Whitespace-Zeichen erlaubt; nach dem Label wird ein beliebiger
    # Mix aus Leerzeichen/*/:/_ konsumiert (deckt **LABEL:**, "LABEL :", "LABEL_" ab).
    label_pat = re.compile(
        r"^\s*[*#>\s]*(" + "|".join(re.escape(l) for l in labels) + r")[\s*:_]*(.*)$",
        re.IGNORECASE,
    )
    sections: dict[str, list[str]] = {l.upper(): [] for l in labels}
    current: Optional[str] = None
    for line in text.splitlines():
        m = label_pat.match(line)
        if m:
            current = m.group(1).upper()
            rest = m.group(2).strip()
            if rest:
                sections[current].append(rest)
            continue
        if current is not None:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


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

    def _generate_text(self, **fields: str) -> str:
        """
        Setzt die Felder in das Template ein ({DOMAIN} wird automatisch ergänzt) und ruft Ollama
        im FREITEXT-Modus auf (kein JSON-Zwang). Die Unterklassen parsen die label-basierte
        Ausgabe (ANTWORT:/SCHRITTE: bzw. URTEIL:/…) mit parse_labeled_sections – das ist für
        kleine Modelle deutlich robuster als JSON (kein Escaping, kein „unterminated string").
        """
        prompt = self.prompt_template.format(DOMAIN=self.domain_name, **fields)
        return self.client.generate(
            model=self.model_name,
            prompt=prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    def _generate_json(self, **fields: str) -> Any:
        """
        Legacy-Pfad (JSON). Aktuell ungenutzt – die Agenten verwenden _generate_text mit
        label-basierter Ausgabe. Bleibt für Rückwärtskompatibilität erhalten.
        """
        prompt = self.prompt_template.format(DOMAIN=self.domain_name, **fields)
        return self.client.generate_json(
            model=self.model_name,
            prompt=prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
