"""
geometry_analyzer.py
--------------------
Schritt 2: Zahnrad-Parameter aus Rohdaten ableiten.

Bekommt die Rohdaten vom step_parser.py und berechnet daraus alle
ableibaren Zahnrad-Parameter gemäß den definierten Parametern.
"""

import math
from typing import List, Tuple, Optional

from output_schema import GearParameters


# ─────────────────────────────────────────────
# PRIO 1: Zahnrad-Typ erkennen
# ─────────────────────────────────────────────

def detect_gear_type(cylinders, planes: int, cones: list, tori: list) -> Tuple[str, bool, Optional[float]]:
    """
    Erkennt den Zahnrad-Typ anhand der Flächen-Verteilung.

    Gibt zurück:
        gear_type     : "spur" | "helical" | "bevel" | "internal" | "worm" | "rack" | "unknown"
        is_internal   : True wenn Innenverzahnung
        cone_angle_deg: Halbkegelwinkel in Grad (nur bei Kegelrad), sonst None
    """
    num_cylinders = len(cylinders)
    inner_cylinders = [r for r, is_inner in cylinders if is_inner]
    is_internal = len(inner_cylinders) > num_cylinders / 2

    # Kegelrad: mehrere konische Flächen mit signifikantem Winkel
    if len(cones) >= 4:
        angles_deg = [abs(math.degrees(a)) for a, _ in cones if abs(a) > 0.01]
        if angles_deg:
            cone_angle = round(sum(angles_deg) / len(angles_deg), 2)
            return "bevel", False, cone_angle

    # Innenverzahnung
    if is_internal:
        return "internal", True, None

    # Zahnstange: keine Rotationssymmetrie — sehr viele Planes, kaum Zylinder
    if num_cylinders == 0 and planes > 10:
        return "rack", False, None

    # Stirnrad vs. Schrägverzahnung: wird in detect_helix_angle entschieden
    return "spur", False, None


# ─────────────────────────────────────────────
# PRIO 1: Zahnzahl schätzen
# ─────────────────────────────────────────────

def estimate_num_teeth(total_edges: int, total_faces: int, tori: list) -> Optional[int]:
    """
    Schätzt die Zahnzahl aus der Topologie.

    Methode 1 (bevorzugt): Torische Flächen = Zahnfuß-Verrundungen → je 2 pro Zahn
    Methode 2 (Fallback):  Kanten-basierte Näherung (~14 Kanten pro Zahn)
    """
    if total_edges < 20:
        return None

    # Methode 1: Tori (je 2 Tori pro Zahn)
    num_tori = len(tori)
    if num_tori >= 2:
        estimated_z = num_tori // 2
        if 5 <= estimated_z <= 200:
            return estimated_z

    # Methode 2: Kanten-Heuristik (~36 Kanten/Zahn für FreeCAD-STEP-Exporte)
    estimated_z = round(total_edges / 36)
    if 5 <= estimated_z <= 200:
        return estimated_z

    return None


def estimate_z_from_diameter(
    outer_diameter_mm: float, total_edges: int
) -> Tuple[Optional[int], Optional[float]]:
    """
    Primärmethode v2: Berechnet (z, m) gemeinsam aus d_a und Kantenzahl.

    Für jeden DIN-780-Modul: z_raw = d_a/m - 2. Kandidaten mit nahezu-
    ganzzahligem z_raw werden per Kanten-pro-Zahn-Nähe selektiert.
    Gibt (z, m) zurück oder (None, None) wenn kein plausibler Kandidat.
    """
    INTEGRALITY_THRESHOLD = 0.12
    TARGET_EDGES_PER_TOOTH = 36    # empirisch: FreeCAD STEP-Export
    EDG_MIN, EDG_MAX = 8, 80

    candidates = []
    for m in STANDARD_MODULES:
        if m < 0.5:
            continue
        z_raw = outer_diameter_mm / m - 2
        z_int = round(z_raw)
        if not (5 <= z_int <= 200):
            continue
        rel_err = abs(z_raw - z_int) / max(z_int, 1)
        if rel_err > INTEGRALITY_THRESHOLD:
            continue
        edt = total_edges / z_int if total_edges > 0 else None
        if edt is not None and not (EDG_MIN <= edt <= EDG_MAX):
            continue
        candidates.append((rel_err, m, z_int, edt))

    if not candidates:
        return None, None
    if len(candidates) == 1:
        _, m, z, _ = candidates[0]
        return z, m

    # Tiebreaker: Kanten-pro-Zahn nächster am Zielwert, dann Integralität
    scored = sorted(
        (abs((edt or 0) - TARGET_EDGES_PER_TOOTH), rel_err, m, z)
        for rel_err, m, z, edt in candidates
    )
    _, _, m_best, z_best = scored[0]
    return z_best, m_best


