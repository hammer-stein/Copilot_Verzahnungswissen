"""
geometry_analyzer.py
--------------------
Schritt 2: Zahnrad-Parameter aus Rohdaten ableiten.

Bekommt die Rohdaten vom step_parser.py und berechnet daraus alle
ableitbaren Zahnrad-Parameter gemäß den definierten Parametern.
Jeder abgeleitete Parameter erhält einen Konfidenzwert (0.0–1.0).
"""

import math
from typing import List, Tuple, Optional, Any

from output_schema import GearParameters, ParameterValue, C
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

    aspect_ratio = face_width_mm / max(outer_diameter_mm, 1.0)

    significant_cones = [(a, i) for a, i in cones if abs(math.degrees(a)) > 5.0]
    cone_fraction = len(cones) / max(total_faces, 1)
    if len(significant_cones) >= 4 and cone_fraction > 0.05:
        angles_deg = [abs(math.degrees(a)) for a, _ in significant_cones]
        cone_angle = round(sum(angles_deg) / len(angles_deg), 2)
        return "bevel", False, cone_angle

    tori_per_cyl = len(tori) / max(num_cylinders, 1)
    if aspect_ratio > 1.5 and (tori_per_cyl > 8 or aspect_ratio > 3.0):
        return "worm", False, None

    tori_fraction = len(tori) / max(total_faces, 1)
    if tori_fraction > 0.30 and aspect_ratio < 1.0 and num_cylinders > 0 and total_faces > 0:
        return "worm_wheel", False, None

    is_internal = (len(inner_cylinders) > len(outer_cylinders)
                   and len(inner_cylinders) >= 2)
    if is_internal:
        return "internal", True, None

    if num_cylinders == 0 and planes > 10:
        return "rack", False, None

    return "spur", False, None


# ─────────────────────────────────────────────
# PRIO 1: Zahnzahl schätzen
# ─────────────────────────────────────────────

def estimate_num_teeth(total_edges: int, total_faces: int, tori: list) -> Optional[int]:
    """
    Schätzt die Zahnzahl aus der Topologie (Fallback-Methode via Tori).

    Methode: Torische Flächen = Zahnfuß-Verrundungen.
        FreeCAD: je 2 Tori/Zahn.  SolidWorks: je 2.  CATIA/NX: je 1–2.
    """
    if total_edges < 20:
        return None

    num_tori = len(tori)
    if num_tori >= 2:
        for tori_per_tooth in (2, 1):
            estimated_z = num_tori // tori_per_tooth
            if 5 <= estimated_z <= 200:
                return estimated_z

    # Fallback via Kantenzahl (FreeCAD: ~36 Kanten/Zahn)
    z_edge = round(total_edges / 36)
    if 5 <= z_edge <= 200:
        return z_edge

    return None


def estimate_z_from_diameter(
    outer_diameter_mm: float, total_edges: int
) -> Tuple[Optional[int], Optional[float]]:
    """
    Primärmethode: Berechnet (z, m) gemeinsam aus d_a und optionaler Kantenzahl.

    Für jeden DIN-780-Modul: z_raw = d_a/m - 2.  Kandidaten mit nahezu-
    ganzzahligem z_raw (Integralitätsfehler < 12 %) werden gesammelt.
    """
    INTEGRALITY_THRESHOLD = 0.12
    EDG_MIN, EDG_MAX = 5, 120

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

    # Tiebreaker: candidate whose edges-per-tooth is closest to 36 (FreeCAD standard)
    EDGES_PER_TOOTH_TYPICAL = 36
    if total_edges > 0:
        best = min(
            candidates,
            key=lambda c: (c[0], abs(total_edges / c[2] - EDGES_PER_TOOTH_TYPICAL), c[1]),
        )
    else:
        best = min(candidates)  # (rel_err, m, z) — smallest rel_err, then smaller m
    _, m_best, z_best = best
    return z_best, m_best


