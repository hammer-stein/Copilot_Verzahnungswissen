"""
tabular_loader_pandas.py – Loader für Tabellen-Dateien (CSV, Excel).

Implementiert das DocumentLoader-Protokoll für strukturierte Daten. Jede Zeile
wird beim Laden in eine natürlichsprachliche Aussage umgewandelt („Zeile→Satz"),
z.B. aus `G-001,Stirnrad Antriebswelle,…` wird
„Bauteil G-001 (Bauteil_ID: G-001): Bezeichnung = Stirnrad Antriebswelle; …".

Hintergrund: Das Embedding-Modell (bge-m3) ist für Fließtext optimiert. Nackte
CSV-Zeilen erzielen nur niedrige Ähnlichkeitswerte und fallen unter den
Retrieval-Threshold. Die Satzform mit explizitem Header-Bezug hebt die Scores
und erhält gleichzeitig die strikte Spalten-Zuordnung für den LLM-Prompt
(Regeln 4–6: Header-Logik, kein Kategorien-Raten, exaktes ID-Matching).

Das zurückgegebene RawDocument trägt doc_kind="table" – der Chunker erzeugt
dann genau einen Chunk pro Zeile (1 Zeile = 1 Datensatz).
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

import pandas as pd

from app.core.types import RawDocument, RawDocumentPage

logger = logging.getLogger(__name__)

# Werte, die als „nicht angegeben" gelten und aus der Satzform weggelassen werden.
_EMPTY_VALUES = {"", "-", "–", "n/a", "na", "nan", "none", "null"}

# Encoding-Kandidaten für CSV-Dateien (Excel-Exporte sind oft latin1/cp1252).
_ENCODINGS_TO_TRY = ["utf-8", "latin1", "cp1252", "iso-8859-1"]


def read_dataframe(path: Path) -> pd.DataFrame:
    """
    Liest eine Tabellen-Datei robust ein: CSV mit Encoding-/Separator-Erkennung,
    Excel via openpyxl. Wird auch vom csv_gear_mapper (CSV → GearParameters) genutzt.
    """
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)

    last_error: Exception | None = None
    for enc in _ENCODINGS_TO_TRY:
        try:
            return pd.read_csv(path, sep=None, engine="python", encoding=enc)
        except Exception as e:  # noqa: BLE001 – nächstes Encoding probieren
            last_error = e
            continue
    raise ValueError(f"Konnte Tabellen-Datei nicht lesen: {path}") from last_error

# Erkennt ID-Suffixe im ersten Spaltennamen: "Bauteil_ID" → Subjektwort "Bauteil".
_ID_SUFFIX_RE = re.compile(r"[_\s-]*id$", re.IGNORECASE)


def _is_empty(value: object) -> bool:
    """True für NaN/None und Platzhalter wie '-', 'n/a'."""
    if value is None or pd.isna(value):
        return True
    return str(value).strip().lower() in _EMPTY_VALUES


def _format_value(value: object) -> str:
    """Zellwert als kompakter String (Ganzzahlen ohne '.0')."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def row_to_sentence(row: pd.Series) -> str:
    """
    Wandelt eine Tabellenzeile in eine natürlichsprachliche Aussage um.
    Die erste Spalte dient als Subjekt (inkl. explizitem Spaltennamen für
    exaktes ID-Matching), alle weiteren gefüllten Spalten folgen als
    „Header = Wert"-Paare.
    """
    items = [(str(col).strip(), val) for col, val in row.items()]
    filled = [(col, _format_value(val)) for col, val in items if col and not _is_empty(val)]
    if not filled:
        return ""

    first_col, first_val = filled[0]
    # "Bauteil_ID" → "Bauteil G-001 (Bauteil_ID: G-001)"; ohne ID-Suffix: "Name Alice (Name: Alice)"
    subject_word = _ID_SUFFIX_RE.sub("", first_col).strip() or first_col
    subject = f"{subject_word} {first_val} ({first_col}: {first_val})"

    props = "; ".join(f"{col} = {val}" for col, val in filled[1:])
    return f"{subject}: {props}." if props else f"{subject}."


class TabularLoader:
    """Lädt CSV- und Excel-Dateien und wandelt jede Zeile in eine Satz-Aussage um."""

    def load(self, file_path: str | Path) -> RawDocument:
        path = Path(file_path)
        df = read_dataframe(path)

        text_lines = [row_to_sentence(row) for _, row in df.iterrows()]
        full_text = "\n".join(line for line in text_lines if line)
        logger.info("tabular_loaded path=%s rows=%d chars=%d", path, df.shape[0], len(full_text))

        doc_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        page = RawDocumentPage(page_number=1, text=full_text)
        return RawDocument(source_path=str(path), doc_hash=doc_hash, pages=[page], doc_kind="table")
