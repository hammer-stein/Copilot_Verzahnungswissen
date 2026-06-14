"""
step_parser.py
--------------
Schritt 1: STEP-Datei einlesen und Rohdaten extrahieren.

Extrahiert ausschließlich was direkt aus der STEP-Geometrie
lesbar ist. Die Interpretation (Zahnzahl, Modul etc.) macht
geometry_analyzer.py in Schritt 2.

Verwendung:
    python src/step_parser.py --input data/examples/zahnrad.stp
    python src/step_parser.py --input data/examples/zahnrad.stp --output output/result.json
"""

import argparse
import logging
import math
import sys
from pathlib import Path

_log = logging.getLogger("step_parser")

# pythonocc
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import (TopAbs_FACE, TopAbs_EDGE, TopAbs_SOLID,
                             TopAbs_REVERSED, TopAbs_FORWARD)
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCC.Core.GeomAbs import (GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Cone,
                               GeomAbs_Torus, GeomAbs_Line)

# Eigene Module — plattformunabhängiger Pfad über pathlib
sys.path.insert(0, str(Path(__file__).resolve().parent))
from output_schema import GearParameters, ParameterValue, C
from geometry_analyzer import analyze_gear_geometry
from gear_metrology import extract_metrology


# ─────────────────────────────────────────────
# STEP Datei laden
# ─────────────────────────────────────────────

def load_step(filepath: str):
    """
    Lädt eine STEP-Datei robust und gibt die OCC-Shape zurück (oder None).

    Hart gegen reale Exporte aus CATIA/NX/SolidWorks/Creo:
      - prüft Lese- und Transfer-Status explizit,
      - überträgt ALLE Roots (auch Baugruppen mit mehreren Solids),
      - verifiziert, dass eine nicht-leere Geometrie mit Faces vorliegt,
      - fängt jede Exception ab und protokolliert sie, statt abzustürzen.
    """
    path = Path(filepath)
    if not path.is_file():
        _log.error("STEP-Datei nicht gefunden: %s", path)
        print(f"[FEHLER] Datei nicht gefunden: {path}")
        return None

    try:
        reader = STEPControl_Reader()
        status = reader.ReadFile(str(path))
        if status != IFSelect_RetDone:
            _log.error("STEP-Datei nicht lesbar (Status=%s): %s", status, path)
            print(f"[FEHLER] STEP-Datei konnte nicht gelesen werden: {path.name}")
            return None

        n_roots = reader.TransferRoots()      # alle Wurzeln (Baugruppen) übertragen
        shape = reader.OneShape()
        if shape is None or shape.IsNull():
            _log.error("Keine übertragbare Geometrie in %s", path)
            print(f"[FEHLER] STEP-Datei enthält keine Geometrie: {path.name}")
            return None

        # Plausibilität: mindestens eine Fläche vorhanden?
        face_exp = TopExp_Explorer(shape, TopAbs_FACE)
        if not face_exp.More():
            _log.error("Geometrie ohne Flächen (evtl. nur Drahtmodell): %s", path)
            print(f"[FEHLER] STEP-Datei enthält keine Flächen: {path.name}")
            return None

        solid_exp = TopExp_Explorer(shape, TopAbs_SOLID)
        n_solids = 0
        while solid_exp.More():
            n_solids += 1
            solid_exp.Next()
        _log.info("Geladen: %s (Roots=%d, Solids=%d)", path.name, n_roots, n_solids)
        print(f"  -> Geladen: {path.name}  (Roots={n_roots}, Solids={n_solids})")
        return shape

    except Exception as exc:  # noqa: BLE001 — defektes File darf nie abstürzen
        _log.exception("Fehler beim Laden der STEP-Datei %s: %s", path, exc)
        print(f"[FEHLER] Ausnahme beim Laden von {path.name}: {exc}")
        return None


# ─────────────────────────────────────────────
# PRIO 1: Bounding Box
# ─────────────────────────────────────────────

