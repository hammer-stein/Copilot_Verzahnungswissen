"""
cad_terms.py – Deutsche Suchbegriffe je CAD-Zahnradtyp für CAD-bewusstes Retrieval.

Hintergrund: Der HybridRetriever suchte ursprünglich NUR mit der Nutzerfrage; das
CAD-JSON floss erst in der Antwortstufe ein. Folge: Bei geladenem Bauteil trafen
Fragen wie „welches Verfahren eignet sich zur Herstellung?" thematisch passende,
aber bauteilfremde Chunks (z. B. Mikrozahnrad-Verfahren statt Kegelrad-Fertigung).

Lösung: Ist ein Bauteil geladen, reichert `_answer_one` (app/api/main.py) die
Retrieval-Query um die hier definierten Zahnradtyp-Begriffe an. Das schiebt die
dichte Einbettung in Richtung des Bauteiltyps und gibt dem lexikalischen
Sparse-Kanal exakte Treffer („Kegelrad", „Kegelradverzahnung"), sodass
bauteilspezifische Literatur vor generischen Treffern rankt. Die Anreicherung
betrifft ausschließlich die SUCHE – der Antwortstufe wird weiterhin die
Originalfrage übergeben, und Listen-/Aggregatfragen (Tabellen-Routing) bleiben
unangereichert (siehe HybridRetriever.retrieve).
"""

from __future__ import annotations

import re
from typing import Any, NamedTuple, Optional

# Deutsche Anzeige-Labels je gear_type (auch von den AnswerGenerators genutzt).
GEAR_TYPE_LABELS: dict[str, str] = {
    "spur": "Stirnrad (Geradverzahnung)", "helical": "Schrägverzahnung", "bevel": "Kegelrad",
    "internal": "Innenverzahnung", "worm": "Schnecke", "rack": "Zahnstange",
    "miter": "Gehrungsrad (Kegelrad, Übersetzung 1:1)", "crown": "Kronrad (Planrad)",
    "worm_wheel": "Schneckenrad", "ratchet": "Sperrrad (Ratsche)",
    # Ehrlicher Unknown-Pfad des cad_processor (keine Zahn-Evidenz gefunden).
    # Bewusst NICHT in _TYPE_FAMILIES/_GEAR_TYPE_SEARCH_TERMS: ein unbekannter Typ
    # löst weder Typ-Abgleich/follow_cad noch Retrieval-Anreicherung aus.
    "unknown": "Unbekannt (Verzahnungstyp nicht sicher bestimmbar)",
}

# Schlüssel = gear_type aus dem GearParameters-JSON des cad_processor
# (cad_processor/src/gear_hints.py: GEAR_KNOWLEDGE). Werte = deutsche
# Synonyme/Fachbegriffe, wie sie in Normen und Fachliteratur vorkommen.
_GEAR_TYPE_SEARCH_TERMS: dict[str, str] = {
    "spur": "Stirnrad Stirnradverzahnung Geradverzahnung",
    "helical": "Schrägverzahnung Schrägstirnrad schrägverzahntes Stirnrad",
    "bevel": "Kegelrad Kegelradverzahnung Kegelverzahnung",
    "miter": "Kegelrad Gehrungsrad Kegelradverzahnung",
    "crown": "Kronrad Planrad Kronenrad Planverzahnung",
    "worm": "Schnecke Schneckengetriebe Schneckenverzahnung",
    "worm_wheel": "Schneckenrad Schneckengetriebe Schneckenverzahnung",
    "internal": "Innenverzahnung Hohlrad innenverzahntes Zahnrad",
    "rack": "Zahnstange Zahnstangenverzahnung",
    "ratchet": "Sperrrad Ratsche Sperrverzahnung Klinke",
}


def cad_gear_type(cad: dict[str, Any]) -> Optional[str]:
    """Entpackt den gear_type aus dem GearParameters-JSON ({"value": …} oder roher String)."""
    if not cad:
        return None
    gear_type = cad.get("gear_type")
    if isinstance(gear_type, dict):  # GearParameters-Format {"value": ..., "confidence": ...}
        gear_type = gear_type.get("value")
    if not gear_type:
        return None
    return str(gear_type).strip().casefold() or None


