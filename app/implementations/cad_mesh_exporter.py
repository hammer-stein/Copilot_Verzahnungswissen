"""
cad_mesh_exporter.py - STEP-Geometrie als browserfähiges Preview-Mesh exportieren.

Der Export läuft bewusst getrennt vom Parameter-Parser: Wenn die visuelle Preview
fehlschlägt, darf die eigentliche CAD-Analyse trotzdem erfolgreich sein.
"""

from __future__ import annotations

from pathlib import Path


def export_step_to_stl(
    step_path: Path,
    stl_path: Path,
    *,
    linear_deflection: float = 0.15,
    angular_deflection: float = 0.45,
) -> Path:
    """
    Lädt eine STEP/STP-Datei mit pythonocc, trianguliert die Shape und schreibt
    ein ASCII-STL. ASCII ist größer als Binär-STL, lässt sich im aktuellen
    Vanilla-Frontend aber ohne zusätzliche Loader zuverlässig parsen.
    """
    step_path = Path(step_path)
    stl_path = Path(stl_path)

    if not step_path.exists():
        raise FileNotFoundError(f"STEP-Datei nicht gefunden: {step_path}")

    try:
        from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.StlAPI import StlAPI_Writer
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError("pythonocc-core/OCC ist für den STEP-Preview-Export nicht verfügbar.") from exc

    reader = STEPControl_Reader()
    status = reader.ReadFile(str(step_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEP-Datei konnte nicht gelesen werden: {step_path.name}")

    reader.TransferRoots()
    shape = reader.OneShape()
    if shape is None or shape.IsNull():
        raise RuntimeError(f"STEP-Datei enthält keine exportierbare Geometrie: {step_path.name}")

    mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)
    mesh.Perform()
    if not mesh.IsDone():
        raise RuntimeError(f"Triangulierung der STEP-Datei fehlgeschlagen: {step_path.name}")

    stl_path.parent.mkdir(parents=True, exist_ok=True)
    writer = StlAPI_Writer()
    writer.SetASCIIMode(True)
    ok = writer.Write(shape, str(stl_path))
    if not ok or not stl_path.exists() or stl_path.stat().st_size <= 0:
        raise RuntimeError(f"STL-Preview konnte nicht geschrieben werden: {stl_path}")

    return stl_path
