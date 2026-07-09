"""
test_table_qa.py – Tests für den deterministischen Tabellen-Filter-Fast-Path.

Reproduziert den Bugfall: "Welche Bauteile bestehen aus 16MnCr5?" muss ALLE
passenden Zeilen liefern, auch wenn nicht passende Zeilen (G-004) die
Trefferfolge unterbrechen – genau daran scheiterte llama3.2:1b.

Alle Tests laufen ohne schwere Abhängigkeiten (kein torch/Qdrant/Ollama).
"""

from __future__ import annotations

import pytest

from app.core.types import Chunk, RetrievedChunk
from app.implementations.table_qa import (
    maybe_answer_table_filter_question,
    parse_table_row,
)
from app.implementations.tabular_loader_pandas import row_to_sentence

import pandas as pd

# ---------------------------------------------------------------------------
# Hilfsdaten: dieselbe Stückliste wie im realen Bugfall (verkürzt, aber mit der
# entscheidenden Unterbrechung: G-004 ist NICHT aus 16MnCr5, W-101/W-102 danach schon).
# ---------------------------------------------------------------------------

ROWS = [
    {"Bauteil_ID": "G-001", "Bezeichnung": "Stirnrad Antriebswelle", "Menge": 1, "Werkstoff": "16MnCr5", "Oberflaechenhaerte": "58 HRC"},
    {"Bauteil_ID": "G-002", "Bezeichnung": "Stirnrad Zwischenwelle", "Menge": 1, "Werkstoff": "16MnCr5", "Oberflaechenhaerte": "58 HRC"},
    {"Bauteil_ID": "G-003", "Bezeichnung": "Ritzel Zwischenwelle", "Menge": 1, "Werkstoff": "16MnCr5", "Oberflaechenhaerte": "60 HRC"},
    {"Bauteil_ID": "G-004", "Bezeichnung": "Hohlrad Ausgangsstufe", "Menge": 1, "Werkstoff": "42CrMo4", "Oberflaechenhaerte": "52 HRC"},
    {"Bauteil_ID": "W-101", "Bezeichnung": "Antriebswelle", "Menge": 1, "Werkstoff": "16MnCr5", "Oberflaechenhaerte": "einsatzgehärtet"},
    {"Bauteil_ID": "W-102", "Bezeichnung": "Zwischenwelle", "Menge": 1, "Werkstoff": "16MnCr5", "Oberflaechenhaerte": "einsatzgehärtet"},
    {"Bauteil_ID": "W-103", "Bezeichnung": "Ausgangswelle", "Menge": 1, "Werkstoff": "42CrMo4", "Oberflaechenhaerte": "vergütet"},
    {"Bauteil_ID": "S-501", "Bezeichnung": "Zylinderschraube M8x35", "Menge": 12, "Werkstoff": "Stahl 8.8", "Oberflaechenhaerte": "galvanisch verzinkt"},
]

ALL_16MNCR5 = {"G-001", "G-002", "G-003", "W-101", "W-102"}


def _table_chunks() -> list[RetrievedChunk]:
    """Baut RetrievedChunks exakt so, wie sie aus TabularLoader + Tabellen-Route kommen."""
    chunks = []
    for pos, row in enumerate(pd.DataFrame(ROWS).iterrows(), start=1):
        text = row_to_sentence(row[1])
        chunks.append(RetrievedChunk(
            chunk=Chunk(text=text, source_path="stueckliste.csv", page_number=1, position=pos, doc_hash="h1"),
            metadata={"doc_kind": "table", "file_name": "Stueckliste.csv"},
            similarity=0.4,
        ))
    return chunks


def _text_chunk(text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(text=text, source_path="doc.pdf", page_number=3, position=1, doc_hash="h2"),
        metadata={"doc_kind": "text", "file_name": "doc.pdf"},
        similarity=0.7,
    )


# ---------------------------------------------------------------------------
# parse_table_row
# ---------------------------------------------------------------------------

def test_parse_table_row_roundtrip():
    sentence = row_to_sentence(pd.DataFrame(ROWS).iloc[0])
    pairs = parse_table_row(sentence)
    assert pairs is not None
    assert pairs[0] == ("Bauteil_ID", "G-001")
    d = dict(pairs)
    assert d["Werkstoff"] == "16MnCr5"
    assert d["Bezeichnung"] == "Stirnrad Antriebswelle"
    assert d["Oberflaechenhaerte"] == "58 HRC"  # trailing "." des Satzes entfernt


def test_parse_table_row_rejects_fliesstext():
    assert parse_table_row("Die Zahnflanke wird nach DIN 3990 ausgelegt.") is None


