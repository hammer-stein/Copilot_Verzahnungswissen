# Spezifikationsprompt: Modulares RAG-System für technische Wissensdomänen

> Dieser Text ist der vollständige Prompt für das implementierende Modell. Er beschreibt Architektur, Komponentenschnittstellen, Konfiguration, Frontend und Antwortlogik so, dass ein lauffähiges System daraus entsteht.

---

## 1. Auftrag

Baue ein RAG-System (Retrieval-Augmented Generation), das fachspezifische Fragen zu einer beliebigen technischen Wissensdomäne beantwortet. Erste Anwendungsdomäne sind **Verzahnungen** (Zahnräder, Normen, Lehrbücher, Produktionsdaten), das System muss aber **vollständig domänen-agnostisch** sein – ein Wechsel auf z.B. Lager, Schweißverbindungen oder Hydraulik darf nur Konfigurationsdateien betreffen, keinen Code.

### Drei Eingangsströme

1. **Wissensbasis** – PDFs, einmalig oder dynamisch hochgeladen, langfristig persistiert.
2. **Bauteildaten** – pro Konversation: später CAD-Datei, aktuell Platzhalter (Random Generator).
3. **Frage(n)** – natürlichsprachlich, ggf. mehrere parallel.

### Zwei Wissensquellen werden verbunden

- Domänenwissen aus den Dokumenten
- Geometrische Metadaten des konkreten Bauteils

Das LLM **darf nur** das nutzen, was ihm explizit übergeben wird (striktes RAG, kein Eigenwissen).

---

## 2. Leitprinzipien (nicht verhandelbar)

### 2.1 Puzzle-Modularität
Jede Komponente ist ein austauschbares Puzzleteil mit klar definierter Schnittstelle (Python `Protocol` oder ABC). Ein Wechsel z.B. von `bge-m3` auf `e5-large` darf nur eine Zeile in der Config kosten – keine Code-Änderung in der Pipeline.

### 2.2 Konfiguration zentral
Alle Parameter, Pfade, Modellnamen, Schwellenwerte, Schemata stehen in einer zentralen `config.yaml`. **Keine** Hardcoded-Werte im Code. Jede Variable, die ein Engineer jemals ändern könnte, ist in der Config.

### 2.3 Domänen-Agnostik
Das Metadatenschema, der Antwort-Prompt und die CAD-Felder sind über separate YAML-Dateien definiert. Verzahnungen ist die Default-Domäne, aber das System startet auch mit einem leeren Schema und ist dann für jede beliebige Domäne nutzbar.

### 2.4 Vollständige Quellenrückführung
Jeder Chunk trägt von der Aufnahme bis zur Antwort einen Pfad mit (Dateiname + Seitenzahl + Position im Dokument). In der Antwort ist jeder Satz zur Quelle rückverfolgbar.

### 2.5 Transparenz vor Eleganz
Lieber ein expliziter, gut nachvollziehbarer Schritt mehr als ein cleverer Einzeiler. Logging an jeder Pipeline-Stufe.

---

## 3. Architekturdiagramm

