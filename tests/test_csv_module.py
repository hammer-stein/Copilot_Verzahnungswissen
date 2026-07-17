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
    def __init__(self):
        self.last_texts = None  # zuletzt eingebettete Query (für Anreicherungs-Tests)

    def embed(self, texts):
        from app.core.types import EmbeddingResult
        self.last_texts = list(texts)
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


# --- CAD-bewusstes Retrieval: context_terms reichern NUR die Suche an ---------

def test_context_terms_enrich_embedding_query():
    embedder = _FakeEmbedder()
    retriever = _retriever(_FakeStore())
    retriever.embedder = embedder
    retriever.retrieve("Welches Verfahren eignet sich zur Herstellung?", context_terms="Kegelrad Kegelradverzahnung")
    assert embedder.last_texts[0].startswith("Welches Verfahren eignet sich zur Herstellung?")
    assert "Kegelradverzahnung" in embedder.last_texts[0]


def test_context_terms_skipped_for_aggregate_questions():
    # Listen-/Aggregatfragen steuern das Tabellen-Routing – sie bleiben unangereichert.
    embedder = _FakeEmbedder()
    retriever = _retriever(_FakeStore())
    retriever.embedder = embedder
    retriever.retrieve("Zeige mir alle Wellen.", context_terms="Kegelrad Kegelradverzahnung")
    assert embedder.last_texts == ["Zeige mir alle Wellen."]


def test_cad_retrieval_terms_mapping():
    from app.core.cad_terms import cad_retrieval_terms
    assert "Kegelrad" in cad_retrieval_terms({"gear_type": "bevel"})
    assert "Gehrungsrad" in cad_retrieval_terms({"gear_type": {"value": "miter", "confidence": 0.9}})
    assert cad_retrieval_terms({}) == ""                          # kein Bauteil geladen
    assert cad_retrieval_terms({"gear_type": "unbekannt"}) == ""  # unbekannter Typ → keine Anreicherung


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


# --- Typ-Abgleich Frage ↔ CAD + Literaturverzeichnis-Filter -------------------

def test_question_gear_families_detection():
    from app.core.cad_terms import question_gear_families
    assert question_gear_families("ich möchte das hochgeladene kegelrad herstellen") == {"kegel"}
    assert question_gear_families("Wie fertigt man ein Sperrrad?") == {"sperr"}
    assert question_gear_families("Vergleich Stirnrad und Kegelrad") == {"stirn", "kegel"}
    assert question_gear_families("Welches Verfahren eignet sich am besten?") == set()


def test_type_mismatch_note_for_ratchet_vs_kegelrad_question():
    from app.core.cad_terms import build_type_mismatch_note
    cad = {"gear_type": {"value": "ratchet", "confidence": 0.92}}
    note = build_type_mismatch_note("ich möchte das hochgeladene kegelrad herstellen", cad)
    assert note is not None
    assert "Sperrrad" in note and "92 %" in note and "[CAD]" in note


def test_type_mismatch_note_absent_when_types_agree_or_unknown():
    from app.core.cad_terms import build_type_mismatch_note
    q = "ich möchte das hochgeladene kegelrad herstellen"
    # Gehrungsrad IST ein Kegelrad (gleiche Familie) → keine Warnung:
    assert build_type_mismatch_note(q, {"gear_type": {"value": "miter"}}) is None
    assert build_type_mismatch_note(q, {"gear_type": "bevel"}) is None
    assert build_type_mismatch_note(q, {}) is None                       # kein Bauteil
    assert build_type_mismatch_note("Wie groß ist der Modul?", {"gear_type": "ratchet"}) is None  # kein Typ genannt


