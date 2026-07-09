# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Projekt-Kontext: KI Copilot für Verzahnungswissen
Ein lokales RAG-System (Retrieval-Augmented Generation) zur Beantwortung von Ingenieursfragen rund um Zahnradgeometrien und Fertigung. Das System analysiert STEP 242 CAD-Dateien, extrahiert Parameter und füttert diese zusammen mit Fachdokumenten in ein lokales LLM. 

**Wichtig:** Es gibt keinen Konversationskontext zwischen den Anfragen. Jede Anfrage an das LLM ist vollständig isoliert.

## System-Architektur & Ports
Das Projekt ist in drei Hauptkomponenten aufgeteilt, die via Docker Compose orchestriert werden:

1. **RAG-System (Gruppe A) - Port 8000**
   - Ordner: `/app/`
   - Stack: FastAPI, Python 3.11, Qdrant (Vektordatenbank)
   - Aufgaben: Dokumenten-Upload, Vektor-Suche, LLM-Orchestrierung (`/ask`).
2. **CAD-Prozessor (Gruppe B) - Port 8001**
   - Ordner: `/cad_processor/`
   - Stack: FastAPI, PythonOCC (Miniconda), STEP AP242
   - Aufgaben: Geometrie-Analyse (`POST /analyze`), Extraktion der `GearParameters`.
   - Pipeline (`src/`): `step_parser.py` (STEP einlesen) → `geometry_analyzer.py` / `gear_metrology.py` (software-unabhängige Vermessung über Trägheitsachsen-Querschnitte) → `gear_hints.py` (Heuristiken/Klassifikation) → `output_schema.py` (kanonische GearParameters-Struktur). Unterstützt u.a. Stirn-, Kegel-, Spiral-, Gehrungs- und Ratschenräder. Jeder Parameter trägt `{value, unit, confidence}` mit Tiers DIRECT/CALC/FALLBACK/HEURISTIC/DEFAULT (Schema 2.0).
3. **Frontend / Web-GUI**
   - Laufzeit-Ordner: `frontend/design-system/ui_kits/copilot/` (von `app` als StaticFiles unter `http://localhost:8000/` ausgeliefert).
   - Stack: React. Der Design-System-Showcase in `design-system-source/` wird zur Laufzeit **nicht** geladen.

## Infrastruktur & externe Services
- **LLM:** Ollama (Modell: `llama3.2:3b`). Läuft **außerhalb** von Docker auf dem Host.
- **Vektordatenbank:** Qdrant (Port 6333 im Container-Netzwerk).
- **Netzwerk-Routing:** Innerhalb von Docker kommunizieren Services über ihre Containernamen (`qdrant`, `cad_processor`). Der Zugriff auf Ollama erfolgt zwingend über `http://host.docker.internal:11434`.

## Architektur-Muster (Protocol + Factory + Config)
Das RAG-System ist konsequent austauschbar aufgebaut. Bevor du eine Komponente änderst, verstehe diese drei Dateien:
- **`app/core/interfaces.py`** – Alle Komponenten sind als Python `Protocol` definiert (`DocumentLoader`, `Chunker`, `Embedder`, `CADAdapter`, `VectorStore`, `Retriever`, `AnswerGenerator`). Eine Implementierung muss nicht erben, nur die Methode haben (structural subtyping).
- **`app/core/factory.py`** – **Einziger** Ort, an dem konkrete Implementierungen instanziiert werden. `build_components()` liest die `config.yaml` und wählt per `implementation`-Key die Klasse aus. Importe sind **bewusst lazy** (erst in der Funktion), damit ein Import von `factory` nicht torch/qdrant/pymupdf nachzieht.
  - **WICHTIG:** Der `Embedder` ist eine **einzige geteilte Instanz** für Chunker UND Retriever – Chunks und Fragen müssen im identischen Vektorraum liegen. Niemals zwei Embedder bauen.
- **`config.yaml`** – Schaltet Implementierungen um: `embedder` (`bge_m3`), `chunker` (`recursive` | `semantic`), `cad_adapter` (`synthetic_json` | `cad_processor_http`), `vector_store` (`qdrant`), `answer_generator` (`llama_ollama`). Neue Implementierung = neue Klasse + `if`-Zweig in der Factory + Eintrag in `config.example.yaml`.

