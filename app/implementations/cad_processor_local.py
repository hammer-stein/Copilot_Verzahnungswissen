"""
cad_processor_local.py - In-Process-Adapter fuer den CAD-Processor.

Ruft die STEP-Analyse direkt im FastAPI-Prozess auf. Damit bleibt /cad/analyze
auf Port 8000, ohne einen zweiten cad_processor-HTTP-Dienst auf Port 8001.
Voraussetzung: Der Prozess laeuft in einer Umgebung mit pythonocc-core, z.B.
im conda-Env gear-copilot.
"""

from __future__ import annotations

import sys
import tempfile
import importlib.util
from pathlib import Path
from typing import Optional


class LocalCadProcessorAdapter:
    """CADAdapter-Implementierung, die cad_processor/src/step_parser.py direkt nutzt."""

    def __init__(self, *, cad_processor_dir: Path) -> None:
        self.cad_processor_dir = Path(cad_processor_dir)
        self.src_dir = self.cad_processor_dir / "src"

    def validate_available(self) -> None:
        """Prueft beim Serverstart, ob der lokale CAD-Parser in diesem Interpreter lauffaehig ist."""
        self._load_parser()

    def extract(self, file_path: Optional[Path]) -> dict:
        """
        Analysiert eine STEP/STP-Datei direkt mit pythonocc.
        Wird aus /cad/analyze bereits via asyncio.to_thread() aufgerufen, da OCC blockiert.
        """
        if file_path is None:
            raise ValueError("LocalCadProcessorAdapter benoetigt einen Pfad zu einer STEP-Datei.")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"STEP-Datei nicht gefunden: {file_path}")

        parse_step_file = self._load_parser()

        with tempfile.TemporaryDirectory(prefix="cad_processor_") as tmp:
            output_path = Path(tmp) / "gear_parameters.json"
            params = parse_step_file(str(file_path), str(output_path))
            result = params.to_dict()
            result.setdefault("filename", file_path.name)
            return result

    def _load_parser(self):
        """
        Laedt den bestehenden CAD-Parser lazy. So koennen Tests und synthetische Modi
        ohne installierte OCC-Abhaengigkeiten weiterhin factory/config importieren.
        """
        if not self.src_dir.exists():
            raise FileNotFoundError(f"cad_processor/src nicht gefunden: {self.src_dir}")

        src = str(self.src_dir)
        if src not in sys.path:
            sys.path.insert(0, src)

        parser_path = self.src_dir / "step_parser.py"
        if not parser_path.exists():
            raise FileNotFoundError(f"step_parser.py nicht gefunden: {parser_path}")

        try:
            spec = importlib.util.spec_from_file_location("_gear_copilot_step_parser", parser_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"step_parser.py konnte nicht geladen werden: {parser_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except (ImportError, ModuleNotFoundError) as exc:
            missing = getattr(exc, "name", "") or ""
            if missing.startswith("OCC") or "OCC" in str(exc):
                raise RuntimeError(
                    "cad_processor_local ist aktiv, aber pythonocc-core/OCC ist in diesem "
                    f"Python-Interpreter nicht verfuegbar: {sys.executable}. Starte mit "
                    "'conda activate gear-copilot' und 'python -m uvicorn app.api.main:app --port 8000'."
                ) from exc
            raise

        return module.parse_step_file
