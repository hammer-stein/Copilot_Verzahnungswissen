"""
text_split.py – Satztrennung, Token-Approximation und Tabellen-Zeilen-Chunking.

Hilfsfunktionen, die von beiden Chunker-Implementierungen gemeinsam genutzt werden.
Bewusst modell- und bibliotheksunabhängig, um keine Embedder-Abhängigkeit einzubringen.
"""

from __future__ import annotations

import re

from app.core.types import Chunk, RawDocument

# Trennt Text an Stellen wo ein Satzzeichen (.!?) folgt von Leerzeichen und Großbuchstabe/Ziffer.
# Bekannte Schwäche: Abkürzungen wie "Dr. Müller" werden fälschlich getrennt.
_sentence_re = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9])")


def split_sentences(text: str) -> list[str]:
    """
    Teilt einen Text in eine Liste von Sätzen auf.
    Leere Sätze werden herausgefiltert; bei leerem Input wird [] zurückgegeben.
    """
    text = (text or "").strip()
    if not text:
        return []
    parts = _sentence_re.split(text)
    return [p.strip() for p in parts if p.strip()]


def approx_tokens(text: str) -> int:
    r"""
    Approximiert die Tokenanzahl durch Wortzählung (\S+-Gruppen).
    Exakte Tokenisierung würde eine Modellabhängigkeit einbringen – Wortzählung reicht als Schwellenwert-Basis.
    """
    return max(1, len(re.findall(r"\S+", text)))


def chunk_table_rows(document: RawDocument) -> list[Chunk]:
    """
    Tabellen-Modus (doc_kind == "table"): genau ein Chunk pro nicht-leerer Zeile.
    Kein Satz-Merging, kein Token-Limit, kein Overlap – eine Zeile entspricht
    einem Datensatz (z.B. Stücklisten-Eintrag) und muss als Einheit auffindbar bleiben.
    Wird von beiden Chunker-Implementierungen genutzt, damit Tabellen unabhängig
    von der konfigurierten Chunking-Strategie korrekt behandelt werden.
    """
    chunks: list[Chunk] = []
    pos = 0

    for page in document.pages:
        for line in page.text.splitlines():
            text = line.strip()
            if not text:
                continue
            pos += 1
            chunks.append(
                Chunk(
                    text=text,
                    source_path=document.source_path,
                    page_number=page.page_number,
                    position=pos,
                    doc_hash=document.doc_hash,
                )
            )

    return chunks
