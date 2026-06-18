# KI-Copilot für Verzahnungswissen

Modulares RAG-System für Verzahnungswissen mit optionaler CAD-Anbindung.

```text
PDFs                 → RAG-Wissensbasis in Qdrant
STEP/STP-Datei       → cad_processor → GearParameters JSON
Nutzerfrage + CAD    → Retrieval aus PDFs → Solver/Reviewer-LLM → Antwort + Lösungsweg + Quellen
```

## Systemüberblick

Das Projekt besteht aus drei laufenden Komponenten:

| Komponente | Port | Aufgabe |
|---|---:|---|
| `app` | `8000` | RAG-Backend, Web-GUI, PDF-Upload, Fragen beantworten |
| `cad_processor` | `8001` | STEP/STP-Dateien analysieren und GearParameters-JSON erzeugen |
| `qdrant` | `6333` | Vektordatenbank für PDF-Chunks |

Ollama läuft separat auf dem Host-Rechner und stellt das Antwortmodell bereit.

### Aktueller Anfragefluss

```text
1. Nutzerfrage wird mit BGE-M3 embedded.
2. HybridRetriever sucht passende PDF-Chunks in Qdrant.
3. Der Antwortgenerator bekommt:
   - ursprüngliche Nutzerfrage
   - gefundene Chunks
   - vollständiges CAD-JSON
   - gewünschtes Ausgabeformat
4. Antwortgenerierung je nach answer_generator.implementation (config.yaml):
   - "multi_agent" (Standard): Orchestrator (Code) → Solver (LLM) → Reviewer (LLM).
     Der Solver entwirft eine quellenbelegte Antwort, der Reviewer prüft sie auf
     Quellendeckung und Plausibilität (optional eine Revision). Der nachvollziehbare
     Lösungsweg wird als agent_trace + review zurückgegeben.
   - "llama_ollama": klassischer Single-Pass (genau ein LLM-Aufruf, kein agent_trace).
5. Ollama erzeugt die Antwort mit Quellenmarkierungen [Q1], [Q2], ... ([CAD] für Bauteildaten).
```

Wichtig:
- Das CAD-JSON wird **nicht** in das Retrieval eingebettet und nicht als Filter verwendet. Es wird erst in der Antwortstufe als Bauteilkontext genutzt.
- Der Multi-Agenten-Fluss fällt bei jedem Fehler (LLM-Fehler, ungültiges JSON) automatisch auf den bewährten Single-Pass zurück – die Antwortqualität ist nie schlechter als zuvor.

---

## Schnellstart Mit Docker Compose

Empfohlener Weg, wenn du das komplette System mit echter STEP-Analyse starten willst.

### Voraussetzungen

- Docker Desktop läuft
- Ollama ist installiert und läuft auf deinem Rechner

### Start

```bash
# 1. In den Projektordner wechseln
cd "/Users/maxhammerstein/Projects/KI-Copilot für Verzahnungswissen"

# 2. Ollama-Modell einmalig laden
ollama pull llama3.2:3b

# 3. Konfiguration anlegen, falls noch nicht vorhanden
cp config.example.yaml config.yaml

# 4. Alle Services bauen und starten
docker compose up --build
```

Danach öffnest du:

```text
http://localhost:8000/
```

Beim ersten Start kann das `app`-Backend zusätzlich das Embedding-Modell `BAAI/bge-m3` herunterladen. Das kann einige Minuten dauern. Der Hugging-Face-Cache wird im Docker-Volume `hf_cache` gespeichert und bleibt für spätere Starts erhalten.

### Was Docker Compose automatisch umstellt

In `docker-compose.yml` werden diese Umgebungsvariablen gesetzt:

```text
QDRANT_HOST=qdrant
CAD_PROCESSOR_URL=http://cad_processor:8001
OLLAMA_URL=http://host.docker.internal:11434
```

Dadurch wird deine lokale `config.yaml` im Container automatisch auf Compose-Betrieb umgestellt:

- Qdrant läuft als Docker-Service.
- STEP-Dateien werden an den echten `cad_processor` geschickt.
- Ollama wird vom Host-Rechner aus genutzt.

---

## Lokaler Start Ohne Komplettes Docker

Dieser Weg ist sinnvoll für Entwicklung am RAG-Backend. Qdrant kann trotzdem per Docker laufen.

### 1. Ollama vorbereiten

```bash
ollama pull llama3.2:3b
```

### 2. Python-Umgebung für das RAG-System erstellen

