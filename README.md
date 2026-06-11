# KI-Copilot für Verzahnungswissen

Pipeline: **CAD-Datei → Parameter-JSON → RAG-Copilot → Antwort**

```
cad_processor (Port 8001)   ← STEP-Datei → GearParameters JSON (PythonOCC)
        ↓ JSON (gemappte Metadaten)
RAG-System    (Port 8000)   ← Wissensbasis (PDFs) + Bauteilparameter → Copilot-Antworten
Qdrant        (Port 6333)   ← Vektordatenbank
```

---

## Schnellstart (Docker Compose)

```bash
# 1. Ollama lokal starten + Modell laden (läuft außerhalb Docker)
ollama pull llama3.2:3b

# 2. Konfiguration anlegen
cp config.example.yaml config.yaml

# 3. Alle Services starten
docker compose up --build
```

Web-GUI öffnen: `http://localhost:8000/` (leitet auf den Verzahnungs-Copilot weiter — Chat, CAD-/STEP-Upload, Quellenangaben, Ausgabeformat-Auswahl).

> **Hinweis:** Ollama läuft auf dem Host. Der `app`-Service erreicht ihn via `http://host.docker.internal:11434` (wird automatisch über `OLLAMA_URL` gesetzt).

---

## Lokale Entwicklung (ohne Docker)

### CAD-Prozessor (Gruppe B)

Benötigt **Miniconda** (wegen PythonOCC C++-Abhängigkeiten).

```bash
conda env create -f cad_processor/environment.yml
conda activate gear-copilot
cd cad_processor
uvicorn src.main:app --reload --port 8001
```

Vollständige Anleitung: [`cad_processor/SETUP_ANLEITUNG.md`](cad_processor/SETUP_ANLEITUNG.md)

### RAG-System (Gruppe A)

> **Python 3.11 erforderlich.** Auf Intel-macOS (x86_64) gibt es für neuere Python-Versionen
> (3.13) kein `torch`-Wheel; die Pins in `requirements.txt` sind auf den 3.11-Stack abgestimmt
> (entspricht dem Docker-Image). Falls der Default-Interpreter 3.12+ ist, eine 3.11-Umgebung
> nutzen, z.B.: `conda create -n py311 python=3.11 && conda run -n py311 python -m venv .venv`.

```bash
python3.11 -m venv .venv
source .venv/bin/activate        # Mac/Linux
pip install -r requirements.txt

# Qdrant starten
docker compose up -d qdrant

# Ollama starten
ollama pull llama3.2:3b

# Konfiguration
cp config.example.yaml config.yaml

# RAG-API starten
uvicorn app.api.main:app --reload --port 8000
```

**Komplett ohne Docker (eingebettetes Qdrant):** In `config.yaml` unter `vector_store` die Zeile
`path: "storage/qdrant"` setzen (Embedded-On-Disk-Modus, kein Qdrant-Server nötig) und bei
`cad_adapter` `implementation: "random_gear_stub"` verwenden (kein CAD-Service nötig). Es bleibt
nur **Ollama** als externe Abhängigkeit. Genau diese Defaults erzeugt ein frisch angelegtes
`config.yaml` für die lokale Entwicklung.

---

## API-Endpunkte

### CAD-Prozessor (Port 8001)
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| `POST` | `/analyze` | STEP/STP-Datei → GearParameters JSON |

### RAG-System (Port 8000)
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| `POST` | `/cad/analyze` | STEP/STP-Datei → gemappte CAD-Metadaten (direkt für `/ask` verwendbar) |
| `GET` | `/cad/random` | Zufälliges Zahnrad (Demo/Test, kein CAD-Service nötig) |
| `POST` | `/upload` | PDF hochladen und indexieren |
| `GET` | `/documents` | Indexierte Dokumente auflisten |
| `DELETE` | `/documents/{doc_hash}` | Dokument löschen |
| `POST` | `/ask` | `{ questions: string[], cad_metadata: object, format?: string }` → Copilot-Antwort |
| `GET` | `/` | Leitet auf das Web-GUI weiter (`/ui/ui_kits/copilot/`) |

`format` steuert das Ausgabeformat der Antwort: `kurz` · `standard` (Default) · `ausführlich` · `stichpunkte` · `tabellarisch`.

### Typischer Ablauf

```
1. POST /cad/analyze   (STEP-Datei hochladen)
        → { "verzahnungstyp": "Stirnrad", "modul": 2.5, ... }

2. POST /ask           (Fragen + CAD-Metadaten)
   Body: { "questions": ["Welche Toleranz gilt?"], "cad_metadata": { ... } }
        → Antwort mit Quellenangaben
```

---

## JSON-Bridge: cad_processor → RAG

Der `CadProcessorClient` (`app/implementations/cad_processor_client.py`) mappt die englischen GearParameters-Felder des cad_processors auf die deutschen Feldnamen des RAG-Schemas (`schemas/gears.yaml`):

| cad_processor | RAG-Schema | Funktion |
|---|---|---|
| `gear_type` | `verzahnungstyp` | Stage-1-Filter im Retriever |
| `tooth_profile.module_mm` | `modul` | Stage-1-Filter (Range) |
| `tooth_profile.num_teeth` | `zaehnezahl` | Kontext |
| `basic_geometry.*` | `teilkreis-/kopf-/fusskreisdurchmesser`, `zahnbreite` | Kontext |
| `material_context.material` | `werkstoff` | Kontext |

---

## Projektstruktur

```
Copilot_Verzahnungswissen/
├── cad_processor/              ← CAD-Prozessor (Gruppe B)
│   ├── src/
│   │   ├── step_parser.py      STEP-Datei einlesen + GearParameters extrahieren
│   │   ├── output_schema.py    GearParameters Datenklasse
│   │   └── main.py             FastAPI (Port 8001)
│   ├── Dockerfile              conda/miniconda-basiertes Image
│   └── environment.yml
├── app/                        ← RAG-System (Gruppe A)
│   ├── api/main.py             FastAPI (Port 8000)
│   ├── core/                   Config, Factory, Interfaces
│   ├── implementations/        Konkrete Implementierungen
│   └── pipeline/               Indexierungs-Pipeline
├── schemas/                    Metadaten-Schema (gears.yaml)
├── frontend/                   Web-UI
│   ├── index.html              Einfaches Fallback-Frontend
│   └── design-system/          Verzahnungs-Copilot GUI (React, unter /ui ausgeliefert) — nur Laufzeit-Dateien
├── design-system-source/       Designer-Quellen/Showcase des Design-Systems (Komponenten-.jsx, guidelines, preview) — nicht zur Laufzeit geladen
├── prompts/                    LLM-Prompt-Templates
├── docs/                       Dokumentation
├── Dockerfile                  Root-Dockerfile (RAG-System)
├── docker-compose.yml          Alle drei Services
├── requirements.txt
└── config.example.yaml
```

---

## Hinweise

- Kein Konversationskontext zwischen Anfragen (Absicht — jede Anfrage ist isoliert).
- Quellen werden pro Antwort als `[Q1]..` referenziert.
- `config.yaml` wird nie ins Git eingecheckt (enthält ggf. lokale Pfade/Ports).
- Im Docker-Compose-Netz: Services kommunizieren über Container-Namen (`qdrant`, `cad_processor`).
