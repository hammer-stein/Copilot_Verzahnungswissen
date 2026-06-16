"""
answer_generator_ollama.py – LLM-basierte Antwortgenerierung via Ollama.

Implementiert das AnswerGenerator-Protokoll. Baut aus Frage, Retriever-Chunks und
CAD-Metadaten einen strukturierten Prompt und lässt das LLM eine quellenverweisende
Antwort generieren – ausschließlich auf Basis der übergebenen Chunks (kein Halluzinieren).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.core.types import Answer, RetrievedChunk
from app.core.utils import stable_json_dumps
from app.implementations.ollama_client import OllamaClient

# Deutsche Bezeichner + Einheiten für die GearParameters-Felder (Format: cad_processor/src/output_schema.py).
# Das LLM (insb. kleine Modelle) kann deutsche Fragebegriffe sonst nicht auf die englischen,
# verschachtelten JSON-Schlüssel abbilden – daher wird das CAD-JSON in einen lesbaren Block übersetzt.
_GEAR_TYPE_LABELS = {
    "spur": "Stirnrad (Geradverzahnung)", "helical": "Schrägverzahnung", "bevel": "Kegelrad",
    "internal": "Innenverzahnung", "worm": "Schnecke", "rack": "Zahnstange",
}
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


def _fmt_value(value: Any, unit: str) -> Optional[str]:
    """Formatiert einen Wert; gibt None für leere/uninteressante Werte zurück (überspringen)."""
    if value is None or value == "" or value == []:
        return None
    if isinstance(value, bool):
        return "ja" if value else "nein"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if unit:
        return f"{value} {unit}"
    return str(value)


def _cad_summary_sentence(cad: dict[str, Any]) -> str:
    """
    Ein natürlicher Identifikationssatz für das Bauteil. Hilft kleinen LLMs, generische
    Fragen wie „Um welches Zahnrad handelt es sich?" direkt zu beantworten, statt nur
    eine Parameterliste vorzufinden, die sie nicht mit der Frage verknüpfen.
    """
    gt = cad.get("gear_type")
    typ = _GEAR_TYPE_LABELS.get(gt, gt) if gt else "Zahnrad"
    tp = cad.get("tooth_profile") or {}
    mc = cad.get("material_context") or {}
    meta = cad.get("metadata") or {}

    parts: list[str] = []
    if tp.get("module_mm") is not None:
        parts.append(f"Modul {tp['module_mm']} mm")
    if tp.get("num_teeth") is not None:
        parts.append(f"{tp['num_teeth']} Zähnen")
    if tp.get("helix_angle_deg"):
        parts.append(f"Schrägungswinkel {tp['helix_angle_deg']}°")
    if mc.get("material"):
        parts.append(f"Werkstoff {mc['material']}")

    # Direkt als Identifikation formuliert, damit auch generische Fragen wie
    # "Um welches Zahnrad handelt es sich?" direkt beantwortbar sind.
    sentence = f"Es handelt sich um folgendes Bauteil: eine {typ}" if gt else "Es handelt sich um folgendes Bauteil: ein Zahnrad"
    if parts:
        sentence += " mit " + ", ".join(parts)
    name = meta.get("part_name")
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

    lines: list[str] = [_cad_summary_sentence(cad), ""]
    gt = cad.get("gear_type")
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
    ) -> None:
        """prompt_path zeigt auf answer_system_prompt.txt mit Variablen {DOMAIN}, {CAD_METADATA_JSON}, {CHUNKS_BLOCK}, {QUESTION}."""
        self.model_name = model_name
        self.client = OllamaClient(base_url=base_url, timeout_s=timeout_s)
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
    ) -> Answer:
        """
        Wandelt Chunks in einen [Q1]/[Q2]-Block um, fügt CAD-Kontext hinzu und ruft das LLM auf.
        answer_format steuert den AUSGABEFORMAT-Abschnitt des Prompts (kurz/standard/ausführlich/…).
        Gibt ein Answer-Dict zurück mit Antworttext und source-Liste für das Frontend.
        question ist immer die ORIGINALFRAGE des Nutzers – nicht die umgeschriebene Retrieval-Anfrage.
        """

        # Chunks als lesbaren Block formatieren: [Q1] Quelle: datei.pdf, Seite 5 \n <text> \n ---
        chunk_lines: list[str] = []
        sources = []
        for idx, rc in enumerate(chunks, start=1):
            qid = f"Q{idx}"
            source_title = str((rc.metadata or {}).get("file_name") or Path(rc.chunk.source_path).name)
            chunk_lines.append(f"[{qid}] Quelle: {source_title}, Seite {rc.chunk.page_number}")
            chunk_lines.append(rc.chunk.text.strip())
            chunk_lines.append("---")
            sources.append({
                "qid": qid,
                "source_path": rc.chunk.source_path,
                "title": source_title,
                "page_number": rc.chunk.page_number,
                "similarity": float(rc.similarity),
                "text": rc.chunk.text,
            })

        format_instruction = FORMAT_INSTRUCTIONS.get(
            (answer_format or DEFAULT_FORMAT).strip().casefold(),
            FORMAT_INSTRUCTIONS[DEFAULT_FORMAT],
        )

        # Ohne Treffer: neutraler Marker + explizite Anweisung. Negative Formulierungen
        # ("keine Treffer gefunden") treiben kleine LLMs unnötig in die Verweigerung, und ohne
        # den Zusatz kommentieren sie den leeren Block mit einer sinnlosen [Q1]-Markierung.
        chunks_block = "\n".join(chunk_lines).strip() or (
            "Derzeit liegen keine Wissensauszüge vor. Beantworte die Frage allein aus den "
            "BAUTEILDATEN und verwende KEINE [Q]-Markierungen."
        )

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

        answer_text = self.client.generate(
            model=self.model_name,
            prompt=prompt,
            temperature=self.temperature,  # niedrig = faktenorientiert
            max_tokens=self.max_tokens,
        )

        return {"question": question, "answer_text": answer_text, "sources": sources}