```bash
cd "/Users/maxhammerstein/Projects/KI-Copilot für Verzahnungswissen"

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.11 ist empfohlen. Die Pins in `requirements.txt` sind auf den 3.11-Stack abgestimmt.

### 3. Konfiguration anlegen

```bash
cp config.example.yaml config.yaml
```

Die Standardkonfiguration nutzt:

- `cad_adapter.implementation: "synthetic_json"`
- Qdrant über `localhost:6333`
- Ollama über `localhost:11434`

### 4. Qdrant starten

```bash
docker compose up -d qdrant
```

### 5. RAG-Backend starten

```bash
uvicorn app.api.main:app --reload --port 8000
```

Dann öffnen:

```text
http://localhost:8000/
```

### Optional: komplett ohne Qdrant-Docker

Wenn du keinen Qdrant-Container nutzen willst, setze in `config.yaml` unter `vector_store`:

```yaml
path: "storage/qdrant"
```

Dann läuft Qdrant eingebettet im lokalen On-Disk-Modus. In diesem Modus brauchst du nur noch Ollama als externen Dienst.

---

## Echte STEP-Analyse Lokal Starten

Für echte CAD-Auswertung ohne Docker Compose muss zusätzlich der CAD-Prozessor lokal laufen.

### 1. CAD-Processor-Umgebung erstellen

```bash
cd "/Users/maxhammerstein/Projects/KI-Copilot für Verzahnungswissen"
conda env create -f cad_processor/environment.yml
conda activate gear-copilot
```

### 2. CAD-Processor starten

```bash
cd cad_processor
uvicorn src.main:app --reload --port 8001
```

### 3. RAG-Konfiguration umstellen

In der Root-`config.yaml`:

```yaml
cad_adapter:
  implementation: "cad_processor_http"
  url: "http://localhost:8001"
```

Dann das RAG-Backend wie oben starten:

```bash
uvicorn app.api.main:app --reload --port 8000
```

Vollständige CAD-Setup-Anleitung: [`cad_processor/SETUP_ANLEITUNG.md`](cad_processor/SETUP_ANLEITUNG.md)

---

## Nutzung Im Web-GUI

1. Öffne `http://localhost:8000/`.
2. Verwalte die Wissensbasis über die Schaltfläche **„Wissensbasis"** in der Seitenleiste
   (öffnet ein Verwaltungsfenster): PDFs hochladen, Dokumente löschen, **Ordner anlegen**
   und Dokumente per Auswahlfeld zwischen Ordnern **verschieben**. Ordner dienen nur der
   Organisation und schränken das Retrieval nicht ein.
3. Warte, bis die Dokumente indexiert sind.
4. Lade als aktives Bauteil eine **STEP/STP-Datei** oder eine **GearParameters-JSON**
   (z. B. die Test-Datensätze `test_verzahnung/cad_testdaten/gear_*.json`) hoch, oder nutze
   die synthetischen CAD-Beispiele. JSON wird im Browser geparst und direkt als Bauteil gesetzt.
5. Stelle eine oder mehrere Fragen.
6. Wähle optional das Ausgabeformat:
   - `kurz`
   - `standard`
   - `ausführlich`
   - `stichpunkte`
   - `tabellarisch`

Ohne hochgeladene PDFs kann das System keine fachlich belegten Antworten aus Quellen erzeugen.

---

## CAD-Datenquellen

In `config.yaml` steuert `cad_adapter.implementation`, woher die CAD-Daten kommen:

| Wert | Verhalten |
|---|---|
| `synthetic_json` | Nutzt synthetische GearParameters-Testdaten aus `test_verzahnung/cad_testdaten/` |
| `cad_processor_http` | Sendet STEP/STP-Dateien an den CAD-Prozessor auf Port `8001` |

Die Endpunkte `/cad/random` und `/cad/examples` nutzen immer die synthetischen Testdaten. Sie sind für Demo und Tests gedacht.

Die synthetischen Datensätze können neu erzeugt werden mit:

```bash
python test_verzahnung/cad_testdaten/generate_testdata.py
```

---

## API-Endpunkte