def cad_retrieval_terms(cad: dict[str, Any]) -> str:
    """
    Liefert die deutschen Suchbegriffe zum Zahnradtyp des geladenen Bauteils –
    oder "" (keine Anreicherung), wenn kein Bauteil geladen ist oder der Typ
    unbekannt ist. Bewusst konservativ: lieber keine Anreicherung als eine falsche.
    """
    gear_type = cad_gear_type(cad)
    return _GEAR_TYPE_SEARCH_TERMS.get(gear_type, "") if gear_type else ""


# ---------------------------------------------------------------------------
# Typ-Abgleich Frage ↔ CAD-Bauteil
# ---------------------------------------------------------------------------
# Problem aus der Praxis: Die Frage sagt „das hochgeladene Kegelrad", das geladene
# Bauteil ist laut CAD-Analyse aber ein Sperrrad – die Antwort behandelt dann
# unbemerkt die falsche Bauteilklasse. Der Abgleich ist deterministisch (kein LLM):
# In der Frage genannte Zahnradtypen werden erkannt und gegen den CAD-Typ geprüft;
# bei Widerspruch wird der Antwort eine klar sichtbare Warnung vorangestellt.

# Verwandte Typen bilden eine Familie – „Stirnrad" deckt auch Schrägverzahnung ab,
# „Kegelrad" auch Gehrungsräder. Nur ein Familien-Unterschied gilt als Widerspruch.
_TYPE_FAMILIES: dict[str, str] = {
    "bevel": "kegel", "miter": "kegel", "spiral_bevel": "kegel",
    "spur": "stirn", "helical": "stirn", "herringbone": "stirn",
    "worm": "schnecke", "worm_wheel": "schnecke",
    "internal": "innen", "rack": "zahnstange", "crown": "kron", "ratchet": "sperr",
}

# Deutsche Typ-Nennungen in der Frage → kanonischer gear_type.
_QUESTION_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("bevel", re.compile(r"kegelr[aä]d|kegelverzahn|gehrungsrad", re.IGNORECASE)),
    ("spur", re.compile(r"stirnr[aä]d|geradverzahn", re.IGNORECASE)),
    ("helical", re.compile(r"schr[äa]gverzahn|schr[äa]gstirnrad", re.IGNORECASE)),
    ("worm", re.compile(r"schneckenrad|schneckengetriebe|\bschnecke\b", re.IGNORECASE)),
    ("internal", re.compile(r"innenverzahn|hohlrad", re.IGNORECASE)),
    ("rack", re.compile(r"zahnstange", re.IGNORECASE)),
    ("crown", re.compile(r"kronrad|kronenrad|planrad", re.IGNORECASE)),
    ("ratchet", re.compile(r"sperr\w*rad|ratsche|sperrklinke|sperrverzahn", re.IGNORECASE)),
]


def question_gear_families(question: str) -> set[str]:
    """Alle in der Frage genannten Zahnradtyp-Familien (leer = kein Typ genannt)."""
    q = question or ""
    return {
        _TYPE_FAMILIES[canonical]
        for canonical, pattern in _QUESTION_TYPE_PATTERNS
        if pattern.search(q)
    }


def question_retrieval_terms(question: str) -> str:
    """
    Suchbegriffe zu den in der FRAGE genannten Zahnradtypen. Nennt die Frage explizit
    einen Typ ("das Kegelrad herstellen"), hat diese Nutzerabsicht Vorrang vor dem
    CAD-Typ des geladenen Bauteils – angereichert wird dann mit den Begriffen des
    GENANNTEN Typs (nicht mit den CAD-Begriffen, die bei einer Typ-Verwechslung die
    Suche verfälschen würden).
    """
    q = question or ""
    terms: list[str] = []
    seen: set[str] = set()
    for canonical, pattern in _QUESTION_TYPE_PATTERNS:
        if pattern.search(q):
            for word in _GEAR_TYPE_SEARCH_TERMS.get(canonical, "").split():
                if word not in seen:
                    seen.add(word)
                    terms.append(word)
    return " ".join(terms)


