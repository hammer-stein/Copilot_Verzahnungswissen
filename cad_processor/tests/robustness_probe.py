"""
robustness_probe.py
-------------------
Generalisierungs-Sonde: prüft, ob die Vermessung (extract_metrology) für eine
gegebene STEP-Datei UNABHÄNGIG von Bauteil-Orientierung und -Position dasselbe
Ergebnis liefert. Das ist die wahrscheinlichste Variation zwischen beliebigen
STEP-242-Dateien derselben Verzahnungsart (verschiedene CAD-Ursprünge/Achsen).

Aufruf:
    python tests/robustness_probe.py <pfad-zur-step-datei> [<weitere> ...]
"""

import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from OCC.Core.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs

from step_parser import load_step
from gear_metrology import extract_metrology

# Zu vergleichende Kerngrößen
KEYS = ["num_teeth", "module_mm", "tip_diameter_mm", "root_diameter_mm",
        "is_bevel", "is_ratchet", "is_internal", "is_crown", "cone_angle_deg",
        "face_width_mm", "bore_diameter_mm", "tooth_depth_mm"]


def _transform(shape, rx_deg, ry_deg, rz_deg, tx, ty, tz):
    """Wendet eine starre Rotation + Translation auf die Shape an."""
    t = gp_Trsf()
    # Rotation um X
    rot = gp_Trsf()
    rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.radians(rx_deg))
    t.Multiply(rot)
    rot = gp_Trsf()
    rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), math.radians(ry_deg))
    t.Multiply(rot)
    rot = gp_Trsf()
    rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.radians(rz_deg))
    t.Multiply(rot)
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(tx, ty, tz))
    t.Multiply(tr)
    moved = BRepBuilderAPI_Transform(shape, t, True).Shape()
    # WICHTIG: über STEP schreiben + neu laden, damit die Geometrie GEBACKEN ist
    # (keine TopLoc_Location). In-Memory-transformierte B-Reps lassen
    # BRepAlgoAPI_Section in OCC katastrophal langsam werden — ein Test-Artefakt,
    # das echte, neu exportierte STEP-Dateien NICHT haben. Erst write+reload bildet
    # den realen „beliebige Orientierung"-Fall getreu ab.
    tmp = tempfile.NamedTemporaryFile(suffix=".step", delete=False)
    tmp.close()
    w = STEPControl_Writer()
    w.Transfer(moved, STEPControl_AsIs)
    w.Write(tmp.name)
    return load_step(tmp.name)


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def probe(step_path):
    print(f"\n{'='*70}\n{Path(step_path).name}\n{'='*70}")
    shape = load_step(step_path)
    if shape is None:
        print("  [SKIP] nicht ladbar")
        return None

    base = extract_metrology(shape)

    # Mehrere zufällige starre Lagen
    transforms = [
        (37, 23, 51, 100, -50, 75),
        (90, 0, 0, 0, 0, 0),
        (12, -64, 130, -200, 33, 5),
    ]
    rows = {k: [base.get(k)] for k in KEYS}
    labels = ["original"]
    for (rx, ry, rz, tx, ty, tz) in transforms:
        tshape = _transform(shape, rx, ry, rz, tx, ty, tz)
        m = extract_metrology(tshape)
        labels.append(f"rot({rx},{ry},{rz})")
        for k in KEYS:
            rows[k].append(m.get(k))

    # Vergleich ausgeben + Abweichung markieren
    any_drift = False
    print(f"  {'param':<20}" + "".join(f"{l:<18}" for l in labels))
    for k in KEYS:
        vals = rows[k]
        ref = vals[0]
        drift = False
        for v in vals[1:]:
            if isinstance(ref, (int, float)) and isinstance(v, (int, float)) and not isinstance(ref, bool):
                if ref and abs(v - ref) / abs(ref) > 0.03:
                    drift = True
            elif v != ref:
                drift = True
        mark = "  <-- DRIFT" if drift else ""
        any_drift = any_drift or drift
        print(f"  {k:<20}" + "".join(f"{_fmt(v):<18}" for v in vals) + mark)
    print(f"\n  => {'INSTABIL (orientierungsabhängig!)' if any_drift else 'stabil über alle Lagen'}")
    return not any_drift


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print("Usage: python tests/robustness_probe.py <step> [<step> ...]")
        sys.exit(1)
    results = [probe(p) for p in paths]
    ok = sum(1 for r in results if r)
    print(f"\n{'#'*70}\nStabil: {ok}/{len([r for r in results if r is not None])}")
