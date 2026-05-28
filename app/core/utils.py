"""
utils.py – Allgemeine Hilfsfunktionen ohne Domänenlogik.

Wird von PDFLoader (sha256_file) und AnswerGenerator/API (stable_json_dumps) genutzt.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """
    Berechnet den SHA-256-Hash einer Datei blockweise, ohne sie vollständig in den RAM zu laden.
    Der Hash dient als stabiler Dokumenten-Fingerabdruck (doc_hash) für Deduplikation und Löschung.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        # 1-MB-Blöcke: konstanter RAM-Verbrauch auch bei großen PDFs
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_json_dumps(obj: Any) -> str:
    """
    Serialisiert ein Objekt zu einem deterministischen JSON-String (sort_keys=True).
    Wird für Query-Logs und den CAD-Metadaten-Block im LLM-Prompt verwendet.
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)