class TypeMismatch(NamedTuple):
    """Ergebnis des Typ-Abgleichs Frage ↔ CAD (nur bei tatsächlichem Widerspruch)."""
    severity: str                 # "soft" (Warnung, Antwort wie gefragt) | "hard" (mode greift)
    cad_type: str                 # kanonischer gear_type des Bauteils (z.B. "ratchet")
    cad_label: str                # deutsches Label (z.B. "Sperrrad (Ratsche)")
    confidence: Optional[float]   # CAD-Konfidenz 0–1 (None = nicht angegeben)


def _confidence_suffix(confidence: Optional[float]) -> str:
    return f", Konfidenz {round(confidence * 100)} %" if confidence is not None else ""


def assess_type_mismatch(
    question: str,
    cad: dict[str, Any],
    *,
    low_confidence: float = 0.5,
    high_confidence: float = 0.85,
) -> Optional[TypeMismatch]:
    """
    Deterministischer, konfidenz-gestufter Typ-Abgleich. None = kein Handlungsbedarf
    (kein Typ genannt, Typen passen zusammen, oder CAD-Konfidenz < low_confidence –
    ein unsicherer CAD-Typ darf der expliziten Frage nicht widersprechen).
    severity "hard" NUR bei Konfidenz ≥ high_confidence: Eine Verhaltensänderung
    (Rückfrage / CAD-Typ-Antwort) braucht eine belastbare Messung; fehlt die
    Konfidenz-Angabe, wird konservativ "soft" eingestuft.
    """
    families = question_gear_families(question)
    if not families:
        return None  # Frage nennt keinen Typ → nichts abzugleichen
    ctype = cad_gear_type(cad)
    if not ctype or _TYPE_FAMILIES.get(ctype) is None:
        return None  # kein Bauteil / unbekannter Typ → kein belastbarer Abgleich
    if _TYPE_FAMILIES[ctype] in families:
        return None  # Frage und Bauteil passen zusammen

    confidence: Optional[float] = None
    raw = (cad or {}).get("gear_type")
    if isinstance(raw, dict) and isinstance(raw.get("confidence"), (int, float)):
        confidence = float(raw["confidence"])

    if confidence is not None and confidence < low_confidence:
        return None
    severity = "hard" if confidence is not None and confidence >= high_confidence else "soft"
    return TypeMismatch(
        severity=severity,
        cad_type=ctype,
        cad_label=GEAR_TYPE_LABELS.get(ctype, ctype),
        confidence=confidence,
    )


def mismatch_warn_note(mismatch: TypeMismatch) -> str:
    """Warnhinweis (soft): Antwort folgt der Frage, aber der Widerspruch wird sichtbar gemacht."""
    return (
        f"⚠️ **Bauteil-Abgleich:** Die Frage nennt einen anderen Zahnradtyp, das geladene "
        f"Bauteil ist laut CAD-Analyse jedoch ein **{mismatch.cad_label}** "
        f"[CAD]{_confidence_suffix(mismatch.confidence)}. "
        f"Bitte prüfen, ob das richtige Bauteil geladen ist – die folgende Antwort "
        f"behandelt die Frage, wie sie gestellt wurde."
    )


def mismatch_followed_cad_note(mismatch: TypeMismatch) -> str:
    """Hinweis (hard, mode=follow_cad): Die Antwort wurde bewusst für den CAD-Typ erstellt."""
    return (
        f"⚠️ **Bauteil-Abgleich:** Die Frage nennt einen anderen Zahnradtyp – die Antwort "
        f"wurde für das TATSÄCHLICH geladene Bauteil erstellt: ein **{mismatch.cad_label}** "
        f"[CAD]{_confidence_suffix(mismatch.confidence)}. Falls doch der in der Frage "
        f"genannte Typ gemeint ist, bitte das geladene Bauteil entfernen und erneut fragen."
    )


