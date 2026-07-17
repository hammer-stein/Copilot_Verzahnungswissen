# Abgabe / Inbetriebnahme — KI-Copilot für Verzahnungswissen

Lokales RAG-System zur Beantwortung von Ingenieursfragen rund um Zahnradgeometrie
und Fertigung (FastAPI + Qdrant + lokales LLM via Ollama, alles per Docker Compose).

## ✅ Die Wissensbasis ist bereits vorbefüllt — KEIN Neu-Indexieren nötig

**181 Dokumente** (Normen + Fachliteratur) sind fertig indexiert und liegen als
Vektor-Index im Projektordner unter **`qdrant_storage/`**. Nach dem Start ist die
Wissensbasis sofort nutzbar — der Prüfer muss **nichts** hochladen oder indexieren.

> ⚠️ **Wichtig: Das Projekt als ORDNER- oder ZIP-KOPIE weitergeben, nicht (nur) über Git.**
> Der Index (`qdrant_storage/`, ~0,5 GB), die Roh-PDFs (`storage/`) und `config.yaml`
> sind bewusst **nicht** in Git (zu groß bzw. lokal). Bei einer kompletten Ordner-/ZIP-Kopie
> sind sie alle dabei. Bei reiner Git-Abgabe fehlt die vorbefüllte Wissensbasis.

---

## Voraussetzungen

1. **Docker Desktop** (laufend). Empfehlung: unter *Settings → Resources → Memory*
   mind. **8 GB** (mehr ist besser für große Dokumente).
2. **Ollama** auf dem Host — läuft **außerhalb** von Docker: https://ollama.com

## Start in 4 Schritten

```bash
# 1) Antwort-LLM laden (läuft auf dem Host, nicht in Docker)
ollama pull qwen3:8b

# 2) config.yaml sicherstellen (liegt bei der Ordner-/ZIP-Kopie schon vor)
#    Falls sie fehlt:
cp config.example.yaml config.yaml

# 3) Starten (erster Build dauert einige Minuten)
docker compose up --build

# 4) Browser öffnen:
#    http://localhost:8000   → 181 Dokumente sind bereits in der Wissensbasis
```

**Beim allerersten Start** wird zusätzlich das Embedding-Modell `BAAI/bge-m3`
(~2 GB) automatisch von Hugging Face geladen — dafür ist **einmalig Internet** nötig
(danach im Cache). Das Modell wird sowohl für die Suche als auch beim Indexieren gebraucht.

---

## Was im Handoff enthalten sein muss (bei Ordner-/ZIP-Kopie automatisch dabei)

| Ordner/Datei | Inhalt | Pflicht |
|---|---|---|
| `qdrant_storage/` | **Vorbefüllter Vektor-Index** (181 Dok.) | **ja** — sonst leere Wissensbasis |
| `storage/` | Die 258 Roh-Dokumente (PDFs) + Ordnerstruktur + Upload-Historie | ja |
| `config.yaml` | Konfiguration (Modelle, Ports, Retrieval-Parameter) | ja |
| `app/`, `cad_processor/`, `frontend/`, `prompts/`, `docker-compose.yml`, … | Quellcode & Setup | ja |

## Gut zu wissen

- **181 von 258 Dokumenten sind indexiert.** Die restlichen ~77 sind die *größten*
  Dateien (umfangreiche Standards + Lehrbücher, z. B. „Roloff & Matek" mit 280 MB) —
  sie wurden auf dem CPU-Rechner aus Zeit-/Speichergründen (Out-of-Memory) nicht
  mit-indexiert. **Alle 258 Roh-PDFs liegen vollständig in `storage/uploads/`**
  (Ordner `Normen/` und `Literaturen & Normen/`) und können jederzeit über die
  GUI („Wissensbasis" → Hochladen) oder das Skript `python -m app.ingest` nachgeladen
  werden, wenn genug Docker-Speicher (≥ 14–16 GB) zur Verfügung steht.
- **Ollama muss laufen**, sonst schlägt nur die *Antwortgenerierung* fehl; die
  Dokumentenanzeige und die Vektor-Suche funktionieren auch ohne.
- **Neuer, leerer Start:** Wer ganz frisch (ohne `qdrant_storage/`) startet, bekommt
  wie vorgesehen eine leere Wissensbasis.

## Kurzer Funktionstest

Auf der Startseite eine Frage stellen, z. B.:
> „Welche Norm behandelt Toleranzen und Abweichungen an Stirnrädern?"

Die Antwort sollte konkrete Normen mit Quellenangaben (`[Q1]`, `[Q2]` …) nennen —
dann läuft die komplette Kette (Suche → LLM-Antwort → Quellen) korrekt.
