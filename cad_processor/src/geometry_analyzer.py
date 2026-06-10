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
from gear_hints import generate_gear_hints


# ─────────────────────────────────────────────
# PRIO 1: Zahnrad-Typ erkennen
# ─────────────────────────────────────────────

def detect_gear_type(
    cylinders, planes: int, cones: list, tori: list,
    outer_diameter_mm: float = 0.0, face_width_mm: float = 0.0,
    total_faces: int = 0
) -> Tuple[str, bool, Optional[float]]:
    """
    Erkennt den Zahnrad-Typ anhand der Flächen-Verteilung und Geometrie-Kenngrößen.

    Gibt zurück:
        gear_type     : "spur" | "helical" | "bevel" | "internal" | "worm" |
                        "worm_wheel" | "rack" | "unknown"
        is_internal   : True wenn Innenverzahnung
        cone_angle_deg: Halbkegelwinkel in Grad (nur bei Kegelrad), sonst None
    """
    num_cylinders = len(cylinders)
    inner_cylinders = [r for r, is_inner in cylinders if is_inner]
    outer_cylinders = [r for r, is_inner in cylinders if not is_inner]

    # Aspektverhältnis b/d_a (Schnecke >> 1, Stirnrad/Kegelrad << 1)
    aspect_ratio = face_width_mm / max(outer_diameter_mm, 1.0)

    # ── Kegelrad: konische Flächen mit signifikantem Winkel + Mindest-Anteil ──
    # Fasen (45°-Kanten) erzeugen ebenfalls Kegel, aber mit kleiner Flächenzahl.
    # Der Anteilscheck cone_fraction > 0.05 trennt Kegelräder von gefasten Stirnrädern.
    significant_cones = [(a, i) for a, i in cones if abs(math.degrees(a)) > 5.0]
    cone_fraction = len(cones) / max(total_faces, 1)
    if len(significant_cones) >= 4 and cone_fraction > 0.05:
        angles_deg = [abs(math.degrees(a)) for a, _ in significant_cones]
        cone_angle = round(sum(angles_deg) / len(angles_deg), 2)
        return "bevel", False, cone_angle

    # ── Schnecke: stark gestrecktes Aspektverhältnis + hohe Tori-Dichte ──
    # Schnecken haben b/d_a >> 1 (Länge > Durchmesser) und viele
    # Torus-Flächen (je eine pro Gewindegang-Fußrundung).
    tori_per_cyl = len(tori) / max(num_cylinders, 1)
    if aspect_ratio > 1.5 and (tori_per_cyl > 8 or aspect_ratio > 3.0):
        return "worm", False, None

    # ── Schneckenrad: hoher Tori-Anteil bei normalem Aspektverhältnis ──
    # Schneckenrad-Zahnflanken sind Sattelflächen (toroidal), daher
    # liegt der Torus-Anteil deutlich höher als bei Stirnrädern.
    # total_faces > 0 sicherstellt, dass der Anteil sinnvoll berechenbar ist.
    tori_fraction = len(tori) / max(total_faces, 1)
    if tori_fraction > 0.30 and aspect_ratio < 1.0 and num_cylinders > 0 and total_faces > 0:
        return "worm_wheel", False, None

    # ── Innenverzahnung: mehr Innenzylinder als Außenzylinder ──
    is_internal = (len(inner_cylinders) > len(outer_cylinders)
                   and len(inner_cylinders) >= 2)
    if is_internal:
        return "internal", True, None

    # ── Zahnstange: keine Rotationssymmetrie, viele Ebenen ──
    if num_cylinders == 0 and planes > 10:
        return "rack", False, None

    # ── Stirnrad vs. Schrägverzahnung: wird in detect_helix_angle_v2 entschieden ──
    return "spur", False, None


# ─────────────────────────────────────────────
# PRIO 1: Zahnzahl schätzen
# ─────────────────────────────────────────────

def estimate_num_teeth(total_edges: int, total_faces: int, tori: list) -> Optional[int]:
    """
    Schätzt die Zahnzahl aus der Topologie.

    Methode 1 (bevorzugt): Torische Flächen = Zahnfuß-Verrundungen.
        FreeCAD: je 2 Tori/Zahn.  SolidWorks: je 2.  CATIA/NX: je 1–2.
        Probiert 1 und 2 Tori/Zahn und wählt plausiblsten Wert.
    Methode 2 (Fallback):  entfällt — rein kanten-basierte Schätzung
        ist zu CAD-spezifisch (FreeCAD 36, SolidWorks 10–20, CATIA 40–80).
    """
    if total_edges < 20:
        return None

    num_tori = len(tori)
    if num_tori >= 2:
        # Versuche 1 und 2 Tori pro Zahn; bevorzuge den Wert im plausiblen Bereich
        for tori_per_tooth in (2, 1):
            estimated_z = num_tori // tori_per_tooth
            if 5 <= estimated_z <= 200:
                return estimated_z

    return None


