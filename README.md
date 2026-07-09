# KI-Copilot für Verzahnungswissen

Ein lokales RAG-System für Verzahnungswissen mit integrierter STEP-Analyse. Web-GUI, API, Dokumentenbibliothek, Fragebeantwortung und CAD-Analyse laufen in einem Python-Prozess auf Port `8000`.

```text
PDFs              -> Wissensbasis / Qdrant
STEP/STP          -> cad_processor_local -> GearParameters JSON
Frage + CAD JSON  -> BAAI/bge-m3 Embedding -> Kosinus-Suche -> Solver/Reviewer-LLM -> Antwort
```

## Zielbetrieb

| Komponente | Adresse | Zweck |
|---|---|---|
| Copilot-App | `http://localhost:8000/` | Web-GUI, API, PDF-Upload, STEP-Analyse, Antworten |
| Qdrant | `localhost:6333` oder `storage/qdrant` | Vektordatenbank |
| Ollama | `localhost:11434` | LLM-Inferenz |

Der CAD-Prozessor läuft standardmäßig **nicht** mehr als eigener Webservice auf Port `8001`. Er wird direkt im App-Prozess geladen (`cad_adapter.implementation: "cad_processor_local"`).

Für einen externen Server ist der empfohlene Zielzustand:

```text
1 Serverprozess auf Port 8000
1 lokaler Ollama-Dienst auf 127.0.0.1:11434
Qdrant entweder eingebettet unter storage/qdrant oder als separater Qdrant-Dienst
Persistente Projektdaten unter storage/
```

## Einmalige Installation

### 1. Repository vorbereiten

```bash
cd "/pfad/zum/KI-Copilot für Verzahnungswissen" # z.B. cd "/Users/maxhammerstein/Projects/KI-Copilot für Verzahnungswissen"
cp config.example.yaml config.yaml
```

### 2. Conda-Umgebung erstellen

Dieser Schritt bündelt RAG-Abhängigkeiten und `pythonocc-core` für die STEP-Analyse in einer Umgebung.

```bash
conda env create -f cad_processor/environment.yml
conda activate gear-copilot
python -m pip install -r requirements.txt
```

### 3. Ollama-Modell laden

```bash
ollama pull llama3.2:3b
```

Falls Ollama nicht bereits als Dienst läuft, `ollama serve` in einem separaten Terminal, `screen`/`tmux` oder als Systemdienst starten.

### 4. Qdrant wählen

Für einen Docker-unabhängigen Server ist der eingebettete On-Disk-Modus am einfachsten. Dafür in `config.yaml` setzen:

```yaml
vector_store:
  implementation: "qdrant"
  path: "storage/qdrant"
  collection_name: "knowledge_base"
```

Wichtig: Wenn vorher ein Docker-Qdrant genutzt wurde, liegen die vorhandenen Vektoren nicht automatisch in `storage/qdrant`. Dann entweder die PDFs neu hochladen/neu indexieren oder Qdrant-Daten gezielt migrieren.

Alternativ kann ein Qdrant-Server laufen:

```bash
docker compose up -d qdrant
```

Dann bleibt in `config.yaml` `path` leer und `host: "localhost"`, `port: 6333`.

## Start

```bash
conda activate gear-copilot
./scripts/start_local.sh
```

Danach öffnen:

```text
http://localhost:8000/
```

`scripts/start_local.sh` beendet alte `uvicorn app.api.main`- und `uvicorn src.main`-Prozesse und startet genau einen App-Prozess auf Port `8000`. Für Entwicklung mit Auto-Reload:

```bash
GEAR_COPILOT_RELOAD=1 ./scripts/start_local.sh
```

## Laufender Anfrageprozess

Während eine Frage bearbeitet wird, zeigt das Web-GUI den aktuellen Ablauf an und hält abgeschlossene Schritte sichtbar:

1. `Embedding` via `BAAI/bge-m3`
2. `Chunk-Suche` via Kosinus-Ähnlichkeit
3. `Antwortgenerierung` via `llama3.1:8b`
4. `Validierung` via `llama3.1:8b`
5. `Verbesserung` via `llama3.1:8b`, falls der Reviewer Mängel findet

Nach Abschluss steht dieselbe Spur unter **Lösungsweg & Prüfung**. Ändert sich das LLM oder das Embedding-Modell in `config.yaml`, übernimmt die Anzeige die neuen Modellnamen beim nächsten Serverstart.

## Nutzung

1. `http://localhost:8000/` öffnen.
2. Über **Wissensbasis** PDFs hochladen, Ordner anlegen und Dokumente organisieren.
3. Optional ganze Ordner hochladen; PDF-Dateien werden inklusive Unterordnerstruktur übernommen.
4. STEP/STP-Datei hochladen. Die App analysiert sie direkt über `cad_processor_local`.
5. Fragen stellen. CAD-Fakten werden mit `[CAD]`, Dokumentquellen mit `[Q1]`, `[Q2]` markiert.