# ─────────────────────────────────────────────
# PRIO 1: Modul berechnen
# ─────────────────────────────────────────────

# DIN 780 Normmoduln
STANDARD_MODULES = [
    0.1, 0.12, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8,
    1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0,
    10.0, 12.0, 16.0, 20.0, 25.0, 32.0, 40.0, 50.0
]

def calculate_module(outer_diameter_mm: float, num_teeth: int) -> Optional[float]:
    """
    Berechnet den Modul aus Außendurchmesser und Zähnezahl.
    Formel: d_a = m * (z + 2)  →  m = d_a / (z + 2)
    Rundet auf nächsten DIN 780 Normmodul.
    """
    if num_teeth is None or num_teeth <= 0:
        return None

    m_raw = outer_diameter_mm / (num_teeth + 2)
    m_norm = min(STANDARD_MODULES, key=lambda m: abs(m - m_raw))

    # Max. 15% Abweichung → Rohwert wenn kein passender Normmodul
    if abs(m_raw - m_norm) / m_norm > 0.15:
        return round(m_raw, 3)

    return m_norm


# ─────────────────────────────────────────────
# PRIO 2: Vollständige Zahnprofil-Parameter
# ─────────────────────────────────────────────

def calculate_tooth_profile(
    num_teeth: int,
    module_mm: float,
    outer_diameter_mm: float,
    root_diameter_mm_direct: Optional[float],
    is_internal: bool
) -> dict:
    """
    Berechnet alle abgeleiteten Zahnprofil-Parameter.

    Gibt dict zurück mit: d, d_f, h, h_a, h_f, x, s
    """
    result = {}

    # Teilkreisdurchmesser d = m * z
    d = round(module_mm * num_teeth, 3)
    result["pitch_diameter_mm"] = d

    # Fußkreis d_f: direkt aus Geometrie bevorzugt, sonst berechnet
    if root_diameter_mm_direct is not None:
        d_f = root_diameter_mm_direct
    elif is_internal:
        d_f = round(module_mm * (num_teeth + 2.5), 3)
    else:
        d_f = round(module_mm * (num_teeth - 2.5), 3)
    result["root_diameter_mm"] = d_f

    # Zahnhöhe h = (d_a - d_f) / 2
    h = round((outer_diameter_mm - d_f) / 2, 3)
    result["tooth_height_mm"] = h

    # Standardaddendum h_a = m, Standarddedendum h_f = 1.25 * m
    h_a = round(module_mm * 1.0, 3)
    h_f = round(module_mm * 1.25, 3)
    result["addendum_mm"] = h_a
    result["dedendum_mm"] = h_f

    # Profilverschiebung x: Abweichung von Standardkopfhöhe
    # x = h_a_ist / m - 1.0  (Standard: x=0 → h_a = m)
    h_a_actual = round((outer_diameter_mm - d) / 2, 3)   # gemessen
    x = round(h_a_actual / module_mm - 1.0, 3)
    if abs(x) < 0.05:   # Rauschen filtern
        x = 0.0
    result["profile_shift_x"] = x

    # Zahndicke s am Teilkreis (Standardverzahnung ohne Profilverschiebung)
    s = round(math.pi * module_mm / 2, 3)
    result["tooth_thickness_mm"] = s

    return result