def test_retriever_drops_bibliography_chunks():
    from app.implementations.retriever_hybrid import _is_bibliography_chunk
    bib = ("Literatur 483 [PETE04] PETER, A.: Entwicklung eines Modells. Dissertation, 2004 "
           "[PISC95] PISCHEL, H.: Bewährtes Innenhochdruck-Umformen. In: Werkstatt 128 (1995) "
           "[RADT65] RADTKE, H.: Der Umformvorgang beim Stülpziehen.")
    assert _is_bibliography_chunk(bib)
    # Normaler Fachtext mit Normverweisen bleibt drin:
    assert not _is_bibliography_chunk("Nach DIN 3990 und ISO 6336 wird die Tragfähigkeit berechnet. [Q1]")

    store = _FakeStore(hits=[
        _FakeStore._hit("pdfdoc", "text", 0.82),
        _FakeStore._hit("bibdoc", "text", 0.80),
    ])
    store.hits[1] = SearchResult(
        chunk=Chunk(text=bib, source_path="x", page_number=504, position=1, doc_hash="bibdoc"),
        metadata={"doc_kind": "text", "file_name": "klocke.pdf"},
        dense_score=0.80, sparse_score=None, score=0.80,
    )
    result = _retriever(store, top_k=5).retrieve("Welche Fertigungsverfahren gibt es?")
    assert [c.metadata["file_name"] for c in result] == ["pdfdoc.pdf"]


def test_question_retrieval_terms_prefer_named_type():
    from app.core.cad_terms import question_retrieval_terms
    terms = question_retrieval_terms("ich möchte das hochgeladene kegelrad herstellen")
    assert "Kegelradverzahnung" in terms and "Sperr" not in terms
    assert question_retrieval_terms("Welches Verfahren eignet sich?") == ""


# --- Konfidenz-gestufter Typ-Abgleich (part_match) ----------------------------

def test_assess_type_mismatch_confidence_tiers():
    from app.core.cad_terms import assess_type_mismatch
    q = "ich möchte das hochgeladene kegelrad herstellen"

    def cad(conf):
        return {"gear_type": {"value": "ratchet", "confidence": conf}}

    assert assess_type_mismatch(q, cad(0.3)) is None                    # < low: keine Warnung
    assert assess_type_mismatch(q, cad(0.7)).severity == "soft"         # low..high: Status quo
    assert assess_type_mismatch(q, cad(0.92)).severity == "hard"        # >= high: mode greift
    # fehlende Konfidenz → konservativ soft (Verhaltensänderung braucht Messung):
    assert assess_type_mismatch(q, {"gear_type": "ratchet"}).severity == "soft"
    # eigene Schwellen:
    assert assess_type_mismatch(q, cad(0.7), high_confidence=0.6).severity == "hard"


def test_mismatch_texts_and_directive():
    from app.core.cad_terms import (
        assess_type_mismatch, mismatch_ask_back_answer,
        mismatch_followed_cad_note, type_focus_directive,
    )
    m = assess_type_mismatch(
        "kegelrad herstellen", {"gear_type": {"value": "ratchet", "confidence": 0.92}}
    )
    assert "Rückfrage" in mismatch_ask_back_answer(m) and "Sperrrad" in mismatch_ask_back_answer(m)
    assert "TATSÄCHLICH geladene" in mismatch_followed_cad_note(m)
    d = type_focus_directive(m)
    assert "Sperrrad" in d and "NICHT" in d


# --- Norm-Verifikation (Post-Generation-Guardrail) ----------------------------

def test_norm_check_flags_unsupported_designations():
    from app.core.norm_check import find_unsupported_norm_references
    refs = [
        "DIN 3991-4_2025-10-00_DE_3640827.pdf",
        "Nach VDI 3720 Blatt 9.1 werden Kegelradsätze hartfein bearbeitet.",
    ]
    text = ("Laut DIN 3991-4:2025-10 [Q4] und VDI 3720 Blatt 9.1 [Q1] gilt das. "
            "Zusätzlich fordert DIN 9999 eine Prüfung nach ISO 6336-6.")
    unsupported = find_unsupported_norm_references(text, refs)
    assert "DIN 9999" in unsupported
    assert any("ISO 6336-6" in u for u in unsupported)
    # belegte Normen (inkl. echtem Ausgabedatum aus dem Dateititel) werden NICHT gemeldet:
    assert not any("3991-4" in u for u in unsupported)
    assert not any("3720" in u for u in unsupported)