```
              ┌─────────────────┐  ┌──────────────┐  ┌─────────────┐
              │  Wissensbasis   │  │  CAD-Datei   │  │   Frage(n)  │
              │  (PDF-Upload)   │  │ (Stub/später)│  │ (n parallel)│
              └────────┬────────┘  └──────┬───────┘  └──────┬──────┘
                       │                  │                 │
                       ▼                  ▼                 ▼
              ┌────────────────┐  ┌──────────────┐  ┌──────────────┐
              │ DocumentLoader │  │ CADAdapter   │  │   Embedder   │
              │   (PDF→Text)   │  │ (Stub→JSON)  │  │   (bge-m3)   │
              └────────┬───────┘  └──────┬───────┘  └──────┬───────┘
                       │                 │                 │
                       ▼                 │                 │
              ┌────────────────┐         │                 │
              │   Chunker      │         │                 │
              │  (semantisch)  │         │                 │
              └────────┬───────┘         │                 │
                       │                 │                 │
              ┌────────┴───────┐         │                 │
              ▼                ▼         │                 │
       ┌────────────┐  ┌──────────────┐  │                 │
       │  Embedder  │  │  Metadata    │  │                 │
       │  (bge-m3)  │  │  Extractor   │  │                 │
       │            │  │  (Llama 3.2) │  │                 │
       └─────┬──────┘  └──────┬───────┘  │                 │
             │                │          │                 │
             └────────┬───────┘          │                 │
                      ▼                  │                 │
              ┌──────────────┐           │                 │
              │ VectorStore  │           │                 │
              │  (Qdrant)    │           │                 │
              └──────┬───────┘           │                 │
                     │                   │                 │
                     │   ┌───────────────┘                 │
                     ▼   ▼                                 │
              ┌─────────────────────────┐                  │
              │  Stage 1: Metadata-     │                  │
              │  Filter (deterministisch)│                  │
              └────────────┬────────────┘                  │
                           ▼                               │
                  ┌─────────────────┐                      │
                  │ gefilterte      │                      │
                  │ Chunkmenge      │                      │
                  └────────┬────────┘                      │
                           │       ┌──────────────────────┘
                           ▼       ▼
                  ┌─────────────────────────┐
                  │  Stage 2: Embedding-    │
                  │  Vergleich (Top-k / τ)  │
                  └────────────┬────────────┘
                               ▼
                       ┌───────────────┐
                       │ Top-k Chunks  │
                       └───────┬───────┘
                               ▼
                  ┌─────────────────────────┐
                  │ AnswerGenerator (LLM)   │
                  │ + festgelegter Prompt   │
                  └────────────┬────────────┘
                               ▼
                       ┌───────────────┐
                       │   Antwort     │
                       │ + Quellen     │
                       └───────────────┘
```

Jeder Kasten in diesem Diagramm = eine austauschbare Komponente mit eigener Schnittstelle (siehe §5).

---

## 4. Tech-Stack (Default-Wahl, jederzeit austauschbar)

| Layer | Default | Begründung |
|---|---|---|
| Sprache | Python 3.11+ | Ökosystem für ML/RAG |
| Backend | FastAPI | Async, OpenAPI-Dokumentation gratis |
| Frontend | HTML + Vanilla JS + Pico.css | Keine Build-Chain, schlicht, solide |
| Embedding | `BAAI/bge-m3` via `FlagEmbedding` oder `sentence-transformers` | Mehrsprachig, dense+sparse, 8k Kontext |
| LLM | `meta-llama/Llama-3.2-3B-Instruct` via Ollama | Lokal, schnell, gut genug |
| Vector-DB | Qdrant (Docker oder embedded) | Native Metadaten-Filter, schnell |
| PDF-Parsing | PyMuPDF (`fitz`) | Stabil, behält Seitenzahlen |
| Konfiguration | YAML + Pydantic | Validierung beim Start |

---

## 5. Komponenten-Schnittstellen

> Jede Komponente ist ein austauschbares Puzzleteil. Implementiere sie als Python `Protocol` oder abstrakte Basisklasse, mit mindestens einer Default-Implementierung. Alle werden über eine Factory aus der Config instanziiert.

### 5.1 DocumentLoader

```python
class DocumentLoader(Protocol):
    def load(self, file_path: Path) -> RawDocument: ...
    # RawDocument enthält: text pro Seite, Quelldatei, doc_hash
```

**Default:** `PDFLoader` (PyMuPDF). Erweiterbar um DOCX, Markdown, HTML.

### 5.2 Chunker

```python
class Chunker(Protocol):
    def chunk(self, document: RawDocument) -> list[Chunk]: ...
    # Chunk enthält: text, source_path, page_number, position, doc_hash
```

