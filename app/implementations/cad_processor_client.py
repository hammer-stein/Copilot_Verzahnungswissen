"""
cad_processor_client.py – HTTP-Client für den CAD-Processor-Service (Gruppe B).

Implementiert das CADAdapter-Protocol: Sendet eine STEP-Datei an den
cad_processor (POST /analyze, Port 8001) und mappt das englische
GearParameters-JSON auf die deutschen Feldnamen des Metadatenschemas
(schemas/gears.yaml), die der TwoStageRetriever für Stage-1-Filter nutzt.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import httpx

# Mapping der gear_type-Werte des cad_processors auf das Schema-Enum in gears.yaml.
# Nicht abgedeckte Typen (worm, rack) werden auf "unspecified" gemappt, damit der
# Stage-1-Filter keine falschen Ausschlüsse erzeugt.
_GEAR_TYPE_MAP = {
    "spur": "Stirnrad",
    "helical": "Schrägverzahnung",
    "bevel": "Kegelrad",
    "worm_wheel": "Schneckenrad",
    "internal": "Innenverzahnung",
}


class CadProcessorClient:
    """Synchroner HTTP-Client für den CAD-Processor. Wird via asyncio.to_thread() aufgerufen."""

    def __init__(self, *, url: str, timeout_s: int = 120) -> None:
        """url ist z.B. "http://localhost:8001". timeout_s großzügig, da STEP-Parsing dauern kann."""
        self.url = url.rstrip("/")
        self.timeout_s = timeout_s

    def extract(self, file_path: Optional[Path]) -> dict:
        """
        Lädt die STEP-Datei zum cad_processor hoch und gibt die gemappten
        CAD-Metadaten zurück. file_path muss auf eine .step/.stp-Datei zeigen.
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
            return self._map_to_schema(r.json())

    @staticmethod
    def _map_to_schema(result: dict[str, Any]) -> dict:
        """
        Mappt das GearParameters-JSON (cad_processor/src/output_schema.py) auf die
        deutschen Schema-Feldnamen. "verzahnungstyp" und "modul" steuern den
        Stage-1-Filter; die übrigen Felder dienen als Kontext für die Antwortgenerierung.
        """
        tooth = result.get("tooth_profile") or {}
        geometry = result.get("basic_geometry") or {}
        material = result.get("material_context") or {}

        metadata: dict[str, Any] = {
            "verzahnungstyp": _GEAR_TYPE_MAP.get(result.get("gear_type"), "unspecified"),
            "modul": tooth.get("module_mm"),
            "zaehnezahl": tooth.get("num_teeth"),
            "eingriffswinkel": tooth.get("pressure_angle_deg"),
            "schraegungswinkel": tooth.get("helix_angle_deg"),
            "profilverschiebung": tooth.get("profile_shift_x"),
            "teilkreisdurchmesser": geometry.get("pitch_diameter_mm"),
            "kopfkreisdurchmesser": geometry.get("outer_diameter_mm"),
            "fusskreisdurchmesser": geometry.get("root_diameter_mm"),
            "zahnbreite": geometry.get("face_width_mm"),
            "werkstoff": material.get("material"),
            "konfidenz": result.get("confidence"),
            "quelldatei": result.get("filename") or result.get("source_file"),
        }

        # None-Werte entfernen: fehlende Felder erzeugen im Retriever keine Filterbedingung
        return {k: v for k, v in metadata.items() if v is not None}
