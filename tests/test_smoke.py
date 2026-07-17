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


# --- Empfehlungs-Direktive + Quellenlisten-Backstop ---------------------------

def test_recommendation_query_detection():
    from app.implementations.answer_generator_ollama import is_recommendation_query
    assert is_recommendation_query("Welches Verfahren eignet sich am besten zur Produktion?")
    assert is_recommendation_query("Was sollte ich für die Fertigung verwenden?")
    assert is_recommendation_query("Welche Methode ist optimal?")
    assert not is_recommendation_query("Wie groß ist der Teilkreisdurchmesser?")
    assert not is_recommendation_query("Zeige mir alle Wellen.")


def test_format_instruction_appends_recommendation_directive():
    from app.implementations.answer_generator_ollama import resolve_format_instruction
    base = resolve_format_instruction("standard")
    with_reco = resolve_format_instruction("standard", "Welches Verfahren eignet sich am besten?")
    assert with_reco.startswith(base)
    assert "Empfehlung:" in with_reco
    # Faktenfragen bleiben unverändert:
    assert resolve_format_instruction("standard", "Wie groß ist der Modul?") == base


def test_strip_self_source_list_removes_trailing_block():
    from app.implementations.answer_generator_ollama import strip_self_source_list
    text = "Empfehlung: Schleifen [Q1].\n\nBegründung folgt.\n\nQuellen:\n\n* VDI 3720 Blatt 9.1 (1990)\n* DIN 3965:2023-04\n"
    assert strip_self_source_list(text) == "Empfehlung: Schleifen [Q1].\n\nBegründung folgt."
    # Antworten ohne Quellenliste bleiben unverändert:
    assert strip_self_source_list("Nur Text [Q1].") == "Nur Text [Q1]."
    # "Quellen" mitten im Text wird NICHT entfernt:
    keep = "Die Quellen:\nnennen dazu nichts. Details siehe [Q2]."
    assert strip_self_source_list(keep) == keep


def test_strip_think_block_removes_reasoning_trace():
    from app.implementations.ollama_client import strip_think_block
    raw = "<think>\nDer Nutzer fragt nach dem Modul…\n</think>\nEmpfehlung: Schleifen [Q1]."
    assert strip_think_block(raw) == "Empfehlung: Schleifen [Q1]."
    assert strip_think_block("Antwort ohne Denkspur.") == "Antwort ohne Denkspur."
    assert strip_think_block("<think></think>Antwort.") == "Antwort."


def test_context_directive_lands_in_llm_prompt_format_slot(tmp_path):
    """
    KRONJUWEL (Prompt-Ebene): Die type_focus_directive muss im tatsächlich ans LLM
    gesendeten Prompt landen – im AUSGABEFORMAT-Slot ({FORMAT}), der zuverlässigsten
    Stelle. Failt, wenn context_directive im Generator verloren geht.
    """
    from app.core.cad_terms import assess_type_mismatch, type_focus_directive

    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text(
        "{DOMAIN}\n{CAD_METADATA_JSON}\n{CHUNKS_BLOCK}\n{QUESTION}\nAUSGABEFORMAT:\n{FORMAT}",
        encoding="utf-8",
    )
    generator = OllamaAnswerGenerator(
        model_name="test", base_url="http://ollama.invalid", timeout_s=1,
        prompt_path=prompt_path, domain_name="Verzahnung", max_tokens=128, temperature=0.0,
    )
    client = _PromptClient()
    generator.client = client

    mismatch = assess_type_mismatch(
        "das kegelrad herstellen", {"gear_type": {"value": "ratchet", "confidence": 0.92}}
    )
    generator.generate(
        question="das kegelrad herstellen",
        chunks=[],
        cad_metadata={"gear_type": {"value": "ratchet", "confidence": 0.92}},
        answer_format="standard",
        context_directive=type_focus_directive(mismatch),
    )

    # Direktive steht im Prompt, im FORMAT-Slot (nach "AUSGABEFORMAT:"), mit CAD-Typ.
    assert "Bauteil-Fokus" in client.prompt
    assert "Sperrrad" in client.prompt
    assert client.prompt.index("Bauteil-Fokus") > client.prompt.index("AUSGABEFORMAT:")
