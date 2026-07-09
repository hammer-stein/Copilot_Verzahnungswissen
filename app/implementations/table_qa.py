"""
table_qa.py – Deterministischer Fast-Path für Filter-/Listenfragen auf Tabellenzeilen.

Kleine LLMs (llama3.2:1b) brechen beim Aufzählen von Tabellentreffern nachweislich
ab, sobald eine nicht passende Zeile die Trefferfolge unterbricht ("Welche Bauteile
bestehen aus 16MnCr5?" → nur 3 von 5 genannt, obwohl alle Zeilen im Kontext lagen).
Dieser Fast-Path beantwortet solche Fragen ohne LLM: Er parst die vom TabularLoader
erzeugten Zeilen-Sätze ("Spalte = Wert"-Paare, siehe tabular_loader_pandas.row_to_sentence),
sucht exakte Zellwerte aus der Frage (z.B. "16MnCr5", "W-103") und baut die
vollständige Trefferliste samt [Qn]-Quellenmarkierungen und Gesamtanzahl deterministisch.

Greift bewusst nur, wenn
  1. die Frage nach Auflistung/Anzahl/Eigenschaft klingt (_LIST_INTENT_RE),
  2. ein Zellwert der Tabelle wortgenau in der Frage vorkommt (exaktes Matching,
     Regeln 4–6 des Systemprompts: kein Kategorien-Raten, striktes ID-Matching),
  3. rein numerische Werte zusätzlich ihren Spaltennamen in der Frage haben
     (sonst würde "Nenne 3 Bauteile" fälschlich auf Menge = 3 filtern).
Alle anderen Fragen laufen unverändert über das LLM.
"""

from __future__ import annotations

import re
from typing import Optional

from app.core.types import RetrievedChunk

# Frage-Muster, die eine Filter-/Listen-/Eigenschaftsfrage anzeigen. Allowlist statt
# Blocklist: Erklärfragen ("Was bedeutet 16MnCr5?") sollen weiterhin ans LLM gehen.
_LIST_INTENT_RE = re.compile(
    r"\b("
    r"welche[srnm]?|wie ?viele|anzahl|liste|auflist\w*|aufz[äa]hl\w*|"
    r"zeige?|nenne?|alle[nrs]?|s[äa]mtliche[nr]?|gibt es|hat|haben|"
    r"besteh\w*|enth[äa]lt|sind aus|ist aus"
    r")\b",
    re.IGNORECASE,
)

# Zeilen-Satz des TabularLoaders: "Subjekt X (Erste_Spalte: X): Col = Val; ...".
_ROW_RE = re.compile(
    r"^.*?\((?P<col>[^():]+):\s*(?P<val>[^()]*?)\)\s*(?::\s*(?P<props>.*?))?\.?\s*$",
    re.DOTALL,
)

# Spalten, deren Wert als beschreibender Zusatz hinter der ID angezeigt wird.
_LABEL_COLUMNS = {"bezeichnung", "name", "beschreibung", "titel", "benennung"}

_UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def _normalize(text: str) -> str:
    """Casefold + Umlaut-Transliteration + Trenner vereinheitlichen ("Bauteil-ID" ≙ "Bauteil_ID")."""
    return re.sub(r"[_\-]+", " ", text.casefold().translate(_UMLAUT_MAP))


def _norm_col(col: str) -> str:
    """Spaltenname normalisiert und ohne Einheiten-Suffix ("Modul_mm" → "modul")."""
    stripped = re.sub(r"_(mm|cm|m|deg|grad|kg|g|hrc|um|µm)$", "", col, flags=re.IGNORECASE)
    return _normalize(stripped).strip()


def _is_numeric(value: str) -> bool:
    return bool(re.fullmatch(r"[\d.,]+", value))


def parse_table_row(text: str) -> Optional[list[tuple[str, str]]]:
    """
    Zerlegt einen Zeilen-Satz in geordnete (Spalte, Wert)-Paare; erstes Paar ist die
    Subjekt-Spalte. None, wenn der Text nicht dem Loader-Format entspricht.
    """
    m = _ROW_RE.match(text.strip())
    if not m:
        return None
    first_col, first_val = m.group("col").strip(), m.group("val").strip()
    if not first_col or not first_val:
        return None
    pairs = [(first_col, first_val)]
    props = (m.group("props") or "").strip().rstrip(".")
    for part in props.split("; "):
        col, sep, val = part.partition(" = ")
        if sep and col.strip() and val.strip():
            pairs.append((col.strip(), val.strip()))
    return pairs