**Default:** `SemanticChunker` (nutzt den Embedder, erkennt Themengrenzen über Kosinusabstand benachbarter Sätze). Konfigurierbar:
- `threshold` (Default 0.75)
- `min_chunk_size` (Default 100 Tokens)
- `max_chunk_size` (Default 512 Tokens)
- `overlap_sentences` (Default 1)

**Alternative Implementierung:** `RecursiveTextChunker` (regelbasiert, schneller).

### 5.3 Embedder

```python
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> EmbeddingResult: ...
    # EmbeddingResult enthält: dense_vectors, sparse_vectors (optional)
```

**Default:** `BGEM3Embedder`. Wird an drei Stellen genutzt – Chunking, Wissensbasis-Indizierung, Frage zur Laufzeit. **Es ist zwingend dasselbe Modell überall** (Vektorraum-Konsistenz).

Hybrid-Modus: dense + sparse parallel speichern, in Stufe 2 gewichtet kombinieren (Default-Gewicht 0.7 dense / 0.3 sparse).

### 5.4 MetadataExtractor

```python
class MetadataExtractor(Protocol):
    def extract(self, chunk: Chunk, schema: MetadataSchema) -> dict: ...
```

**Default:** `LlamaMetadataExtractor` (Llama 3.2 lokal via Ollama). Bekommt Chunk-Text + Schema-Beschreibung, gibt JSON zurück. JSON wird gegen das Pydantic-Schema validiert; ungültige Antworten werden bis zu 3× retried, bei Misserfolg leeres dict.

**Wichtig:** Das Schema kommt aus einer separaten YAML-Datei (`schemas/<domain>.yaml`). Schema-Beispiel siehe §7.

### 5.5 CADAdapter

```python
class CADAdapter(Protocol):
    def extract(self, file_path: Path | None) -> dict: ...
```

**Default (Stub):** `RandomGearGenerator` – generiert zufällige, in sich konsistente Verzahnungs-Metadaten (siehe §8).

**Anschlusspunkt für Zukunft:** `PythonOCCAdapter` (regelbasierte Geometrieanalyse aus STEP-Dateien). Schnittstelle ist identisch, einfacher Tausch in der Config.

### 5.6 VectorStore

```python
class VectorStore(Protocol):
    def upsert(self, chunks: list[EmbeddedChunk]) -> None: ...
    def search(self, query_vector, filter: dict, top_k: int, threshold: float) -> list[SearchResult]: ...
    def delete_by_doc_hash(self, doc_hash: str) -> None: ...
    def list_documents(self) -> list[DocumentInfo]: ...
```

**Default:** `QdrantStore`. Speichert Dense+Sparse-Vektor + alle Metadaten + Quellpfad + doc_hash. Löschung eines Dokuments entfernt zuverlässig alle zugehörigen Chunks.

### 5.7 Retriever (zwei Stufen)

```python
class Retriever(Protocol):
    def retrieve(self, question: str, cad_metadata: dict) -> list[RetrievedChunk]: ...
```

**Default:** `TwoStageRetriever`:
- Stufe 1: deterministischer Filter über CAD-Metadaten (siehe §6)
- Stufe 2: bge-m3-Vektorsuche, top-k oder threshold

Konfigurierbar:
- `stage1_strict` (true/false)
- `stage1_relax_on_empty` (Default true – wenn 0 Chunks, Filter lockern)
- `stage2_top_k` (Default 5)
- `stage2_min_similarity` (Default 0.65)
- `stage2_use_hybrid` (Default true)

**Optional zuschaltbar:** `Reranker` (bge-reranker-v2-m3) als dritte Stufe für höhere Präzision.

### 5.8 AnswerGenerator

```python
class AnswerGenerator(Protocol):
    def generate(self,
                 question: str,
                 chunks: list[RetrievedChunk],
                 cad_metadata: dict,
                 output_format: OutputFormat) -> Answer: ...
```

**Default:** `LlamaAnswerGenerator`. Verwendet einen **fest definierten System-Prompt** (siehe §9). Das LLM bekommt nur:
- Frage
- CAD-Metadaten
- Top-k Chunks mit Quelle
- Format-Anweisung

