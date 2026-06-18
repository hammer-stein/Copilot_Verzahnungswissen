"""
answer_generator_multiagent.py – Multi-Agenten-Antwortgenerierung via Ollama.

Implementiert das AnswerGenerator-Protokoll und ersetzt den einzelnen LLM-Aufruf des
OllamaAnswerGenerator durch einen leichtgewichtigen, abgesicherten Fluss:

    Orchestrator (Code) → Solver (LLM) → Reviewer (LLM) → [optional 1 Revision]

Ziel ist die vom Feedback geforderte Zuverlässigkeit + Nachvollziehbarkeit:
- Der Reviewer prüft den Lösungsentwurf des Solvers auf Quellendeckung und Plausibilität.
- Der gesamte Lösungsweg wird als `agent_trace` zurückgegeben und im Frontend prüfbar angezeigt.

Robustheit: Schlägt der Multi-Agenten-Fluss fehl (LLM-Fehler, nicht parsebares JSON o.ä.),
wird transparent auf den erprobten Single-Pass-Generator zurückgefallen – die Antwortqualität
ist damit nie schlechter als zuvor. Vollständig zustandslos (kein Konversationskontext).
"""

from __future__ import annotations

import logging
from typing import Optional

from app.core.types import AgentStep, Answer, ReviewSummary, RetrievedChunk
from app.implementations.answer_generator_ollama import (
    OllamaAnswerGenerator,
    build_chunks_block_and_sources,
    cad_to_prompt_context,
    resolve_format_instruction,
)
from app.pipeline.agents.reviewer import ReviewerAgent, ReviewResult
from app.pipeline.agents.solver import SolverAgent

logger = logging.getLogger(__name__)


