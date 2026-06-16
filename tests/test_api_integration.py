"""
test_api_integration.py – HTTP-Integrationstest der FastAPI-App ohne schwere Abhängigkeiten.

Stubbt build_components (Embedder/Qdrant/Ollama werden NICHT geladen) und prüft mit dem
FastAPI-TestClient die komplette Verdrahtung zwischen GUI und Backend:
  - Root leitet auf das Design-System-GUI um
  - Statische GUI-Assets werden ausgeliefert (relative Pfade lösen korrekt auf)
  - /ask reicht das gewählte Ausgabeformat bis zum AnswerGenerator durch
  - /cad/analyze und /documents liefern die erwarteten Strukturen

Wichtig: build_components muss VOR dem Import von app.api.main gepatcht werden,
da main beim Import `app = create_app()` ausführt.
"""

from __future__ import annotations

import app.core.factory as factory
from app.core.types import DocumentInfo

# Merkt sich, mit welchem answer_format der Generator zuletzt aufgerufen wurde.
_LAST_CALL: dict = {}


class _FakeRetriever:
    def retrieve(self, question):
        return []  # Inhalt egal – der Fake-Generator ignoriert die Chunks


class _FakeAnswerGenerator:
    def generate(self, *, question, chunks, cad_metadata, answer_format="standard"):
        _LAST_CALL["answer_format"] = answer_format
        _LAST_CALL["cad_metadata"] = cad_metadata
        return {
            "question": question,
            "answer_text": f"Antwort im Format '{answer_format}'. [Q1]",
            "sources": [{
                "qid": "Q1",
                "source_path": "DIN3990.pdf",
                "title": "DIN3990.pdf",
                "page_number": 7,
                "similarity": 0.83,
                "text": "Beispiel-Chunktext.",
            }],
        }


class _FakeCadAdapter:
    def extract(self, file_path=None):
        return {"verzahnungstyp": "Stirnrad", "modul": 2.5, "zaehnezahl": 34}


class _FakeStore:
    def list_documents(self):
        return [DocumentInfo(source_path="DIN3990.pdf", doc_hash="abc123", chunk_count=42, file_name="DIN3990.pdf")]


class _FakeComponents:
    def __init__(self):
        self.loader = object()
        self.chunker = object()
        self.embedder = object()
        self.metadata_extractor = object()
        self.vector_store = _FakeStore()
        self.retriever = _FakeRetriever()
        self.answer_generator = _FakeAnswerGenerator()
        self.cad_adapter = _FakeCadAdapter()


def _fake_build_components(config, *, base_dir):
    return _FakeComponents()


# Patch VOR dem Import von main, damit das modulweite create_app() den Fake nutzt.
factory.build_components = _fake_build_components

from starlette.testclient import TestClient  # noqa: E402

from app.api.main import create_app  # noqa: E402

client = TestClient(create_app())


def test_root_redirects_to_gui():
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"].startswith("/ui/ui_kits/copilot/")


def test_gui_index_served():
    r = client.get("/ui/ui_kits/copilot/")
    assert r.status_code == 200
    assert '<div id="root">' in r.text


def test_gui_relative_assets_resolve():
    # styles.css wird in index.html als ../../styles.css referenziert → /ui/styles.css
    assert client.get("/ui/styles.css").status_code == 200
    assert client.get("/ui/_ds_bundle.js").status_code == 200
    assert client.get("/ui/ui_kits/copilot/App.jsx").status_code == 200


def test_documents_endpoint():
    r = client.get("/documents")
    assert r.status_code == 200
    body = r.json()
    assert body[0]["source_path"] == "DIN3990.pdf"
    assert body[0]["chunk_count"] == 42


def test_cad_analyze_endpoint():
    r = client.post("/cad/analyze", files={"file": ("part.step", b"ISO-10303-21;", "application/step")})
    assert r.status_code == 200
    assert r.json()["verzahnungstyp"] == "Stirnrad"


def test_ask_threads_format_through_to_generator():
    r = client.post("/ask", json={
        "questions": ["Welche Werkstoffe?"],
        "cad_metadata": {"verzahnungstyp": "Stirnrad"},
        "format": "stichpunkte",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["cad_metadata"] == {"verzahnungstyp": "Stirnrad"}
    assert "[Q1]" in data["answers"][0]["answer_text"]
    # Kernpunkt: das im GUI gewählte Format kommt tatsächlich beim Generator an.
    assert _LAST_CALL["answer_format"] == "stichpunkte"


def test_ask_defaults_to_standard_format():
    client.post("/ask", json={"questions": ["Frage ohne Format?"]})
    assert _LAST_CALL["answer_format"] == "standard"