def estimate_z_from_diameter(
    outer_diameter_mm: float, total_edges: int
) -> Tuple[Optional[int], Optional[float]]:
    """
    Primärmethode: Berechnet (z, m) gemeinsam aus d_a und optionaler Kantenzahl.

    Für jeden DIN-780-Modul: z_raw = d_a/m - 2.  Kandidaten mit nahezu-
    ganzzahligem z_raw (Integralitätsfehler < 12 %) werden gesammelt.

    Sanity-Filter via Kanten (CAD-agnostisch):
        EDG_MIN / EDG_MAX = [5, 120] — deckt FreeCAD (~36), SolidWorks (~10–20)
        und CATIA (~40–80) ab.  Kanten werden NUR als Ausschlussfilter
        verwendet, NICHT als Tiebreaker-Zielwert.

    Tiebreaker (CAD-agnostisch):
        1. Kleinster Integralitätsfehler (geometrisch am exaktesten)
        2. Bei Gleichstand: größerer Modul bevorzugt (konservativere Schätzung)
    """
    INTEGRALITY_THRESHOLD = 0.12
    EDG_MIN, EDG_MAX = 5, 120   # breit genug für alle gängigen CAD-Exporte

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
        candidates.append((rel_err, m, z_int))

    if not candidates:
        return None, None
    if len(candidates) == 1:
        _, m, z = candidates[0]
        return z, m

    # Tiebreaker: kleinster Integralitätsfehler, bei Gleichstand größerer Modul
    scored = sorted((rel_err, -m, z) for rel_err, m, z in candidates)
    _, neg_m, z_best = scored[0]
    m_best = -neg_m
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
# PRIO 2: Schrägungswinkel aus 3D-Kurven
# ─────────────────────────────────────────────

def detect_helix_angle_v2(edge_helix_data: list,
                           pitch_radius: Optional[float]) -> Optional[float]:
    """
    Berechnet den Schrägungswinkel β aus der Helixsteigung der Zahnflankenkanten.

    Formel: β = arctan(r_pitch × |dθ/dz|)

    edge_helix_data: Liste von (avg_r, d_theta_dz) aus extract_edge_helix_data().
    - Stirnrad  (β=0°): dθ/dz ≈ 0 — Kanten laufen parallel zur Z-Achse
    - Schrägverzahnung: dθ/dz ≠ 0 — Kanten drehen sich um die Z-Achse

    Gibt den Median aller Kandidaten zurück (robust gegen Ausreißer).
    """
    if not edge_helix_data or pitch_radius is None or pitch_radius <= 0:
        return None

    beta_candidates = []
    for _avg_r, d_theta_dz in edge_helix_data:
        tan_beta = pitch_radius * abs(d_theta_dz)
        if tan_beta < 0.005:
            # Unter ~0.3° → Rauschen / Stirnrad-Kante
            beta_candidates.append(0.0)
        else:
            beta_deg = math.degrees(math.atan(tan_beta))
            if 0.5 < beta_deg <= 55:
                beta_candidates.append(beta_deg)

    if not beta_candidates:
        return 0.0

    beta_candidates.sort()
    median_beta = beta_candidates[len(beta_candidates) // 2]
    return round(median_beta, 1) if median_beta > 0.3 else 0.0


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
    "spur":       ["DIN 867", "DIN ISO 1328-1", "ISO 1122-1"],
    "helical":    ["DIN 867", "DIN ISO 1328-1", "ISO 1122-1"],
    "bevel":      ["DIN 868", "DIN ISO 17485", "ISO 23509"],
    "internal":   ["DIN 867", "DIN ISO 1328-1"],
    "worm":       ["DIN 3975", "ISO 1122-2"],
    "worm_wheel": ["DIN 3975", "ISO 1122-2"],
    "rack":       ["DIN 867", "DIN 3960"],
    "unknown":    ["DIN 867"],
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
    edge_helix_data: list,
    total_faces: int = 0
) -> GearParameters:
    """
    Hauptfunktion: Leitet alle Zahnrad-Parameter aus den Rohdaten ab.
    Gibt das aktualisierte GearParameters-Objekt zurück.
    """

    # ── Typ erkennen ───────────────────────────────────────────────
    gear_type, is_internal, cone_angle = detect_gear_type(
        cylinders, planes, cones, tori,
        params.outer_diameter_mm, params.face_width_mm, total_faces
    )
    params.gear_type = gear_type
    params.is_internal_gear = is_internal
    params.cone_angle_deg = cone_angle
    params.symmetry_type = "translational" if gear_type == "rack" else "rotational"
    params.extraction_notes["gear_type"] = "Erkannt anhand Flächen-Verteilung und Geometrie-Kenngrößen"
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

    # ── Schrägungswinkel (3D-Kurven-Abtastung entlang Z-Achse) ────
    # Nur für Stirnrad-Basis-Typ anwenden; Kegelrad/Schnecke nicht überschreiben
    pitch_radius = (params.pitch_diameter_mm / 2
                    if params.pitch_diameter_mm else params.outer_diameter_mm / 2)
    if gear_type in ("spur", "helical"):
        beta = detect_helix_angle_v2(edge_helix_data, pitch_radius)
        params.helix_angle_deg = beta
        if beta is not None:
            if beta == 0.0:
                params.gear_type = "spur" if not is_internal else "internal"
                print("  Schrägungswinkel:  0° → Stirnverzahnung bestätigt")
            else:
                params.gear_type = "helical"
                params.extraction_notes["helix_angle"] = (
                    "Aus Helixsteigung dθ/dz der Zahnflankenkanten berechnet"
                )
                params.warnings.append(f"Schrägungswinkel β={beta}° aus 3D-Kurven-Abtastung")
                print(f"  Schrägungswinkel:  {beta}° → Schrägverzahnung erkannt")
        else:
            params.warnings.append("Schrägungswinkel nicht bestimmbar (keine geeigneten Kanten)")
            print("  Schrägungswinkel:  nicht bestimmbar")
    else:
        print(f"  Schrägungswinkel:  nicht relevant für Typ '{gear_type}'")

    # ── Masse schätzen ─────────────────────────────────────────────
    params.mass_kg = estimate_mass(params.volume_mm3, params.material)
    if params.mass_kg:
        print(f"  Masse (geschätzt): {params.mass_kg} kg")

    # ── Normreferenzen ─────────────────────────────────────────────
    params.norm_reference = assign_norm_reference(params.gear_type)

    # ── Hinweise (Normen, Anwendung, Fertigung, Qualität, Optimierung) ──
    params.hints = generate_gear_hints(params)

    return params
