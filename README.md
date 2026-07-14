# KI-Copilot für Verzahnungswissen

Lokales Retrieval-Augmented-Generation-System (RAG) für Verzahnungswissen. Die Anwendung verbindet eine Dokumentenwissensbasis, die Analyse von STEP/STP-Dateien und ein lokales Ollama-Sprachmodell in einer Weboberfläche.

```text
PDF, CSV, Excel  -> Aufbereitung und Indexierung -> Qdrant
STEP/STP         -> CAD-Analyse -> Geometrieparameter
Frage + Quellen + CAD-Daten -> Solver/Reviewer über Ollama -> belegte Antwort
```

## Funktionsumfang

- Dokumente und ganze Ordner als Wissensbasis verwalten
- PDF-, CSV- und Excel-Dateien indexieren
- STEP/STP-Dateien analysieren und als 3D-Vorschau darstellen
- Dense- oder Hybrid-Retrieval mit `BAAI/bge-m3`
- Mehrstufige Antwortgenerierung mit Solver und Reviewer
- Quellenkennzeichnung für Dokumente (`[Q1]`, `[Q2]`) und CAD-Daten (`[CAD]`)
- Persistente Wissensbasis und Query-Protokolle

## Systemkomponenten

| Komponente | Standardadresse | Aufgabe |
|---|---|---|
| Web-App und API | `http://localhost:8000` | Benutzeroberfläche, Retrieval und Antwortgenerierung |
| Qdrant | `http://localhost:6333` | Vektordatenbank |
| CAD-Prozessor | `http://localhost:8001` | STEP-Analyse im Docker-Modus |
| Ollama | `http://localhost:11434` | Lokale LLM-Inferenz |

Ollama läuft bewusst auf dem Host, weil die Modelldateien nicht in das Docker-Image gehören. Im lokalen Conda-Modus wird der CAD-Prozessor direkt in die App geladen; Port `8001` ist dann nicht erforderlich.

## Empfohlener Schnellstart mit Docker

Dieser Weg benötigt nur Git, Docker Desktop und Ollama. Python, Conda, Qdrant und `pythonocc-core` werden nicht separat auf dem Host installiert.

### 1. Repository klonen

```bash
git clone https://github.com/hammer-stein/Copilot_Verzahnungswissen.git
cd Copilot_Verzahnungswissen
cp config.example.yaml config.yaml
```

`config.yaml` enthält die lokale Konfiguration und wird absichtlich nicht in Git eingecheckt.

### 2. Ollama vorbereiten

Ollama installieren und das konfigurierte Modell laden:

```bash
ollama pull llama3.2:3b
```

Falls Ollama nicht bereits als Dienst läuft, in einem eigenen Terminal starten:

```bash
ollama serve
```

Verbindung prüfen:

```bash
curl http://localhost:11434/api/tags
```

### 3. Anwendung starten

```bash
docker compose up --build -d
docker compose ps
```

Beim ersten Start werden die Images und das Embedding-Modell geladen. Danach die Anwendung öffnen:

```text
http://localhost:8000/
```

Logs anzeigen:

```bash
docker compose logs -f app cad_processor qdrant
```

Anwendung beenden:

```bash
docker compose down
```

Die Wissensbasis bleibt dabei im Docker-Volume `qdrant_data` und unter `storage/` erhalten. Nur `docker compose down -v` löscht auch die Docker-Volumes.

## Alternativer lokaler Start mit Conda

Dieser Modus eignet sich für Entwicklung und benötigt keinen separaten CAD-Container. Qdrant kann eingebettet oder als Docker-Service betrieben werden.

### 1. Umgebung erstellen

```bash
cp config.example.yaml config.yaml
conda env create -f cad_processor/environment.yml
conda activate gear-copilot
python -m pip install -r requirements.txt
```

Installation der CAD-Bibliothek prüfen:

```bash
python -c "import OCC; print('OCC ok')"
```

### 2. Dienste vorbereiten

Ollama starten und das Modell laden:

```bash
ollama pull llama3.2:3b
ollama serve
```

Die Beispielkonfiguration verwendet eingebettetes Qdrant:

```yaml
vector_store:
  implementation: "qdrant"
  path: "storage/qdrant"
```

Damit ist kein Qdrant-Container nötig. Alternativ `path` in `config.yaml` auskommentieren und Qdrant starten:

```bash
docker compose up -d qdrant
```

### 3. App starten

```bash
conda activate gear-copilot
./scripts/start_local.sh
```

Für Auto-Reload während der Entwicklung:

```bash
GEAR_COPILOT_RELOAD=1 ./scripts/start_local.sh
```

Danach `http://localhost:8000/` öffnen.

## Nutzung

1. Unter **Wissensbasis** PDF-, CSV- oder Excel-Dateien hochladen.
2. Optional Ordner anlegen oder einen ganzen Dokumentordner hochladen.
3. Eine STEP/STP-Datei oder eine Bauteiltabelle laden.
4. Eine oder mehrere Fragen stellen.
5. Antwort, Quellen und den Solver/Reviewer-Ablauf prüfen.

CAD-Fragen funktionieren auch ohne Treffer aus der Wissensbasis. Wenn weder CAD-Daten noch Dokumentquellen eine Antwort belegen, soll das Modell die fehlende Informationsgrundlage ausdrücklich nennen.

