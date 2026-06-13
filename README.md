# KI-Copilot für Verzahnungswissen

Pipeline: **CAD-Datei → Parameter-JSON → RAG-Copilot (Retrieval + CAD-Kontext) → Antwort**

```
cad_processor (Port 8001)   ← STEP-Datei → GearParameters JSON (PythonOCC)
        ↓ volles GearParameters-JSON
RAG-System    (Port 8000)   ← Wissensbasis (PDFs) + Bauteilparameter → Copilot-Antworten
Qdrant        (Port 6333)   ← Vektordatenbank
```

### Anfrage-Fluss pro Frage (CAD-aware RAG)

```
1. HybridRetriever       Nutzerfrage wird embedded → Dense + lexikalische Sparse-Suche in Qdrant
2. AnswerGenerator (LLM) beantwortet die Frage aus den gefundenen Chunks + dem vollen CAD-JSON
```

Das Retrieval arbeitet **ausschließlich mit der Nutzerfrage**. Das CAD-JSON fließt
erst in der Antwortstufe als Bauteilkontext ein — so beeinflusst es die Antwort,
ohne das Retrieval auf die CAD-Parameter zu verengen.

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

## CAD-Schalter: synthetische Testdaten vs. echte STEP-Analyse

In `config.yaml` steuert `cad_adapter.implementation`, woher die CAD-Daten kommen:

| Wert | Verhalten |
|---|---|
| `synthetic_json` | `/cad/analyze` liefert synthetische Testdatensätze aus `test_verzahnung/cad_testdaten/` — kein cad_processor-Service nötig |
| `cad_processor_http` | STEP-Dateien werden an den cad_processor (Port 8001) geschickt und echt analysiert |

`/cad/random` und `/cad/examples` nutzen immer die synthetischen Datensätze.
Die 10 Testdatensätze (`gear_01.json` … `gear_10.json`) sind geometrisch konsistent
nach DIN 3960 und im identischen GearParameters-Format wie die echte STEP-Analyse.
Neu generieren: `python test_verzahnung/cad_testdaten/generate_testdata.py`

---

## API-Endpunkte

### CAD-Prozessor (Port 8001)
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| `POST` | `/analyze` | STEP/STP-Datei → GearParameters JSON |

### RAG-System (Port 8000)
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| `POST` | `/cad/analyze` | STEP/STP-Datei → GearParameters-JSON (je nach Schalter echt oder synthetisch) |
| `GET` | `/cad/random` | Zufälliger synthetischer Testdatensatz |
| `GET` | `/cad/examples` | Liste der synthetischen Testdatensätze |
| `GET` | `/cad/examples/{name}` | Bestimmten Testdatensatz laden |
| `POST` | `/upload` | PDF hochladen und indexieren |
| `GET` | `/documents` | Indexierte Dokumente auflisten |
| `DELETE` | `/documents/{doc_hash}` | Dokument löschen |
| `POST` | `/ask` | `{ questions: string[], cad_metadata: object, format?: string }` → Copilot-Antwort |
| `GET` | `/` | Leitet auf das Web-GUI weiter (`/ui/ui_kits/copilot/`) |

`format` steuert das Ausgabeformat der Antwort: `kurz` · `standard` (Default) · `ausführlich` · `stichpunkte` · `tabellarisch`.

### Typischer Ablauf

```
1. POST /cad/analyze   (STEP-Datei hochladen)
        → volles GearParameters-JSON { "gear_type": "helical", "tooth_profile": {...}, ... }

2. POST /ask           (Fragen + CAD-JSON)
   Body: { "questions": ["Welches Fertigungsverfahren ist geeignet?"], "cad_metadata": { ... } }
        → pro Frage: Retrieval auf der Nutzerfrage + Antwort mit Quellen,
          generiert aus den Chunks und dem CAD-JSON als Bauteilkontext
```

---

## Evaluation

`test_verzahnung/evaluation.ipynb` misst die Retrieval-Qualität (MRR / Hit@k):

- **Block 1**: PDFs laden, Evaluationsset (Gold-Fragen je Chunk) erzeugen/laden
- **Block 2**: Chunking → Hybrid-Retrieval auf der Nutzerfrage → MRR

> Das Retrieval nutzt ausschließlich die Nutzerfrage; das CAD-JSON beeinflusst
> nur die Antwortgenerierung und damit nicht den MRR. Die Evaluation misst daher
> reine Retrieval-Qualität.

---

## Projektstruktur

```
Copilot_Verzahnungswissen/
├── cad_processor/              ← CAD-Prozessor (Gruppe B)
│   ├── src/
│   │   ├── step_parser.py      STEP-Datei einlesen + GearParameters extrahieren
│   │   ├── output_schema.py    GearParameters Datenklasse (JSON-Schnittstelle)
│   │   └── main.py             FastAPI (Port 8001)
│   ├── Dockerfile              conda/miniconda-basiertes Image
│   └── environment.yml
├── app/                        ← RAG-System (Gruppe A)
│   ├── api/main.py             FastAPI (Port 8000)
│   ├── core/                   Config, Factory, Interfaces
│   ├── implementations/        Embedder, Chunker, HybridRetriever, AnswerGenerator, ...
│   └── pipeline/               Indexierungs-Pipeline
├── frontend/                   Web-UI
│   ├── index.html              Einfaches Fallback-Frontend
│   └── design-system/          Verzahnungs-Copilot GUI (React, unter /ui ausgeliefert) — nur Laufzeit-Dateien
├── design-system-source/       Designer-Quellen/Showcase des Design-Systems (Komponenten-.jsx, guidelines, preview) — nicht zur Laufzeit geladen
├── prompts/                    LLM-Prompt-Template (Antwortgenerierung)
├── test_verzahnung/
│   ├── cad_testdaten/          10 synthetische GearParameters-JSONs + Generator
│   └── evaluation.ipynb        Retrieval-Evaluation (MRR)
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
- Hybrid-Retrieval benötigt `embedder.use_sparse: true`; nach Umstellung müssen
  bestehende Dokumente neu indexiert werden (alte Qdrant-Punkte haben keine Sparse-Vektoren).
