"""
reviewer.py – Review-Agent des Multi-Agenten-Flows.

Prüft den Lösungsentwurf des Solvers kritisch gegen Bauteildaten und Wissensauszüge:
Quellendeckung, Quellentreue und technische Plausibilität. Liefert ein Urteil
({"status", "findings", "issues", "corrected_answer"}) und – bei Bedarf – eine korrigierte Antwort.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.pipeline.agents.base import LlmAgent, as_str, as_str_list

# Erlaubte Urteile. Kleine Modelle weichen oft ab ("ok", "approved", "needs revision"),
# daher wird der gelieferte Status unten heuristisch auf diese drei Werte abgebildet.
STATUS_APPROVED = "freigegeben"
STATUS_CORRECTED = "korrigiert"
STATUS_UNCERTAIN = "unsicher"


def normalize_status(raw_status: str) -> str:
    """Bildet einen frei formulierten LLM-Status robust auf freigegeben/korrigiert/unsicher ab."""
    s = as_str(raw_status).casefold()
    if not s:
        return STATUS_UNCERTAIN
    if "frei" in s or "approv" in s or s in {"ok", "okay", "pass", "valid", "korrekt"}:
        return STATUS_APPROVED
    if "korr" in s or "correct" in s or "revis" in s or "fix" in s:
        return STATUS_CORRECTED
    if "unsicher" in s or "uncertain" in s or "unklar" in s or "unknown" in s:
        return STATUS_UNCERTAIN
    return STATUS_UNCERTAIN


@dataclass(frozen=True)
class ReviewResult:
    """Urteil des Reviewers über den Lösungsentwurf."""
    status: str               # freigegeben | korrigiert | unsicher
    findings: str             # kurzer Befund
    issues: list[str]         # konkrete Beanstandungen
    corrected_answer: str     # finale Antwort bei korrigiert/unsicher, sonst leer

    @property
    def approved(self) -> bool:
        return self.status == STATUS_APPROVED


class ReviewerAgent(LlmAgent):
    """Prüft den Antwortentwurf. Zustandslos; nutzt prompts/reviewer_prompt.txt."""

    def review(
        self,
        *,
        question: str,
        cad_block: str,
        chunks_block: str,
        draft_answer: str,
        format_instruction: str,
    ) -> ReviewResult:
        """
        Ruft das LLM mit dem Reviewer-Prompt auf und normalisiert die JSON-Antwort zu ReviewResult.
        Wirft ValueError bei nicht verwertbarem JSON – der Aufrufer entscheidet über die Behandlung.
        """
        raw = self._generate_json(
            CAD_METADATA_JSON=cad_block,
            CHUNKS_BLOCK=chunks_block,
            QUESTION=question,
            DRAFT_ANSWER=draft_answer,
            FORMAT=format_instruction,
        )
        if not isinstance(raw, dict):
            raise ValueError(f"Reviewer lieferte kein JSON-Objekt: {type(raw).__name__}")

        status = normalize_status(raw.get("status", ""))
        return ReviewResult(
            status=status,
            findings=as_str(raw.get("findings")),
            issues=as_str_list(raw.get("issues")),
            corrected_answer=as_str(raw.get("corrected_answer")),
        )