Kein anderer Input. Antwort enthält pro Aussage einen Quellenverweis.

---

## 6. Stage-1-Filter: Deterministische Logik

```python
def stage1_filter(cad_metadata: dict, chunk_metadata: dict, schema: MetadataSchema) -> bool:
    for field in schema.filter_fields:
        if field.type == "exact":
            if cad_metadata.get(field.name) != chunk_metadata.get(field.name):
                return False
        elif field.type == "range":
            cad_value = cad_metadata.get(field.name)
            chunk_min = chunk_metadata.get(f"{field.name}_min")
            chunk_max = chunk_metadata.get(f"{field.name}_max")
            if cad_value is None or chunk_min is None or chunk_max is None:
                continue  # Feld fehlt → Chunk passieren lassen (großzügig)
            if not (chunk_min <= cad_value <= chunk_max):
                return False
        elif field.type == "set":
            if cad_metadata.get(field.name) not in chunk_metadata.get(field.name, []):
                return False
    return True
```

**Großzügigkeit-Prinzip:** Wenn ein Chunk ein Metadatenfeld nicht hat (z.B. ein allgemeiner Lehrbuch-Chunk ohne Modul-Angabe), wird er **nicht** ausgeschlossen. Filter sind hart nur bei explizit unverträglichen Werten.

**Relax-on-Empty:** Wenn nach Stage 1 weniger als `min_candidates` (Default 5) Chunks übrig sind, werden Range-Filter um einen Faktor (Default 1.5) erweitert und Stage 1 erneut ausgeführt. Maximal 2 Relax-Stufen.

---

## 7. Metadaten-Schema (extern, YAML)

Eine separate Datei `schemas/gears.yaml`:

```yaml
domain: "Verzahnungen"
description: "Metadatenschema für Verzahnungs-Wissensbasis"

fields:
  - name: verzahnungstyp
    type: string
    enum: ["Stirnrad", "Schrägverzahnung", "Kegelrad", "Schneckenrad", "Innenverzahnung", "unspecified"]
    filter_type: exact
    description: "Art der Verzahnung. 'unspecified' für allgemeine Inhalte."

  - name: modul
    type: number
    filter_type: range
    range_fields: [modul_min, modul_max]
    description: "Modul der Verzahnung in mm. Bei Bereichsangaben min und max füllen."

  - name: norm
    type: string
    filter_type: exact
    nullable: true
    description: "Referenzierte Norm (z.B. DIN 3960, ISO 1328). null wenn keine."

  - name: themenkategorie
    type: string
    enum: ["Geometrie", "Festigkeit", "Fertigung", "Werkstoff", "Prüfung", "Wirtschaftlichkeit", "allgemein"]
    filter_type: set
    description: "Inhaltliche Hauptkategorie des Chunks."

  - name: anwendungsbereich
    type: string
    nullable: true
    description: "Spezielle Anwendung wenn relevant (z.B. 'Getriebe', 'Antrieb', 'Lenkung')."

extraction_prompt_hint: |
  Du analysierst einen Textabschnitt aus einem Dokument zu Verzahnungen.
  Extrahiere die Metadaten möglichst konservativ - lieber null/unspecified
  angeben als raten. Modul-Bereiche nur wenn der Text sie explizit nennt.
```

**Wechsel der Domäne** = neue YAML-Datei + Pfadangabe in `config.yaml`. Kein Code-Eingriff.

---

## 8. CAD-Metadaten (Stub und reale Felder)

### Sinnvolle Verzahnungs-Metadaten (von späterem CAD-Modell auszulesen):

