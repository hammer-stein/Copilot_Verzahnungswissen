"""
accuracy_test.py
----------------
Integration-Test: Führt die Pipeline auf STEP-Dateien aus und
misst die Genauigkeit der extrahierten Parameter gegen bekannte Soll-Werte.

Verwendung:
    conda activate gear-copilot
    python tests/accuracy_test.py
   
   
     python tests/accuracy_test.py --step-dir data/examples
    python tests/accuracy_test.py --warn 2.0 --error 5.0
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from step_parser import parse_step_file


WARN_THRESHOLD_PCT = 2.0
ERROR_THRESHOLD_PCT = 5.0

# Mapping: ground-truth-Key → Pfad im JSON-Output (tuple von Keys)
PARAM_MAP = {
    "gear_type":          ("gear_type",),
    "is_internal_gear":   ("topology", "is_internal_gear"),
    "num_teeth":          ("tooth_profile", "num_teeth"),
    "module_mm":          ("tooth_profile", "module_mm"),
    "outer_diameter_mm":  ("basic_geometry", "outer_diameter_mm"),
    "pitch_diameter_mm":  ("basic_geometry", "pitch_diameter_mm"),
    "root_diameter_mm":   ("basic_geometry", "root_diameter_mm"),
    "face_width_mm":      ("basic_geometry", "face_width_mm"),
    "helix_angle_deg":    ("tooth_profile", "helix_angle_deg"),
    "pressure_angle_deg": ("tooth_profile", "pressure_angle_deg"),
}

EXACT_MATCH_PARAMS = {"gear_type", "num_teeth", "is_internal_gear"}


def _get_nested(data: dict, *keys):
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def _compare(param: str, actual, expected, warn_pct: float, error_pct: float):
    """Gibt (status, beschreibung) zurück. Status: ok | warn | error | missing."""
    if actual is None:
        return "missing", f"None  (erwartet: {expected})"

    if param in EXACT_MATCH_PARAMS:
        ok = actual == expected
        return ("ok", f"{actual}") if ok else ("error", f"{actual!r} != {expected!r}")

    try:
        act_f, exp_f = float(actual), float(expected)
    except (TypeError, ValueError):
        return "error", f"Typfehler: {actual!r} vs {expected!r}"

    if exp_f == 0.0:
        status = "ok" if abs(act_f) < 0.01 else "error"
        return status, f"{act_f:.3f}  (erwartet: 0)"

    pct = abs(act_f - exp_f) / abs(exp_f) * 100.0
    desc = f"{act_f:.3f}  (erwartet: {exp_f:.3f},  Δ={pct:.1f}%)"
    if pct <= warn_pct:
        return "ok", desc
    elif pct <= error_pct:
        return "warn", desc
    else:
        return "error", desc


def run(step_dir: str, ground_truth_path: str, warn_pct: float, error_pct: float):
    if not os.path.exists(ground_truth_path):
        print(f"[FEHLER] Ground-Truth-Datei nicht gefunden: {ground_truth_path}")
        sys.exit(1)

    with open(ground_truth_path, encoding="utf-8") as f:
        raw = json.load(f)

    ground_truth = {k: v for k, v in raw.items() if not k.startswith("_")}

    available = {}
    for ext in ("*.stp", "*.step", "*.STP", "*.STEP"):
        for p in Path(step_dir).glob(ext):
            available[p.name] = str(p)

    testable = {n: available[n] for n in available if n in ground_truth}
    skipped  = [n for n in available if n not in ground_truth]
    missing  = [n for n in ground_truth if n not in available]

    if not testable:
        print("\n[INFO] Keine testbaren STEP-Dateien in", step_dir)
        print("  Erwartet (aus ground_truth.json):", list(ground_truth.keys()))
        print("  Gefunden:                        ", list(available.keys()) or "(leer)")
        if missing:
            print("\n  Tipp: Generiere diese Dateien mit FreeCAD (FCGear-Workbench)")
            print("  und lege sie in", step_dir, "ab.")
        return

    print("\n" + "=" * 65)
    print("  ACCURACY REPORT — Gear-Geometrie-Pipeline")
    print(f"  Schwellenwerte: OK ≤{warn_pct}%  |  Warnung ≤{error_pct}%  |  Fehler >{error_pct}%")
    print("=" * 65)

    icons = {"ok": "✓", "warn": "⚠", "error": "✗", "missing": "?"}
    summary = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for filename, step_path in sorted(testable.items()):
            expected = ground_truth[filename]
            out_json = os.path.join(tmpdir, Path(filename).stem + ".json")

            print(f"\n{filename}")
            print("-" * 55)

            try:
                parse_step_file(step_path, out_json)
            except Exception as exc:
                print(f"  [FEHLER] Pipeline-Exception: {exc}")
                summary.append((filename, "CRASH", 0, 0, 0))
                continue

            if not os.path.exists(out_json):
                print("  [FEHLER] Keine JSON-Ausgabe erzeugt.")
                summary.append((filename, "NO OUTPUT", 0, 0, 0))
                continue

            with open(out_json, encoding="utf-8") as f:
                output = json.load(f)

            counts = {"ok": 0, "warn": 0, "error": 0, "missing": 0}

            for param, exp_val in expected.items():
                if param.startswith("_") or param not in PARAM_MAP:
                    continue
                actual = _get_nested(output, *PARAM_MAP[param])
                status, desc = _compare(param, actual, exp_val, warn_pct, error_pct)
                counts[status] += 1
                print(f"  {icons[status]}  {param:<28} {desc}")

            total = sum(counts.values())
            print(f"\n  Ergebnis: {counts['ok']}/{total} OK  "
                  f"({counts['warn']} ⚠  {counts['error']} ✗  {counts['missing']} ?)")
            summary.append((filename, "OK", counts["ok"], counts["warn"],
                            counts["error"] + counts["missing"]))

    # Gesamtübersicht
    print("\n" + "=" * 65)
    print("  GESAMTÜBERSICHT")
    print("=" * 65)

    total_ok = total_warn = total_err = 0
    for fname, status, ok, warn, err in summary:
        if status == "OK":
            total = ok + warn + err
            total_ok += ok
            total_warn += warn
            total_err += err
            bar = f"{ok}/{total} OK  ({warn}⚠  {err}✗)"
        else:
            bar = status
        print(f"  {fname:<38} {bar}")

    total_all = total_ok + total_warn + total_err
    if total_all > 0:
        pct = total_ok / total_all * 100
        print(f"\n  Gesamt: {total_ok}/{total_all} Parameter korrekt ({pct:.0f}%)  "
              f"|  {total_warn} Warnungen  |  {total_err} Fehler")

    if skipped:
        print(f"\n  Übersprungen (kein Ground Truth): {', '.join(skipped)}")
    if missing:
        print(f"  Ground Truth vorhanden, STEP fehlt: {', '.join(missing)}")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genauigkeitstest der Gear-Geometrie-Pipeline")
    parser.add_argument(
        "--step-dir",
        default=str(Path(__file__).parent.parent / "data" / "examples"),
        help="Ordner mit STEP-Testdateien (Standard: data/examples/)",
    )
    parser.add_argument(
        "--ground-truth",
        default=str(Path(__file__).parent / "ground_truth.json"),
        help="Pfad zur Ground-Truth-JSON-Datei",
    )
    parser.add_argument("--warn",  type=float, default=WARN_THRESHOLD_PCT,
                        help=f"Warnschwelle in %% (Standard: {WARN_THRESHOLD_PCT})")
    parser.add_argument("--error", type=float, default=ERROR_THRESHOLD_PCT,
                        help=f"Fehlerschwelle in %% (Standard: {ERROR_THRESHOLD_PCT})")
    args = parser.parse_args()

    run(args.step_dir, args.ground_truth, args.warn, args.error)