### RAG-System (`localhost:8000`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/` | Leitet auf das Web-GUI weiter |
| `POST` | `/upload` | PDF hochladen und indexieren (optionaler Form-Parameter `folder`) |
| `GET` | `/documents` | Indexierte Dokumente auflisten (inkl. `file_name`, `folder`) |
| `DELETE` | `/documents/{doc_hash}` | Dokument löschen |
| `POST` | `/documents/{doc_hash}/move` | Dokument in einen Ordner verschieben (`{ "folder": "…" }`, `""` = kein Ordner) |
| `GET` | `/folders` | Ordner auflisten (registrierte + von Dokumenten genutzte) |
| `POST` | `/folders` | Ordner anlegen (`{ "name": "…" }`) |
| `DELETE` | `/folders/{name}` | Ordner löschen (Dokumente bleiben erhalten, gehen auf „kein Ordner“) |
| `POST` | `/cad/analyze` | STEP/STP-Datei analysieren oder synthetischen CAD-Datensatz liefern |
| `GET` | `/cad/random` | Zufälligen synthetischen CAD-Datensatz laden |
| `GET` | `/cad/examples` | Synthetische CAD-Beispiele auflisten |
| `GET` | `/cad/examples/{name}` | Bestimmtes CAD-Beispiel laden |
| `POST` | `/ask` | Fragen beantworten |

Beispiel für `/ask`:

```json
{
  "questions": ["Welches Fertigungsverfahren ist geeignet?"],
  "cad_metadata": {
    "gear_type": "helical",
    "tooth_profile": {
      "module_mm": 2.0,
      "num_teeth": 25
    }
  },
  "format": "standard"
}
```

Antwort: `{ "cad_metadata": {...}, "answers": [ { "question", "answer_text", "sources": [...] } ] }`.
Im Modus `multi_agent` trägt jede Antwort zusätzlich die optionalen Felder `agent_trace`
(die geprüften Einzelschritte Orchestrator/Solver/Reviewer) und `review` (Gesamturteil) –
das Web-GUI zeigt sie als aufklappbaren Block „Lösungsweg & Prüfung". Beide Felder sind
optional, sodass der Single-Pass-Modus und ältere Clients unverändert funktionieren.

### CAD-Prozessor (`localhost:8001`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/analyze` | STEP/STP-Datei hochladen und GearParameters-JSON erhalten |

---

## Evaluation

`test_verzahnung/evaluation.ipynb` misst die Retrieval-Qualität:

- PDF-Dokumente laden
- Evaluationsfragen erzeugen oder laden
- Chunking und Hybrid-Retrieval ausführen
- MRR und Hit@k berechnen

Die Evaluation misst die reine Retrieval-Qualität. Das CAD-JSON beeinflusst aktuell nur die Antwortgenerierung.

---

## Projektstruktur

```text
Copilot_Verzahnungswissen/
├── app/                        RAG-System
│   ├── api/main.py             FastAPI-App auf Port 8000
│   ├── core/                   Config, Factory, Interfaces, Types
│   ├── implementations/        Embedder, Chunker, Retriever, CAD-Adapter, AnswerGenerator (Single-Pass + Multi-Agent)
│   └── pipeline/               PDF-Indexierung + agents/ (Solver-/Reviewer-Agenten)
├── cad_processor/              CAD-Prozessor
│   ├── src/main.py             FastAPI-App auf Port 8001
│   ├── src/step_parser.py      STEP-Datei einlesen
│   └── src/output_schema.py    GearParameters-JSON-Struktur
├── frontend/                   Web-GUI und Fallback-Frontend
├── prompts/                    Prompt-Templates
├── test_verzahnung/
│   ├── cad_testdaten/          Synthetische CAD-JSONs
│   └── evaluation.ipynb        Retrieval-Evaluation
├── Dockerfile                  RAG-App-Image
├── docker-compose.yml          Qdrant + CAD-Prozessor + RAG-App
├── requirements.txt            Python-Abhängigkeiten für RAG-System
├── config.example.yaml         Vorlage für lokale Konfiguration
└── README.md
```

---

## Häufige Probleme

### `COPY schemas/ schemas/` schlägt beim Docker-Build fehl

Der Ordner `schemas/` existiert in der aktuellen Architektur nicht mehr. Der Dockerfile darf ihn nicht kopieren.

### `/cad/random` findet keine Testdaten

Prüfe, ob `test_verzahnung/cad_testdaten/` vorhanden ist. Im Docker-Image wird dieser Ordner explizit mitkopiert.

### Antworten enthalten keine Quellen

Dann sind vermutlich noch keine PDFs indexiert. Lade zuerst mindestens ein PDF über das Web-GUI hoch.

### Ollama ist aus Docker nicht erreichbar

Prüfe, ob Ollama auf dem Host läuft:

```bash
ollama list
```

Im Compose-Betrieb nutzt die App `http://host.docker.internal:11434`.

### Nach Änderung von Embedding- oder Chunking-Einstellungen sind alte Treffer schlecht

Dann die Dokumente neu indexieren. Alte Qdrant-Punkte wurden mit den vorherigen Einstellungen erzeugt.