def get_bounding_box(shape):
    """
    Berechnet Bounding Box.
    Gibt (x_mm, y_mm, z_mm) zurück.
    Annahme: Rotationsachse des Zahnrads = Z-Achse.
    """
    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    return (
        round(xmax - xmin, 4),
        round(ymax - ymin, 4),
        round(zmax - zmin, 4)
    )


# ─────────────────────────────────────────────
# PRIO 1: Volumen & Oberfläche
# ─────────────────────────────────────────────

def get_mass_properties(shape):
    """Berechnet Volumen (mm³) und Oberfläche (mm²)."""
    vol_props = GProp_GProps()
    brepgprop.VolumeProperties(shape, vol_props)
    volume = round(vol_props.Mass(), 3)

    surf_props = GProp_GProps()
    brepgprop.SurfaceProperties(shape, surf_props)
    surface = round(surf_props.Mass(), 3)

    return volume, surface


# ─────────────────────────────────────────────
# PRIO 1 & 2: Flächen-Analyse
# ─────────────────────────────────────────────

def analyze_surfaces(shape):
    """
    Iteriert über alle Faces und klassifiziert Oberflächen.
    Jede Face wird einzeln in try/except geschützt — fehlerhafte Faces werden
    gezählt und in face_parse_success_rate zurückgegeben.

    Gibt zurück:
        cylinders            : Liste von (radius_mm, is_inner)
        planes               : Anzahl ebener Flächen
        cones                : Liste von (semi_angle_rad, is_inner)
        tori                 : Liste von Torus-Minor-Radien (r_f-Kandidaten)
        total_faces          : Gesamtzahl Faces
        plane_z_coords       : Z-Koordinaten der ebenen Flächen (für Flanschdetektion)
        face_parse_success_rate : Anteil erfolgreich geparster Faces (0.0–1.0)
    """
    cylinders = []
    planes = 0
    cones = []
    tori = []
    total_faces = 0
    failed_faces = 0
    plane_z_coords = []

    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = explorer.Current()
        total_faces += 1
        try:
            surf = BRepAdaptor_Surface(face)
            stype = surf.GetType()
            is_inner = (face.Orientation() == TopAbs_REVERSED)

            if stype == GeomAbs_Cylinder:
                radius = round(surf.Cylinder().Radius(), 4)
                cylinders.append((radius, is_inner))

            elif stype == GeomAbs_Plane:
                planes += 1
                try:
                    loc = surf.Plane().Location()
                    plane_z_coords.append(round(loc.Z(), 3))
                except Exception:
                    pass

            elif stype == GeomAbs_Cone:
                semi_angle = round(surf.Cone().SemiAngle(), 6)
                cones.append((semi_angle, is_inner))

            elif stype == GeomAbs_Torus:
                minor_r = round(surf.Torus().MinorRadius(), 4)
                if minor_r > 0:
                    tori.append(minor_r)

        except Exception as exc:
            failed_faces += 1
            _log.debug("Face %d classification failed: %s", total_faces, exc)
        explorer.Next()

    face_parse_success_rate = (
        (total_faces - failed_faces) / total_faces if total_faces > 0 else 1.0
    )
    return cylinders, planes, cones, tori, total_faces, plane_z_coords, face_parse_success_rate


# ─────────────────────────────────────────────
# PRIO 1: Zylinder-Hierarchie auswerten
# ─────────────────────────────────────────────

def extract_cylinder_hierarchy(cylinders):
    """
    Klassifiziert Zylinder nach Größe und Orientierung.

    Gibt zurück:
        outer_r  : Größter Außenzylinder-Radius → d_a / 2
        root_r   : Mittlerer Innen-Radius → d_f / 2 (Zahnfuß-Zylinder)
        bore_r   : Kleinster Innen-Radius → d_N / 2 (Nabenbohrung)
    """
    if not cylinders:
        return None, None, None

    outer_radii = sorted([r for r, inner in cylinders if not inner], reverse=True)
    inner_radii = sorted([r for r, inner in cylinders if inner])

    outer_r = outer_radii[0] if outer_radii else None

    # Innen-Radien: Kleinster = Nabenbohrung, größter Innen-Radius nahe Zahnfuß
    bore_r = inner_radii[0] if inner_radii else None
    root_r = inner_radii[-1] if len(inner_radii) > 1 else None

    # Wenn nur ein Innen-Zylinder: Unterscheidung schwierig
    if len(inner_radii) == 1:
        bore_r = inner_radii[0]
        root_r = None

    return outer_r, root_r, bore_r


