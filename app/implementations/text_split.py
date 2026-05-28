"""
text_split.py – Satztrennung und Token-Approximation.

Hilfsfunktionen, die von beiden Chunker-Implementierungen gemeinsam genutzt werden.
Bewusst modell- und bibliotheksunabhängig, um keine Embedder-Abhängigkeit einzubringen.
"""

from __future__ import annotations

import re

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
    """
    Approximiert die Tokenanzahl durch Wortzählung (\S+-Gruppen).
    Exakte Tokenisierung würde eine Modellabhängigkeit einbringen – Wortzählung reicht als Schwellenwert-Basis.
    """
    return max(1, len(re.findall(r"\S+", text)))