Eine neue Komponente fügst du hinzu, indem du das passende Protocol implementierst und sie in `factory.py` registrierst – die Pipeline (`app/pipeline/indexer.py`) und die API (`app/api/main.py`) bleiben unverändert.

## Datenfluss & CAD-Bridge
- **CAD-JSON ist English-keyed und wird unverändert durchgereicht:** Der `CadProcessorClient` (`app/implementations/cad_processor_client.py`) gibt das GearParameters-JSON des `cad_processor` (Struktur in `cad_processor/src/output_schema.py`) **unverändert** zurück. Es gibt **kein** Mapping auf deutsche Keys mehr und **keine** `schemas/gears.yaml`. `cad_metadata` im `/ask`-Request nutzt durchgängig die englischen Keys (z.B. `gear_type`, `tooth_profile.module_mm`).
- **CAD-JSON fließt erst in der Antwortstufe ein**, nicht ins Retrieval: Es wird weder embedded noch als Filter genutzt. Der `HybridRetriever` sucht nur mit der Original-Frage; der `AnswerGenerator` bekommt dann Frage + Chunks + vollständiges CAD-JSON + Ausgabeformat.
- **`cad_adapter: synthetic_json`** liefert Testdaten aus `test_verzahnung/cad_testdaten/`; die Endpunkte `/cad/random` und `/cad/examples` nutzen **immer** diese synthetischen Daten (unabhängig vom konfigurierten Hauptadapter).
- **Env-Variablen überschreiben `config.yaml`** (siehe `docker-compose.yml`): `QDRANT_HOST`, `QDRANT_PORT`, `CAD_PROCESSOR_URL`, `OLLAMA_URL`. So wird die lokal eingebettete Config im Compose-Betrieb auf echte Services umgestellt.

## Coding-Richtlinien
- **Python-Umgebungen:** 
  - RAG-System: Strikt Python 3.11 verwenden (wegen `torch`-Wheels auf Intel-macOS).
  - CAD-Prozessor: Zwingend Miniconda/Conda nutzen (`environment.yml`), um die C++ Abhängigkeiten von PythonOCC aufzulösen.
- **Konfiguration:** Die `config.yaml` darf niemals in Git eingecheckt werden (nur `config.example.yaml` anpassen).
- **Abhängigkeiten:** Keine Cloud-LLM-APIs verwenden. Bei neuen Paketen immer die jeweilige `requirements.txt` oder `environment.yml` sowie die Dockerfiles aktualisieren.

## Wichtige Befehle (Entwicklung)
**Docker-Setup (Standard):**
- Starten: `docker compose up --build`
- Ollama lokal: `ollama pull llama3.2:3b`

**Lokale Entwicklung (ohne Docker):**
- CAD-Prozessor: `conda activate gear-copilot` -> `cd cad_processor` -> `uvicorn src.main:app --reload --port 8001`
- RAG-System: `source .venv/bin/activate` -> `uvicorn app.api.main:app --reload --port 8000` (Benötigt Embedded Qdrant via `path: "storage/qdrant"` in der config.yaml).

**Tests:**
- RAG-System (im `.venv`, vom Repo-Root): `pytest` (Suite unter `tests/`: `test_smoke.py`, `test_config.py`, `test_api_integration.py`).
- Einzelner Test: `pytest tests/test_smoke.py::test_answer_prompt_has_required_placeholders -q`.
- CAD-Prozessor (im Conda-Env `gear-copilot`, aus `cad_processor/`): `pytest tests/test_geometry.py`.
- CAD-Genauigkeits-Test gegen Soll-Werte (kein pytest): `cd cad_processor && python tests/accuracy_test.py` (Optionen: `--step-dir data/examples`, `--warn 2.0 --error 5.0`).
- Retrieval-Evaluation (MRR/Hit@k): Notebook `test_verzahnung/evaluation.ipynb`.

## Anweisungen für Claude Code
- Wenn du API-Routen im RAG-System bearbeitest, stelle sicher, dass die Response das geforderte `format` (kurz, standard, ausführlich, stichpunkte, tabellarisch) unterstützt.
- Referenziere Quellen im LLM-Prompt/Output immer strikt im Format `[Q1]`, `[Q2]`.
- Modifiziere niemals den `design-system-source/` Ordner, wenn Fehler im laufenden Frontend (unter `/frontend/design-system/`) behoben werden sollen.