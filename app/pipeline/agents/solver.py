"""
solver.py – Lösungs-Agent des Multi-Agenten-Flows.

Entwirft aus Frage, Retriever-Chunks und CAD-Bauteildaten eine begründete Antwort und
legt seinen Lösungsweg in Einzelschritten offen. Liefert strukturiertes JSON
({"answer": ..., "steps": [...]}) für die nachgelagerte Prüfung durch den ReviewerAgent.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.pipeline.agents.base import LlmAgent, as_str, as_str_list


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
        Ruft das LLM mit dem Solver-Prompt auf und normalisiert die JSON-Antwort zu SolverResult.
        Wirft ValueError, wenn keine verwertbare Antwort geliefert wird – der Aufrufer
        (MultiAgentAnswerGenerator) fängt das ab und fällt auf den Single-Pass zurück.
        """
        raw = self._generate_json(
            CAD_METADATA_JSON=cad_block,
            CHUNKS_BLOCK=chunks_block,
            QUESTION=question,
            FORMAT=format_instruction,
        )
        if not isinstance(raw, dict):
            raise ValueError(f"Solver lieferte kein JSON-Objekt: {type(raw).__name__}")

        answer = as_str(raw.get("answer"))
        if not answer:
            raise ValueError("Solver-Antwort enthält kein nicht-leeres Feld 'answer'.")

        return SolverResult(answer=answer, steps=as_str_list(raw.get("steps")))

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
