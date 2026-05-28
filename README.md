# KI-Copilot für Verzahnungswissen (Modulares RAG)

Striktes RAG-System: Antworten **nur** aus hochgeladenen PDFs + (Stub-)Bauteildaten.

## Setup

### 1) Python installieren und Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Qdrant starten

```bash
docker compose up -d
```

Qdrant läuft dann auf `http://localhost:6333`.

### 3) Ollama starten (lokales LLM)

- Ollama installieren: siehe [Ollama](https://ollama.com/)
- Modell ziehen:

```bash
ollama pull llama3.2:3b
```

### 4) Konfiguration

`config.yaml` liegt im Repo-Root. Als Vorlage gibt es `config.example.yaml`.

### 5) API starten

```bash
uvicorn app.api.main:app --reload --port 8000
```

Dann im Browser öffnen: `http://localhost:8000/` (liefert `frontend/index.html`).

## API

- `POST /upload` (multipart `file`): PDF hochladen und indexieren
- `GET /documents`: indexierte Dokumente (Summary)
- `DELETE /documents/{doc_hash}`: Dokument löschen (alle Chunks via `doc_hash`)
- `GET /cad/random`: zufälliges Zahnrad (Stub)
- `POST /ask`: `{ questions: string[], cad_metadata: object, format?: "kurz" | ... }`

## Hinweise

- Es gibt **keinen Konversationskontext** zwischen Anfragen (Absicht).
- Quellen sind pro Antwort als `[Q1]..` referenziert und im Frontend als Chunk-Liste einsehbar.

