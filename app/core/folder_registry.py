"""
folder_registry.py – Persistente Liste der Wissensbasis-Ordner.

Ordner dienen nur der Organisation der Dokumente in der UI (kein Retrieval-Filter).
Die Ordnerzuordnung eines Dokuments lebt im Qdrant-Payload; diese Registry hält
zusätzlich die Liste ALLER Ordnernamen – inklusive leerer Ordner, die (noch) kein
Dokument enthalten und daher in Qdrant nicht auftauchen würden.

Speicherort: storage/folders.json. Threadsicher über einen Prozess-Lock, da
FastAPI die synchronen Aufrufe via asyncio.to_thread() parallelisieren kann.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path


class FolderRegistry:
    """Einfache JSON-gestützte Liste von Ordnernamen."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> list[str]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            folders = data.get("folders", []) if isinstance(data, dict) else []
            return [str(f) for f in folders if str(f).strip()]
        except Exception:
            return []

    def _write(self, folders: list[str]) -> None:
        ordered = sorted(dict.fromkeys(folders), key=str.casefold)  # dedupe, stabil sortiert
        self.path.write_text(
            json.dumps({"folders": ordered}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list(self) -> list[str]:
        """Gibt alle registrierten Ordnernamen zurück (alphabetisch)."""
        with self._lock:
            return sorted(self._read(), key=str.casefold)

    def add(self, name: str) -> list[str]:
        """Legt einen Ordner an (idempotent). Gibt die aktualisierte Liste zurück."""
        name = name.strip()
        if not name:
            raise ValueError("Ordnername darf nicht leer sein.")
        with self._lock:
            folders = self._read()
            if name not in folders:
                folders.append(name)
                self._write(folders)
            return sorted(folders, key=str.casefold)

    def remove(self, name: str) -> list[str]:
        """Entfernt einen Ordner aus der Registry (Dokumente werden separat verschoben)."""
        name = name.strip()
        with self._lock:
            folders = [f for f in self._read() if f != name]
            self._write(folders)
            return sorted(folders, key=str.casefold)

    def clear(self) -> list[str]:
        """Entfernt alle Ordner aus der Registry (für "Alle löschen"). Gibt die nun leere Liste zurück."""
        with self._lock:
            self._write([])
            return []
