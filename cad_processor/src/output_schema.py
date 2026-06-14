"""
output_schema.py
----------------
JSON-Ausgabestruktur für die Schnittstelle zu Gruppe A (RAG-Pipeline).

Schema Version 2.0: Jeder messbare Parameter wird als
{"value": X, "unit": "...", "confidence": 0.0–1.0} ausgegeben.

Konfidenz-Stufen (Klasse C):
  DIRECT    = 0.92  direkt gemessen (Zylinder-Radius aus OCC)
  CALC      = 0.82  aus gemessenen Werten berechnet (d = m*z)
  FALLBACK  = 0.65  Formel-Fallback (d_f = m*(z-2.5))
  HEURISTIC = 0.45  Heuristik / Kantenanzahl-Schätzung
  DEFAULT   = 0.30  DIN-Normwert angenommen (alpha = 20°)
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import json
import os
import math


SCHEMA_VERSION = "2.0"


# ─────────────────────────────────────────────
# Parameter-Wert mit Konfidenz
# ─────────────────────────────────────────────

@dataclass
class ParameterValue:
    """Hält einen extrahierten Wert zusammen mit Maßeinheit und Konfidenz."""
    value: Any
    unit: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "unit": self.unit,
            "confidence": round(self.confidence, 3),
        }

    @staticmethod
    def make(value: Any, unit: str, confidence: float) -> "ParameterValue":
        return ParameterValue(value=value, unit=unit, confidence=round(confidence, 3))


class C:
    """Benannte Konfidenz-Stufen nach Extraktionsmethode."""
    DIRECT    = 0.92
    CALC      = 0.82
    FALLBACK  = 0.65
    HEURISTIC = 0.45
    DEFAULT   = 0.30


# ─────────────────────────────────────────────
# Haupt-Datenstruktur
# ─────────────────────────────────────────────

@dataclass
class GearParameters:
    """
    Vollständige Parameter-Struktur für ein Zahnrad.
    Wird als verschachteltes JSON an die RAG-Pipeline (Gruppe A) übergeben.

    Messbare Parameter (Typ Optional[ParameterValue]) werden als
    {"value": X, "unit": "...", "confidence": 0.0–1.0} serialisiert.
    Plain-value-Zuweisungen (z.B. in Tests) werden unverändert durchgereicht.
    """

    # ── Quelldatei ──────────────────────────────────────────────
    source_file: str

    # ═══════════════════════════════════════════════════════════
    # PRIO 1: Immer aus Geometrie extrahierbar
    # ═══════════════════════════════════════════════════════════

    bbox_x_mm: float = 0.0
    bbox_y_mm: float = 0.0
    bbox_z_mm: float = 0.0

    outer_diameter_mm: Optional[ParameterValue] = None    # d_a
    face_width_mm: Optional[ParameterValue] = None        # b
    total_width_mm: Optional[ParameterValue] = None       # B

    volume_mm3: Optional[ParameterValue] = None
    surface_area_mm2: Optional[ParameterValue] = None

    gear_type: Optional[ParameterValue] = None
    is_internal_gear: bool = False

    num_teeth: Optional[ParameterValue] = None            # z
    module_mm: Optional[ParameterValue] = None            # m

    # ═══════════════════════════════════════════════════════════
    # PRIO 2: Meistens extrahierbar / ableitbar
    # ═══════════════════════════════════════════════════════════

    root_diameter_mm: Optional[ParameterValue] = None     # d_f
    pitch_diameter_mm: Optional[ParameterValue] = None    # d
    hub_bore_diameter_mm: Optional[ParameterValue] = None # d_N (Bohrung)
    hub_diameter_mm: Optional[ParameterValue] = None      # Nabendurchmesser
    hub_width_mm: Optional[ParameterValue] = None         # Nabenbreite

    helix_angle_deg: Optional[ParameterValue] = None      # β
    pressure_angle_deg: ParameterValue = field(
        default_factory=lambda: ParameterValue.make(20.0, "°", C.DEFAULT)
    )
    tooth_height_mm: Optional[ParameterValue] = None      # h
    addendum_mm: Optional[ParameterValue] = None          # h_a
    dedendum_mm: Optional[ParameterValue] = None          # h_f
    profile_shift_x: Optional[ParameterValue] = None      # x
    root_fillet_radius_mm: Optional[ParameterValue] = None  # r_f
    tooth_thickness_mm: Optional[ParameterValue] = None   # s

    cone_angle_deg: Optional[ParameterValue] = None       # δ (Kegelrad)
    shaft_angle_deg: Optional[ParameterValue] = None      # Σ
    worm_starts: Optional[int] = None
    symmetry_type: Optional[str] = None

    keyway_present: Optional[bool] = None
    has_flanges: Optional[bool] = None

    # ═══════════════════════════════════════════════════════════
    # PRIO 3: Optional aus PMI / STEP-Metadaten
    # ═══════════════════════════════════════════════════════════

    part_name: Optional[str] = None
    part_number: Optional[str] = None
    material: Optional[str] = None
    created_by: Optional[str] = None

    tolerance_class: Optional[str] = None
    surface_roughness_ra: Optional[float] = None
    bore_fit: Optional[str] = None
    quality_class_din: Optional[int] = None

    mass_kg: Optional[float] = None
    norm_reference: list = field(default_factory=list)

    # ═══════════════════════════════════════════════════════════
    # Qualität der Extraktion
    # ═══════════════════════════════════════════════════════════

    overall_confidence: float = 1.0
    face_parse_success_rate: Optional[float] = None
    warnings: list = field(default_factory=list)
    extraction_notes: dict = field(default_factory=dict)

    # ═══════════════════════════════════════════════════════════
    # Hinweise
    # ═══════════════════════════════════════════════════════════

    hints: Optional[dict] = None

    # ══════════════════════════════════════════════════════════
    # Methoden
    # ══════════════════════════════════════════════════════════

    def _pv(self, v) -> Any:
        """Serialisiert ParameterValue → dict. Gibt plain values unverändert zurück."""
        if v is None:
            return None
        if isinstance(v, ParameterValue):
            return v.to_dict()
        return v

    def to_dict(self) -> dict:
        """Gibt verschachtelte JSON-Struktur zurück (Schnittstelle zu Gruppe A)."""
        return {
            "schema_version": SCHEMA_VERSION,
            "source_file": self.source_file,
            "gear_type": self._pv(self.gear_type),
            "overall_confidence": round(self.overall_confidence, 3),

            "basic_geometry": {
                "outer_diameter_mm":    self._pv(self.outer_diameter_mm),
                "root_diameter_mm":     self._pv(self.root_diameter_mm),
                "pitch_diameter_mm":    self._pv(self.pitch_diameter_mm),
                "face_width_mm":        self._pv(self.face_width_mm),
                "total_width_mm":       self._pv(self.total_width_mm),
                "hub_bore_diameter_mm": self._pv(self.hub_bore_diameter_mm),
                "hub_diameter_mm":      self._pv(self.hub_diameter_mm),
                "hub_width_mm":         self._pv(self.hub_width_mm),
                "volume_mm3":           self._pv(self.volume_mm3),
                "surface_area_mm2":     self._pv(self.surface_area_mm2),
            },

            "tooth_profile": {
                "num_teeth":             self._pv(self.num_teeth),
                "module_mm":             self._pv(self.module_mm),
                "helix_angle_deg":       self._pv(self.helix_angle_deg),
                "pressure_angle_deg":    self._pv(self.pressure_angle_deg),
                "tooth_height_mm":       self._pv(self.tooth_height_mm),
                "addendum_mm":           self._pv(self.addendum_mm),
                "dedendum_mm":           self._pv(self.dedendum_mm),
                "profile_shift_x":       self._pv(self.profile_shift_x),
                "root_fillet_radius_mm": self._pv(self.root_fillet_radius_mm),
                "tooth_thickness_mm":    self._pv(self.tooth_thickness_mm),
            },

            "topology": {
                "is_internal_gear": self.is_internal_gear,
                "symmetry_type":    self.symmetry_type,
                "cone_angle_deg":   self._pv(self.cone_angle_deg),
                "shaft_angle_deg":  self._pv(self.shaft_angle_deg),
                "worm_starts":      self.worm_starts,
                "keyway_present":   self.keyway_present,
                "has_flanges":      self.has_flanges,
            },

            "material_context": {
                "material":             self.material,
                "mass_kg":              self.mass_kg,
                "bore_fit":             self.bore_fit,
                "quality_class_din":    self.quality_class_din,
                "norm_reference":       self.norm_reference,
                "tolerance_class":      self.tolerance_class,
                "surface_roughness_ra": self.surface_roughness_ra,
            },

            "metadata": {
                "part_name":   self.part_name,
                "part_number": self.part_number,
                "created_by":  self.created_by,
            },

            "extraction_quality": {
                "face_parse_success_rate": self.face_parse_success_rate,
                "warnings":         self.warnings,
                "extraction_notes": self.extraction_notes,
                "bbox_mm": {
                    "x": self.bbox_x_mm,
                    "y": self.bbox_y_mm,
                    "z": self.bbox_z_mm,
                },
            },

            "hints": self.hints or {},
        }

    def to_json(self, output_path: str):
        """Speichert Parameter als JSON-Datei."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"  -> JSON gespeichert: {output_path}")

    def summary(self):
        """Gibt eine kurze Zusammenfassung auf der Konsole aus."""
        def val(f):
            return f.value if isinstance(f, ParameterValue) else f

        def conf(f):
            return f" [{f.confidence:.0%}]" if isinstance(f, ParameterValue) else ""

        print("\n" + "=" * 55)
        print("EXTRAHIERTE PARAMETER")
        print("=" * 55)

        print("\n[PRIO 1 — Grundgeometrie]")
        print(f"  Typ:                {val(self.gear_type) or 'nicht erkannt'}{conf(self.gear_type)}")
        print(f"  Innenverzahnung:    {self.is_internal_gear}")
        print(f"  Symmetrie:          {self.symmetry_type or 'n/a'}")
        print(f"  Außendurchm. d_a:   {val(self.outer_diameter_mm) or 0} mm{conf(self.outer_diameter_mm)}")
        print(f"  Zahnbreite b:       {val(self.face_width_mm) or 0} mm{conf(self.face_width_mm)}")
        print(f"  Gesamtbreite B:     {val(self.total_width_mm) or 0} mm")
        print(f"  Zähnezahl z:        {val(self.num_teeth) or 'nicht erkannt'}{conf(self.num_teeth)}")
        print(f"  Modul m:            {val(self.module_mm) or 'nicht erkannt'} mm{conf(self.module_mm)}")

        print("\n[PRIO 2 — Abgeleitete Parameter]")
        print(f"  Teilkreis d:        {val(self.pitch_diameter_mm) or 'n/a'} mm{conf(self.pitch_diameter_mm)}")
        print(f"  Fußkreis d_f:       {val(self.root_diameter_mm) or 'n/a'} mm{conf(self.root_diameter_mm)}")
        print(f"  Nabenbohrung d_N:   {val(self.hub_bore_diameter_mm) or 'n/a'} mm{conf(self.hub_bore_diameter_mm)}")
        print(f"  Zahnhöhe h:         {val(self.tooth_height_mm) or 'n/a'} mm{conf(self.tooth_height_mm)}")
        print(f"  Kopfhöhe h_a:       {val(self.addendum_mm) or 'n/a'} mm{conf(self.addendum_mm)}")
        print(f"  Fußhöhe h_f:        {val(self.dedendum_mm) or 'n/a'} mm{conf(self.dedendum_mm)}")
        x_val = val(self.profile_shift_x)
        print(f"  Profilverschiebung x: {x_val if x_val is not None else 'n/a'}{conf(self.profile_shift_x)}")
        print(f"  Fußrundungsrad. r_f:{val(self.root_fillet_radius_mm) or 'n/a'} mm{conf(self.root_fillet_radius_mm)}")
        print(f"  Zahndicke s:        {val(self.tooth_thickness_mm) or 'n/a'} mm{conf(self.tooth_thickness_mm)}")
        beta = val(self.helix_angle_deg)
        print(f"  Schrägungswinkel β: {beta if beta is not None else 'n/a'}°{conf(self.helix_angle_deg)}")
        alpha = val(self.pressure_angle_deg)
        print(f"  Eingriffswinkel α:  {alpha or 20.0}°{conf(self.pressure_angle_deg)}")
        cone = val(self.cone_angle_deg)
        if cone is not None:
            print(f"  Konuswinkel δ:      {cone}°{conf(self.cone_angle_deg)}")
        print(f"  Passfedernut:       {self.keyway_present if self.keyway_present is not None else 'n/a'}")
        print(f"  Flansche:           {self.has_flanges if self.has_flanges is not None else 'n/a'}")

        print("\n[PRIO 3 — Metadaten]")
        print(f"  Teilename:          {self.part_name or 'n/a'}")
        print(f"  Material:           {self.material or 'n/a'}")
        print(f"  Masse:              {self.mass_kg or 'n/a'} kg")
        print(f"  DIN ISO 1328 Kl.:   {self.quality_class_din or 'n/a'}")
        print(f"  Normreferenzen:     {', '.join(self.norm_reference) if self.norm_reference else 'n/a'}")
        print(f"  Toleranzklasse:     {self.tolerance_class or 'n/a'}")

        print(f"\n[Qualität]")
        if self.face_parse_success_rate is not None:
            print(f"  Face-Parse-Rate:    {self.face_parse_success_rate:.0%}")
        print(f"  Konfidenz:          {self.overall_confidence:.0%}")
        if self.warnings:
            print("  Warnungen:")
            for w in self.warnings:
                print(f"    - {w}")
        print("=" * 55)