# ─────────────────────────────────────────────
# PRIO 2: Kanten-Analyse
# ─────────────────────────────────────────────

def analyze_edges(shape):
    """
    Zählt Kanten und ihre Längen.
    Periodische Muster deuten auf Zähne hin.
    Kurze parallele Kanten-Cluster → Passfedernut (keyway).
    """
    total_edges = 0
    edge_lengths = []
    short_edges = 0   # kurze, gerade Kanten (Passfedernut-Indikator)

    explorer = TopExp_Explorer(shape, TopAbs_EDGE)
    while explorer.More():
        edge = explorer.Current()
        total_edges += 1
        try:
            props = GProp_GProps()
            brepgprop.LinearProperties(edge, props)
            length = round(props.Mass(), 4)
            if length > 0:
                edge_lengths.append(length)
                if length < 5.0:   # kurze Kante < 5 mm = Nut-Kandidat
                    short_edges += 1
        except Exception:
            pass
        explorer.Next()

    # Passfedernut-Heuristik: viele kurze Kanten relativ zur Gesamtzahl
    keyway_present = None
    if total_edges > 0:
        short_ratio = short_edges / total_edges
        if short_ratio > 0.15 and short_edges >= 4:
            keyway_present = True
        elif total_edges > 20:
            keyway_present = False

    return total_edges, edge_lengths, keyway_present


# ─────────────────────────────────────────────
# PRIO 2: Helix-Abtastung für Schrägungswinkel
# ─────────────────────────────────────────────

def extract_edge_helix_data(shape, outer_radius: float, face_width_mm: float) -> list:
    """
    Tastet alle nicht-linearen Kanten als 3D-Kurven ab und berechnet dθ/dz
    in Zylinderkoordinaten (r, θ, z).

    Gibt Liste von (avg_r, d_theta_dz) zurück — nur Kanten mit signifikantem Z-Span
    nahe der Zahnflanke (zwischen Bohrung und Kopfkreis).

    Verwendung durch detect_helix_angle_v2():
        β = arctan(r_pitch × |dθ/dz|)
    """
    if outer_radius <= 0 or face_width_mm <= 0:
        return []

    results = []
    N_SAMPLES = 15

    explorer = TopExp_Explorer(shape, TopAbs_EDGE)
    while explorer.More():
        edge = explorer.Current()
        try:
            adaptor = BRepAdaptor_Curve(edge)

            # Gerade Linien überspringen (Stirnflächen, Bohrungskanten)
            if adaptor.GetType() == GeomAbs_Line:
                explorer.Next()
                continue

            t0 = adaptor.FirstParameter()
            t1 = adaptor.LastParameter()
            if abs(t1 - t0) < 1e-10:
                explorer.Next()
                continue

            pts = []
            for i in range(N_SAMPLES):
                t = t0 + (t1 - t0) * i / (N_SAMPLES - 1)
                p = adaptor.Value(t)
                r = math.sqrt(p.X() ** 2 + p.Y() ** 2)
                theta = math.atan2(p.Y(), p.X())
                pts.append((r, theta, p.Z()))

            # Kanten zu nah an der Rotationsachse überspringen (Bohrung / Nabe)
            avg_r = sum(p[0] for p in pts) / N_SAMPLES
            if avg_r < outer_radius * 0.35:
                explorer.Next()
                continue

            # Z-Span muss signifikant sein (mindestens 25% der Zahnbreite)
            z_vals = [p[2] for p in pts]
            z_span = max(z_vals) - min(z_vals)
            if z_span < face_width_mm * 0.25:
                explorer.Next()
                continue

            # Theta-Unwrapping: Sprünge bei ±π auflösen
            theta_uw = [pts[0][1]]
            for i in range(1, N_SAMPLES):
                d = pts[i][1] - pts[i - 1][1]
                if d > math.pi:
                    d -= 2 * math.pi
                elif d < -math.pi:
                    d += 2 * math.pi
                theta_uw.append(theta_uw[-1] + d)

            # Lineare Regression: dθ/dz (Steigung der Helixlinie)
            n = N_SAMPLES
            sz  = sum(z_vals)
            st  = sum(theta_uw)
            szt = sum(z * t for z, t in zip(z_vals, theta_uw))
            sz2 = sum(z ** 2 for z in z_vals)
            denom = n * sz2 - sz ** 2
            if abs(denom) < 1e-10:
                explorer.Next()
                continue

            d_theta_dz = (n * szt - sz * st) / denom
            results.append((avg_r, d_theta_dz))

        except Exception:
            pass
        explorer.Next()

    return results