def _value_in_question(value: str, question: str) -> bool:
    """Wortgenaues Vorkommen des Zellwerts in der Frage (keine Teilwort-Treffer)."""
    return bool(re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", question, re.IGNORECASE))


def _row_entry(qidx: int, pairs: list[tuple[str, str]], filter_col: str, target_cols: list[str]) -> str:
    """Ein Treffer als Listenzeile: 'ID (Bezeichnung): Zielspalte = Wert [Qn]'."""
    first_col, first_val = pairs[0]
    d = dict(pairs)
    label = first_val
    for col, val in pairs[1:]:
        if _norm_col(col) in _LABEL_COLUMNS and val != first_val:
            label += f" ({val})"
            break

    shown = [f"{c} = {d[c]}" for c in target_cols if c in d]
    if not shown and filter_col in d and filter_col != first_col and _norm_col(filter_col) not in _LABEL_COLUMNS:
        shown.append(f"{filter_col} = {d[filter_col]}")
    detail = "; ".join(shown)
    return f"{label}: {detail} [Q{qidx}]" if detail else f"{label} [Q{qidx}]"


def _render(
    sections: list[tuple[str, str, list[tuple[int, list[tuple[str, str]]]]]],
    target_cols: list[str],
    answer_format: Optional[str],
) -> str:
    """Baut die Antwort im gewünschten AUSGABEFORMAT (kurz/tabellarisch/Stichpunkte)."""
    fmt = (answer_format or "").strip().casefold()
    blocks: list[str] = []

    for col, val, rows in sections:
        count = len(rows)
        noun = "Datensatz" if count == 1 else "Datensätze"
        header = f"{count} {noun} mit {col} = {val}"

        if fmt == "kurz":
            entries = ", ".join(_row_entry(i, p, col, target_cols) for i, p in rows)
            blocks.append(f"{header}: {entries}.")
        elif fmt == "tabellarisch":
            first_col = rows[0][1][0][0]
            label_col = next(
                (c for _, pairs in rows for c, _ in pairs if _norm_col(c) in _LABEL_COLUMNS),
                None,
            )
            cols = [first_col] + ([label_col] if label_col else []) + [col] + [c for c in target_cols if c not in (first_col, label_col, col)]
            lines = [header + ":", "", "| " + " | ".join(cols) + " | Quelle |",
                     "|" + "---|" * (len(cols) + 1)]
            for qidx, pairs in rows:
                d = dict(pairs)
                lines.append("| " + " | ".join(d.get(c, "–") for c in cols) + f" | [Q{qidx}] |")
            blocks.append("\n".join(lines))
        else:  # standard/ausführlich/stichpunkte → vollständige Liste, ein Treffer pro Zeile
            lines = [header + ":"] + [f"- {_row_entry(i, p, col, target_cols)}" for i, p in rows]
            lines.append(f"Gesamt: {count} Treffer.")
            blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def maybe_answer_table_filter_question(
    question: str,
    chunks: list[RetrievedChunk],
    answer_format: Optional[str] = None,
) -> Optional[str]:
    """
    Deterministische Antwort für Filter-/Listenfragen über Tabellenzeilen – oder None,
    wenn der normale LLM-Pfad greifen soll. Die [Qn]-Nummern entsprechen der
    Chunk-Reihenfolge und damit exakt der Nummerierung aus build_chunks_block_and_sources.
    """
    if not question or not chunks or not _LIST_INTENT_RE.search(question):
        return None

    rows: list[tuple[int, list[tuple[str, str]]]] = []
    for qidx, rc in enumerate(chunks, start=1):
        if (rc.metadata or {}).get("doc_kind") != "table":
            continue
        pairs = parse_table_row(rc.chunk.text)
        if pairs:
            rows.append((qidx, pairs))
    if not rows:
        return None

    # Zellwert → Zeilen, die ihn tragen (pro Spalte gruppiert).
    value_rows: dict[tuple[str, str], list[tuple[int, list[tuple[str, str]]]]] = {}
    for qidx, pairs in rows:
        for col, val in dict(pairs).items():
            value_rows.setdefault((col, val), []).append((qidx, pairs))

    norm_q = _normalize(question)
    matched: list[tuple[str, str]] = []
    for col, val in value_rows:
        if len(val) < 2 or not _value_in_question(val, question):
            continue
        # Reine Zahlen nur filtern, wenn die Spalte auch genannt ist ("Menge 3", "24 Zähne").
        if _is_numeric(val) and _norm_col(col) not in norm_q:
            continue
        matched.append((col, val))
    if not matched:
        return None

    # Bei überlappenden Treffern gewinnt der längere Wert ("Stirnrad Antriebswelle"
    # verdrängt "Antriebswelle"), sonst würde dieselbe Frage zwei Filter auslösen.
    matched = [
        (col, val) for col, val in matched
        if not any(val.casefold() in other.casefold() and val != other for _, other in matched)
    ]
    if not matched:
        return None

    # Zielspalten: in der Frage genannte Spalten, die nicht selbst Filter sind
    # ("Welche Oberflächenhärte haben Bauteile aus 16MnCr5?" → Oberflaechenhaerte).
    filter_cols = {col for col, _ in matched}
    all_cols: list[str] = []
    for _, pairs in rows:
        for col, _ in pairs:
            if col not in all_cols:
                all_cols.append(col)
    target_cols = [c for c in all_cols if c not in filter_cols and _norm_col(c) and _norm_col(c) in norm_q]

    sections = [(col, val, value_rows[(col, val)]) for col, val in matched]
    return _render(sections, target_cols, answer_format)