Fragen zum aktuell geladenen Bauteil, etwa „Um welches Zahnrad handelt es sich?“, werden bevorzugt aus dem CAD-JSON beantwortet. Wenn CAD-Daten und Wissensbasis keine Antwort enthalten, muss das Modell dies eindeutig ausgeben.

## Was Nach Änderungen Neu Ausgeführt Werden Muss

| Änderung | Erforderlicher Schritt |
|---|---|
| Prompt-Dateien, Frontend, Python-Code | Server neu starten: `./scripts/start_local.sh` |
| `answer_generator.model_name` | Modell mit `ollama pull ...` laden, Server neu starten |
| `embedder.model_name`, `embedder.use_sparse`, Chunking-Parameter | PDFs neu indexieren |
| `cad_adapter.implementation` | Server neu starten |
| `vector_store.path`, `collection_name` | Wissensbasis neu aufbauen oder Qdrant-Daten migrieren |

## Paketierung Für Einen Anderen Server

### 0. Schnellster Weg: Neuer Rechner Mit Docker (ohne Conda)

Für einen frischen Rechner (z.B. neuen Mac) ist **keine** Miniconda-, Python- oder
torch-Installation nötig – alle Abhängigkeiten (Conda/PythonOCC im CAD-Prozessor,
torch/bge-m3 im RAG-System) stecken in den Docker-Images und bauen sich selbst.
Auf dem Zielrechner werden nur zwei Programme installiert: **Docker Desktop** und **Ollama**.

```bash
git clone https://github.com/hammer-stein/Copilot_Verzahnungswissen.git
cd Copilot_Verzahnungswissen
cp config.example.yaml config.yaml   # model_name muss zum gezogenen Ollama-Modell passen
ollama pull llama3.1:8b              # Default der config.example.yaml; auf Apple Silicon flüssig
                                     # (schwächere Hardware: llama3.2:3b ziehen + model_name anpassen)
docker compose up --build            # erster Build dauert (Images), danach Start in Sekunden
```

Danach läuft die GUI unter `http://localhost:8000/` (Checks siehe Abschnitt 6).

Hinweise:

- **Images auf dem Zielrechner bauen, nicht übertragen:** `docker save`-Exporte von einem
  Intel-Mac laufen auf Apple Silicon nur emuliert (langsam). `docker compose up --build`
  baut nativ für die jeweilige Architektur.
- **Wissensbasis:** Der Docker-Qdrant startet leer. Entweder die Dokumente (PDFs/CSVs aus
  `storage/uploads/` des alten Rechners) über die UI neu hochladen – oder Daten wie in
  Abschnitt 1 beschrieben mitnehmen.
- `config.yaml` ist nicht im Repository (gitignored) und muss separat kopiert oder wie oben
  aus `config.example.yaml` neu erzeugt werden. Im Compose-Betrieb überschreiben die
  Umgebungsvariablen aus `docker-compose.yml` automatisch Qdrant-/CAD-/Ollama-Adressen.

### 1. Vor Dem Kopieren Entscheiden: Daten Mitnehmen Oder Neu Aufbauen

Die Wissensbasis besteht aus mehreren Teilen:

| Pfad/Ort | Inhalt | Muss mit, wenn Daten erhalten bleiben sollen? |
|---|---|---|
| `storage/uploads/` | Original-PDFs | ja |
| `storage/folders.json` | Ordnerstruktur | ja |
| `storage/cad_previews/` | gerenderte STEP/STL-Vorschauen | optional |
| `storage/qdrant/` | Vektoren bei eingebettetem Qdrant | ja, falls `vector_store.path` genutzt wird |
| Docker-Volume `*_qdrant_data` | Vektoren bei Docker-Qdrant | ja, falls Docker-Qdrant weitergenutzt wird |
| `config.yaml` | lokale Modell-/Serverkonfiguration | ja |
| `logs/` | Query-Logs | optional |

Wenn der Zielserver mit sauberer Wissensbasis starten soll, reicht Repository + `config.yaml`; PDFs werden danach über die UI neu hochgeladen.

### 2. Projekt übertragen

Kopiere das Repository inklusive dieser Ordner, wenn Daten erhalten bleiben sollen:

```text
storage/
logs/
config.yaml
```

Wenn die Wissensbasis neu aufgebaut wird, reicht das Repository plus `config.yaml`; PDFs können danach wieder hochgeladen werden.

### 3. Server vorbereiten

Installiere auf dem Zielserver:

- Miniconda/Miniforge oder Mambaforge
- Ollama
- optional NVIDIA/CUDA-Treiber, falls `embedder.device: "cuda"` genutzt wird
- Git und ein Prozessmanager wie `screen`, `tmux` oder `systemd`

Dann im Projekt:

```bash
conda env create -f cad_processor/environment.yml
conda activate gear-copilot
python -m pip install -r requirements.txt
ollama pull llama3.1:8b
```

