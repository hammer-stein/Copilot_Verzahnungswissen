"""
solver.py – Lösungs-Agent des Multi-Agenten-Flows.

Entwirft aus Frage, Retriever-Chunks und CAD-Bauteildaten eine begründete Antwort und
legt seinen Lösungsweg in Einzelschritten offen. Nutzt ein label-basiertes Ausgabeformat
(ANTWORT:/SCHRITTE:) statt JSON – das halten kleine Modelle zuverlässig ein und es kann
nicht wie JSON an Escaping oder abgeschnittenen Strings scheitern.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.pipeline.agents.base import LlmAgent, parse_bullets, parse_labeled_sections


@dataclass(frozen=True)
class SolverResult:
    """Ergebnis des Solvers: der Antwortentwurf samt offengelegtem Lösungsweg."""
    answer: str            # vollständige Antwort mit [Q..]-/[CAD]-Markierungen
    steps: list[str]       # nachvollziehbare Einzelschritte des Lösungswegs


class SolverAgent(LlmAgent):
    """Erzeugt einen quellenbelegten Antwortentwurf. Zustandslos; nutzt prompts/solver_prompt.txt."""

    def solve(
        self,
        *,
        question: str,
        cad_block: str,
        chunks_block: str,
        format_instruction: str,
    ) -> SolverResult:
        """
        Ruft das LLM mit dem Solver-Prompt auf und parst die label-basierte Antwort zu SolverResult.
        Robuster Fallback: Lässt das Modell die ANTWORT-Marke weg, wird der Text bis "SCHRITTE"
        als Antwort genommen. Wirft ValueError nur, wenn gar keine verwertbare Antwort kommt –
        der Aufrufer (MultiAgentAnswerGenerator) fängt das ab und fällt auf den Single-Pass zurück.
        """
        text = self._generate_text(
            CAD_METADATA_JSON=cad_block,
            CHUNKS_BLOCK=chunks_block,
            QUESTION=question,
            FORMAT=format_instruction,
        )
        sections = parse_labeled_sections(text, ["ANTWORT", "SCHRITTE"])
        answer = sections["ANTWORT"].strip()
        steps = parse_bullets(sections["SCHRITTE"])

        if not answer:
            # Modell hat die ANTWORT-Marke weggelassen → Text bis "SCHRITTE" als Antwort nehmen.
            raw = text.strip()
            idx = raw.upper().find("SCHRITTE")
            answer = (raw[:idx] if idx > 0 else raw).strip()

        if not answer:
            raise ValueError("Solver lieferte keine verwertbare Antwort.")

        return SolverResult(answer=answer, steps=steps)

    def revise(
        self,
        *,
        question: str,
        cad_block: str,
        chunks_block: str,
        format_instruction: str,
        issues: list[str],
    ) -> SolverResult:
        """
        Optionale Revisionsrunde: löst die Frage erneut, ergänzt um die Beanstandungen des Reviewers.
        Die Hinweise werden an die Frage gehängt, damit kein zusätzliches Prompt-Template nötig ist.
        """
        if issues:
            hints = "\n".join(f"- {i}" for i in issues)
            question = (
                f"{question}\n\n"
                "VERBESSERUNGSHINWEISE DES PRÜFERS (behebe diese Mängel und bleibe quellenbelegt):\n"
                f"{hints}"
            )
        return self.solve(
            question=question,
            cad_block=cad_block,
            chunks_block=chunks_block,
            format_instruction=format_instruction,
        )