# ─────────────────────────────────────────────
# PRIO 2: Schrägungswinkel schätzen
# ─────────────────────────────────────────────

def detect_helix_angle(edge_angles_to_z: List[float], face_width_mm: float) -> Optional[float]:
    """
    Berechnet den Schrägungswinkel β basierend auf den exakten Kantenvektoren.
    """
    if not edge_angles_to_z:
        return None

    # Ignoriere Kanten nahe 90° (Stirnflächen, Flansche)
    relevant_angles = [a for a in edge_angles_to_z if 0 <= a < 45]
    
    if not relevant_angles:
        return None

    # Bilde den Durchschnitt der relevanten Winkel
    avg_angle = sum(relevant_angles) / len(relevant_angles)
    
    if avg_angle < 2.0:
        return 0.0   # Stirnverzahnung
    
    return round(avg_angle, 1)


# ─────────────────────────────────────────────
# PRIO 2: Masse schätzen
# ─────────────────────────────────────────────

# Materialdichte-Lookup (g/cm³)
MATERIAL_DENSITY = {
    "16MnCr5":  7.85,
    "42CrMo4":  7.85,
    "18CrNiMo7-6": 7.85,
    "C45":      7.85,
    "1.4301":   7.93,   # Edelstahl
    "Aluminium": 2.70,
    "PA66":     1.14,   # Kunststoff
}
DEFAULT_DENSITY = 7.85   # Stahl

def estimate_mass(volume_mm3: float, material: Optional[str]) -> Optional[float]:
    """Schätzt die Masse in kg aus Volumen und Materialdichte."""
    if volume_mm3 <= 0:
        return None
    density = DEFAULT_DENSITY
    if material:
        for key, rho in MATERIAL_DENSITY.items():
            if key.lower() in material.lower():
                density = rho
                break
    mass_kg = round(volume_mm3 * density * 1e-6, 4)   # mm³ × g/cm³ → kg (1cm³=1000mm³, 1kg=1000g)
    return mass_kg


# ─────────────────────────────────────────────
# PRIO 2: Normreferenzen zuweisen
# ─────────────────────────────────────────────

NORM_MAP = {
    "spur":     ["DIN 867", "DIN ISO 1328-1", "ISO 1122-1"],
    "helical":  ["DIN 867", "DIN ISO 1328-1", "ISO 1122-1"],
    "bevel":    ["DIN 868", "DIN ISO 17485", "ISO 23509"],
    "internal": ["DIN 867", "DIN ISO 1328-1"],
    "worm":     ["DIN 3975", "ISO 1122-2"],
    "rack":     ["DIN 867", "DIN 3960"],
    "unknown":  ["DIN 867"],
}

def assign_norm_reference(gear_type: Optional[str]) -> list:
    """Weist passende DIN/ISO-Normen basierend auf dem Zahnrad-Typ zu."""
    if gear_type is None:
        return []
    return NORM_MAP.get(gear_type, ["DIN 867"])


# ─────────────────────────────────────────────
# Hauptfunktion
# ─────────────────────────────────────────────