Falls Ollama nicht bereits als Dienst läuft, `ollama serve` in einem separaten Terminal, `screen`/`tmux` oder als Systemdienst starten.

Prüfen:

```bash
python -c "import OCC; print('OCC ok')"
ollama list
```

### 4. Konfiguration setzen

Für robuste Übertragung ohne zusätzlichen Qdrant-Container:

```yaml
vector_store:
  implementation: "qdrant"
  path: "storage/qdrant"

cad_adapter:
  implementation: "cad_processor_local"

answer_generator:
  implementation: "multi_agent"
  model_name: "llama3.1:8b"
```

Wenn stattdessen ein externer oder Docker-Qdrant genutzt wird:

```yaml
vector_store:
  implementation: "qdrant"
  host: "localhost"
  port: 6333
  collection_name: "knowledge_base"
```

Dann muss Qdrant vor der App laufen.

### 5. Starten

```bash
./scripts/start_local.sh
```

Firewall/Reverse Proxy nur für Port `8000` öffnen. Ollama und Qdrant sollten nicht öffentlich exponiert werden.

Für direkten Serverzugriff:

```bash
GEAR_COPILOT_HOST=0.0.0.0 ./scripts/start_local.sh
```

Für produktiveren Betrieb empfiehlt sich ein `systemd`-Service oder `tmux`/`screen`, damit der Prozess nach dem Schließen der SSH-Verbindung weiterläuft.

Minimaler `systemd`-Startbefehl im Service wäre sinngemäß:

```ini
WorkingDirectory=/pfad/zum/KI-Copilot für Verzahnungswissen
Environment=GEAR_COPILOT_HOST=127.0.0.1
ExecStart=/bin/bash scripts/start_local.sh
Restart=always
```

Bei direkter Veröffentlichung ohne Reverse Proxy `GEAR_COPILOT_HOST=0.0.0.0` setzen und Port `8000` per Firewall gezielt freigeben.

### 6. Nach Dem Start Prüfen

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/documents
curl http://127.0.0.1:11434/api/tags
```

Bei Qdrant-Servermodus zusätzlich:

```bash
curl http://127.0.0.1:6333/
```

Danach im Browser:

```text
http://SERVER-IP:8000/
```

Wenn `storage/qdrant` leer ist oder ein neuer Qdrant-Dienst verwendet wird, PDFs über die Wissensbasis erneut hochladen.

## Docker-Entscheidung

Für diesen Stand ist der empfohlene Serverweg **Conda + Startskript**, nicht vollständiges Docker Compose. Grund: `pythonocc-core` und CAD-Kernel-Abhängigkeiten sind über Conda zuverlässiger reproduzierbar als in einem generischen Python-Docker-Image.

`docker-compose.yml` ist aktuell als Legacy-/Optionalpfad zu verstehen. Es enthält noch einen separaten `cad_processor`-Service auf Port `8001`; der empfohlene Standard ist dagegen `cad_processor_local` im Port-`8000`-App-Prozess.

Docker bleibt sinnvoll für einen separaten Qdrant-Server. Wenn Docker komplett vermieden werden soll, `vector_store.path: "storage/qdrant"` setzen und die Wissensbasis dort neu aufbauen oder migrieren.

## Browser-Abhängigkeiten

Das Frontend lädt React, Babel, Lucide und Three.js aktuell über CDN (`unpkg.com`). Für normale Server mit Internetzugang ist das ausreichend. Für ein vollständig isoliertes Rechenzentrum müssen diese JavaScript-Dateien lokal vendort und in `frontend/design-system/ui_kits/copilot/index.html` auf lokale Pfade umgestellt werden.

## API

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/` | Web-GUI |
| `POST` | `/upload` | PDF hochladen und indexieren |
| `GET` | `/documents` | Dokumente inkl. Titel, Ordner, Chunk-Anzahl |
| `POST` | `/folders` | Ordner anlegen |
| `POST` | `/cad/analyze` | STEP/STP analysieren |
| `GET` | `/cad/preview/{name}.stl` | gerendertes STEP-Preview-Mesh |
| `POST` | `/ask` | Fragen beantworten |
| `GET` | `/ask/status/{request_id}` | Live-Prozessstatus einer Anfrage |

## Fehlerbehebung

### Weiße Seite nach STEP-Analyse

Browser hart neu laden. Falls es weiter passiert, Serverlog prüfen und sicherstellen, dass die aktuelle UI ausgeliefert wird:

```bash
./scripts/start_local.sh
```

### `CAD analysis failed`

Prüfen, ob die App im Conda-Env läuft:

```bash
conda activate gear-copilot
python -c "import OCC; print('OCC ok')"
```

### Antwortmodell nicht gefunden

```bash
ollama list
ollama pull llama3.1:8b
```

### Quellen fehlen

Es sind vermutlich noch keine PDFs indexiert oder der Retrieval-Threshold ist zu hoch. Dokumente hochladen oder in `config.yaml` `retriever.min_similarity` vorsichtig senken.
