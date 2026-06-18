"""
cad_processor_client.py – HTTP-Client für den CAD-Processor-Service (Gruppe B).

Implementiert das CADAdapter-Protocol: Sendet eine STEP-Datei an den
cad_processor (POST /analyze, Port 8001) und gibt das vollständige
GearParameters-JSON (cad_processor/src/output_schema.py) unverändert zurück.
Das JSON fließt erst in der Antwortstufe als Bauteilkontext ein – nicht ins Retrieval.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import httpx


class CadProcessorClient:
    """Synchroner HTTP-Client für den CAD-Processor. Wird via asyncio.to_thread() aufgerufen."""

    def __init__(self, *, url: str, timeout_s: int = 120) -> None:
        """url ist z.B. "http://localhost:8001". timeout_s großzügig, da STEP-Parsing dauern kann."""
        self.url = url.rstrip("/")
        self.timeout_s = timeout_s

    def extract(self, file_path: Optional[Path]) -> dict:
        """
        Lädt die STEP-Datei zum cad_processor hoch und gibt das GearParameters-JSON
        zurück. file_path muss auf eine .step/.stp-Datei zeigen.
        """
        if file_path is None:
            raise ValueError("CadProcessorClient benötigt einen Pfad zu einer STEP-Datei.")

        file_path = Path(file_path)
        with httpx.Client(timeout=self.timeout_s) as client:
            with file_path.open("rb") as f:
                r = client.post(
                    f"{self.url}/analyze",
                    files={"file": (file_path.name, f, "application/octet-stream")},
                )
            r.raise_for_status()
            return r.json()