```python
@dataclass
class GearMetadata:
    verzahnungstyp: str          # Stirnrad / Schrägverzahnung / Kegelrad / Schneckenrad
    modul: float                 # mm
    zaehnezahl: int
    eingriffswinkel: float       # Grad, typ. 20°
    schraegungswinkel: float     # Grad, 0 bei Geradverzahnung
    profilverschiebung: float    # x-Faktor, dimensionslos
    kopfkreisdurchmesser: float  # mm
    fusskreisdurchmesser: float  # mm
    teilkreisdurchmesser: float  # mm
    zahnbreite: float            # mm
    werkstoff: str | None        # falls aus CAD-Attributen ableitbar
    haerte: str | None           # z.B. "vergütet", "einsatzgehärtet"
    verzahnungsqualitaet: int | None  # DIN-Qualitätsklasse 1-12
    drehrichtung: str | None     # "rechts" / "links" bei Schrägverzahnung
```

### Stub-Implementierung (Random Gear Generator)

Generiert plausible, in sich konsistente Werte:

```python
def generate_random_gear() -> dict:
    typ = random.choice(["Stirnrad", "Schrägverzahnung"])
    modul = random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0])
    z = random.randint(15, 60)
    alpha = 20.0
    beta = 0.0 if typ == "Stirnrad" else random.choice([8, 10, 12, 15, 20])
    x = round(random.uniform(-0.3, 0.5), 2)
    d = modul * z                         # Teilkreis
    da = d + 2 * modul * (1 + x)           # Kopfkreis
    df = d - 2 * modul * (1.25 - x)        # Fußkreis
    return {
        "verzahnungstyp": typ,
        "modul": modul,
        "zaehnezahl": z,
        "eingriffswinkel": alpha,
        "schraegungswinkel": beta,
        "profilverschiebung": x,
        "teilkreisdurchmesser": round(d, 2),
        "kopfkreisdurchmesser": round(da, 2),
        "fusskreisdurchmesser": round(df, 2),
        "zahnbreite": round(modul * random.uniform(8, 14), 1),
        "werkstoff": random.choice(["16MnCr5", "20MnCr5", "42CrMo4", "C45"]),
        "haerte": random.choice(["vergütet", "einsatzgehärtet", "nitriert"]),
        "verzahnungsqualitaet": random.choice([6, 7, 8]),
        "drehrichtung": "rechts" if beta > 0 else None,
    }
```

Dieser Stub muss **dieselbe Schnittstelle** liefern wie der spätere echte CAD-Adapter.

---

## 9. System-Prompt für die Antwortgenerierung (fest)

Dieser Prompt liegt als Datei `prompts/answer_system_prompt.txt` und wird zur Laufzeit nur mit Variablen befüllt:

```
Du bist ein technischer Assistent für die Domäne {DOMAIN}.

REGELN (zwingend):
1. Antworte AUSSCHLIESSLICH auf Basis der unten gelieferten Wissensauszüge ("Chunks") und Bauteildaten.
2. Verwende KEIN externes oder internes Vorwissen, das nicht in den Chunks steht.
3. Wenn die Information für eine Aussage nicht in den Chunks vorhanden ist, sage das explizit ("Aus den verfügbaren Quellen lässt sich dazu keine Aussage treffen.").
4. Hänge an JEDE inhaltliche Aussage eine Quellenmarkierung im Format [Q1], [Q2]... an. Die Nummer entspricht der Reihenfolge der Chunks unten.
5. Beziehe dich auf die Bauteildaten dort, wo sie für die Frage relevant sind.
6. Halte das Format ein, das unter "AUSGABEFORMAT" angegeben ist.

BAUTEILDATEN (aus CAD):
{CAD_METADATA_JSON}

WISSENSAUSZÜGE:
{CHUNKS_BLOCK}
# Format pro Chunk:
# [Q1] Quelle: {dateiname}, Seite {n}
# {chunk_text}
# ---

FRAGE:
{QUESTION}

AUSGABEFORMAT:
{FORMAT_INSTRUCTION}
# z.B. "Strukturiert mit Zwischenüberschriften, ca. 200 Wörter"
# oder "Stichpunktliste, max. 5 Punkte"
# oder "Fließtext, prägnant, max. 100 Wörter"

ANTWORT:
```