# ---------------------------------------------------------------------------
# Bugfall: vollständige Aufzählung trotz Unterbrechung der Trefferfolge
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Welche Bauteile bestehen aus 16MnCr5?",
    "Welche Teile sind aus 16MnCr5?",
    "Liste alle Bauteile aus 16MnCr5 auf",
    "Wie viele Bauteile sind aus 16MnCr5?",
])
def test_material_filter_findet_alle_fuenf(question):
    answer = maybe_answer_table_filter_question(question, _table_chunks())
    assert answer is not None
    for bauteil_id in ALL_16MNCR5:
        assert bauteil_id in answer
    assert "G-004" not in answer and "W-103" not in answer and "S-501" not in answer
    assert "5" in answer  # Gesamtanzahl


def test_qn_markierungen_entsprechen_chunk_reihenfolge():
    answer = maybe_answer_table_filter_question("Welche Bauteile bestehen aus 16MnCr5?", _table_chunks())
    # G-001 ist Chunk 1, W-102 ist Chunk 6
    assert "[Q1]" in answer and "[Q5]" in answer and "[Q6]" in answer
    assert "[Q4]" not in answer  # G-004 (42CrMo4) darf nicht zitiert werden


def test_zielspalte_wird_ausgegeben():
    answer = maybe_answer_table_filter_question(
        "Welche Oberflächenhärte haben die Bauteile aus 42CrMo4?", _table_chunks()
    )
    assert answer is not None
    assert "52 HRC" in answer and "vergütet" in answer
    assert "G-004" in answer and "W-103" in answer


def test_id_frage_liefert_exakten_datensatz():
    answer = maybe_answer_table_filter_question("Welchen Werkstoff hat W-103?", _table_chunks())
    assert answer is not None
    assert "42CrMo4" in answer
    assert "G-004" not in answer  # anderes 42CrMo4-Bauteil ist NICHT gefragt


# ---------------------------------------------------------------------------
# Ausgabeformate
# ---------------------------------------------------------------------------

def test_format_tabellarisch_erzeugt_markdown_tabelle():
    answer = maybe_answer_table_filter_question(
        "Welche Bauteile bestehen aus 16MnCr5?", _table_chunks(), answer_format="tabellarisch"
    )
    assert answer.count("|") > 10
    assert "Bauteil_ID" in answer and "Werkstoff" in answer


def test_format_kurz_bleibt_einzeilig_und_vollstaendig():
    answer = maybe_answer_table_filter_question(
        "Welche Bauteile bestehen aus 16MnCr5?", _table_chunks(), answer_format="kurz"
    )
    assert "\n" not in answer
    for bauteil_id in ALL_16MNCR5:
        assert bauteil_id in answer


# ---------------------------------------------------------------------------
# Nicht-Zuständigkeit: Fragen, die weiter ans LLM gehen müssen
# ---------------------------------------------------------------------------

def test_erklaerfrage_geht_ans_llm():
    assert maybe_answer_table_filter_question("Was bedeutet 16MnCr5?", _table_chunks()) is None


def test_frage_ohne_zellwert_geht_ans_llm():
    assert maybe_answer_table_filter_question("Welche Wellen gibt es?", _table_chunks()) is None


def test_nackte_zahl_filtert_nicht_ohne_spaltennennung():
    # "3" käme als Menge/Position vor – ohne Spaltennennung kein Filter-Hijack.
    assert maybe_answer_table_filter_question("Nenne 12 Fakten über Zahnräder", _table_chunks()) is None


def test_zahl_mit_spaltennennung_filtert():
    answer = maybe_answer_table_filter_question("Welches Bauteil hat Menge 12?", _table_chunks())
    assert answer is not None
    assert "S-501" in answer


def test_ohne_tabellen_chunks_geht_ans_llm():
    chunks = [_text_chunk("16MnCr5 ist ein Einsatzstahl nach DIN EN 10084.")]
    assert maybe_answer_table_filter_question("Welche Bauteile bestehen aus 16MnCr5?", chunks) is None


def test_gemischter_kontext_nutzt_nur_tabellenzeilen():
    chunks = [_text_chunk("16MnCr5 ist ein Einsatzstahl.")] + _table_chunks()
    answer = maybe_answer_table_filter_question("Welche Bauteile bestehen aus 16MnCr5?", chunks)
    assert answer is not None
    # Q-Nummern verschieben sich um 1 (Text-Chunk ist Q1)
    assert "[Q2]" in answer and "[Q7]" in answer
