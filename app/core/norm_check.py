"""
norm_check.py – Deterministische Post-Generation-Prüfung harter Fakten.

Halluzinations-Guardrail in zwei Stufen (beide ohne LLM-Call):

1. NORMBEZEICHNUNGEN: LLMs verfälschen gern Ziffern und Ausgabedaten von Normen
   (aus "DIN 3990-11" wird "DIN 3991-11", aus ":1995-11" wird ":2015-11"). Jede
   Bezeichnung (DIN/ISO/VDI/…) aus dem Antworttext muss in den Referenztexten
   vorkommen (Chunk-Texte, Dokumenttitel – Titel tragen Nummer + Ausgabedatum,
   z.B. "DIN 3991-4_2025-10-00_DE_….pdf" – sowie CAD-Bauteildaten).

2. KENNZAHLEN (Zahl + Einheit, z.B. "Ra < 0,8 µm", "50 mm", "20°"): LLMs schieben
   dem Bauteil gern Beispielwerte aus Quellen unter oder erfinden Messwerte. Jede
   Kennzahl der Antwort muss numerisch in den Referenztexten belegt sein. Verglichen
   wird der ZAHLENWERT (Komma/Punkt-tolerant) mit Rundung auf die in der Antwort
   angezeigte Präzision – so ist "25,4 mm" durch den CAD-Wert 25.399 gedeckt.
   Bewusst NUR Zahl+Einheit-Paare: nackte Zahlen (Listennummern, Zähnezahlen,
   "Qualität 7") würden zu viele Fehlalarme erzeugen.

Unbelegte Angaben werden MARKIERT, nicht entfernt: Entfernen zerstört den Satzbau
und kaschiert das Problem – die Markierung macht es prüfbar.
"""

from __future__ import annotations

import re

