"""
test_multiagent_generator.py – Unit-Tests für den Multi-Agenten-Antwortfluss.

Verwendet einen Fake-OllamaClient mit gecanntem JSON – es wird KEIN echtes Ollama/Qdrant
angesprochen. Geprüft werden die vier zentralen Pfade des MultiAgentAnswerGenerator:
  - Happy Path (Reviewer gibt frei)
  - Reviewer korrigiert direkt (corrected_answer)
  - Reviewer beanstandet ohne Korrektur → eine Solver-Revision
  - Robustheit: ungültiges Solver-JSON → Fallback auf den Single-Pass
  - Reviewer-Fehler verwirft den gültigen Solver-Entwurf NICHT
sowie die Abwärtskompatibilität des erweiterten Answer-Schemas.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import TypeAdapter

from app.core.types import Answer, Chunk, RetrievedChunk
from app.implementations.answer_generator_multiagent import MultiAgentAnswerGenerator
from app.implementations.answer_generator_ollama import OllamaAnswerGenerator
from app.pipeline.agents.reviewer import ReviewerAgent
from app.pipeline.agents.solver import SolverAgent

BASE_DIR = Path(__file__).resolve().parents[1]
SOLVER_PROMPT = BASE_DIR / "prompts" / "solver_prompt.txt"
REVIEWER_PROMPT = BASE_DIR / "prompts" / "reviewer_prompt.txt"
ANSWER_PROMPT = BASE_DIR / "prompts" / "answer_system_prompt.txt"

FALLBACK_TEXT = "Einzeldurchlauf-Antwort [Q1]."


class FakeOllamaClient:
    """Liefert gecannte Antworten und protokolliert die Aufrufe – ohne Netzwerk."""

    def __init__(self, *, json_responses=None, text_response=FALLBACK_TEXT):
        self._json = list(json_responses or [])
        self._text_response = text_response
        self.json_calls: list[str] = []
        self.text_calls: list[str] = []

    def generate_json(self, *, model, prompt, temperature=None, max_tokens=None):
        self.json_calls.append(prompt)
        if not self._json:
            raise AssertionError("Unerwarteter generate_json-Aufruf (Queue leer).")
        nxt = self._json.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    def generate(self, *, model, prompt, temperature=None, max_tokens=None):
        self.text_calls.append(prompt)
        return self._text_response


def _make_chunks() -> list[RetrievedChunk]:
    chunk = Chunk(text="Stirnräder werden nach DIN 3990 berechnet.",
                  source_path="DIN3990.pdf", page_number=7, position=0, doc_hash="abc123")
    return [RetrievedChunk(chunk=chunk, metadata={"title": "DIN3990.pdf"}, similarity=0.83)]


def _make_generator(json_responses, *, enable_review=True, max_revisions=1):
    fake = FakeOllamaClient(json_responses=json_responses)
    solver = SolverAgent(client=fake, model_name="m", prompt_path=SOLVER_PROMPT,
                         domain_name="Verzahnungen", max_tokens=800, temperature=0.2)
    reviewer = ReviewerAgent(client=fake, model_name="m", prompt_path=REVIEWER_PROMPT,
                             domain_name="Verzahnungen", max_tokens=800, temperature=0.0)
    fallback = OllamaAnswerGenerator(model_name="m", base_url="http://localhost:11434", timeout_s=1,
                                     prompt_path=ANSWER_PROMPT, domain_name="Verzahnungen",
                                     max_tokens=800, temperature=0.2)
    fallback.client = fake  # kein Netzwerk im Fallback-Pfad
    gen = MultiAgentAnswerGenerator(solver=solver, reviewer=reviewer, fallback_generator=fallback,
                                    enable_review=enable_review, max_revisions=max_revisions)
    return gen, fake


SOLVER_OK = {"answer": "Stirnräder nach DIN 3990 [Q1]. [CAD]",
             "steps": ["Bauteildaten geprüft", "Wissensauszug [Q1] herangezogen"]}


def _ask(gen, **kw) -> Answer:
    return gen.generate(question="Wie werden Stirnräder berechnet?", chunks=_make_chunks(),
                        cad_metadata={"gear_type": "spur", "tooth_profile": {"num_teeth": 20}},
                        answer_format="standard", **kw)


def test_happy_path_approved():
    reviewer_ok = {"status": "freigegeben", "findings": "Alle Aussagen belegt.", "issues": []}
    gen, fake = _make_generator([SOLVER_OK, reviewer_ok])

    answer = _ask(gen)

    assert answer["answer_text"] == SOLVER_OK["answer"]
    assert len(answer["sources"]) == 1 and answer["sources"][0]["qid"] == "Q1"
    # Trace: Orchestrator zuerst, dann Solver-Schritte, dann Reviewer.
    agents = [s["agent"] for s in answer["agent_trace"]]
    assert agents[0] == "orchestrator"
    assert "solver" in agents and "reviewer" in agents
    assert answer["review"]["status"] == "freigegeben"
    assert len(fake.json_calls) == 2  # genau Solver + Reviewer, keine Revision


def test_reviewer_corrects_directly():
    reviewer_corr = {"status": "korrigiert", "findings": "Quellenbezug korrigiert.",
                     "issues": ["[Q1] passte nicht"], "corrected_answer": "Korrigierte Antwort [Q1]."}
    gen, fake = _make_generator([SOLVER_OK, reviewer_corr])

    answer = _ask(gen)

    assert answer["answer_text"] == "Korrigierte Antwort [Q1]."
    assert answer["review"]["status"] == "korrigiert"
    statuses = [s.get("status") for s in answer["agent_trace"]]
    assert "korrigiert" in statuses
    assert len(fake.json_calls) == 2  # corrected_answer vorhanden → keine zusätzliche Revision


def test_revision_when_no_corrected_answer():
    reviewer_flag = {"status": "korrigiert", "findings": "Aussage unbelegt.",
                     "issues": ["Behauptung ohne Quelle"], "corrected_answer": ""}
    revised = {"answer": "Überarbeitete, belegte Antwort [Q1].", "steps": ["Mangel behoben"]}
    gen, fake = _make_generator([SOLVER_OK, reviewer_flag, revised], max_revisions=1)

    answer = _ask(gen)

    assert answer["answer_text"] == "Überarbeitete, belegte Antwort [Q1]."
    assert len(fake.json_calls) == 3  # Solver + Reviewer + eine Revision


def test_no_revision_when_disabled():
    reviewer_flag = {"status": "korrigiert", "findings": "Mangel.", "issues": ["x"], "corrected_answer": ""}
    gen, fake = _make_generator([SOLVER_OK, reviewer_flag], max_revisions=0)

    answer = _ask(gen)

    # Keine Korrektur möglich → Entwurf bleibt, aber klar gekennzeichnet.
    assert answer["answer_text"] == SOLVER_OK["answer"]
    assert len(fake.json_calls) == 2


def test_review_disabled_runs_only_solver():
    gen, fake = _make_generator([SOLVER_OK], enable_review=False)

    answer = _ask(gen)

    assert answer["answer_text"] == SOLVER_OK["answer"]
    assert "review" not in answer
    assert all(s["agent"] != "reviewer" for s in answer["agent_trace"])
    assert len(fake.json_calls) == 1


def test_fallback_on_invalid_solver_json():
    # Solver liefert kein verwertbares JSON → Fallback auf Single-Pass.
    gen, fake = _make_generator([ValueError("kein JSON")])

    answer = _ask(gen)

    assert answer["answer_text"] == FALLBACK_TEXT
    assert len(answer["agent_trace"]) == 1
    assert answer["agent_trace"][0]["status"] == "fallback"
    assert len(fake.text_calls) == 1  # Single-Pass wurde genutzt


def test_reviewer_failure_keeps_draft():
    # Solver ok, Reviewer scheitert → gültiger Entwurf darf NICHT verworfen werden.
    gen, fake = _make_generator([SOLVER_OK, ValueError("Reviewer kaputt")])

    answer = _ask(gen)

    assert answer["answer_text"] == SOLVER_OK["answer"]   # kein teurer Fallback
    assert "review" not in answer
    assert any(s["agent"] == "reviewer" and s.get("status") == "warnung" for s in answer["agent_trace"])
    assert len(fake.text_calls) == 0  # Single-Pass NICHT genutzt


def test_extended_answer_schema_is_backward_compatible():
    """Answer mit agent_trace/review validiert; Answer ohne die Felder ebenfalls (NotRequired)."""
    adapter = TypeAdapter(Answer)
    with_trace = {
        "question": "q", "answer_text": "a [Q1]", "sources": [],
        "agent_trace": [{"agent": "solver", "title": "t", "content": "c", "status": "ok"}],
        "review": {"status": "freigegeben", "summary": "ok"},
    }
    without = {"question": "q", "answer_text": "a", "sources": []}
    adapter.validate_python(with_trace)
    adapter.validate_python(without)