**Format-Optionen** (in Config definiert, im Frontend wählbar):
- `kurz` – Fließtext, max. 100 Wörter
- `standard` – strukturiert, ca. 200 Wörter
- `ausführlich` – mit Zwischenüberschriften, ca. 400 Wörter
- `stichpunkte` – Liste, max. 7 Punkte
- `tabellarisch` – wenn Vergleichsdaten gefragt sind

`max_tokens` ist eigenständig konfigurierbar und überschreibt das Format-Limit.

---

## 10. Konfigurationsdatei (zentral)

`config.yaml`:

```yaml
domain:
  name: "Verzahnungen"
  schema_path: "schemas/gears.yaml"
  prompt_path: "prompts/answer_system_prompt.txt"

embedder:
  implementation: "bge_m3"
  model_name: "BAAI/bge-m3"
  device: "cuda"   # oder "cpu" / "mps"
  use_sparse: true
  max_length: 8192

chunker:
  implementation: "semantic"
  threshold: 0.75
  min_chunk_size: 100
  max_chunk_size: 512
  overlap_sentences: 1

metadata_extractor:
  implementation: "llama_ollama"
  model_name: "llama3.2:3b"
  ollama_url: "http://localhost:11434"
  max_retries: 3
  timeout_s: 30

cad_adapter:
  implementation: "random_gear_stub"   # später: "pythonocc"

vector_store:
  implementation: "qdrant"
  host: "localhost"
  port: 6333
  collection_name: "knowledge_base"

retriever:
  stage1_strict: true
  stage1_relax_on_empty: true
  stage1_min_candidates: 5
  stage2_top_k: 5
  stage2_min_similarity: 0.65
  stage2_use_hybrid: true
  hybrid_dense_weight: 0.7
  hybrid_sparse_weight: 0.3
  reranker_enabled: false
  reranker_model: "BAAI/bge-reranker-v2-m3"

answer_generator:
  implementation: "llama_ollama"
  model_name: "llama3.2:3b"
  default_format: "standard"
  max_tokens: 800
  temperature: 0.2

frontend:
  default_question_fields: 3
  max_question_fields: 6
  show_metadata_panel: true
```

---

## 11. Frontend-Spezifikation

### 11.1 Look & Feel
- Schlicht, technisch, hohe Lesbarkeit
- Pico.css als Basis (klassenfrei, kein Build), eigene Akzentfarbe
- Monospace für Metadaten-Ausgabe
- Keine Animationen außer dezente Loading-Indikatoren

### 11.2 Hauptansicht (Single Page)

**Bereich A: Wissensbasis-Verwaltung (oben, ausklappbar)**
- Drag-and-Drop oder Button-Upload für PDFs
- Liste aller indexierten Dokumente mit Status:
  - `📄 Dateiname.pdf — n Chunks indexiert — [Entfernen]`
  - Status-Badge: `indexing` (Spinner) / `ready` (grün) / `error` (rot mit Tooltip)
- Beim Entfernen: Bestätigungsdialog, anschließend echte Löschung aller Chunks aus VectorStore

**Bereich B: Bauteildaten (Mitte)**
- Upload-Feld für CAD-Datei (visuell vorhanden, **deaktiviert** mit Hinweis "wird in zukünftiger Version aktiv")
- Daneben prominenter Button: **"Zufälliges Zahnrad generieren"**
- Nach Klick: alle CAD-Metadaten als hübsches Key-Value-Panel anzeigen (bearbeitbar – der Nutzer kann einzelne Werte überschreiben, falls er etwas Spezifisches testen will)
- Knopf "Andere Werte würfeln"

**Bereich C: Fragen-Eingabe (Mitte)**
- Standardmäßig **3 Eingabefelder** sichtbar
- Über jedem Feld der Hinweis: *"Bitte pro Feld nur eine Frage. Verschiedene Themen in verschiedene Felder."*
- Button "Weiteres Feld hinzufügen" (bis zum Maximum aus Config)
- Button "Feld entfernen" pro Feld (außer dem ersten)
- Format-Selector (Dropdown mit den Optionen aus §9)
- "Fragen stellen"-Button