# Normbezeichnung: Präfix + Nummernkern (inkl. Teil "3991-4") + optional "Blatt 9.1"
# + optionales Ausgabedatum (":2025-10", ":1995"). Längere Präfixe zuerst, damit
# "DIN EN ISO 4287" nicht als "DIN 4287" zerfällt.
_NORM_RE = re.compile(
    r"\b(DIN\s+EN\s+ISO|DIN\s+ISO|DIN\s+EN|VDI[/-]VDE|DIN|ISO|VDI|AGMA|ANSI)"
    r"\s*(\d{2,6}(?:\s*[-–]\s*\d{1,3})?)"
    r"((?:\s+Blatt\s+\d+(?:\.\d+)?)?)"
    r"(?:\s*:\s*(\d{4}(?:-\d{2})?))?",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Vergleichsform: Großschreibung, Unterstriche→Leerzeichen (Dateititel!),
    Gedankenstrich→Bindestrich, Whitespace kollabiert."""
    text = (text or "").upper().replace("_", " ").replace("–", "-")
    return re.sub(r"\s+", " ", text)


def _canonical(prefix: str, number: str, blatt: str) -> str:
    """Kanonische Bezeichnung für Vergleich UND Anzeige, z.B. "VDI 3720 BLATT 9.1"."""
    prefix = re.sub(r"\s+", " ", prefix.upper().strip())
    number = re.sub(r"\s*[-–]\s*", "-", number.strip())
    blatt = re.sub(r"\s+", " ", blatt.upper().strip())
    return " ".join(p for p in (prefix, number, blatt) if p)


def find_unsupported_norm_references(answer_text: str, reference_texts: list[str]) -> list[str]:
    """
    Liefert alle Normbezeichnungen aus answer_text, die NICHT in den Referenztexten
    (Chunk-Texte + Dokumenttitel) vorkommen – dedupliziert, in Fundreihenfolge.
    Zwei Prüfstufen je Fund:
      1. Bezeichnungskern ("DIN 3991-4"): fehlt er → komplett unbelegt.
      2. Ausgabedatum (":2025-10"): Kern belegt, aber Datum nirgends → Datum unbelegt
         (typische Halluzination: echte Norm, erfundenes Jahr).
    """
    reference = _normalize("\n".join(reference_texts))
    unsupported: list[str] = []
    seen: set[str] = set()

    for m in _NORM_RE.finditer(answer_text or ""):
        prefix, number, blatt, date = m.group(1), m.group(2), m.group(3), m.group(4)
        core = _canonical(prefix, number, blatt)
        if core in seen:
            continue
        seen.add(core)

        if core not in reference:
            shown = core.title().replace("Din", "DIN").replace("Iso", "ISO").replace(
                "Vdi", "VDI").replace("Agma", "AGMA").replace("Ansi", "ANSI")
            unsupported.append(shown)
        elif date and date not in reference:
            unsupported.append(f"Ausgabedatum {date} zu {core}")

    return unsupported


# ---------------------------------------------------------------------------
# Stufe 2: Kennzahlen (Zahl + Einheit)
# ---------------------------------------------------------------------------

# Einheiten der Domäne, LÄNGSTE zuerst (sonst frisst "m" das "mm" weg).
_UNIT = (
    r"(?:N/mm²|N/mm2|mm²|mm2|mm³|mm3|µm|μm|Mikrometer|Millimeter|Zentimeter|Meter|"
    r"m/min|mm/min|m/s|U/min|1/min|min⁻¹|°C|MPa|GPa|kNm|kN|Nm|HRC|HV|HB|kW|kHz|Hz|"
    r"dB|kg|mm|cm|dm|km|Grad|Prozent|[%°]|N|W|g|m|s|min|h)"
)

# Kennzahl: optionaler Vergleicher/Toleranz + Zahl + Einheit (Wortgrenze danach).
_MEASURE_RE = re.compile(
    r"(?:[<>≤≥≈±]|ca\.|etwa|bis)?\s*"
    r"(\d+(?:[.,]\d+)?)"
    r"\s*(" + _UNIT + r")(?![\w²³/])",
)

# Zahl-Tokens in Referenztexten (Chunk-Texte, CAD-JSON, Titel, Frage).
_REF_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _parse_variants(token: str) -> list[float]:
    """
    Zahlen-Token → mögliche Werte. Deutsche UND englische Dezimalschreibweise werden
    akzeptiert; bei exakt 3 Nachkommastellen zusätzlich die Tausender-Lesart
    ("1.000" kann 1.0 oder 1000 bedeuten – beide Deutungen zählen als Beleg).
    """
    normalized = token.replace(",", ".")
    try:
        values = [float(normalized)]
    except ValueError:
        return []
    parts = re.split(r"[.,]", token)
    if len(parts) == 2 and len(parts[1]) == 3:  # Tausender-Ambiguität
        values.append(float(parts[0] + parts[1]))
    return values


def _reference_values(reference_texts: list[str]) -> list[float]:
    """Alle Zahlenwerte der Referenztexte (inkl. Schreibweisen-Varianten)."""
    values: list[float] = []
    for text in reference_texts:
        for token in _REF_NUMBER_RE.findall(text or ""):
            values.extend(_parse_variants(token))
    return values


def _is_supported_value(token: str, reference_values: list[float]) -> bool:
    """
    True, wenn irgendein Referenzwert auf die in der Antwort ANGEZEIGTE Präzision
    gerundet den Antwortwert ergibt (z.B. Referenz 25.399 deckt "25,4" und "25").
    """
    decimals = len(token.split(",")[-1].split(".")[-1]) if ("," in token or "." in token) else 0
    tolerance = 0.5 * 10 ** (-decimals) + 1e-9
    for claim in _parse_variants(token):
        if any(abs(ref - claim) <= tolerance for ref in reference_values):
            return True
    return False


def find_unsupported_measurements(answer_text: str, reference_texts: list[str]) -> list[str]:
    """
    Liefert alle Kennzahlen (Zahl+Einheit) aus answer_text, deren Zahlenwert in
    KEINEM Referenztext vorkommt – dedupliziert, in Fundreihenfolge, formatiert
    als 'Kennzahl „0,8 µm"'. Normbezeichnungen werden vorab entfernt, damit deren
    Ziffern (z.B. "DIN 3965:2023-04") nicht fälschlich als Messwerte gelten.
    """
    text = _NORM_RE.sub(" ", answer_text or "")
    reference_values = _reference_values(reference_texts)
    unsupported: list[str] = []
    seen: set[str] = set()

    for m in _MEASURE_RE.finditer(text):
        token, unit = m.group(1), m.group(2)
        key = f"{token} {unit}"
        if key in seen:
            continue
        seen.add(key)
        if not _is_supported_value(token, reference_values):
            unsupported.append(f"Kennzahl „{key}“")
    return unsupported


def norm_warning_footnote(unsupported: list[str]) -> str:
    """Fußnote für das Antwortende – markiert unbelegte Angaben, statt sie zu löschen."""
    return (
        "⚠️ *Ohne Beleg in den abgerufenen Quellen/Bauteildaten (bitte vor Verwendung prüfen): "
        + "; ".join(unsupported) + ".*"
    )
