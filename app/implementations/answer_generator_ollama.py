
"""
answer_generator_ollama.py – LLM-basierte Antwortgenerierung via Ollama.

Implementiert das AnswerGenerator-Protokoll. Baut aus Frage, Retriever-Chunks und
CAD-Metadaten einen strukturierten Prompt und lässt das LLM eine quellenverweisende
Antwort generieren – ausschließlich auf Basis der übergebenen Chunks (kein Halluzinieren).
"""

from __future__ import annotations

from pathlib import Path

from app.core.types import Answer, RetrievedChunk
from app.core.utils import stable_json_dumps
from app.implementations.ollama_client import OllamaClient


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
        answer_format: str = DEFAULT_FORMAT,
    ) -> Answer:
        """
        Wandelt Chunks in einen [Q1]/[Q2]-Block um, fügt CAD-Kontext hinzu und ruft das LLM auf.
        answer_format steuert den AUSGABEFORMAT-Abschnitt des Prompts (kurz/standard/ausführlich/…).
        Gibt ein Answer-Dict zurück mit Antworttext und source-Liste für das Frontend.
        """

        # Chunks als lesbaren Block formatieren: [Q1] Quelle: datei.pdf, Seite 5 \n <text> \n ---
        # Extrahierte Metadaten werden mit ausgegeben, damit das LLM Fakten (Alter, Sonnenstunden, ...)
        # direkt aus der strukturierten Extraktion zitieren kann – nicht nur aus dem Fließtext.
        chunk_lines: list[str] = []
        sources = []
        for idx, rc in enumerate(chunks, start=1):
            qid = f"Q{idx}"
            chunk_lines.append(f"[{qid}] Quelle: {Path(rc.chunk.source_path).name}, Seite {rc.chunk.page_number}")
            non_null_meta = {
                k: v for k, v in (rc.metadata or {}).items()
                if v is not None and v not in ("unspecified", "")
            }
            if non_null_meta:
                chunk_lines.append(f"  Extrahierte Fakten: {stable_json_dumps(non_null_meta)}")
            chunk_lines.append(rc.chunk.text.strip())
            chunk_lines.append("---")
            sources.append({
                "qid": qid,
                "source_path": rc.chunk.source_path,
                "page_number": rc.chunk.page_number,
                "similarity": float(rc.similarity),
                "text": rc.chunk.text,
            })

        format_instruction = FORMAT_INSTRUCTIONS.get(answer_format, FORMAT_INSTRUCTIONS[DEFAULT_FORMAT])

        prompt = self.prompt_template.format(
            DOMAIN=self.domain_name,
            CAD_METADATA_JSON=stable_json_dumps(cad_metadata),  # deterministisches JSON für den Prompt
            CHUNKS_BLOCK="\n".join(chunk_lines).strip(),
            QUESTION=question,
            FORMAT_INSTRUCTION=format_instruction,
        )

        answer_text = self.client.generate(
            model=self.model_name,
            prompt=prompt,
            temperature=self.temperature,  # niedrig = faktenorientiert
            max_tokens=self.max_tokens,
        )

        return {"question": question, "answer_text": answer_text, "sources": sources}