# ─────────────────────────────────────────────
# PRIO 1: Modul berechnen
# ─────────────────────────────────────────────

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

    Gibt dict zurück mit: pitch_diameter_mm, root_diameter_mm, tooth_height_mm,
                          addendum_mm, dedendum_mm, profile_shift_x, tooth_thickness_mm
    """
    result = {}

    d = round(module_mm * num_teeth, 3)
    result["pitch_diameter_mm"] = d

    if root_diameter_mm_direct is not None:
        d_f = root_diameter_mm_direct
    elif is_internal:
        d_f = round(module_mm * (num_teeth + 2.5), 3)
    else:
        d_f = round(module_mm * (num_teeth - 2.5), 3)
    result["root_diameter_mm"] = d_f

    h = round((outer_diameter_mm - d_f) / 2, 3)
    result["tooth_height_mm"] = h

    h_a = round(module_mm * 1.0, 3)
    h_f = round(module_mm * 1.25, 3)
    result["addendum_mm"] = h_a
    result["dedendum_mm"] = h_f

    h_a_actual = round((outer_diameter_mm - d) / 2, 3)
    x = round(h_a_actual / module_mm - 1.0, 3)
    if abs(x) < 0.05:
        x = 0.0
    result["profile_shift_x"] = x

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
    """
    if not edge_helix_data or pitch_radius is None or pitch_radius <= 0:
        return None

    beta_candidates = []
    for _avg_r, d_theta_dz in edge_helix_data:
        tan_beta = pitch_radius * abs(d_theta_dz)
        if tan_beta < 0.005:
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

MATERIAL_DENSITY = {
    "16MnCr5":  7.85,
    "42CrMo4":  7.85,
    "18CrNiMo7-6": 7.85,
    "C45":      7.85,
    "1.4301":   7.93,
    "Aluminium": 2.70,
    "PA66":     1.14,
}
DEFAULT_DENSITY = 7.85

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
    return round(volume_mm3 * density * 1e-6, 4)


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
# Primärquelle: direkte Vermessung (gear_metrology)
# ─────────────────────────────────────────────

