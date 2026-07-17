from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from typing import Optional
import uuid
import os
import shutil

# Direkter Import eurer bestehenden Module
from src.step_parser import parse_step_file

app = FastAPI(
    title="Gear Copilot API",
    description="Multi-User REST-API zur automatisierten Zahnrad-Geometrieanalyse",
    version="1.0.0"
)

# Temporäre Verzeichnisse für die Uploads und Outputs sicherstellen
UPLOAD_DIR = "data/examples"
OUTPUT_DIR = "output"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/analyze")
def analyze_gear(
    file: UploadFile = File(...),
    session_id: Optional[str] = Header(None, description="Optionale Session-ID für das RAG-System")
):
    # 1. Multi-User Session-Management
    # Wenn Gruppe A (RAG) noch keine Session-ID mitschickt, generieren wir eine neue
    if not session_id:
        session_id = str(uuid.uuid4())

    # Einzigartigen Dateinamen generieren, damit sich Nutzer nicht gegenseitig Dateien überschreiben
    file_ext = os.path.splitext(file.filename)[1]
    if file_ext.lower() not in ['.step', '.stp']:
        raise HTTPException(status_code=400, detail="Ungültiges Dateiformat. Nur .step oder .stp erlaubt.")
        
    unique_id = uuid.uuid4().hex
    unique_filename = f"{session_id}_{unique_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Dynamischen Output-Pfad für den Parser generieren
    output_path = os.path.join(OUTPUT_DIR, f"{session_id}_{unique_id}_result.json")

    try:
        # 2. Datei sicher auf dem Server speichern
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. Pipeline ausführen: Parsing + Geometrie-Analyse, Ergebnis als GearParameters
        parsed_data = parse_step_file(file_path, output_path)

        # Vollständiges Analyse-JSON zurückgeben, ergänzt um Session-Infos für das RAG-System
        final_result = parsed_data.to_dict()
        final_result["session_id"] = session_id
        final_result["filename"] = file.filename

        return final_result

    except ValueError:
        # step_parser: "STEP-Datei konnte nicht geladen werden" (beschädigt/leer/kein STEP).
        # 422 mit verständlicher Meldung – der interne Serverpfad gehört nicht in die GUI.
        raise HTTPException(
            status_code=422,
            detail="Die Datei konnte nicht als STEP gelesen werden – sie ist beschädigt, "
                   "leer oder kein gültiges STEP-Format (.step/.stp).",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Geometrieanalyse: {str(e)}")

    finally:
        # 4. Saubere Müllabfuhr: Hochgeladene STEP-Datei und generierte JSON wieder löschen
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(output_path):
            os.remove(output_path)

@app.post("/export-stl")
def export_stl(file: UploadFile = File(...)):
    """
    Tesselliert eine STEP-Datei zu ASCII-STL für die 3D-Vorschau des Frontends.
    Wird vom RAG-System (app-Container, KEIN OCC) als Preview-Fallback aufgerufen –
    die eigentliche Analyse läuft unabhängig davon über POST /analyze.
    """
    from fastapi.responses import Response
    from src.mesh_export import export_step_to_stl

    file_ext = os.path.splitext(file.filename or "")[1]
    if file_ext.lower() not in ['.step', '.stp']:
        raise HTTPException(status_code=400, detail="Ungültiges Dateiformat. Nur .step oder .stp erlaubt.")

    uid = uuid.uuid4().hex
    step_path = os.path.join(UPLOAD_DIR, f"stl_{uid}{file_ext}")
    stl_path = os.path.join(OUTPUT_DIR, f"stl_{uid}.stl")
    try:
        with open(step_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        export_step_to_stl(step_path, stl_path)
        with open(stl_path, "rb") as fh:
            data = fh.read()
        return Response(content=data, media_type="model/stl")
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Die Datei konnte nicht als STEP gelesen werden – sie ist beschädigt, "
                   "leer oder kein gültiges STEP-Format (.step/.stp).",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STL-Export fehlgeschlagen: {str(e)}")
    finally:
        for p in (step_path, stl_path):
            if os.path.exists(p):
                os.remove(p)