def test_norm_check_flags_fabricated_edition_date():
    from app.core.norm_check import find_unsupported_norm_references
    refs = ["DIN 3965_2023-04-00_DE_3412567.pdf"]
    # Norm existiert, aber das Jahr wurde verfälscht:
    unsupported = find_unsupported_norm_references("Siehe DIN 3965:1986-08.", refs)
    assert unsupported == ["Ausgabedatum 1986-08 zu DIN 3965"]
    # korrektes Datum → kein Befund:
    assert find_unsupported_norm_references("Siehe DIN 3965:2023-04.", refs) == []


def test_norm_check_clean_answer_returns_empty():
    from app.core.norm_check import find_unsupported_norm_references
    assert find_unsupported_norm_references("Empfehlung: Schleifen [Q1].", ["Text ohne Norm"]) == []


# --- Kennzahlen-Verifikation (Zahl + Einheit, Post-Generation-Guardrail) ------

def test_measurement_check_flags_fabricated_values():
    from app.core.norm_check import find_unsupported_measurements
    refs = ["Die Zahnbreite beträgt 6,35 mm.", '{"module_mm": {"value": 1.0583}}']
    # Die zwei real beobachteten Halluzinationen: Ra-Wert und Rm frei erfunden.
    text = "Schleifen erzielt Ra-Werte < 0,8 µm. Die mittlere Teilkegellänge Rm beträgt 50 mm."
    unsupported = find_unsupported_measurements(text, refs)
    assert 'Kennzahl „0,8 µm“' in unsupported
    assert 'Kennzahl „50 mm“' in unsupported


def test_measurement_check_accepts_grounded_and_rounded_values():
    from app.core.norm_check import find_unsupported_measurements
    refs = ['{"pitch_diameter_mm": {"value": 25.399}, "module_mm": {"value": 1.0583}}',
            "Der Eingriffswinkel beträgt 20°. Härte 60 HRC."]
    # exakt, gerundet auf Anzeige-Präzision, Komma-Schreibweise, Grad, HRC:
    text = ("Teilkreis 25,4 mm, Modul 1,06 mm bzw. 1,0583 mm, Eingriffswinkel 20°, "
            "Härte 60 HRC.")
    assert find_unsupported_measurements(text, refs) == []


def test_measurement_check_ignores_bare_numbers_and_norm_digits():
    from app.core.norm_check import find_unsupported_measurements
    refs = ["Nur Fließtext ohne Zahlen."]
    # Qualität 7, z = 24, [Q1], Normziffern: alles ohne Einheit bzw. Norm → kein Befund.
    text = "Nach DIN 3965:2023-04 gilt Qualität 7 bei z = 24 [Q1]."
    assert find_unsupported_measurements(text, refs) == []


def test_measurement_check_question_counts_as_grounding():
    from app.core.norm_check import find_unsupported_measurements
    # main.py übergibt die Frage als Referenz: vom Nutzer genannte Werte sind belegt.
    q = "Was bedeutet eine Zahnbreite von 12 mm?"
    assert find_unsupported_measurements("Eine Zahnbreite von 12 mm bedeutet …", [q]) == []
    assert find_unsupported_measurements("Eine Zahnbreite von 12 mm …", ["andere Zahl 13"]) \
        == ['Kennzahl „12 mm“']


def test_unknown_gear_type_never_triggers_follow_cad():
    """Regression: Der ehrliche unknown-Pfad des cad_processor darf im RAG-Stack
    weder Typ-Abgleich/follow_cad noch Retrieval-Anreicherung auslösen."""
    from app.core.cad_terms import GEAR_TYPE_LABELS, assess_type_mismatch, cad_retrieval_terms
    cad = {"gear_type": {"value": "unknown", "confidence": 0.45}}
    assert assess_type_mismatch("ich möchte das kegelrad herstellen", cad) is None
    assert cad_retrieval_terms(cad) == ""
    assert "Unbekannt" in GEAR_TYPE_LABELS["unknown"]  # ehrliches GUI-/Prompt-Label