def _apply_metrology(params: GearParameters, m: dict) -> bool:
    """
    Übernimmt die direkt aus der B-Rep vermessenen Kerngrößen (software-
    unabhängig, siehe gear_metrology.py) als hochkonfidente Primärquelle.

    Liefert True, wenn die Vermessung verwendet wurde.
    """
    if not m or not m.get("ok"):
        return False

    z = m["num_teeth"]
    d_a = m["tip_diameter_mm"]
    d_f = m["root_diameter_mm"]
    mod = m["module_mm"]
    is_internal = bool(m["is_internal"])
    is_bevel = bool(m["is_bevel"])
    is_ratchet = bool(m.get("is_ratchet"))
    helix = m.get("helix_angle_deg")

    # ── Verzahnungstyp aus gemessener Geometrie ───────────────────
    if is_ratchet:
        gear_type = "ratchet"
    elif is_bevel:
        gear_type = "bevel"
    elif is_internal:
        gear_type = "internal"
    elif helix is not None and helix >= 5.0:
        gear_type = "helical"
    else:
        gear_type = "spur"

    params.gear_type = ParameterValue.make(gear_type, "", C.DIRECT)
    params.is_internal_gear = is_internal
    params.symmetry_type = "rotational"
    params.extraction_notes["method"] = (
        "Direkte Vermessung über planare Querschnitte — herstellerunabhängig"
    )
    if is_bevel and m.get("cone_angle_deg") is not None:
        params.cone_angle_deg = ParameterValue.make(m["cone_angle_deg"], "°", C.CALC)
        params.shaft_angle_deg = ParameterValue.make(90.0, "°", C.FALLBACK)

    # ── Direkt gemessene Größen ───────────────────────────────────
    params.num_teeth = ParameterValue.make(int(z), "", C.DIRECT)
    params.outer_diameter_mm = ParameterValue.make(d_a, "mm", C.DIRECT)
    params.module_mm = ParameterValue.make(
        mod, "mm", C.DIRECT if m.get("module_is_norm") else C.CALC
    )
    if m.get("bore_diameter_mm"):
        params.hub_bore_diameter_mm = ParameterValue.make(
            m["bore_diameter_mm"], "mm", C.DIRECT
        )
    if m.get("overall_width_mm"):
        # Gesamtbreite aus der gemessenen Achsausdehnung (überschreibt den
        # Bounding-Box-Wert, der bei nicht-achsparalleler Orientierung falsch ist)
        params.total_width_mm = ParameterValue.make(m["overall_width_mm"], "mm", C.DIRECT)
    if m.get("hub_diameter_mm"):
        params.hub_diameter_mm = ParameterValue.make(m["hub_diameter_mm"], "mm", C.DIRECT)
    if m.get("hub_width_mm"):
        # Nabenbreite: Zylinder-Stirnflächen können durch Fasen/Verrundungen
        # leicht kürzer ausfallen → etwas geringere Konfidenz.
        params.hub_width_mm = ParameterValue.make(m["hub_width_mm"], "mm", round(C.CALC - 0.1, 2))
    # Zahnbreite: volltiefer Bereich; bei Werkzeugauslauf leicht unscharf
    params.face_width_mm = ParameterValue.make(
        m["face_width_mm"], "mm", round(C.CALC - 0.12, 2)
    )

    # ── Abgeleitetes Zahnprofil aus den Messwerten ────────────────
    profile = calculate_tooth_profile(int(z), mod, d_a, d_f, is_internal)
    params.pitch_diameter_mm  = ParameterValue.make(profile["pitch_diameter_mm"],  "mm", C.CALC)
    params.root_diameter_mm   = ParameterValue.make(d_f,                            "mm", C.DIRECT)
    params.tooth_height_mm    = ParameterValue.make(profile["tooth_height_mm"],     "mm", C.CALC)
    params.addendum_mm        = ParameterValue.make(profile["addendum_mm"],         "mm", C.CALC)
    params.dedendum_mm        = ParameterValue.make(profile["dedendum_mm"],         "mm", C.CALC)
    params.profile_shift_x    = ParameterValue.make(profile["profile_shift_x"],    "",   C.FALLBACK)
    params.tooth_thickness_mm = ParameterValue.make(profile["tooth_thickness_mm"],  "mm", C.CALC)

    # ── Schrägungswinkel ──────────────────────────────────────────
    if helix is not None:
        params.helix_angle_deg = ParameterValue.make(helix, "°", C.CALC)

    # ── Fußrundungsradius plausibilisieren ────────────────────────
    # Ein echter Zahnfuß-Radius liegt bei ~0.1–0.4·m. Größere Werte stammen aus
    # fehlklassifizierten Übergangs-Tori und werden verworfen.
    rf_pv = params.root_fillet_radius_mm
    if isinstance(rf_pv, ParameterValue) and rf_pv.value is not None:
        if not (0.05 * mod <= rf_pv.value <= 0.5 * mod):
            params.root_fillet_radius_mm = None
            params.warnings.append(
                f"Fußrundungsradius {rf_pv.value}mm unplausibel für m={mod} — verworfen"
            )

    # ── Kegelrad: Fußkreis & Tiefenmaße als Schätzung markieren ───────
    # Bei Kegelrädern liegt der Lückengrund je achsnormaler Schnittebene auf einer
    # anderen Kegelposition; der so gemessene Fußkreis (und davon abgeleitete
    # Maße) ist daher nicht der Norm-Fußkreis am großen Ende. Werte bleiben
    # erhalten, werden aber als grobe Schätzung gekennzeichnet (ehrliche Konfidenz).
    if is_bevel:
        for attr in ("root_diameter_mm", "tooth_height_mm", "dedendum_mm", "profile_shift_x"):
            pv = getattr(params, attr, None)
            if isinstance(pv, ParameterValue):
                pv.confidence = C.HEURISTIC
        params.warnings.append(
            "Kegelrad: Fußkreis und abgeleitete Tiefenmaße nur grob "
            "(Konfundierung durch achsnormale Schnitte) — am großen Ende prüfen"
        )

    # ── Ratschenrad: Sägezahn-Profil — Evolventen-Kenngrößen gelten nicht ──
    # Zähnezahl und Außendurchmesser sind aussagekräftig; Modul, Eingriffs-
    # winkel, Teilkreis etc. sind beim Ratschenrad bedeutungslos.
    if is_ratchet:
        for attr in ("module_mm", "pitch_diameter_mm", "root_diameter_mm",
                     "tooth_height_mm", "addendum_mm", "dedendum_mm",
                     "profile_shift_x", "tooth_thickness_mm"):
            pv = getattr(params, attr, None)
            if isinstance(pv, ParameterValue):
                pv.confidence = C.HEURISTIC
        if isinstance(params.pressure_angle_deg, ParameterValue):
            params.pressure_angle_deg.confidence = C.HEURISTIC
        params.warnings.append(
            "Ratschenrad (Sägezahn): z und Außendurchmesser gültig; Modul, "
            "Eingriffswinkel und Teilkreis sind hier nicht aussagekräftig"
        )

    print(f"  [Metrologie] Typ={gear_type}  z={int(z)}  m={mod}mm  "
          f"d_a={d_a}mm  d_f={d_f}mm  d={profile['pitch_diameter_mm']}mm  "
          f"b={m['face_width_mm']}mm  β={helix}°  Bohrung={m.get('bore_diameter_mm')}mm")
    return True


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
    total_faces: int = 0,
    face_parse_success_rate: float = 1.0,
    metrology: dict = None,
) -> GearParameters:
    """
    Hauptfunktion: Leitet alle Zahnrad-Parameter aus den Rohdaten ab.
    Weist jedem Parameter einen Konfidenzwert zu.
    Gibt das aktualisierte GearParameters-Objekt zurück.

    Wenn `metrology` (direkte Querschnitts-Vermessung, software-unabhängig)
    erfolgreich war, dient sie als Primärquelle; sonst greifen die Heuristiken.
    """

    def _val(pv: Any) -> float:
        """Rohwert aus ParameterValue oder plain float."""
        if isinstance(pv, ParameterValue):
            return pv.value or 0.0
        return pv or 0.0

    outer_d = _val(params.outer_diameter_mm)
    face_w  = _val(params.face_width_mm)

    used_metrology = _apply_metrology(params, metrology)
    is_internal = bool(metrology.get("is_internal")) if used_metrology else False
    gear_type = (
        params.gear_type.value if isinstance(params.gear_type, ParameterValue) else "spur"
    ) if used_metrology else "spur"

    if not used_metrology:
        # ── Typ erkennen ───────────────────────────────────────────────
        gear_type, is_internal, cone_angle = detect_gear_type(
            cylinders, planes, cones, tori, outer_d, face_w, total_faces
        )
        params.gear_type = ParameterValue.make(gear_type, "", round(C.DIRECT - 0.04, 2))
        params.is_internal_gear = is_internal
        params.cone_angle_deg = (
            ParameterValue.make(cone_angle, "°", C.CALC) if cone_angle is not None else None
        )
        params.symmetry_type = "translational" if gear_type == "rack" else "rotational"
        params.extraction_notes["gear_type"] = "Erkannt anhand Flächen-Verteilung und Geometrie-Kenngrößen"
        print(f"  Zahnrad-Typ:       {gear_type}  (Innenverzahnung: {is_internal})")
        if cone_angle is not None:
            print(f"  Konuswinkel δ:     {cone_angle}°")

        # ── Zahnzahl + Modul schätzen ──────────────────────────────────
        num_teeth, m_hint = estimate_z_from_diameter(outer_d, total_edges)

        if num_teeth is not None:
            z_conf = round(C.CALC - 0.07, 2)   # 0.75 — Durchmesser-Enumeration
            params.num_teeth = ParameterValue.make(num_teeth, "", z_conf)
            params.extraction_notes["num_teeth"] = "Geschätzt via Modul-Enumeration (d_a + Kantenzahl)"
            params.warnings.append(f"Zahnzahl z={num_teeth} ist eine Schätzung — bitte prüfen")
            print(f"  Zahnzahl z:        {num_teeth} (via Durchmesser-Enumeration)")
        else:
            num_teeth_tori = estimate_num_teeth(total_edges, 0, tori)
            m_hint = None
            if num_teeth_tori is not None:
                num_teeth = num_teeth_tori
                z_conf = C.FALLBACK   # 0.65 — Torus-Zählung
                params.num_teeth = ParameterValue.make(num_teeth, "", z_conf)
                params.extraction_notes["num_teeth"] = "Geschätzt via Torus-Zählung"
                params.warnings.append(f"Zahnzahl z={num_teeth} aus Tori-Zählung — bitte prüfen")
                print(f"  Zahnzahl z:        {num_teeth} (via Tori)")
            else:
                params.num_teeth = ParameterValue.make(None, "", C.HEURISTIC)
                params.overall_confidence = min(params.overall_confidence, 0.5)
                params.warnings.append("Zahnzahl konnte nicht automatisch erkannt werden")
                print("  Zahnzahl z:        nicht erkannt")

        # ── Modul berechnen ────────────────────────────────────────────
        module_mm = None
        if num_teeth:
            if m_hint is not None:
                module_mm = m_hint
                m_conf = C.CALC   # 0.82 — m aus derselben Enumeration wie z
            else:
                module_mm = calculate_module(outer_d, num_teeth)
                m_conf = C.FALLBACK  # 0.65 — m aus z-Fallback berechnet

            params.module_mm = ParameterValue.make(module_mm, "mm", m_conf)

            if module_mm:
                params.extraction_notes["module"] = (
                    f"m = d_a/(z+2) = {outer_d}/({num_teeth}+2), gerundet auf DIN 780 Normmodul"
                )
                print(f"  Modul m:           {module_mm} mm (DIN 780)")

                # ── Vollständige Zahnprofil-Parameter ─────────────────
                root_d_direct = _val(params.root_diameter_mm) if params.root_diameter_mm else None
                root_was_direct = params.root_diameter_mm is not None

                profile = calculate_tooth_profile(
                    num_teeth, module_mm, outer_d, root_d_direct, is_internal
                )

                params.pitch_diameter_mm  = ParameterValue.make(profile["pitch_diameter_mm"],  "mm", C.CALC)
                root_conf = C.DIRECT if root_was_direct else C.FALLBACK
                if not root_was_direct:
                    params.warnings.append("d_f aus Formel berechnet (kein Fußkreis-Zylinder gefunden)")
                params.root_diameter_mm   = ParameterValue.make(profile["root_diameter_mm"],   "mm", root_conf)
                params.tooth_height_mm    = ParameterValue.make(profile["tooth_height_mm"],    "mm", C.CALC)
                params.addendum_mm        = ParameterValue.make(profile["addendum_mm"],        "mm", C.CALC)
                params.dedendum_mm        = ParameterValue.make(profile["dedendum_mm"],        "mm", C.CALC)
                params.profile_shift_x    = ParameterValue.make(profile["profile_shift_x"],   "",   C.FALLBACK)
                params.tooth_thickness_mm = ParameterValue.make(profile["tooth_thickness_mm"], "mm", C.CALC)

                print(f"  Teilkreis d:       {profile['pitch_diameter_mm']} mm")
                print(f"  Fußkreis d_f:      {profile['root_diameter_mm']} mm")
                print(f"  Zahnhöhe h:        {profile['tooth_height_mm']} mm")
                print(f"  Profilverschiebung x: {profile['profile_shift_x']}")

        # ── Schrägungswinkel (3D-Kurven-Abtastung) ────────────────────
        pitch_d_val = _val(params.pitch_diameter_mm) if params.pitch_diameter_mm else outer_d
        pitch_radius = (pitch_d_val / 2) if pitch_d_val else (outer_d / 2)

        if gear_type in ("spur", "helical"):
            beta = detect_helix_angle_v2(edge_helix_data, pitch_radius)
            if beta is not None:
                helix_conf = C.FALLBACK if edge_helix_data else C.HEURISTIC
                params.helix_angle_deg = ParameterValue.make(beta, "°", helix_conf)
                if beta == 0.0:
                    params.gear_type = ParameterValue.make(
                        "spur" if not is_internal else "internal", "", round(C.DIRECT - 0.04, 2)
                    )
                    print("  Schrägungswinkel:  0° → Stirnverzahnung bestätigt")
                else:
                    params.gear_type = ParameterValue.make("helical", "", round(C.DIRECT - 0.04, 2))
                    params.extraction_notes["helix_angle"] = (
                        "Aus Helixsteigung dθ/dz der Zahnflankenkanten berechnet"
                    )
                    params.warnings.append(f"Schrägungswinkel β={beta}° aus 3D-Kurven-Abtastung")
                    print(f"  Schrägungswinkel:  {beta}° → Schrägverzahnung erkannt")
            else:
                params.helix_angle_deg = ParameterValue.make(None, "°", C.HEURISTIC)
                params.warnings.append("Schrägungswinkel nicht bestimmbar (keine geeigneten Kanten)")
                print("  Schrägungswinkel:  nicht bestimmbar")
        else:
            print(f"  Schrägungswinkel:  nicht relevant für Typ '{gear_type}'")

    # ── face_parse_success_rate als Korrekturfaktor ───────────────
    if face_parse_success_rate < 1.0:
        for attr in ("num_teeth", "module_mm", "outer_diameter_mm", "root_diameter_mm"):
            pv = getattr(params, attr, None)
            if isinstance(pv, ParameterValue):
                pv.confidence = round(pv.confidence * face_parse_success_rate, 3)

    # ── Gesamt-Konfidenz (geometrisches Mittel ausgewählter Felder) ─
    _conf_sources = [
        params.outer_diameter_mm, params.face_width_mm, params.gear_type,
        params.num_teeth, params.module_mm, params.pitch_diameter_mm,
        params.root_diameter_mm, params.tooth_height_mm, params.helix_angle_deg,
    ]
    _conf_vals = [
        f.confidence for f in _conf_sources
        if isinstance(f, ParameterValue) and f.value is not None and f.confidence > 0
    ]
    if _conf_vals:
        computed = round(math.exp(sum(math.log(v) for v in _conf_vals) / len(_conf_vals)), 3)
        params.overall_confidence = min(params.overall_confidence, computed)

    # ── Masse schätzen ─────────────────────────────────────────────
    vol = _val(params.volume_mm3) if params.volume_mm3 else 0.0
    params.mass_kg = estimate_mass(vol, params.material)
    if params.mass_kg:
        print(f"  Masse (geschätzt): {params.mass_kg} kg")

    # ── Normreferenzen ─────────────────────────────────────────────
    gear_type_val = (
        params.gear_type.value if isinstance(params.gear_type, ParameterValue) else gear_type
    )
    params.norm_reference = assign_norm_reference(gear_type_val)

    # ── Hinweise (Normen, Anwendung, Fertigung, Qualität, Optimierung) ──
    params.hints = generate_gear_hints(params)

    return params
