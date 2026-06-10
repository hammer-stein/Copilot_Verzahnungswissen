"""
output_schema.py
----------------
JSON-Ausgabestruktur für die Schnittstelle zu Gruppe A (RAG-Pipeline).

Struktur:
  PRIO 1 — immer aus Geometrie extrahierbar
  PRIO 2 — meistens extrahierbar / ableitbar
  PRIO 3 — optional aus PMI / STEP-Metadaten

Felder mit None = nicht erkannt / nicht in Datei vorhanden.
Gruppe A muss damit umgehen können.
"""

from dataclasses import dataclass, field
from typing import Optional
import json
import os
import math


SCHEMA_VERSION = "1.0"


@dataclass
class GearParameters:
    """
    Vollständige Parameter-Struktur für ein Zahnrad.
    Wird als verschachteltes JSON an die RAG-Pipeline (Gruppe A) übergeben.
    """

    # ── Quelldatei ───────────────────────────────────────────────
    source_file: str

    # ═══════════════════════════════════════════════════════════
    # PRIO 1: Immer aus Geometrie extrahierbar
    # ═══════════════════════════════════════════════════════════

    # Bounding Box (Rohdaten)
    bbox_x_mm: float = 0.0
    bbox_y_mm: float = 0.0
    bbox_z_mm: float = 0.0

    # Grundgeometrie
    outer_diameter_mm: float = 0.0          # d_a  = max(bbox_x, bbox_y)
    face_width_mm: float = 0.0              # b    = bbox_z
    total_width_mm: float = 0.0             # B    = Gesamtbreite inkl. Nabe/Flansche

    # Volumen & Oberfläche
    volume_mm3: float = 0.0
    surface_area_mm2: float = 0.0

    # Verzahnungstyp
    gear_type: Optional[str] = None         # "spur" | "helical" | "bevel" | "internal" | "worm" | "rack"
    is_internal_gear: bool = False

    # Zähnezahl
    num_teeth: Optional[int] = None         # z

    # Modul (abgeleitet aus d_a und z)
    module_mm: Optional[float] = None       # m

    # ═══════════════════════════════════════════════════════════
    # PRIO 2: Meistens extrahierbar / ableitbar
    # ═══════════════════════════════════════════════════════════

    # Durchmesser (direkt aus Geometrie oder abgeleitet)
    root_diameter_mm: Optional[float] = None         # d_f  (direkt oder m*(z-2.5))
    pitch_diameter_mm: Optional[float] = None        # d    = m * z
    hub_bore_diameter_mm: Optional[float] = None     # d_N  = kleinste Innenbohrung

    # Zahnprofil-Parameter
    helix_angle_deg: Optional[float] = None          # β  (0 = Stirnrad)
    pressure_angle_deg: float = 20.0                 # α  (Norm: 20°)
    tooth_height_mm: Optional[float] = None          # h  = (d_a - d_f) / 2
    addendum_mm: Optional[float] = None              # h_a = m * 1.0
    dedendum_mm: Optional[float] = None              # h_f = m * 1.25
    profile_shift_x: Optional[float] = None          # x  (Profilverschiebung)
    root_fillet_radius_mm: Optional[float] = None    # r_f (aus Torus-Flächen)
    tooth_thickness_mm: Optional[float] = None       # s  am Teilkreis = π*m/2

    # Topologie-Features
    cone_angle_deg: Optional[float] = None           # δ  (Kegelrad: Halbkegelwinkel)
    shaft_angle_deg: Optional[float] = None          # Σ  (90° = Schnecke/Kegelrad)
    worm_starts: Optional[int] = None               # Schneckengang-Anzahl
    symmetry_type: Optional[str] = None             # "rotational" | "translational"

    # Bauteil-Kontext
    keyway_present: Optional[bool] = None            # Passfedernut vorhanden?
    has_flanges: Optional[bool] = None               # Absätze / Flansche?

    # ═══════════════════════════════════════════════════════════
    # PRIO 3: Optional aus PMI / STEP-Metadaten
    # ═══════════════════════════════════════════════════════════

    # STEP-Header Metadaten
    part_name: Optional[str] = None
    part_number: Optional[str] = None
    material: Optional[str] = None                   # z.B. "16MnCr5"
    created_by: Optional[str] = None

    # Toleranz / Qualität
    tolerance_class: Optional[str] = None            # z.B. "DIN 3961 Grad 6"
    surface_roughness_ra: Optional[float] = None     # Ra in µm
    bore_fit: Optional[str] = None                   # z.B. "H7"
    quality_class_din: Optional[int] = None          # DIN ISO 1328 Klasse 3–12

    # Abgeleitete Kontext-Felder
    mass_kg: Optional[float] = None                  # Masse aus Volumen × Dichte
    norm_reference: list = field(default_factory=list)  # ["DIN 867", "DIN ISO 1328"]

    # ═══════════════════════════════════════════════════════════
    # Qualität der Extraktion
    # ═══════════════════════════════════════════════════════════
    confidence: float = 1.0                          # 0.0 (unsicher) bis 1.0 (sicher)
    warnings: list = field(default_factory=list)
    extraction_notes: dict = field(default_factory=dict)

    # ═══════════════════════════════════════════════════════════
    # Hinweise (Normen, Anwendung, Fertigung, Qualität, Optimierung)
    # ═══════════════════════════════════════════════════════════
    hints: Optional[dict] = None

    # ══════════════════════════════════════════════════════════
    # Methoden
    # ══════════════════════════════════════════════════════════

    def to_dict(self) -> dict:
        """Gibt verschachtelte JSON-Struktur zurück (Schnittstelle zu Gruppe A)."""
        return {
            "schema_version": SCHEMA_VERSION,
            "source_file": self.source_file,
            "gear_type": self.gear_type,
            "confidence": round(self.confidence, 3),

            "basic_geometry": {
                "outer_diameter_mm": self.outer_diameter_mm,
                "root_diameter_mm": self.root_diameter_mm,
                "pitch_diameter_mm": self.pitch_diameter_mm,
                "face_width_mm": self.face_width_mm,
                "total_width_mm": self.total_width_mm,
                "hub_bore_diameter_mm": self.hub_bore_diameter_mm,
                "volume_mm3": self.volume_mm3,
                "surface_area_mm2": self.surface_area_mm2,
            },

            "tooth_profile": {
                "num_teeth": self.num_teeth,
                "module_mm": self.module_mm,
                "helix_angle_deg": self.helix_angle_deg,
                "pressure_angle_deg": self.pressure_angle_deg,
                "tooth_height_mm": self.tooth_height_mm,
                "addendum_mm": self.addendum_mm,
                "dedendum_mm": self.dedendum_mm,
                "profile_shift_x": self.profile_shift_x,
                "root_fillet_radius_mm": self.root_fillet_radius_mm,
                "tooth_thickness_mm": self.tooth_thickness_mm,
            },

            "topology": {
                "is_internal_gear": self.is_internal_gear,
                "symmetry_type": self.symmetry_type,
                "cone_angle_deg": self.cone_angle_deg,
                "shaft_angle_deg": self.shaft_angle_deg,
                "worm_starts": self.worm_starts,
                "keyway_present": self.keyway_present,
                "has_flanges": self.has_flanges,
            },

            "material_context": {
                "material": self.material,
                "mass_kg": self.mass_kg,
                "bore_fit": self.bore_fit,
                "quality_class_din": self.quality_class_din,
                "norm_reference": self.norm_reference,
                "tolerance_class": self.tolerance_class,
                "surface_roughness_ra": self.surface_roughness_ra,
            },

            "metadata": {
                "part_name": self.part_name,
                "part_number": self.part_number,
                "created_by": self.created_by,
            },

            "extraction_quality": {
                "warnings": self.warnings,
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
        print("\n" + "=" * 55)
        print("EXTRAHIERTE PARAMETER")
        print("=" * 55)

        print("\n[PRIO 1 — Grundgeometrie]")
        print(f"  Typ:                {self.gear_type or 'nicht erkannt'}")
        print(f"  Innenverzahnung:    {self.is_internal_gear}")
        print(f"  Symmetrie:          {self.symmetry_type or 'n/a'}")
        print(f"  Außendurchm. d_a:   {self.outer_diameter_mm} mm")
        print(f"  Zahnbreite b:       {self.face_width_mm} mm")
        print(f"  Gesamtbreite B:     {self.total_width_mm} mm")
        print(f"  Zähnezahl z:        {self.num_teeth or 'nicht erkannt'}")
        print(f"  Modul m:            {self.module_mm or 'nicht erkannt'} mm")

        print("\n[PRIO 2 — Abgeleitete Parameter]")
        print(f"  Teilkreis d:        {self.pitch_diameter_mm or 'n/a'} mm")
        print(f"  Fußkreis d_f:       {self.root_diameter_mm or 'n/a'} mm")
        print(f"  Nabenbohrung d_N:   {self.hub_bore_diameter_mm or 'n/a'} mm")
        print(f"  Zahnhöhe h:         {self.tooth_height_mm or 'n/a'} mm")
        print(f"  Kopfhöhe h_a:       {self.addendum_mm or 'n/a'} mm")
        print(f"  Fußhöhe h_f:        {self.dedendum_mm or 'n/a'} mm")
        print(f"  Profilverschiebung x: {self.profile_shift_x if self.profile_shift_x is not None else 'n/a'}")
        print(f"  Fußrundungsrad. r_f:{self.root_fillet_radius_mm or 'n/a'} mm")
        print(f"  Zahndicke s:        {self.tooth_thickness_mm or 'n/a'} mm")
        print(f"  Schrägungswinkel β: {self.helix_angle_deg if self.helix_angle_deg is not None else 'n/a'}°")
        print(f"  Eingriffswinkel α:  {self.pressure_angle_deg}°")
        if self.cone_angle_deg is not None:
            print(f"  Konuswinkel δ:      {self.cone_angle_deg}°")
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
        print(f"  Konfidenz:          {self.confidence:.0%}")
        if self.warnings:
            print("  Warnungen:")
            for w in self.warnings:
                print(f"    - {w}")
        print("=" * 55)