**Bereich D: Ausgabe (unten, erscheint nach Anfrage)**

Aufbau **fest in dieser Reihenfolge**:

1. **Allgemeine Bauteildaten** (Akkordeon, standardmäßig offen)
   - Schöne Auflistung aller CAD-Metadaten als Tabelle
   - Kurzer Klartext-Header: "Untersuchtes Bauteil: {verzahnungstyp} mit Modul {modul} und {zaehnezahl} Zähnen"

2. **Antworten** (eine Karte pro Frage)
   - Karten-Header: die Originalfrage
   - Antworttext mit Inline-Quellenmarkierungen `[Q1]`, `[Q2]`...
   - Akkordeon "Quellen anzeigen" → Liste der verwendeten Chunks mit:
     - Dateiname, Seitenzahl
     - Ähnlichkeitsscore
     - Original-Chunktext (Vorschau, ausklappbar voll)

3. **Neuer-Anlauf-Button**: "Weitere Fragen stellen"
   - Setzt Frage-Felder zurück, behält Wissensbasis und CAD-Daten
   - **Wichtig:** Es gibt **keinen Konversationskontext zwischen Anfragen**. Folgefragen, die sich auf vorige Antworten beziehen, sind explizit nicht unterstützt (vermeidet Mehrdeutigkeit, wie der Auftraggeber richtig anmerkt).

### 11.3 Mehrere Fragen parallel

Backend nimmt eine Liste von Fragen entgegen und verarbeitet sie **asynchron parallel** (asyncio.gather). Jede Frage durchläuft die volle Pipeline isoliert:
- eigene Stage-1-Filterung
- eigene Stage-2-Suche
- eigene LLM-Antwort

Erst wenn **alle** Antworten fertig sind, wird die Gesamtausgabe gerendert (Loading-State zeigt pro Frage einen eigenen Fortschritt).

---

## 12. Datenfluss-Beispiel (eine vollständige Anfrage)

```
1. User generiert Zufallszahnrad → CAD-JSON im State
2. User stellt 3 Fragen, Format "standard"
3. Frontend POST /ask {questions: [...], cad_metadata: {...}, format: "standard"}
4. Backend für jede Frage parallel:
   a. Embedder.embed(frage)
   b. Retriever.retrieve(frage_vec, cad_metadata)
      - Stage 1: Qdrant-Filter mit cad_metadata
      - Stage 2: Vector-Search top-k mit threshold
      - (optional) Reranker
   c. AnswerGenerator.generate(frage, chunks, cad_metadata, format)
      - System-Prompt aus Datei + Variablen
      - Llama 3.2 via Ollama
   d. Quellenmarkierungen zu echten Pfaden auflösen
5. Backend Response: {
     cad_metadata: {...},
     answers: [
       {question, answer_text, sources: [{path, page, similarity, text}]},
       ...
     ]
   }
6. Frontend rendert in fester Reihenfolge (CAD-Panel → Antwort-Karten)
```

---

## 13. Logging & Observability

Pro Anfrage in `logs/queries/{timestamp}_{uuid}.json` speichern:
- Originalfragen
- CAD-Metadaten
- Pro Frage: Stage-1-Filter, Anzahl Kandidaten, Top-k Chunk-IDs mit Score, finale LLM-Antwort
- Modellversionen aller beteiligten Komponenten

Das ist später Gold wert für Debugging und Qualitätsverbesserung.

---

## 14. Implementierungs-Reihenfolge

Bauen in dieser Reihenfolge, jede Stufe lauffähig testbar:

1. **Skelett** – Config-Loader, Pydantic-Schemas, Komponenten-Factory
2. **Wissensbasis-Pipeline** – PDF-Upload → Chunking → Embedding → Metadata-Extraktion → Qdrant
3. **CAD-Stub** – Random Gear Generator
4. **Retriever** – beide Stufen, ohne LLM
5. **AnswerGenerator** – Llama via Ollama, mit fixiertem Prompt
6. **API** – FastAPI-Endpunkte (`/upload`, `/documents`, `/cad/random`, `/ask`)
7. **Frontend** – schlichtes HTML/JS, gegen die API
8. **Logging & Tests** – End-to-End-Test mit Beispiel-PDF
9. **Optionales** – Reranker, Hybrid-Search-Tuning

---

## 15. Anti-Patterns (bitte vermeiden)

- ❌ Hardcoded Modellnamen oder Pfade im Code
- ❌ Eine zentrale "main.py" mit 800 Zeilen Logik
- ❌ Frontend-Frameworks mit Build-Chain (React/Vue) für so ein schlichtes UI
- ❌ Speicherung von Chunks ohne `doc_hash` und Quellpfad – sonst ist sauberes Löschen unmöglich
- ❌ LLM-Antworten ohne Quellenmarkierung
- ❌ Konversationskontext zwischen Anfragen (führt zu Mehrdeutigkeit, explizit nicht gewünscht)
- ❌ Verschiedene Embedding-Modelle für Wissensbasis und Frage (Vektorraum-Bruch)

---

## 16. Erweiterungspunkte (für später)

Diese sind in der Architektur bereits "verkabelt", aber bewusst nicht ausimplementiert:

- **Echter CAD-Adapter** (pythonOCC) – Schnittstelle steht
- **Reranker** – per Config zuschaltbar
- **Hybrid-Suche-Tuning** – Gewichte sind Config-Werte
- **Weitere Domänen** – neues Schema-YAML reicht
- **Multi-User & Auth** – aktuell Single-User, FastAPI lässt sich aber sauber erweitern

---

## 17. Lieferumfang

1. Vollständiges, lauffähiges Python-Repository
2. `README.md` mit Setup-Anleitung (Ollama + Qdrant + Python-Deps)
3. `docker-compose.yml` für Qdrant
4. Beispiel-Konfiguration `config.example.yaml`
5. Beispiel-Schema `schemas/gears.yaml`
6. Beispiel-Prompt `prompts/answer_system_prompt.txt`
7. Mindestens ein End-to-End-Test mit Beispiel-PDF
8. Frontend als statische Dateien unter `frontend/`

---

## 18. Erfolgskriterien

Das System gilt als fertig, wenn:

- [ ] Ein PDF kann hochgeladen, indexiert, wieder entfernt werden – ohne Reststände in Qdrant
- [ ] Drei verschiedene Fragen parallel gestellt werden, drei separate Antworten zurückkommen
- [ ] Jede Aussage in einer Antwort eine nachvollziehbare Quelle (Datei + Seite) hat
- [ ] Ein Wechsel des Embedding-Modells in der Config funktioniert ohne Code-Änderung
- [ ] Ein Wechsel der Domäne (z.B. neues Schema "Lager") funktioniert nur durch neue YAML
- [ ] Die Antwort enthält **nichts**, was nicht in den gelieferten Chunks oder CAD-Daten steht
- [ ] Stage-1-Filter ist deterministisch und nachvollziehbar in den Logs
- [ ] Frontend zeigt Status jedes Dokuments (indexing/ready/error)
- [ ] Bei leerer Stage-1-Menge greift Relax-Logik

---

## 19. Frage an den Implementierer

Bitte vor Implementierungsbeginn klären:

1. Soll Qdrant als Docker-Container laufen oder embedded (`qdrant-client` mit `:memory:`)? Empfehlung: Docker für Persistenz.
2. Llama 3.2 in welcher Größe? Default 3B reicht für Metadaten-Extraktion und kurze Antworten; 8B für höhere Qualität.
3. GPU verfügbar? Falls nein, kleinere Embedding-Modelle als Fallback (`bge-m3` läuft auf CPU, aber langsam).

Falls einer dieser Punkte unklar ist, **Default-Werte aus Config nutzen und in der README dokumentieren**.

---

*Ende des Spezifikationsprompts.*