# ─────────────────────────────────────────────
# PRIO 2: Flansch-Detektion
# ─────────────────────────────────────────────

def detect_flanges(plane_z_coords: list, face_width_mm: float) -> bool:
    """
    Erkennt Absätze / Flansche anhand der Z-Positionen der ebenen Flächen.
    Wenn mehr als 2 deutlich verschiedene Z-Ebenen existieren → Flansche.
    """
    if len(plane_z_coords) < 3:
        return False

    unique_z = sorted(set(round(z, 1) for z in plane_z_coords))
    # Mehr als 2 Ebenen (Stirnflächen) bei normalem Zahnrad → Absatz/Flansch
    return len(unique_z) > 2


# ─────────────────────────────────────────────
# PRIO 3: Metadaten aus STEP-Header
# ─────────────────────────────────────────────

def get_step_metadata(filepath: str) -> dict:
    """
    Liest den STEP-Datei-Header (reines Text-Parsing).
    Gibt dict mit: part_name, part_number, created_by, material,
                   tolerance_class, surface_roughness_ra zurück.
    """
    metadata = {
        "part_name": None,
        "part_number": None,
        "created_by": None,
        "material": None,
        "tolerance_class": None,
        "surface_roughness_ra": None,
        "bore_fit": None,
    }

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            in_data_section = False
            for line in f:
                line = line.strip()

                if line == "DATA;":
                    in_data_section = True

                if not in_data_section:
                    # Header: FILE_DESCRIPTION und FILE_NAME
                    if "FILE_DESCRIPTION" in line:
                        parts = line.split("'")
                        if len(parts) > 1 and parts[1]:
                            metadata["part_name"] = parts[1]
                    if "FILE_NAME" in line:
                        parts = line.split("'")
                        if len(parts) > 3:
                            metadata["created_by"] = parts[3] or None
                else:
                    # Data-Bereich
                    if "PRODUCT(" in line or "PRODUCT (" in line:
                        parts = line.split("'")
                        if len(parts) > 1 and parts[1] and not metadata["part_name"]:
                            metadata["part_name"] = parts[1]
                        if len(parts) > 3 and parts[3]:
                            metadata["part_number"] = parts[3]

                    if "MATERIAL_DESIGNATION" in line:
                        parts = line.split("'")
                        if len(parts) > 1 and parts[1]:
                            metadata["material"] = parts[1]

                    # PMI: Toleranzklasse (DIN/ISO Angaben)
                    if "DIMENSIONAL_CHARACTERISTIC_REPRESENTATION" in line or \
                       "TOLERANCE_VALUE" in line:
                        if "DIN" in line or "ISO" in line:
                            parts = line.split("'")
                            for p in parts:
                                if "DIN" in p or "ISO" in p:
                                    metadata["tolerance_class"] = p.strip()
                                    break

                    # Passung (z.B. H7, k6)
                    if "PLUS_MINUS_TOLERANCE" in line or "LIMITS_AND_FITS" in line:
                        parts = line.split("'")
                        for p in parts:
                            p = p.strip()
                            if len(p) >= 2 and p[0].isalpha() and p[1:].isdigit():
                                metadata["bore_fit"] = p
                                break

                    # Oberflächenrauheit Ra
                    if "SURFACE_ROUGHNESS" in line or "ROUGHNESS_PARAMETER" in line:
                        import re
                        numbers = re.findall(r'\d+\.?\d*', line)
                        if numbers:
                            try:
                                metadata["surface_roughness_ra"] = float(numbers[0])
                            except ValueError:
                                pass

    except Exception as e:
        print(f"  [Warnung] Metadaten-Fehler: {e}")

    return metadata


