# KI-Copilot für Verzahnungswissen

Pipeline: **CAD-Datei → Parameter-JSON → RAG-Copilot → Antwort**

```
cad_processor/   ← CAD-Datei einlesen, Zahnrad-Parameter extrahieren (PythonOCC)
     ↓ JSON
RAG-System       ← Wissensbasis (PDFs) + Bauteilparameter → Copilot-Antworten
```

---

## Setup — CAD-Prozessor (Gruppe B)

Benötigt **Miniconda** (wegen PythonOCC C++-Abhängigkeiten).

```bash
# 1. conda-Umgebung erstellen (einmalig, ~5 min)
conda env create -f cad_processor/environment.yml

# 2. Umgebung aktivieren
conda activate gear-copilot

# 3. CAD-API starten
cd cad_processor
uvicorn src.main:app --reload --port 8001
```

Vollständige Anleitung: [`cad_processor/SETUP_ANLEITUNG.md`](cad_processor/SETUP_ANLEITUNG.md)

---

## Setup — RAG-System (Gruppe A)

Benötigt **Docker** (für Qdrant) und **Ollama** (lokales LLM).

```bash
# 1. Python-Umgebung erstellen (einmalig)
python -m venv .venv
source .venv/bin/activate       # Mac/Linux
# .venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Qdrant starten (Vektor-Datenbank)
docker compose up -d

# 3. Ollama starten + Modell laden
ollama pull llama3.2:3b

# 4. Konfiguration
cp config.example.yaml config.yaml   # anpassen falls nötig

# 5. RAG-API starten
uvicorn app.api.main:app --reload --port 8000
```

Frontend öffnen: `http://localhost:8000/`

---

## API-Endpunkte

### CAD-Prozessor (Port 8001)
- `POST /analyze` — STEP/IGES-Datei hochladen → JSON mit Zahnrad-Parametern

### RAG-System (Port 8000)
- `POST /upload` — PDF hochladen und indexieren
- `POST /ask` — `{ questions: string[], cad_metadata: object }` → Copilot-Antwort
- `GET /documents` — indexierte Dokumente
- `DELETE /documents/{doc_hash}` — Dokument löschen
- `GET /cad/random` — zufälliges Zahnrad (Stub)

---

## Projektstruktur

```
Copilot_Verzahnungswissen/
├── cad_processor/              ← CAD-Prozessor (Gruppe B)
│   ├── src/
│   │   ├── step_parser.py      STEP-Datei einlesen
│   │   ├── geometry_analyzer.py Zahnrad-Parameter berechnen
│   │   ├── output_schema.py    JSON-Schema
│   │   └── main.py             FastAPI
│   ├── environment.yml         conda-Umgebung (gear-copilot)
│   └── SETUP_ANLEITUNG.md
├── app/                        ← RAG-System (Gruppe A)
├── schemas/                    ← Gemeinsame JSON-Schemas
├── frontend/
├── requirements.txt            pip-Abhängigkeiten (RAG)
├── docker-compose.yml          Qdrant
└── config.example.yaml
```

## Hinweise

- Beide Services laufen lokal parallel (Port 8000 + 8001).
- Es gibt keinen Konversationskontext zwischen Anfragen (Absicht).
- Quellen sind pro Antwort als `[Q1]..` referenziert.