def mismatch_ask_back_answer(mismatch: TypeMismatch) -> str:
    """
    Rückfrage (hard, mode=ask_back) STATT einer Sachantwort. Anfragen sind zustandslos,
    daher bittet die Rückfrage um eine präzisierte Neu-Eingabe.
    """
    return (
        f"❓ **Rückfrage statt Antwort:** Das geladene Bauteil ist laut CAD-Analyse ein "
        f"**{mismatch.cad_label}** [CAD]{_confidence_suffix(mismatch.confidence)} – die Frage "
        f"nennt jedoch einen anderen Zahnradtyp. Für welchen Typ soll die Antwort erstellt "
        f"werden?\n\n"
        f"- **Geladenes Bauteil ({mismatch.cad_label}):** Frage erneut stellen und den Typ "
        f"aus der Frage weglassen oder durch „{mismatch.cad_label}“ ersetzen.\n"
        f"- **Der in der Frage genannte Typ:** Das geladene Bauteil entfernen (oder das "
        f"passende Bauteil laden) und die Frage erneut stellen."
    )


def type_focus_directive(mismatch: TypeMismatch) -> str:
    """
    Direktive für den AUSGABEFORMAT-Slot des Generators (hard, mode=follow_cad):
    zwingt den Fließtext terminologisch auf den CAD-Typ, damit die Antwort dem
    vorangestellten Bauteil-Abgleich-Hinweis nicht widerspricht.
    """
    label = mismatch.cad_label
    return (
        f"WICHTIG – Bauteil-Fokus: Das geladene Bauteil ist ein {label}, NICHT der in der "
        f"Frage genannte Zahnradtyp. Beantworte die Frage für das {label}: Sprich im gesamten "
        f"Text vom {label} (nie vom Typ aus der Frage) und übernimm aus den Wissensauszügen "
        f"nur Aussagen, die für ein {label} technisch überhaupt gelten. Tragen die Auszüge "
        f"für ein {label} nichts, sage das klar."
    )


def build_type_mismatch_note(question: str, cad: dict[str, Any]) -> Optional[str]:
    """
    Abwärtskompatibler Wrapper (mit Default-Schwellen): Warnhinweis-Text oder None.
    Neue Aufrufer nutzen assess_type_mismatch() + die Textbausteine direkt.
    """
    mismatch = assess_type_mismatch(question, cad)
    return mismatch_warn_note(mismatch) if mismatch else None


# ---------------------------------------------------------------------------
# Toleranz-Plausibilität Frage ↔ CAD-Bauteil (deterministischer Guardrail)
# ---------------------------------------------------------------------------
# Real beobachtet: Frage nennt "Toleranz 5 mm", das geladene Bauteil ist ein
# Mikro-Zahnrad (Modul 0,26 mm). Eine solche Toleranz übersteigt die gesamte
# Zahnprofilgröße – das LLM erkennt das nicht und leitet daraus grobe Verfahren
# ab. Bezugsgröße ist der MODUL (nicht der Teilkreis): Er skaliert das Zahnprofil
# (Zahnhöhe ≈ 2,25·m nach DIN 867, Zahndicke ≈ 1,57·m). Einordnung der Schwellen:
# Verzahnungsabweichungen liegen selbst in den gröbsten genormten Qualitäten
# (DIN 3961/3962, ISO 1328) deutlich unter ~0,2·m; ab ~0,3·m ist keine
# Verzahnungsqualität mehr darstellbar, ab 1,0·m ist das Profil zerstört.
# Der Guardrail MARKIERT nur (Fußnote + Trace) – die Antwort wird nie unterdrückt.