# ─────────────────────────────────────────────
# Hauptfunktion
# ─────────────────────────────────────────────

def parse_step_file(input_path: str, output_path: str) -> GearParameters:

    print("\n" + "=" * 55)
    print("STEP Parser — Gruppe B Geometrie-Modul")
    print("=" * 55)

    # Shape laden
    print("\n[1/5] STEP-Datei laden...")
    shape = load_step(input_path)
    if shape is None:
        raise ValueError(f"STEP-Datei konnte nicht geladen werden: {input_path}")

    params = GearParameters(source_file=Path(input_path).name)

    # PRIO 1: Bounding Box & Masse
    print("[2/5] Bounding Box & Masse...")
    x, y, z = get_bounding_box(shape)
    params.bbox_x_mm, params.bbox_y_mm, params.bbox_z_mm = x, y, z
    d_a_bbox = round(max(x, y), 4)
    b_bbox   = round(z, 4)
    # Bounding-Box ist verlässlich, aber nicht so präzise wie Zylinder-Fit
    params.outer_diameter_mm = ParameterValue.make(d_a_bbox, "mm", round(C.DIRECT - 0.04, 2))
    params.face_width_mm     = ParameterValue.make(b_bbox,   "mm", round(C.DIRECT - 0.04, 2))
    params.total_width_mm    = ParameterValue.make(b_bbox,   "mm", round(C.DIRECT - 0.04, 2))
    params.extraction_notes["outer_diameter"] = "max(bbox_x, bbox_y) — Annahme: Z = Rotationsachse"
    print(f"    d_a = {d_a_bbox} mm  |  b = {b_bbox} mm")

    vol, surf = get_mass_properties(shape)
    params.volume_mm3       = ParameterValue.make(vol,  "mm3", C.DIRECT)
    params.surface_area_mm2 = ParameterValue.make(surf, "mm2", C.DIRECT)
    print(f"    V   = {vol} mm³  |  A = {surf} mm²")

    # PRIO 1+2: Flächen
    print("[3/5] Flächen analysieren...")
    cylinders, planes, cones, tori, total_faces, plane_z_coords, face_parse_success_rate = (
        analyze_surfaces(shape)
    )
    params.face_parse_success_rate = face_parse_success_rate
    print(f"    Faces: {total_faces}  |  Zylinder: {len(cylinders)}  |  "
          f"Eben: {planes}  |  Kegel: {len(cones)}  |  Torus: {len(tori)}  |  "
          f"Parse-Rate: {face_parse_success_rate:.0%}")

    # Zylinder-Hierarchie: d_a, d_f, d_N direkt aus Geometrie
    outer_r, root_r, bore_r = extract_cylinder_hierarchy(cylinders)
    if outer_r is not None:
        d_a_direct = round(outer_r * 2, 4)
        d_a_bbox_val = params.outer_diameter_mm.value
        if abs(d_a_direct - d_a_bbox_val) / max(d_a_bbox_val, 1) < 0.05:
            # Zylinder-Messung ist präziser als Bounding-Box
            params.outer_diameter_mm = ParameterValue.make(d_a_direct, "mm", C.DIRECT)
            params.extraction_notes["outer_diameter"] = "Direkt aus größtem Außenzylinder"
    if root_r is not None:
        params.root_diameter_mm = ParameterValue.make(round(root_r * 2, 4), "mm", C.DIRECT)
        params.extraction_notes["root_diameter"] = "Direkt aus Geometrie (Zahnfuß-Zylinder)"
    if bore_r is not None:
        params.hub_bore_diameter_mm = ParameterValue.make(round(bore_r * 2, 4), "mm", C.DIRECT)
        params.extraction_notes["hub_bore"] = "Direkt aus kleinster Innenbohrung"
    else:
        params.warnings.append("Nabenbohrung nicht erkannt — ggf. Vollwelle oder kein Innen-Zylinder")

    # Torus → Fußrundungsradius r_f
    if tori:
        tori_sorted = sorted(tori)
        median_idx = len(tori_sorted) // 2
        params.root_fillet_radius_mm = ParameterValue.make(
            tori_sorted[median_idx], "mm", round(C.DIRECT - 0.07, 2)
        )
        params.extraction_notes["root_fillet"] = f"Median der {len(tori)} Torus-Minor-Radien"

    # Flansche
    params.has_flanges = detect_flanges(
        plane_z_coords,
        params.face_width_mm.value if isinstance(params.face_width_mm, ParameterValue) else params.face_width_mm
    )

    if not cylinders:
        params.overall_confidence = 0.2
        params.warnings.append("Keine zylindrischen Flächen — möglicherweise kein Stirnrad")

    # PRIO 2: Kanten
    print("[4/5] Kanten analysieren...")
    total_edges, edge_lengths, keyway_present = analyze_edges(shape)
    params.keyway_present = keyway_present
    print(f"    Kanten: {total_edges}  |  Passfedernut: {keyway_present}")

    # PRIO 2: Helix-Abtastung (3D-Kurven entlang Z-Achse)
    _outer_d = params.outer_diameter_mm.value if isinstance(params.outer_diameter_mm, ParameterValue) else params.outer_diameter_mm
    _face_w  = params.face_width_mm.value if isinstance(params.face_width_mm, ParameterValue) else params.face_width_mm
    edge_helix_data = extract_edge_helix_data(shape, _outer_d / 2, _face_w)
    print(f"    Helix-Kanten für β: {len(edge_helix_data)}")

    # PRIO 3: Metadaten
    print("[5/5] Metadaten...")
    metadata = get_step_metadata(input_path)
    params.part_name = metadata["part_name"]
    params.part_number = metadata["part_number"]
    params.created_by = metadata["created_by"]
    params.material = metadata["material"]
    params.tolerance_class = metadata["tolerance_class"]
    params.surface_roughness_ra = metadata["surface_roughness_ra"]
    params.bore_fit = metadata["bore_fit"]
    print(f"    Name: {params.part_name or 'n/a'}  |  Material: {params.material or 'n/a'}")

    # Direkte Vermessung (software-unabhängig, planare Querschnitte)
    print("\n[Vermessung] Achse, Zahnkranz, Querschnitte...")
    metrology = extract_metrology(shape)
    if metrology.get("ok"):
        print(f"    Zahnkranz erkannt: z={metrology['num_teeth']}  "
              f"({metrology['band_sections']}/{metrology['total_sections']} Schnitte)")
    else:
        print("    Kein Zahnkranz vermessbar — Rückfall auf Heuristik")

    # Geometrie-Analyse (Schritt 2)
    print("\n[Geometrie-Analyse]...")
    params = analyze_gear_geometry(
        params, cylinders, planes, cones, tori,
        total_edges, edge_helix_data, total_faces,
        face_parse_success_rate=face_parse_success_rate,
        metrology=metrology,
    )

    params.summary()
    params.to_json(output_path)

    return params


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="STEP AP242 Parser für Verzahnungsgeometrien (Gruppe B)"
    )
    parser.add_argument("--input",  "-i", required=True, help="Pfad zur STEP-Datei")
    parser.add_argument("--output", "-o", default="output/gear_parameters.json",
                        help="JSON-Ausgabepfad (default: output/gear_parameters.json)")
    args = parser.parse_args()
    try:
        parse_step_file(args.input, args.output)
    except ValueError as e:
        print(f"\n[FEHLER] {e}")
        sys.exit(1)