class MultiAgentAnswerGenerator:
    """
    Orchestriert Solver- und Reviewer-Agenten zu einer abgesicherten Antwort. Der Orchestrator
    selbst ist diese Klasse (Code, kein eigener LLM-Call): Sie bereitet den Kontext auf, delegiert
    an die Agenten, wendet das Prüfergebnis an und baut die finale Answer inkl. agent_trace.
    """

    def __init__(
        self,
        *,
        solver: SolverAgent,
        reviewer: ReviewerAgent,
        fallback_generator: OllamaAnswerGenerator,
        enable_review: bool = True,
        max_revisions: int = 1,
    ) -> None:
        """
        fallback_generator ist der bewährte Single-Pass-Generator; er wird bei jedem Fehler
        im Multi-Agenten-Fluss genutzt und stellt damit die Mindest-Antwortqualität sicher.
        """
        self.solver = solver
        self.reviewer = reviewer
        self.fallback_generator = fallback_generator
        self.enable_review = enable_review
        self.max_revisions = max(0, int(max_revisions))

    # ------------------------------------------------------------------ public

    def generate(
        self,
        *,
        question: str,
        chunks: list[RetrievedChunk],
        cad_metadata: dict,
        answer_format: Optional[str] = None,
    ) -> Answer:
        """
        Führt den Multi-Agenten-Fluss aus und gibt eine Answer mit nachvollziehbarem
        agent_trace (+ review) zurück. Bei jedem Fehler erfolgt ein Fallback auf den Single-Pass.
        Signatur identisch zum AnswerGenerator-Protokoll – in _answer_one ist keine Änderung nötig.
        """
        try:
            chunks_block, sources = build_chunks_block_and_sources(chunks)
            cad_block = cad_to_prompt_context(cad_metadata)
            format_instruction = resolve_format_instruction(answer_format)

            trace: list[AgentStep] = [self._orchestrator_step(sources)]

            # 1) Solver: Lösungsentwurf + offengelegter Lösungsweg (LLM-Call 1)
            solution = self.solver.solve(
                question=question,
                cad_block=cad_block,
                chunks_block=chunks_block,
                format_instruction=format_instruction,
            )
            trace.extend(self._solver_steps(solution.steps))

            final_answer = solution.answer
            review_summary: Optional[ReviewSummary] = None

            # 2) Reviewer: Prüfung + ggf. Korrektur/Revision (LLM-Call 2, optional 3)
            if self.enable_review:
                review = self._safe_review(
                    question=question,
                    cad_block=cad_block,
                    chunks_block=chunks_block,
                    draft_answer=final_answer,
                    format_instruction=format_instruction,
                )
                if review is None:
                    trace.append({
                        "agent": "reviewer",
                        "title": "Plausibilitätsprüfung",
                        "content": "Automatische Prüfung nicht verfügbar – Entwurf unverändert übernommen.",
                        "status": "warnung",
                    })
                else:
                    final_answer, review_summary, review_steps = self._apply_review(
                        review=review,
                        draft_answer=final_answer,
                        question=question,
                        cad_block=cad_block,
                        chunks_block=chunks_block,
                        format_instruction=format_instruction,
                    )
                    trace.extend(review_steps)

            # 3) Orchestrator-Assembly: finale, prüfbare Answer
            answer: Answer = {
                "question": question,
                "answer_text": final_answer,
                "sources": sources,
                "agent_trace": trace,
            }
            if review_summary is not None:
                answer["review"] = review_summary
            return answer

        except Exception:
            logger.exception("multiagent_generate_failed; Fallback auf Single-Pass")
            return self._fallback(
                question=question,
                chunks=chunks,
                cad_metadata=cad_metadata,
                answer_format=answer_format,
            )

    # ----------------------------------------------------------------- helpers

    def _orchestrator_step(self, sources: list) -> AgentStep:
        """Macht die Recherche-/Delegationsentscheidung des Orchestrators transparent."""
        if sources:
            titles = ", ".join(dict.fromkeys(s["title"] for s in sources))  # eindeutig, Reihenfolge erhalten
            content = (
                f"{len(sources)} relevante Wissensauszüge gefunden (Quellen: {titles}). "
                "Frage und Kontext an den Lösungs-Agenten delegiert."
            )
        else:
            content = (
                "Keine passenden Wissensauszüge gefunden – der Lösungs-Agent arbeitet allein "
                "mit den CAD-Bauteildaten."
            )
        return {"agent": "orchestrator", "title": "Recherche & Delegation", "content": content, "status": "ok"}

    def _solver_steps(self, steps: list[str]) -> list[AgentStep]:
        """Wandelt die offengelegten Solver-Schritte in trace-Einträge um."""
        if not steps:
            return [{"agent": "solver", "title": "Lösungsentwurf", "content": "Antwortentwurf aus Quellen und Bauteildaten erstellt.", "status": "ok"}]
        return [
            {"agent": "solver", "title": f"Lösungsschritt {i}", "content": step, "status": "ok"}
            for i, step in enumerate(steps, start=1)
        ]

    def _safe_review(
        self,
        *,
        question: str,
        cad_block: str,
        chunks_block: str,
        draft_answer: str,
        format_instruction: str,
    ) -> Optional[ReviewResult]:
        """
        Führt die Prüfung aus, fängt Fehler aber ab: Ein gescheiterter Reviewer soll einen
        gültigen Solver-Entwurf NICHT verwerfen (das wäre teurer Fallback ohne Mehrwert).
        Gibt None zurück, wenn die Prüfung nicht verfügbar ist.
        """
        try:
            return self.reviewer.review(
                question=question,
                cad_block=cad_block,
                chunks_block=chunks_block,
                draft_answer=draft_answer,
                format_instruction=format_instruction,
            )
        except Exception:
            logger.warning("reviewer_failed; Entwurf wird ungeprüft übernommen", exc_info=True)
            return None

    def _apply_review(
        self,
        *,
        review: ReviewResult,
        draft_answer: str,
        question: str,
        cad_block: str,
        chunks_block: str,
        format_instruction: str,
    ) -> tuple[str, ReviewSummary, list[AgentStep]]:
        """
        Wendet das Prüfurteil an und liefert (finale_antwort, review_summary, trace_schritte).
        - freigegeben: Entwurf bleibt unverändert.
        - sonst: bevorzugt die vom Reviewer gelieferte corrected_answer; fehlt sie, wird bei
          max_revisions > 0 eine einzelne Solver-Revision versucht; andernfalls bleibt der Entwurf
          (klar als ungeprüft/unsicher gekennzeichnet).
        """
        summary: ReviewSummary = {
            "status": review.status,
            "summary": review.findings or "Prüfung abgeschlossen.",
        }
        if review.issues:
            summary["issues"] = review.issues

        if review.approved:
            step: AgentStep = {
                "agent": "reviewer",
                "title": "Plausibilitätsprüfung",
                "content": review.findings or "Antwort geprüft und freigegeben.",
                "status": "freigegeben",
            }
            return draft_answer, summary, [step]

        # Nicht freigegeben → Befund dokumentieren
        finding_text = review.findings or "Der Prüfer hat Mängel am Entwurf festgestellt."
        if review.issues:
            finding_text += "\n" + "\n".join(f"- {i}" for i in review.issues)
        steps: list[AgentStep] = [{
            "agent": "reviewer",
            "title": "Plausibilitätsprüfung",
            "content": finding_text,
            "status": "warnung",
        }]

        if review.corrected_answer:
            steps.append({
                "agent": "reviewer",
                "title": "Korrigierte Antwort",
                "content": "Antwort vom Prüfer gemäß Befund korrigiert.",
                "status": "korrigiert",
            })
            return review.corrected_answer, summary, steps

        if self.max_revisions > 0:
            try:
                revised = self.solver.revise(
                    question=question,
                    cad_block=cad_block,
                    chunks_block=chunks_block,
                    format_instruction=format_instruction,
                    issues=review.issues or [finding_text],
                )
                steps.append({
                    "agent": "solver",
                    "title": "Überarbeitete Antwort",
                    "content": "Antwort nach Prüfbefund einmalig überarbeitet.",
                    "status": "korrigiert",
                })
                summary["status"] = "korrigiert"
                return revised.answer, summary, steps
            except Exception:
                logger.warning("revision_failed; Entwurf bleibt unverändert", exc_info=True)

        # Keine Korrektur möglich – Entwurf unverändert, aber klar gekennzeichnet
        steps.append({
            "agent": "reviewer",
            "title": "Hinweis",
            "content": "Es konnte keine korrigierte Fassung erstellt werden; der Entwurf wird mit Vorbehalt ausgegeben.",
            "status": "warnung",
        })
        return draft_answer, summary, steps

    def _fallback(
        self,
        *,
        question: str,
        chunks: list[RetrievedChunk],
        cad_metadata: dict,
        answer_format: Optional[str],
    ) -> Answer:
        """Single-Pass-Antwort des bewährten Generators, mit einem Fallback-Hinweis im agent_trace."""
        answer = dict(self.fallback_generator.generate(
            question=question,
            chunks=chunks,
            cad_metadata=cad_metadata,
            answer_format=answer_format,
        ))
        answer["agent_trace"] = [{
            "agent": "orchestrator",
            "title": "Einzeldurchlauf (Fallback)",
            "content": (
                "Der Multi-Agenten-Fluss war nicht verfügbar; die Antwort wurde im bewährten "
                "Einzeldurchlauf erzeugt."
            ),
            "status": "fallback",
        }]
        return answer  # type: ignore[return-value]
