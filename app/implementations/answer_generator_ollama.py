
"""
answer_generator_ollama.py – LLM-basierte Antwortgenerierung via Ollama.

Implementiert das AnswerGenerator-Protokoll. Baut aus Frage, Retriever-Chunks und
CAD-Metadaten einen strukturierten Prompt und lässt das LLM eine quellenverweisende
Antwort generieren – ausschließlich auf Basis der übergebenen Chunks (kein Halluzinieren).
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Callable, Optional

from app.core.cad_terms import GEAR_TYPE_LABELS
from app.core.types import Answer, AnswerSource, RetrievedChunk
from app.core.utils import stable_json_dumps
from app.implementations.ollama_client import OllamaClient
from app.implementations.table_qa import maybe_answer_table_filter_question

ProgressCallback = Callable[[str], None]

# Deutsche Bezeichner + Einheiten für die GearParameters-Felder (Format: cad_processor/src/output_schema.py).
# Das LLM (insb. kleine Modelle) kann deutsche Fragebegriffe sonst nicht auf die englischen,
# verschachtelten JSON-Schlüssel abbilden – daher wird das CAD-JSON in einen lesbaren Block übersetzt.
# Deutsche Anzeige-Labels je gear_type – zentral in app/core/cad_terms.py definiert
# (dort auch vom Typ-Abgleich Frage↔CAD genutzt).
_GEAR_TYPE_LABELS = GEAR_TYPE_LABELS
# (Sektion, Schlüssel) -> (deutsches Label, Einheit)
_CAD_FIELD_LABELS: dict[tuple[str, str], tuple[str, str]] = {
    ("tooth_profile", "num_teeth"): ("Zähnezahl", ""),
    ("tooth_profile", "module_mm"): ("Modul", "mm"),
    ("tooth_profile", "helix_angle_deg"): ("Schrägungswinkel", "°"),
    ("tooth_profile", "pressure_angle_deg"): ("Eingriffswinkel", "°"),
    ("tooth_profile", "profile_shift_x"): ("Profilverschiebung x", ""),
    ("tooth_profile", "tooth_height_mm"): ("Zahnhöhe", "mm"),
    ("tooth_profile", "addendum_mm"): ("Kopfhöhe", "mm"),
    ("tooth_profile", "dedendum_mm"): ("Fußhöhe", "mm"),
    ("tooth_profile", "tooth_thickness_mm"): ("Zahndicke am Teilkreis", "mm"),
    ("tooth_profile", "root_fillet_radius_mm"): ("Fußrundungsradius", "mm"),
    ("basic_geometry", "pitch_diameter_mm"): ("Teilkreisdurchmesser", "mm"),
    ("basic_geometry", "outer_diameter_mm"): ("Kopfkreisdurchmesser", "mm"),
    ("basic_geometry", "root_diameter_mm"): ("Fußkreisdurchmesser", "mm"),
    ("basic_geometry", "face_width_mm"): ("Zahnbreite", "mm"),
    ("basic_geometry", "total_width_mm"): ("Gesamtbreite", "mm"),
    ("basic_geometry", "hub_bore_diameter_mm"): ("Nabenbohrung", "mm"),
    ("topology", "cone_angle_deg"): ("Konuswinkel", "°"),
    ("topology", "shaft_angle_deg"): ("Achswinkel", "°"),
    ("topology", "worm_starts"): ("Schneckengänge", ""),
    ("material_context", "material"): ("Werkstoff", ""),
    ("material_context", "mass_kg"): ("Masse", "kg"),
    ("material_context", "quality_class_din"): ("DIN-Qualitätsklasse (ISO 1328)", ""),
    ("material_context", "tolerance_class"): ("Toleranzklasse", ""),
    ("material_context", "bore_fit"): ("Bohrungspassung", ""),
    ("material_context", "surface_roughness_ra"): ("Oberflächenrauheit Ra", "µm"),
    ("metadata", "part_name"): ("Teilename", ""),
    ("metadata", "part_number"): ("Teilenummer", ""),
}


def _cad_value(value: Any) -> Any:
    """Entpackt GearParameters-Werte im Format {"value": ..., "unit": ..., "confidence": ...}."""
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def _fmt_value(value: Any, unit: str) -> Optional[str]:
    """Formatiert einen Wert; gibt None für leere/uninteressante Werte zurück (überspringen)."""
    if isinstance(value, dict) and "value" in value:
        unit = unit or str(value.get("unit") or "")
        value = value.get("value")
    if value is None or value == "" or value == []:
        return None
    if isinstance(value, bool):
        return "ja" if value else "nein"
    if isinstance(value, list):
        return ", ".join(str(_cad_value(v)) for v in value)
    if unit:
        return f"{value} {unit}"
    return str(value)


def _cad_summary_sentence(cad: dict[str, Any]) -> str:
    """
    Ein natürlicher Identifikationssatz für das Bauteil. Hilft kleinen LLMs, generische
    Fragen wie „Um welches Zahnrad handelt es sich?" direkt zu beantworten, statt nur
    eine Parameterliste vorzufinden, die sie nicht mit der Frage verknüpfen.
    """
    gt = _cad_value(cad.get("gear_type"))
    typ = _GEAR_TYPE_LABELS.get(gt, gt) if gt else "Zahnrad"
    tp = cad.get("tooth_profile") or {}
    mc = cad.get("material_context") or {}
    meta = cad.get("metadata") or {}

    parts: list[str] = []
    if tp.get("module_mm") is not None:
        parts.append(f"Modul {_fmt_value(tp['module_mm'], 'mm')}")
    if tp.get("num_teeth") is not None:
        parts.append(f"{_fmt_value(tp['num_teeth'], '')} Zähnen")
    helix_angle = _cad_value(tp.get("helix_angle_deg"))
    if helix_angle:
        parts.append(f"Schrägungswinkel {_fmt_value(tp['helix_angle_deg'], '°')}")
    if mc.get("material"):
        parts.append(f"Werkstoff {_fmt_value(mc['material'], '')}")

    # Direkt als Identifikation formuliert, damit auch generische Fragen wie
    # "Um welches Zahnrad handelt es sich?" direkt beantwortbar sind.
    sentence = f"CAD-Identifikation: Das aktuell geladene Bauteil ist eine {typ}" if gt else "CAD-Identifikation: Das aktuell geladene Bauteil ist ein Zahnrad"
    if parts:
        sentence += " mit " + ", ".join(parts)
    name = _cad_value(meta.get("part_name"))
    if name:
        sentence += f" (Teilename „{name}“)"
    return sentence + "."


def cad_to_readable(cad: dict[str, Any]) -> str:
    """
    Übersetzt das verschachtelte GearParameters-JSON in einen deutsch beschrifteten
    Klartext-Block: zuerst ein Identifikationssatz, dann "Label: Wert Einheit"-Zeilen.
    So kann das LLM die Bauteildaten zuverlässig als Wissensquelle nutzen.
    Leere/None-Felder werden weggelassen.
    """
    if not cad:
        return "(Kein Bauteil geladen.)"

    lines: list[str] = [
        "CAD-Bauteildaten haben Vorrang für Fragen zum aktuell geladenen Bauteil.",
        _cad_summary_sentence(cad),
        "",
    ]
    gt = _cad_value(cad.get("gear_type"))
    if gt:
        lines.append(f"- Verzahnungstyp: {_GEAR_TYPE_LABELS.get(gt, gt)}")
    if cad.get("topology", {}).get("is_internal_gear"):
        lines.append("- Innenverzahnung: ja")

    for (section, key), (label, unit) in _CAD_FIELD_LABELS.items():
        raw = (cad.get(section) or {}).get(key)
        formatted = _fmt_value(raw, unit)
        if formatted is not None:
            lines.append(f"- {label}: {formatted}")

    norms = (cad.get("material_context") or {}).get("norm_reference")
    if norms:
        lines.append(f"- Normreferenzen: {', '.join(str(n) for n in norms)}")

    return "\n".join(lines) if lines else "(Bauteildaten ohne auswertbare Parameter.)"


def cad_to_prompt_context(cad: dict[str, Any]) -> str:
    """
    Liefert zuerst eine deutsch beschriftete Lesefassung und danach das vollständige
    CAD-JSON. Die Lesefassung hilft bei deutschen Fragen; das Roh-JSON verhindert,
    dass seltenere CAD-Felder aus dem Kontext herausfallen.
    """
    if not cad:
        return "(Kein Bauteil geladen.)"
    return "\n".join((
        "Lesefassung:",
        cad_to_readable(cad),
        "",
        "Vollständiges CAD-JSON:",
        stable_json_dumps(cad),
    ))

# Übersetzt die Format-Auswahl aus dem Frontend in eine konkrete LLM-Anweisung,
# die unter "AUSGABEFORMAT" in den Prompt eingesetzt wird.
FORMAT_INSTRUCTIONS: dict[str, str] = {
    "kurz": "Antworte knapp und präzise in 2–3 Sätzen. Nur das Wesentliche, keine Zwischenüberschriften.",
    "standard": "Strukturierter Fließtext mit kurzen Absätzen, ca. 150–200 Wörter.",
    "ausführlich": "Ausführliche Antwort mit Zwischenüberschriften und Begründungen, ca. 300–400 Wörter.",
    "stichpunkte": "Antworte als kompakte Stichpunktliste: ein Aspekt pro Zeile, jede Zeile beginnt mit '- '.",
    "tabellarisch": "Stelle die Antwort, wo sinnvoll, als Markdown-Tabelle dar; ergänze nur knappe Erläuterungen.",
}
DEFAULT_FORMAT = "standard"

# Ohne Retriever-Treffer: neutraler Marker statt negativer Formulierung. Negative Sätze
# ("keine Treffer gefunden") treiben kleine LLMs unnötig in die Verweigerung, und ohne diesen
# Zusatz kommentieren sie den leeren Block mit einer sinnlosen [Q1]-Markierung.
NO_CHUNKS_NOTICE = (
    "Derzeit liegen keine Wissensauszüge vor. Beantworte die Frage allein aus den "
    "BAUTEILDATEN und verwende KEINE [Q]-Markierungen."
)

_CAD_IDENTITY_PATTERNS = (
    r"\bum welches\s+zahnrad\b",
    r"\bwelches\s+zahnrad\b",
    r"\bwas\s+ist\s+das\s+f[uü]r\s+ein\s+zahnrad\b",
    r"\bzahnradtyp\b",
    r"\bverzahnungstyp\b",
    r"\bbauteiltyp\b",
)


# Empfehlungs-Fragen ("welches Verfahren eignet sich am besten?") verlangen eine klare
# Festlegung statt einer Aufzählung von Möglichkeiten. Kleine LLMs befolgen Regeln aus der
# Mitte des Prompts unzuverlässig – deshalb wird diese Direktive zusätzlich deterministisch
# in den AUSGABEFORMAT-Slot injiziert (letzter Abschnitt vor "ANTWORT:" = höchste Befolgung).
_RECOMMENDATION_RE = re.compile(
    r"\b("
    r"eignet|geeignet\w*|eignung|empfehl\w*|empfiehl\w*|am besten|besser geeignet|"
    r"welches verfahren|welche methode|welcher prozess|was sollte|sollte? (ich|man|wir)|"
    r"auswähl\w*|auswahl|bevorzug\w*|optimal\w*|sinnvollst\w*"
    r")\b",
    re.IGNORECASE,
)

RECOMMENDATION_DIRECTIVE = (
    "WICHTIG – die Frage verlangt eine Empfehlung: Der ALLERERSTE Satz der Antwort beginnt "
    "wörtlich mit \"Empfehlung:\" und nennt die klare Wahl. Danach folgt die Begründung mit den "
    "konkreten Zahlenwerten des geladenen Bauteils aus den BAUTEILDATEN, danach knapp die "
    "nachrangigen Alternativen mit dem Grund ihrer Nachrangigkeit. Hänge an jede Aussage aus "
    "einem Wissensauszug dessen Quellenmarkierung an – Beispiel: \"Für einsatzgehärtete "
    "Kegelräder wird Schleifen empfohlen [Q1].\" Verboten: Füllfloskeln wie \"es ist wichtig "
    "zu beachten\" oder \"es ist ratsam\" sowie eine eigene Quellenliste am Ende "
    "(die Quellen zeigt die Oberfläche separat an)."
)


def is_recommendation_query(question: str) -> bool:
    """True, wenn die Frage eine Auswahl/Eignung/Empfehlung verlangt (statt reiner Fakten)."""
    return bool(_RECOMMENDATION_RE.search(question or ""))


def resolve_format_instruction(answer_format: Optional[str], question: Optional[str] = None) -> str:
    """
    Übersetzt die Format-Auswahl (kurz/standard/…) in die konkrete LLM-Anweisung; Fallback: standard.
    Wird eine question übergeben und ist sie eine Empfehlungsfrage, wird die
    RECOMMENDATION_DIRECTIVE angehängt – sie landet damit im AUSGABEFORMAT-Slot des Prompts.
    """
    instruction = FORMAT_INSTRUCTIONS.get(
        (answer_format or DEFAULT_FORMAT).strip().casefold(),
        FORMAT_INSTRUCTIONS[DEFAULT_FORMAT],
    )
    if question and is_recommendation_query(question):
        instruction = f"{instruction}\n{RECOMMENDATION_DIRECTIVE}"
    return instruction


# Kleine LLMs hängen trotz Verbots gern eine eigene "Quellen:"-Liste an die Antwort –
# redundant, da die Oberfläche die Quellen strukturiert anzeigt. Deterministisch entfernen.
_TRAILING_SOURCES_RE = re.compile(
    r"\n+\s*(Quellen|Quellenliste|Quellenangaben)\s*:?\s*\n(\s*([*\-•]|\[?Q?\d).*\n?)*\s*$",
    re.IGNORECASE,
)


def strip_self_source_list(answer_text: str) -> str:
    """Entfernt eine vom LLM selbst angehängte Quellenliste am Antwortende (Backstop)."""
    return _TRAILING_SOURCES_RE.sub("", answer_text or "").rstrip()


def maybe_answer_cad_identity_question(question: str, cad: dict[str, Any]) -> Optional[str]:
    """
    Deterministischer Fast-Path für CAD-Identifikationsfragen.
    Solche Fragen sollen den `gear_type` aus der STEP/CAD-Analyse verwenden und nicht erst
    durch einen langsamen LLM-Call oder allgemeine Wissensauszüge verwässert werden.
    """
    if not cad:
        return None
    q = (question or "").casefold()
    if not any(re.search(pattern, q) for pattern in _CAD_IDENTITY_PATTERNS):
        return None

    gt = _cad_value(cad.get("gear_type"))
    if not gt:
        return None

    label = _GEAR_TYPE_LABELS.get(gt, str(gt))
    tp = cad.get("tooth_profile") or {}
    geo = cad.get("basic_geometry") or {}
    mc = cad.get("material_context") or {}

    details: list[str] = []
    teeth = _fmt_value(tp.get("num_teeth"), "")
    module = _fmt_value(tp.get("module_mm"), "mm")
    pitch = _fmt_value(geo.get("pitch_diameter_mm"), "mm")
    material = _fmt_value(mc.get("material"), "")
    if teeth:
        details.append(f"{teeth} Zähnen")
    if module:
        details.append(f"Modul {module}")
    if pitch:
        details.append(f"Teilkreisdurchmesser {pitch}")
    if material:
        details.append(f"Werkstoff {material}")

    answer = f"Es handelt sich um ein {label}"
    if details:
        answer += " mit " + ", ".join(details)
    return answer + " [CAD]."


def _source_title(chunk_source_path: str, metadata: dict[str, Any]) -> str:
    """
    Liefert einen nutzerfreundlichen Dokumenttitel für Quellenangaben.
    Neu indexierte Dokumente tragen file_name in den Metadaten. Bei alten Indizes
    darf der technische storage/uploads/<timestamp>_<uuid>.pdf-Pfad nicht in die UI.
    """
    for key in ("title", "file_name", "document_title", "original_filename"):
        value = str((metadata or {}).get(key) or "").strip()
        if value:
            return value

    name = Path(chunk_source_path or "").name.strip()
    if not name:
        return "Unbenanntes Dokument"

    stem = Path(name).stem
    generated_upload_name = re.fullmatch(r"\d{8}_\d{6}_[0-9a-fA-F]{16,}", stem)
    if generated_upload_name:
        return "Unbenanntes Dokument"

    return name


def build_chunks_block_and_sources(
    chunks: list[RetrievedChunk],
) -> tuple[str, list[AnswerSource]]:
    """
    Formatiert die Retriever-Chunks zu einem [Q1]/[Q2]-Prompt-Block samt zugehöriger
    Source-Liste fürs Frontend. Gemeinsam genutzt vom Single-Pass- und vom Multi-Agenten-Generator,
    damit Quellennummerierung ([Q1] …) und Zitierkontext garantiert identisch sind.
    Ohne Treffer wird ein neutraler Hinweis-Block (NO_CHUNKS_NOTICE) statt einer leeren Zeichenkette geliefert.
    """
    chunk_lines: list[str] = []
    sources: list[AnswerSource] = []
    for idx, rc in enumerate(chunks, start=1):
        qid = f"Q{idx}"
        source_title = _source_title(rc.chunk.source_path, rc.metadata or {})
        chunk_lines.append(f"[{qid}] Quelle: {source_title}, Seite {rc.chunk.page_number}")
        chunk_lines.append(rc.chunk.text.strip())
        chunk_lines.append("---")
        sources.append({
            "qid": qid,
            "doc_hash": rc.chunk.doc_hash,
            "source_path": rc.chunk.source_path,
            "title": source_title,
            "page_number": rc.chunk.page_number,
            "similarity": float(rc.similarity),
            "text": rc.chunk.text,
        })

    chunks_block = "\n".join(chunk_lines).strip() or NO_CHUNKS_NOTICE
    return chunks_block, sources


class OllamaAnswerGenerator:
    """Generiert Antworten auf Basis von Retriever-Chunks via LLM. Vollständig zustandslos."""

    def __init__(
        self,
        *,
        model_name: str,
        base_url: str,
        timeout_s: int,
        prompt_path: Path,
        domain_name: str,
        max_tokens: int,
        temperature: float,
        think: Optional[bool] = None,
    ) -> None:
        """prompt_path zeigt auf answer_system_prompt.txt mit Variablen {DOMAIN}, {CAD_METADATA_JSON}, {CHUNKS_BLOCK}, {QUESTION}."""
        self.model_name = model_name
        self.client = OllamaClient(base_url=base_url, timeout_s=timeout_s, think=think)
        self.prompt_template = prompt_path.read_text(encoding="utf-8")  # einmalig beim Start laden
        self.domain_name = domain_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(
        self,
        *,
        question: str,
        chunks: list[RetrievedChunk],
        cad_metadata: dict,
        answer_format: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
        context_directive: Optional[str] = None,
    ) -> Answer:
        """
        Wandelt Chunks in einen [Q1]/[Q2]-Block um, fügt CAD-Kontext hinzu und ruft das LLM auf.
        answer_format steuert den AUSGABEFORMAT-Abschnitt des Prompts (kurz/standard/ausführlich/…).
        context_directive (optional) wird zusätzlich in den AUSGABEFORMAT-Slot injiziert
        (z.B. Bauteil-Fokus bei Typ-Diskrepanz).
        Gibt ein Answer-Dict zurück mit Antworttext und source-Liste für das Frontend.
        question ist die Originalfrage des Nutzers (es gibt kein Query-Rewriting).
        """

        # Chunks als lesbaren [Q1]/[Q2]-Block + Source-Liste (gemeinsamer Helper, auch vom
        # Multi-Agenten-Generator genutzt – garantiert identische Quellennummerierung).
        chunks_block, sources = build_chunks_block_and_sources(chunks)

        # Deterministische Fast-Paths: CAD-Identifikation vor Tabellen-Filter. Beide
        # umgehen das LLM – kleine Modelle zählen Tabellentreffer sonst unvollständig auf.
        fast_answer = maybe_answer_cad_identity_question(question, cad_metadata) or \
            maybe_answer_table_filter_question(question, chunks, answer_format)
        if fast_answer:
            if progress_callback:
                progress_callback("answer_generation_start")
                progress_callback("answer_generation_done")
                progress_callback("validation_skipped")
                progress_callback("improvement_skipped")
            return {"question": question, "answer_text": fast_answer, "sources": sources}

        format_instruction = resolve_format_instruction(answer_format, question)
        if context_directive:
            format_instruction = f"{format_instruction}\n{context_directive}"

        # CAD-Daten als deutsch beschrifteter Klartext plus vollständiges Roh-JSON,
        # damit CAD-only-Fragen auch ohne Retriever-Treffer beantwortbar bleiben.
        cad_block = cad_to_prompt_context(cad_metadata)

        prompt = self.prompt_template.format(
            DOMAIN=self.domain_name,
            CAD_METADATA_JSON=cad_block,
            CHUNKS_BLOCK=chunks_block,
            QUESTION=question,
            FORMAT=format_instruction,
        )

        if progress_callback:
            progress_callback("answer_generation_start")
        try:
            answer_text = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                temperature=self.temperature,  # niedrig = faktenorientiert
                max_tokens=self.max_tokens,
            )
        finally:
            if progress_callback:
                progress_callback("answer_generation_done")
                progress_callback("validation_skipped")
                progress_callback("improvement_skipped")

        return {"question": question, "answer_text": strip_self_source_list(answer_text), "sources": sources}