## Konfiguration

Alle Einstellungen stehen in `config.yaml`, das aus `config.example.yaml` erzeugt wird.

| Bereich | Wichtige Einstellung | Hinweis |
|---|---|---|
| `answer_generator` | `model_name` | Muss mit einem lokal geladenen Ollama-Modell übereinstimmen |
| `answer_generator` | `implementation` | `multi_agent` oder `llama_ollama` |
| `embedder` | `device` | `cpu`, `mps` oder `cuda` |
| `embedder` | `use_sparse` | Änderung erfordert eine neue Indexierung |
| `cad_adapter` | `implementation` | `cad_processor_local`, `cad_processor_http` oder `synthetic_json` |
| `vector_store` | `path` | Eingebettetes Qdrant; ohne `path` werden `host` und `port` verwendet |
| `retriever` | `min_similarity` | Mindestähnlichkeit für Texttreffer |

Docker Compose überschreibt die Serviceadressen automatisch:

- Qdrant: `qdrant:6333`
- CAD-Prozessor: `cad_processor:8001`
- Ollama auf dem Host: `host.docker.internal:11434`

Nach Änderungen an Embedding-, Sparse- oder Chunking-Einstellungen müssen die Dokumente neu indexiert werden. Änderungen an Prompts, Modell oder CAD-Adapter erfordern einen Neustart der App.

## Persistente und lokale Daten

Folgende Dateien werden absichtlich nicht über Git verteilt:

| Pfad | Inhalt |
|---|---|
| `config.yaml` | Rechnerbezogene Konfiguration |
| `storage/uploads/` | Hochgeladene Originaldateien |
| `storage/folders.json` | Ordnerstruktur der Wissensbasis |
| `storage/cad_previews/` | Erzeugte 3D-Vorschauen |
| `storage/qdrant/` | Eingebettete Vektordatenbank |
| `logs/` | Query- und Serverlogs |

Bei einer Abgabe oder Neuinstallation startet die Wissensbasis deshalb leer. Dokumente werden anschließend über die Weboberfläche neu hochgeladen. Sollen vorhandene Daten migriert werden, müssen `storage/` und bei Docker-Nutzung das Qdrant-Volume separat gesichert werden.

## API-Auswahl

| Methode | Route | Beschreibung |
|---|---|---|
| `GET` | `/` | Weboberfläche |
| `POST` | `/upload` | PDF, CSV oder Excel indexieren |
| `GET` | `/documents` | Dokumente auflisten |
| `POST` | `/folders` | Wissensbasisordner anlegen |
| `POST` | `/cad/analyze` | STEP/STP analysieren |
| `POST` | `/cad/from-csv` | Bauteildaten aus Tabelle laden |
| `GET` | `/cad/preview/{name}` | 3D-Vorschau abrufen |
| `POST` | `/ask` | Fragen beantworten |
| `GET` | `/ask/status/{request_id}` | Bearbeitungsstatus abrufen |

## Tests und Abgabeprüfung

Schnelle statische und funktionale Prüfung:

```bash
python -m compileall app cad_processor/src
python -m pytest -q tests
python -m pytest -q cad_processor/tests
docker compose config --quiet
```

Die CAD-Tests benötigen `pythonocc-core` und müssen deshalb im Conda-Environment `gear-copilot` laufen. Eine reine Python-`.venv` reicht nur für die Tests unter `tests/`.

Docker-Images vollständig bauen:

```bash
docker compose build app cad_processor
```

Nach einem Start lassen sich die wichtigsten Dienste so prüfen:

```bash
curl http://localhost:8000/documents
curl http://localhost:6333/healthz
curl http://localhost:11434/api/tags
```

## Fehlerbehebung

### `[Errno 61] Connection refused` bei der Antwortgenerierung

Ollama ist auf Port `11434` nicht erreichbar:

```bash
ollama serve
curl http://localhost:11434/api/tags
```

### Ollama-Modell nicht gefunden

```bash
ollama list
ollama pull llama3.2:3b
```

Der Wert unter `answer_generator.model_name` muss exakt dem Namen aus `ollama list` entsprechen.

### CAD-Analyse im lokalen Modus schlägt fehl

```bash
conda activate gear-copilot
python -c "import OCC; print('OCC ok')"
```

### Keine Quellen in der Antwort

Zuerst Dokumente über die Wissensbasis hochladen. Bei einer neuen Qdrant-Instanz oder nach geänderten Embedding-Einstellungen muss der Bestand neu indexiert werden.

### Containerstatus und Logs prüfen

```bash
docker compose ps
docker compose logs --tail=200 app cad_processor qdrant
```

## Projektstruktur

```text
app/                    FastAPI, RAG-Pipeline und Implementierungen
cad_processor/          STEP-Analyse und eigener Docker-Service
frontend/               Weboberfläche
prompts/                System-, Solver- und Reviewer-Prompts
tests/                  Automatisierte Tests
test_verzahnung/        Aktuelle Evaluations- und Stresstestartefakte
docs/                   Technische Projektdokumentation
scripts/start_local.sh  Lokaler Start im Conda-Environment
config.example.yaml     Versionierte Beispielkonfiguration
docker-compose.yml      Vollständiger Docker-Start
```
