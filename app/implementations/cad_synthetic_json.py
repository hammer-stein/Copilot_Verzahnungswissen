"""
cad_synthetic_json.py – CAD-Adapter für synthetische Testdatensätze.

Implementiert das CADAdapter-Protocol ohne cad_processor-Service: Liest die
geometrisch konsistenten GearParameters-JSONs aus test_verzahnung/cad_testdaten/
(gleiches Format wie cad_processor/src/output_schema.py). Dient als Schalter-
Gegenstück zu CadProcessorClient, wenn keine echten STEP-Dateien vorliegen.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional


class SyntheticCadJsonAdapter:
    """Liefert synthetische GearParameters-JSONs aus einem Verzeichnis."""

    def __init__(self, *, data_dir: Path) -> None:
        """data_dir enthält die Testdatensätze (gear_01.json, gear_02.json, ...)."""
        self.data_dir = Path(data_dir)

    def list_files(self) -> list[Path]:
        """Alle verfügbaren Testdatensätze, alphabetisch sortiert."""
        return sorted(self.data_dir.glob("*.json"))

    def extract(self, file_path: Optional[Path] = None) -> dict:
        """
        Gibt einen Testdatensatz zurück. Ohne file_path wird zufällig einer der
        vorhandenen JSONs gewählt (Demo-Modus, z.B. für GET /cad/random).
        Mit file_path wird – unabhängig vom übergebenen Dateityp – deterministisch
        ein Datensatz anhand des Dateinamens gewählt, damit derselbe Upload
        immer dieselben Testdaten liefert.
        """
        files = self.list_files()
        if not files:
            raise FileNotFoundError(
                f"Keine synthetischen CAD-Testdaten in {self.data_dir} gefunden. "
                "Führe test_verzahnung/cad_testdaten/generate_testdata.py aus."
            )

        if file_path is None:
            chosen = random.choice(files)
        else:
            chosen = files[hash(Path(file_path).name) % len(files)]

        return self.load_file(chosen)

    @staticmethod
    def load_file(path: Path) -> dict:
        """Lädt einen einzelnen Testdatensatz."""
        return json.loads(Path(path).read_text(encoding="utf-8"))
