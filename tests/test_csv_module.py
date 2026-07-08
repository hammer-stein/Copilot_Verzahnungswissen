"""
test_csv_module.py – Tests für das CSV-Modul (beide Kanäle).

Kanal A (Wissen):  TabularLoader (Zeile→Satz), Tabellen-Chunking (1 Zeile = 1 Chunk),
                   Text-Chunking-Regression (PDF), Aggregat-Routing im HybridRetriever.
Kanal B (Bauteil): csv_gear_mapper (CSV → GearParameters-Struktur).

Alle Tests laufen ohne schwere Abhängigkeiten (kein torch/Qdrant/Ollama).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.types import Chunk, RawDocument, RawDocumentPage, SearchResult
from app.implementations.chunker_recursive import RecursiveTextChunker
from app.implementations.chunker_semantic import SemanticChunker
from app.implementations.csv_gear_mapper import map_tabular_to_gear_parameters
from app.implementations.retriever_hybrid import HybridRetriever, is_aggregate_query
from app.implementations.tabular_loader_pandas import TabularLoader

# ---------------------------------------------------------------------------
# Hilfsdaten
# ---------------------------------------------------------------------------

STUECKLISTE_CSV = (
    "Bauteil_ID,Bezeichnung,Menge,Werkstoff,Modul_mm,Zaehnezahl\n"
    "G-001,Stirnrad Antriebswelle,1,16MnCr5,3.0,24\n"
    "W-103,Ausgangswelle,1,42CrMo4,-,-\n"
)


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _table_doc(rows: int) -> RawDocument:
    text = "\n".join(f"Bauteil X-{i} (Bauteil_ID: X-{i}): Menge = {i}." for i in range(rows))
    return RawDocument(source_path="t.csv", doc_hash="h" * 8, pages=[RawDocumentPage(1, text)], doc_kind="table")


# ---------------------------------------------------------------------------
# Kanal A: TabularLoader (Zeile→Satz)
# ---------------------------------------------------------------------------

def test_tabular_loader_builds_sentences_and_marks_table(tmp_path):
    doc = TabularLoader().load(_write(tmp_path, "s.csv", STUECKLISTE_CSV))

    assert doc.doc_kind == "table"
    lines = doc.pages[0].text.splitlines()
    assert len(lines) == 2  # Header wird nicht als Datenzeile ausgegeben

    # Subjekt aus erster Spalte + Header-Bezug, "Spalte = Wert"-Paare
    assert lines[0].startswith("Bauteil G-001 (Bauteil_ID: G-001):")
    assert "Werkstoff = 16MnCr5" in lines[0]
    assert "Modul_mm = 3.0" in lines[0]

    # '-'-Platzhalter werden übersprungen, Werte nicht verallgemeinert
    assert "Modul_mm" not in lines[1]
    assert "Bezeichnung = Ausgangswelle" in lines[1]


# ---------------------------------------------------------------------------
# Kanal A: Chunker (Tabellen-Modus + Text-Regression)
# ---------------------------------------------------------------------------

def _recursive_chunker() -> RecursiveTextChunker:
    return RecursiveTextChunker(min_chunk_tokens=1, max_chunk_tokens=100, overlap_sentences=1)


def test_recursive_chunker_table_mode_one_chunk_per_row():
    chunks = _recursive_chunker().chunk(_table_doc(rows=12))
    assert len(chunks) == 12
    assert all(c.text.startswith("Bauteil X-") for c in chunks)
    # Zeilenreihenfolge bleibt erhalten (positions monoton)
    assert [c.position for c in chunks] == list(range(1, 13))


def test_recursive_chunker_text_mode_merges_sentences_across_lines():
    """Regression: PDF-Text darf NICHT zeilenweise zerhackt werden (Zeilen-Splitter-Bug)."""
    text = "Das Modul beträgt\ndrei Millimeter."  # eine Aussage über zwei Zeilen (PDF-Umbruch)
    doc = RawDocument(source_path="a.pdf", doc_hash="h" * 8, pages=[RawDocumentPage(1, text)])

    chunks = _recursive_chunker().chunk(doc)
    assert len(chunks) == 1  # der Zeilen-Splitter hätte 2 Chunks erzeugt
    assert "Modul" in chunks[0].text and "Millimeter" in chunks[0].text


def test_semantic_chunker_table_mode_bypasses_embedder():
    class _ExplodingEmbedder:
        def embed(self, texts):
            raise AssertionError("Tabellen-Chunking darf den Embedder nicht aufrufen")

    chunker = SemanticChunker(
        embedder=_ExplodingEmbedder(), threshold=0.5,
        min_chunk_tokens=100, max_chunk_tokens=512, overlap_sentences=1,
    )
    chunks = chunker.chunk(_table_doc(rows=5))
    assert len(chunks) == 5  # min_chunk_tokens gilt für Tabellenzeilen nicht


# ---------------------------------------------------------------------------
# Kanal A: Aggregat-Routing im HybridRetriever
# ---------------------------------------------------------------------------

def test_aggregate_query_detection():
    assert is_aggregate_query("Zeige mir alle Wellen.")
    assert is_aggregate_query("Wie viele Lager sind verbaut?")
    assert is_aggregate_query("Liste sämtliche Bauteile auf")
    assert not is_aggregate_query("Welchen Werkstoff hat W-103?")
    assert not is_aggregate_query("Wofür nutzt man Metalle im Getriebebau?")  # 'alle' nur als Teilwort


class _FakeEmbedder:
    def embed(self, texts):
        from app.core.types import EmbeddingResult
        return EmbeddingResult(dense_vectors=[[1.0, 0.0]], sparse_vectors=None)


class _FakeStore:
    """Konfigurierbarer Store: feste Trefferliste + synthetische Tabellenzeilen beim Scroll."""

    DEFAULT_HITS = None  # wird unten gesetzt (bester Treffer PDF, zweiter Tabelle)

    def __init__(self, hits=None, table_rows: int = 10):
        self.hits = list(self.DEFAULT_HITS) if hits is None else hits
        self.table_rows = table_rows
        self.scroll_calls: list[str] = []
        self.last_threshold: float | None = None

    @staticmethod
    def _hit(doc_hash: str, kind: str, score: float, position: int = 1) -> SearchResult:
        chunk = Chunk(text=f"chunk {doc_hash} {position}", source_path="x", page_number=1, position=position, doc_hash=doc_hash)
        meta = {"doc_kind": kind, "file_name": f"{doc_hash}.{'csv' if kind == 'table' else 'pdf'}"}
        return SearchResult(chunk=chunk, metadata=meta, dense_score=score, sparse_score=None, score=score)

    def search(self, qvec, *, top_k, threshold, **kwargs):
        self.last_threshold = threshold
        return list(self.hits)

    def scroll_by_doc_hash(self, doc_hash, *, limit):
        self.scroll_calls.append(doc_hash)
        return [self._hit(doc_hash, "table", 0.0, position=i + 1) for i in range(min(self.table_rows, limit))]


_FakeStore.DEFAULT_HITS = [
    _FakeStore._hit("pdfdoc", "text", 0.82),
    _FakeStore._hit("tabledoc", "table", 0.74),
    _FakeStore._hit("pdfdoc", "text", 0.61),
]


def _retriever(store, **overrides) -> HybridRetriever:
    kwargs = dict(
        embedder=_FakeEmbedder(), store=store, top_k=2,
        min_similarity=0.5, table_min_similarity=0.35,
        use_hybrid=False, aggregate_max_chunks=150, auto_table_context_rows=40,
    )
    kwargs.update(overrides)
    return HybridRetriever(**kwargs)


def test_retriever_expands_full_table_for_aggregate_question():
    store = _FakeStore()
    result = _retriever(store).retrieve("Zeige mir alle Wellen.")

    assert store.scroll_calls == ["tabledoc"]  # Route 1: bestplatzierter Tabellen-Treffer expandiert
    assert len(result) == 10  # alle Zeilen statt top_k=2
    assert all(r.similarity == pytest.approx(0.74) for r in result)  # Score des Seed-Treffers


def test_retriever_keeps_top_k_for_fact_question():
    store = _FakeStore()
    result = _retriever(store).retrieve("Welchen Werkstoff hat W-103?")

    assert store.scroll_calls == []
    assert len(result) == 2  # normaler top_k-Pfad (keine Mehrheit aus einer Tabelle)


def test_retriever_keeps_top_k_when_no_table_hit():
    store = _FakeStore(hits=[_FakeStore._hit("pdfdoc", "text", 0.8)])
    result = _retriever(store).retrieve("Zeige mir alle Wellen.")

    assert store.scroll_calls == []
    assert len(result) == 1


# --- Tabellen-Threshold (niedrigerer Schwellenwert NUR für doc_kind=table) ---

def test_retriever_applies_table_specific_threshold():
    store = _FakeStore(hits=[
        _FakeStore._hit("pdfdoc", "text", 0.80),
        _FakeStore._hit("pdfdoc2", "text", 0.45),   # Text unter 0.5 → raus
        _FakeStore._hit("tabledoc", "table", 0.40),  # Tabelle über 0.35 → bleibt
    ])
    result = _retriever(store, top_k=5).retrieve("Welchen Werkstoff hat W-103?")

    # Qdrant-Vorfilter läuft mit dem niedrigeren der beiden Thresholds
    assert store.last_threshold == pytest.approx(0.35)
    kinds_scores = [(r.metadata["doc_kind"], r.similarity) for r in result]
    assert ("text", pytest.approx(0.45)) not in kinds_scores
    assert ("table", pytest.approx(0.40)) in kinds_scores
    assert len(result) == 2


# --- Route 2: ergebnisgetriebenes Routing (ohne Signalwörter) ----------------

_DOMINANCE_HITS = [
    _FakeStore._hit("tabledoc", "table", 0.62, position=3),
    _FakeStore._hit("pdfdoc", "text", 0.60),
    _FakeStore._hit("tabledoc", "table", 0.58, position=7),
    _FakeStore._hit("tabledoc", "table", 0.55, position=9),
    _FakeStore._hit("pdfdoc", "text", 0.52),
]


def test_retriever_dominance_expands_small_table_without_keyword():
    question = "Welche Wellen gibt es?"
    assert not is_aggregate_query(question)  # kein Signalwort – genau der frühere Blindfleck

    store = _FakeStore(hits=list(_DOMINANCE_HITS), table_rows=16)
    result = _retriever(store, top_k=5).retrieve(question)

    assert store.scroll_calls == ["tabledoc"]  # Mehrheit (3/5) → Tabelle komplett laden
    assert len(result) == 16
    assert all(r.similarity == pytest.approx(0.62) for r in result)  # bester Tabellen-Treffer
    assert [r.chunk.position for r in result] == list(range(1, 17))  # Zeilenreihenfolge


def test_retriever_dominance_skips_large_table():
    store = _FakeStore(hits=list(_DOMINANCE_HITS), table_rows=60)  # > auto_table_context_rows
    result = _retriever(store, top_k=5, auto_table_context_rows=40).retrieve("Welche Wellen gibt es?")

    assert len(result) == 5  # zu groß fürs automatische Voll-Laden → top_k-Pfad
    assert store.scroll_calls == ["tabledoc"]  # Größe wurde per Scroll-Sentinel geprüft


def test_retriever_dominance_requires_majority():
    hits = [
        _FakeStore._hit("pdfdoc", "text", 0.70),
        _FakeStore._hit("pdfdoc", "text", 0.65),
        _FakeStore._hit("tabledoc", "table", 0.60),
        _FakeStore._hit("tabledoc", "table", 0.55),
        _FakeStore._hit("pdfdoc", "text", 0.52),
    ]
    store = _FakeStore(hits=hits, table_rows=16)
    result = _retriever(store, top_k=5).retrieve("Welche Wellen gibt es?")

    assert store.scroll_calls == []  # nur 2/5 aus der Tabelle → keine Mehrheit
    assert len(result) == 5


def test_retriever_dominance_can_be_disabled():
    store = _FakeStore(hits=list(_DOMINANCE_HITS), table_rows=16)
    result = _retriever(store, top_k=5, auto_table_context_rows=0).retrieve("Welche Wellen gibt es?")

    assert store.scroll_calls == []
    assert len(result) == 5


# --- Nachvollziehbarkeit: Detailtexte im Prozess-Schritt "Chunk-Suche" -------

def _collect_events(retriever, question):
    events: list[tuple[str, str | None]] = []
    retriever.retrieve(question, progress_callback=lambda e, d=None: events.append((e, d)))
    return dict(e for e in events if e[0] == "search_done"), [e[0] for e in events]


def test_search_detail_names_files_and_route_for_table_expansion():
    store = _FakeStore(table_rows=16)
    details, order = _collect_events(_retriever(store), "Zeige mir alle Wellen.")

    detail = details["search_done"]
    assert "tabledoc.csv" in detail          # WELCHE Datei geladen wurde
    assert "16 Zeilen" in detail             # WIE VIEL Kontext
    assert "Signalwort" in detail            # WELCHE Route
    assert order == ["embedding_start", "embedding_done", "search_start", "search_done"]


def test_search_detail_lists_files_for_top_k_path():
    details, _ = _collect_events(_retriever(_FakeStore()), "Welchen Werkstoff hat W-103?")

    detail = details["search_done"]
    assert detail.startswith("2 Treffer")
    assert "pdfdoc.pdf" in detail and "S. 1" in detail and "82" in detail  # Datei, Seite, Score


def test_search_detail_explains_empty_result_with_thresholds():
    details, _ = _collect_events(_retriever(_FakeStore(hits=[])), "Völlig fremdes Thema?")

    detail = details["search_done"]
    assert "Keine Treffer" in detail and "0.5" in detail and "0.35" in detail


def test_progress_callback_with_legacy_single_arg_signature_does_not_crash():
    events: list[str] = []
    _retriever(_FakeStore()).retrieve("Welchen Werkstoff hat W-103?", progress_callback=events.append)
    assert "search_done" in events  # TypeError-Fallback: Event kommt ohne Detail an


# ---------------------------------------------------------------------------
# Kanal B: csv_gear_mapper
# ---------------------------------------------------------------------------

def test_csv_gear_mapper_maps_german_columns(tmp_path):
    csv = (
        "Bauteil_ID,Bezeichnung,Verzahnungstyp,Modul_mm,Zaehnezahl,Eingriffswinkel,Zahnbreite,Werkstoff\n"
        'G-010,Stirnrad Testrad,Stirnrad,"2,5",32,20,25,16MnCr5\n'
    )
    result = map_tabular_to_gear_parameters(_write(tmp_path, "gear.csv", csv))

    # Verschachtelte GearParameters-Struktur mit {value, unit, confidence}
    assert result["gear_type"]["value"] == "spur"  # deutsche Bezeichnung → Enum
    assert result["tooth_profile"]["module_mm"] == {"value": 2.5, "unit": "mm", "confidence": 0.92}
    assert result["tooth_profile"]["num_teeth"]["value"] == 32
    assert result["basic_geometry"]["face_width_mm"]["value"] == 25.0
    assert result["material_context"]["material"] == "16MnCr5"
    assert result["metadata"]["part_number"] == "G-010"
    assert result["extraction_quality"]["warnings"] == []


def test_csv_gear_mapper_picks_first_gear_row_and_warns(tmp_path):
    result = map_tabular_to_gear_parameters(_write(tmp_path, "s.csv", STUECKLISTE_CSV))

    assert result["metadata"]["part_number"] == "G-001"  # erste Zeile mit Verzahnungsdaten
    assert result["tooth_profile"]["module_mm"]["value"] == 3.0
    assert any("Stücklisten" in w for w in result["extraction_quality"]["warnings"])


def test_csv_gear_mapper_rejects_csv_without_gear_columns(tmp_path):
    with pytest.raises(ValueError, match="Verzahnungs-Spalten"):
        map_tabular_to_gear_parameters(_write(tmp_path, "adressen.csv", "Name,Ort\nMax,Ulm\n"))
