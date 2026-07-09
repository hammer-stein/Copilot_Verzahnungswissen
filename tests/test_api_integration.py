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
        if question.startswith("FAIL"):
            # Simulierter LLM-Ausfall für den Fehlerpfad-Test (z.B. Ollama nicht erreichbar)
            raise RuntimeError("Ollama nicht erreichbar (Testfehler)")
        _LAST_CALL["answer_format"] = answer_format
        _LAST_CALL["cad_metadata"] = cad_metadata
        return {
            "question": question,
            "answer_text": f"Antwort im Format '{answer_format}'. [Q1]",
            "sources": [{
                "qid": "Q1",
                "doc_hash": "abc123",
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

    def set_document_title(self, doc_hash, title):
        self.last_title = (doc_hash, title)


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


def test_document_title_endpoint():
    r = client.post("/documents/abc123/title", json={"title": "DIN 3990 Tragfähigkeit.pdf"})
    assert r.status_code == 200
    assert r.json()["title"] == "DIN 3990 Tragfähigkeit.pdf"


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


def test_cad_from_csv_endpoint_returns_gear_parameters():
    csv = (
        "Bauteil_ID,Bezeichnung,Verzahnungstyp,Modul_mm,Zaehnezahl,Werkstoff\n"
        "G-010,Stirnrad Testrad,Stirnrad,2.5,32,16MnCr5\n"
    ).encode("utf-8")
    r = client.post("/cad/from-csv", files={"file": ("zahnrad.csv", csv, "text/csv")})
    assert r.status_code == 200
    body = r.json()
    # Formgleich mit /cad/analyze: verschachtelte GearParameters-Struktur, direkt als cad_metadata nutzbar.
    assert body["filename"] == "zahnrad.csv"
    assert body["gear_type"]["value"] == "spur"
    assert body["tooth_profile"]["module_mm"]["value"] == 2.5
    assert body["tooth_profile"]["num_teeth"]["value"] == 32
    assert body["material_context"]["material"] == "16MnCr5"


def test_cad_from_csv_rejects_wrong_extension_and_non_gear_csv():
    r = client.post("/cad/from-csv", files={"file": ("part.step", b"ISO-10303-21;", "application/step")})
    assert r.status_code == 400

    r = client.post("/cad/from-csv", files={"file": ("adressen.csv", b"Name,Ort\nMax,Ulm\n", "text/csv")})
    assert r.status_code == 400
    assert "Verzahnungs-Spalten" in r.json()["detail"]


def test_ask_status_endpoint_tracks_request_id():
    request_id = "pytest-status-request"
    r = client.post("/ask", json={"questions": ["Status?"], "request_id": request_id})
    assert r.status_code == 200

    s = client.get(f"/ask/status/{request_id}")
    assert s.status_code == 200
    body = s.json()
    assert body["request_id"] == request_id
    assert body["status"] == "done"
    assert [step["key"] for step in body["steps"]][:2] == ["embedding", "search"]


def test_ask_failure_marks_failing_step_with_error_message():
    """Nachvollziehbarkeit: Beim Pipeline-Fehler zeigt der Prozessstatus, WELCHER
    Schritt mit WELCHER Meldung abgebrochen ist (Frontend rendert ihn rot)."""
    request_id = "pytest-fail-request"
    r = client.post("/ask", json={"questions": ["FAIL bitte"], "request_id": request_id})
    assert r.status_code == 500
    assert "Ollama nicht erreichbar" in r.json()["detail"]

    s = client.get(f"/ask/status/{request_id}")
    body = s.json()
    assert body["status"] == "error"
    failed = [step for step in body["steps"] if step["status"] == "error"]
    assert len(failed) == 1
    assert failed[0]["key"] == "answer_generation"  # Fehlerort ist der Generierungs-Schritt
    assert "Antwortgenerierung fehlgeschlagen" in failed[0]["content"]
    assert "Ollama nicht erreichbar" in failed[0]["content"]


def test_delete_cad_preview_removes_file_and_rejects_bad_names():
    """'Bauteil entfernen' im Frontend räumt das STL-Preview serverseitig auf."""
    from pathlib import Path

    previews = Path(__file__).resolve().parents[1] / "storage" / "cad_previews"
    previews.mkdir(parents=True, exist_ok=True)
    victim = previews / "test_delete_preview.stl"
    victim.write_text("solid t\nendsolid t\n", encoding="utf-8")

    r = client.delete(f"/cad/preview/{victim.name}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    assert not victim.exists()

    # Zweites Löschen ist idempotent, Pfad-Traversal/fremde Endungen werden abgelehnt.
    assert client.delete(f"/cad/preview/{victim.name}").json()["deleted"] is False
    assert client.delete("/cad/preview/..%2Fconfig.yaml").status_code == 404
    assert client.delete("/cad/preview/evil.txt").status_code == 404
