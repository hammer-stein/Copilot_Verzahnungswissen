"""
reviewer.py – Review-Agent des Multi-Agenten-Flows.

Prüft den Lösungsentwurf des Solvers kritisch gegen Bauteildaten und Wissensauszüge:
Quellendeckung, Quellentreue und technische Plausibilität. Liefert ein label-basiertes Urteil
(URTEIL/BEFUND/MAENGEL/KORREKTUR) und – bei Bedarf – eine korrigierte Antwort. Kein JSON,
damit kleine Modelle das Format zuverlässig einhalten.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.pipeline.agents.base import LlmAgent, as_str, parse_bullets, parse_labeled_sections

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
        Ruft das LLM mit dem Reviewer-Prompt auf und parst die label-basierte Antwort zu ReviewResult.
        Das Parsen ist tolerant: fehlende Abschnitte → leere Felder, unbekannter Status → "unsicher".
        Der Reviewer wirft damit praktisch nie – ein unsicheres Urteil lässt den Solver-Entwurf
        unverändert (der Aufrufer behandelt das über _safe_review).
        """
        text = self._generate_text(
            CAD_METADATA_JSON=cad_block,
            CHUNKS_BLOCK=chunks_block,
            QUESTION=question,
            DRAFT_ANSWER=draft_answer,
            FORMAT=format_instruction,
        )
        sections = parse_labeled_sections(text, ["URTEIL", "BEFUND", "MAENGEL", "KORREKTUR"])
        return ReviewResult(
            status=normalize_status(sections["URTEIL"]),
            findings=as_str(sections["BEFUND"]),
            issues=parse_bullets(sections["MAENGEL"]),
            corrected_answer=as_str(sections["KORREKTUR"]),
        )