# Toleranzangaben NUR mit explizitem Signal (Toleranz/Genauigkeit/±/"auf X genau"),
# damit nackte Maßangaben ("Zahnbreite 5 mm") keine Fehlalarme erzeugen.
_TOLERANCE_RE = re.compile(
    r"(?:toleranz(?:\s+von)?|toleriert(?:\s+auf)?|genauigkeit(?:\s+von)?|±|\+/-)\s*"
    r"(\d+(?:[.,]\d+)?)\s*(mm|µm|μm|mikrometern?)"
    r"|auf\s+(\d+(?:[.,]\d+)?)\s*(mm|µm|μm|mikrometern?)\s+genau",
    re.IGNORECASE,
)

TOLERANCE_UNREALISTIC_FACTOR = 1.0   # t ≥ 1,0·m → Profil zerstört
TOLERANCE_BORDERLINE_FACTOR = 0.3    # t ≥ 0,3·m → außerhalb genormter Qualitäten


class ToleranceFinding(NamedTuple):
    """Befund der Toleranz-Plausibilitätsprüfung (nur bei auffälliger Angabe)."""
    severity: str        # "unrealistic" | "borderline"
    quoted: str          # Angabe wie in der Frage genannt, z.B. "5 mm"
    tolerance_mm: float
    module_mm: float


def _extract_tolerances_mm(question: str) -> list[tuple[float, str]]:
    """Alle explizit als Toleranz/Genauigkeit erkennbaren Angaben, in mm normalisiert."""
    found: list[tuple[float, str]] = []
    for m in _TOLERANCE_RE.finditer(question or ""):
        number, unit = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        value = float(number.replace(",", "."))
        if unit.lower() not in ("mm",):
            value /= 1000.0  # µm → mm
        found.append((value, f"{number} {unit}"))
    return found


def assess_tolerance_plausibility(question: str, cad: dict[str, Any]) -> Optional[ToleranceFinding]:
    """
    Prüft in der Frage genannte Toleranzangaben gegen den Modul des geladenen
    Bauteils. None = kein Befund (keine Toleranz genannt, kein Bauteil/Modul,
    oder Angabe plausibel) – der Normalfall, bewusst fehlalarmfrei.
    Bei mehreren Angaben wird die größte (kritischste) bewertet.
    """
    tolerances = _extract_tolerances_mm(question)
    if not tolerances:
        return None
    tp = (cad or {}).get("tooth_profile") or {}
    module = tp.get("module_mm")
    if isinstance(module, dict):
        module = module.get("value")
    try:
        module_mm = float(module)
    except (TypeError, ValueError):
        return None
    if module_mm <= 0:
        return None

    tolerance_mm, quoted = max(tolerances, key=lambda t: t[0])
    ratio = tolerance_mm / module_mm
    if ratio >= TOLERANCE_UNREALISTIC_FACTOR:
        severity = "unrealistic"
    elif ratio >= TOLERANCE_BORDERLINE_FACTOR:
        severity = "borderline"
    else:
        return None
    return ToleranceFinding(severity=severity, quoted=quoted,
                            tolerance_mm=tolerance_mm, module_mm=module_mm)


def tolerance_note(finding: ToleranceFinding) -> str:
    """Fußnote im Stil der übrigen Guardrails – markiert, überschreibt nicht."""
    module = finding.module_mm
    if finding.severity == "unrealistic":
        return (
            f"⚠️ **Toleranz-Plausibilität:** Die genannte Toleranz ({finding.quoted}) übersteigt "
            f"die Zahnprofilgröße des geladenen Bauteils (Modul {module:g} mm, Zahnhöhe "
            f"≈ {2.25 * module:.2f} mm) – an dieser Verzahnung ist eine solche Toleranz "
            f"fertigungstechnisch nicht sinnvoll. Bitte Toleranzangabe prüfen; die Antwort "
            f"oben bewertet die Frage, wie sie gestellt wurde."
        )
    return (
        f"⚠️ **Toleranz-Plausibilität:** Die genannte Toleranz ({finding.quoted}) ist sehr grob "
        f"für dieses Bauteil (Modul {module:g} mm) – sie liegt außerhalb genormter "
        f"Verzahnungsqualitäten (DIN 3961/ISO 1328). Bitte Toleranzangabe prüfen."
    )
