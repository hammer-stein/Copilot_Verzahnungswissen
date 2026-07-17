"""
mesh_export.py – STEP-Geometrie als browserfähiges ASCII-STL tessellieren.

Lebt bewusst IM cad_processor (hier ist pythonocc/OCC installiert). Das RAG-System
(app-Container, KEIN OCC) ruft dafür den Endpoint POST /export-stl auf – siehe
app/api/main.py `_analyze_cad_with_preview` (HTTP-Fallback der 3D-Vorschau).
Logik identisch zu app/implementations/cad_mesh_exporter.py (lokaler Conda-Betrieb).
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
    """Lädt STEP, trianguliert die Shape und schreibt ein ASCII-STL (Frontend-Parser)."""
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.StlAPI import StlAPI_Writer

    step_path = Path(step_path)
    stl_path = Path(stl_path)
    if not step_path.exists():
        raise FileNotFoundError(f"STEP-Datei nicht gefunden: {step_path}")

    reader = STEPControl_Reader()
    if reader.ReadFile(str(step_path)) != IFSelect_RetDone:
        raise ValueError(f"STEP-Datei konnte nicht gelesen werden: {step_path.name}")
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape is None or shape.IsNull():
        raise ValueError(f"STEP-Datei enthält keine exportierbare Geometrie: {step_path.name}")

    mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)
    mesh.Perform()
    if not mesh.IsDone():
        raise RuntimeError(f"Triangulierung fehlgeschlagen: {step_path.name}")

    stl_path.parent.mkdir(parents=True, exist_ok=True)
    writer = StlAPI_Writer()
    writer.SetASCIIMode(True)
    ok = writer.Write(shape, str(stl_path))
    if not ok or not stl_path.exists() or stl_path.stat().st_size <= 0:
        raise RuntimeError(f"STL konnte nicht geschrieben werden: {stl_path}")
    return stl_path
