from pathlib import Path

from app.core.types import Chunk, RetrievedChunk
from app.implementations.answer_generator_ollama import OllamaAnswerGenerator, cad_to_prompt_context


class _PromptClient:
    def __init__(self):
        self.prompt = ""

    def generate(self, *, model, prompt, temperature=None, max_tokens=None):
        self.prompt = prompt
        return "Aus den CAD-Daten beantwortet. [CAD]"


def test_repo_has_config_and_prompts():
    root = Path(__file__).resolve().parents[1]
    assert (root / "config.yaml").exists()
    assert (root / "prompts" / "answer_system_prompt.txt").exists()


def test_answer_prompt_has_required_placeholders():
    root = Path(__file__).resolve().parents[1]
    text = (root / "prompts" / "answer_system_prompt.txt").read_text(encoding="utf-8")
    for placeholder in ("{DOMAIN}", "{CAD_METADATA_JSON}", "{CHUNKS_BLOCK}", "{QUESTION}", "{FORMAT}"):
        assert placeholder in text


def test_answer_generator_keeps_cad_context_when_no_chunks(tmp_path):
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text(
        "{DOMAIN}\nBAUTEILDATEN:\n{CAD_METADATA_JSON}\n"
        "WISSENSAUSZÜGE:\n{CHUNKS_BLOCK}\nFRAGE:\n{QUESTION}\n{FORMAT}",
        encoding="utf-8",
    )
    generator = OllamaAnswerGenerator(
        model_name="test",
        base_url="http://ollama.invalid",
        timeout_s=1,
        prompt_path=prompt_path,
        domain_name="Verzahnung",
        max_tokens=128,
        temperature=0.0,
    )
    client = _PromptClient()
    generator.client = client

    answer = generator.generate(
        question="Welche interne CAD-Notiz ist hinterlegt?",
        chunks=[],
        cad_metadata={"metadata": {"part_name": "Demo"}, "analysis": {"custom_tooth_note": "nur CAD"}},
        answer_format="kurz",
    )

    assert answer["sources"] == []
    assert "Derzeit liegen keine Wissensauszüge vor" in client.prompt
    assert "Vollständiges CAD-JSON" in client.prompt
    assert '"custom_tooth_note": "nur CAD"' in client.prompt


def test_answer_sources_use_document_title_instead_of_upload_path(tmp_path):
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text(
        "{DOMAIN}\n{CAD_METADATA_JSON}\n{CHUNKS_BLOCK}\n{QUESTION}\n{FORMAT}",
        encoding="utf-8",
    )
    generator = OllamaAnswerGenerator(
        model_name="test",
        base_url="http://ollama.invalid",
        timeout_s=1,
        prompt_path=prompt_path,
        domain_name="Verzahnung",
        max_tokens=128,
        temperature=0.0,
    )
    client = _PromptClient()
    generator.client = client
    chunk = Chunk(
        text="Normtext.",
        source_path="/tmp/storage/uploads/20260616_110541_08986056963b4d438d8c3ccbbe.pdf",
        page_number=3,
        position=1,
        doc_hash="abc",
    )

    answer = generator.generate(
        question="Was steht in der Norm?",
        chunks=[RetrievedChunk(chunk=chunk, metadata={"file_name": "DIN_3990_Tragfaehigkeit.pdf"}, similarity=0.82)],
        cad_metadata={},
    )

    assert answer["sources"][0]["title"] == "DIN_3990_Tragfaehigkeit.pdf"
    assert answer["sources"][0]["doc_hash"] == "abc"
    assert "DIN_3990_Tragfaehigkeit.pdf" in client.prompt
    assert "20260616_110541" not in answer["sources"][0]["title"]


def test_cad_prompt_accepts_parameter_value_dicts():
    cad = {
        "gear_type": {"value": "spur", "unit": "", "confidence": 0.82},
        "tooth_profile": {
            "module_mm": {"value": 2.5, "unit": "mm", "confidence": 0.82},
            "num_teeth": {"value": 34, "unit": "", "confidence": 0.45},
            "helix_angle_deg": {"value": 0.0, "unit": "°", "confidence": 0.3},
        },
        "basic_geometry": {
            "outer_diameter_mm": {"value": 90.0, "unit": "mm", "confidence": 0.92},
        },
        "material_context": {
            "material": {"value": "16MnCr5", "unit": "", "confidence": 0.6},
        },
    }

    prompt = cad_to_prompt_context(cad)

    assert "Stirnrad" in prompt
    assert "Modul 2.5 mm" in prompt
    assert "34 Zähnen" in prompt
    assert "Werkstoff 16MnCr5" in prompt


def test_cad_identity_question_is_answered_without_llm_call(tmp_path):
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text(
        "{DOMAIN}\n{CAD_METADATA_JSON}\n{CHUNKS_BLOCK}\n{QUESTION}\n{FORMAT}",
        encoding="utf-8",
    )

    class FailingClient:
        def generate(self, **kwargs):
            raise AssertionError("LLM should not be called for direct CAD identity questions")

    generator = OllamaAnswerGenerator(
        model_name="test",
        base_url="http://ollama.invalid",
        timeout_s=1,
        prompt_path=prompt_path,
        domain_name="Verzahnung",
        max_tokens=128,
        temperature=0.0,
    )
    generator.client = FailingClient()

    answer = generator.generate(
        question="Um welches Zahnrad handelt es sich?",
        chunks=[],
        cad_metadata={
            "gear_type": {"value": "spur"},
            "tooth_profile": {
                "num_teeth": {"value": 24},
                "module_mm": {"value": 2.5, "unit": "mm"},
            },
        },
    )

    assert "Stirnrad" in answer["answer_text"]
    assert "[CAD]" in answer["answer_text"]


def test_synthetic_cad_testdata_exists_and_is_consistent():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "test_verzahnung" / "cad_testdaten"
    files = sorted(data_dir.glob("gear_*.json"))
    assert len(files) == 10

    import json
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d["gear_type"] in ("spur", "helical", "bevel", "internal", "worm", "rack")
        tp = d["tooth_profile"]
        geo = d["basic_geometry"]
        # Geometrie-Konsistenz: d = m_t * z (Stirnmodul bei Schraegverzahnung)
        import math
        m_t = tp["module_mm"] / math.cos(math.radians(tp["helix_angle_deg"] or 0.0))
        assert abs(geo["pitch_diameter_mm"] - m_t * tp["num_teeth"]) < 0.01
