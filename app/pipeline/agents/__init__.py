"""
agents/ – Leichtgewichtige LLM-Agenten für den Multi-Agenten-Antwortfluss.

Der Fluss (Orchestrator → Solver → Reviewer) sichert RAG-Antworten ab und macht den
Lösungsweg für den Nutzer prüfbar. Der Orchestrator selbst ist Code (kein eigener LLM-Call,
siehe MultiAgentAnswerGenerator); hier liegen die beiden LLM-Schritte:

- SolverAgent:   entwirft aus Chunks + CAD-Daten eine begründete Lösung samt offengelegtem Lösungsweg.
- ReviewerAgent: prüft den Entwurf auf Quellendeckung, Quellentreue und Plausibilität.

Alle Agenten teilen sich denselben lokalen Ollama-Client und liefern strukturiertes JSON.
"""

from app.pipeline.agents.reviewer import ReviewerAgent, ReviewResult
from app.pipeline.agents.solver import SolverAgent, SolverResult

__all__ = ["SolverAgent", "SolverResult", "ReviewerAgent", "ReviewResult"]