def analyze_gear_geometry(
    params: GearParameters,
    cylinders: List[Tuple[float, bool]],
    planes: int,
    cones: list,
    tori: list,
    total_edges: int,
    edge_lengths: List[float],
    edge_angles_to_z: List[float]
) -> GearParameters:
    """
    Hauptfunktion: Leitet alle Zahnrad-Parameter aus den Rohdaten ab.
    Gibt das aktualisierte GearParameters-Objekt zurück.
    """

    # ── Typ erkennen ───────────────────────────────────────────────
    gear_type, is_internal, cone_angle = detect_gear_type(cylinders, planes, cones, tori)
    params.gear_type = gear_type
    params.is_internal_gear = is_internal
    params.cone_angle_deg = cone_angle
    params.symmetry_type = "translational" if gear_type == "rack" else "rotational"
    params.extraction_notes["gear_type"] = "Erkannt anhand Flächen-Verteilung"
    print(f"  Zahnrad-Typ:       {gear_type}  (Innenverzahnung: {is_internal})")
    if cone_angle is not None:
        print(f"  Konuswinkel δ:     {cone_angle}°")

    # ── Zahnzahl + Modul schätzen (v2: Durchmesser-Enumeration) ───
    num_teeth, m_hint = estimate_z_from_diameter(params.outer_diameter_mm, total_edges)
    if num_teeth is None:
        num_teeth = estimate_num_teeth(total_edges, 0, tori)
        m_hint = None
    params.num_teeth = num_teeth
    if num_teeth:
        params.extraction_notes["num_teeth"] = "Geschätzt via Modul-Enumeration (d_a + Kantenzahl)"
        params.warnings.append(f"Zahnzahl z={num_teeth} ist eine Schätzung — bitte prüfen")
        print(f"  Zahnzahl z:        {num_teeth} (geschätzt)")
    else:
        params.confidence = min(params.confidence, 0.5)
        params.warnings.append("Zahnzahl konnte nicht automatisch erkannt werden")
        print("  Zahnzahl z:        nicht erkannt")

    # ── Modul berechnen ────────────────────────────────────────────
    if num_teeth:
        module_mm = m_hint if m_hint is not None else calculate_module(params.outer_diameter_mm, num_teeth)
        params.module_mm = module_mm
        if module_mm:
            params.extraction_notes["module"] = (
                f"m = d_a/(z+2) = {params.outer_diameter_mm}/({num_teeth}+2), "
                f"gerundet auf DIN 780 Normmodul"
            )
            print(f"  Modul m:           {module_mm} mm (DIN 780)")

            # Vollständige Zahnprofil-Parameter
            profile = calculate_tooth_profile(
                num_teeth, module_mm,
                params.outer_diameter_mm,
                params.root_diameter_mm,   # direkt aus Geometrie (kann None sein)
                is_internal
            )
            params.pitch_diameter_mm   = profile["pitch_diameter_mm"]
            params.root_diameter_mm    = profile["root_diameter_mm"]
            params.tooth_height_mm     = profile["tooth_height_mm"]
            params.addendum_mm         = profile["addendum_mm"]
            params.dedendum_mm         = profile["dedendum_mm"]
            params.profile_shift_x     = profile["profile_shift_x"]
            params.tooth_thickness_mm  = profile["tooth_thickness_mm"]

            print(f"  Teilkreis d:       {params.pitch_diameter_mm} mm")
            print(f"  Fußkreis d_f:      {params.root_diameter_mm} mm")
            print(f"  Zahnhöhe h:        {params.tooth_height_mm} mm")
            print(f"  Profilverschiebung x: {params.profile_shift_x}")
            if params.profile_shift_x != 0.0:
                params.warnings.append("Profilverschiebung x basiert auf Kopfkreis und ignoriert eventuelle Kopfkürzungen.")

    # ── Schrägungswinkel ───────────────────────────────────────────
    beta = detect_helix_angle(edge_angles_to_z, params.face_width_mm)
    params.helix_angle_deg = beta
    if beta is not None:
        if beta == 0.0:
            params.gear_type = "spur" if not is_internal else "internal"
            print("  Schrägungswinkel:  0° → Stirnverzahnung bestätigt")
        else:
            params.gear_type = "helical"
            params.extraction_notes["helix_angle"] = "Aus Kantenvektoren zur Z-Achse ermittelt"
            params.warnings.append(f"Schrägungswinkel β={beta}° ist eine Schätzung")
            print(f"  Schrägungswinkel:  {beta}° → Schrägverzahnung erkannt")
    else:
        params.warnings.append("Schrägungswinkel nicht bestimmbar")
        print("  Schrägungswinkel:  nicht bestimmbar")

    # ── Masse schätzen ─────────────────────────────────────────────
    params.mass_kg = estimate_mass(params.volume_mm3, params.material)
    if params.mass_kg:
        print(f"  Masse (geschätzt): {params.mass_kg} kg")

    # ── Normreferenzen ─────────────────────────────────────────────
    params.norm_reference = assign_norm_reference(params.gear_type)

    return params
