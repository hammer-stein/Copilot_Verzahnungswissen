"""
generate_testdata.py – Erzeugt 10 synthetische CAD-Testdatensätze.

Importiert GearParameters direkt aus cad_processor/src/output_schema.py,
damit das JSON-Format garantiert identisch zur echten STEP-Analyse ist.
Alle geometrischen Größen werden konsistent nach DIN 3960 berechnet:

  d  = m_t * z          (Teilkreis, m_t = m_n / cos(β) bei Schrägverzahnung)
  da = d + 2 m_n (1+x)  (Kopfkreis, Außenverzahnung)
  df = d - 2 m_n (1.25-x) (Fußkreis, Außenverzahnung)

Aufruf:  python test_verzahnung/cad_testdaten/generate_testdata.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "cad_processor" / "src"))

from output_schema import GearParameters  # noqa: E402

STEEL_DENSITY_KG_MM3 = 7.85e-6

# (name, gear_type, m_n, z, beta_deg, x, material, quality, face_width_factor, internal)
GEAR_SPECS = [
    ("gear_01", "spur",     2.0, 20,  0.0,  0.00, "16MnCr5",      7, 10.0, False),
    ("gear_02", "spur",     3.0, 34,  0.0,  0.20, "C45",          8, 11.0, False),
    ("gear_03", "spur",     1.5, 48,  0.0, -0.10, "42CrMo4",      6, 12.0, False),
    ("gear_04", "spur",     5.0, 17,  0.0,  0.35, "20MnCr5",      7,  9.0, False),
    ("gear_05", "helical",  2.0, 25, 20.0,  0.15, "16MnCr5",      6, 12.0, False),
    ("gear_06", "helical",  2.5, 41, 15.0,  0.00, "18CrNiMo7-6",  6, 13.0, False),
    ("gear_07", "helical",  4.0, 23, 12.0,  0.25, "42CrMo4",      7, 10.0, False),
    ("gear_08", "internal", 2.0, 62,  0.0,  0.00, "16MnCr5",      7, 10.0, True),
    ("gear_09", "internal", 3.0, 55, 18.0,  0.10, "20MnCr5",      6, 11.0, True),
    ("gear_10", "bevel",    3.5, 28,  0.0,  0.00, "C45",          8,  9.0, False),
]


def build_gear(name, gear_type, m_n, z, beta_deg, x, material, quality, fw_factor, internal):
    beta_rad = math.radians(beta_deg)
    m_t = m_n / math.cos(beta_rad)            # Stirnmodul
    d = round(m_t * z, 3)                      # Teilkreisdurchmesser
    b = round(m_n * fw_factor, 1)              # Zahnbreite

    if internal:
        # Innenverzahnung (Hohlrad): Kopfkreis liegt INNEN, Fußkreis außen.
        da = round(d - 2 * m_n * (1 + x), 3)
        df = round(d + 2 * m_n * (1.25 - x), 3)
        ring_od = round(df + 6 * m_n, 3)       # Außendurchmesser des Hohlrad-Rings
        outer_diameter = ring_od
        bore = da                               # "Bohrung" = verzahnter Innenraum
    else:
        da = round(d + 2 * m_n * (1 + x), 3)
        df = round(d - 2 * m_n * (1.25 - x), 3)
        outer_diameter = da
        bore = round(max(8.0, 0.25 * d), 1)    # plausible Nabenbohrung

    tooth_height = round(abs(da - df) / 2, 3)  # h = 2.25 * m_n
    addendum = round(m_n * 1.0, 3)
    dedendum = round(m_n * 1.25, 3)
    tooth_thickness = round(math.pi * m_n / 2, 3)

    # Volumen: Vollzylinder über da minus Bohrung (bzw. Ring bei Innenverzahnung)
    if internal:
        volume = (math.pi / 4) * (ring_od**2 - da**2) * b
    else:
        volume = (math.pi / 4) * (da**2 - bore**2) * b
    volume = round(volume, 1)
    surface = round(2 * (math.pi / 4) * outer_diameter**2 + math.pi * outer_diameter * b, 1)
    mass = round(volume * STEEL_DENSITY_KG_MM3, 3)

    gp = GearParameters(source_file=f"{name}.step")
    gp.gear_type = gear_type
    gp.is_internal_gear = internal
    gp.num_teeth = z
    gp.module_mm = m_n
    gp.pressure_angle_deg = 20.0
    gp.helix_angle_deg = beta_deg
    gp.profile_shift_x = x

    gp.bbox_x_mm = outer_diameter
    gp.bbox_y_mm = outer_diameter
    gp.bbox_z_mm = b
    gp.outer_diameter_mm = outer_diameter
    gp.root_diameter_mm = df
    gp.pitch_diameter_mm = d
    gp.face_width_mm = b
    gp.total_width_mm = b
    gp.hub_bore_diameter_mm = bore
    gp.volume_mm3 = volume
    gp.surface_area_mm2 = surface

    gp.tooth_height_mm = tooth_height
    gp.addendum_mm = addendum
    gp.dedendum_mm = dedendum
    gp.tooth_thickness_mm = tooth_thickness
    gp.root_fillet_radius_mm = round(0.38 * m_n, 3)  # DIN 867: ρ_f ≈ 0.38 m

    gp.symmetry_type = "rotational"
    gp.keyway_present = not internal
    gp.has_flanges = False
    if gear_type == "bevel":
        gp.cone_angle_deg = 45.0
        gp.shaft_angle_deg = 90.0

    gp.part_name = f"Testzahnrad {name}"
    gp.part_number = f"TEST-{name.upper()}"
    gp.material = material
    gp.quality_class_din = quality
    gp.mass_kg = mass
    gp.norm_reference = ["DIN 867", "DIN 3960", "DIN ISO 1328"]

    gp.confidence = 0.95
    gp.warnings = []
    gp.extraction_notes = {"synthetic": "Erzeugt von generate_testdata.py, kein echtes STEP-Parsing."}
    return gp


def main():
    for spec in GEAR_SPECS:
        gp = build_gear(*spec)
        gp.to_json(str(HERE / f"{spec[0]}.json"))
    print(f"\n{len(GEAR_SPECS)} Testdatensätze erzeugt in {HERE}")


if __name__ == "__main__":
    main()
