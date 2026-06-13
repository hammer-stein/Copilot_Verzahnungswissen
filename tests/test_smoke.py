from pathlib import Path


def test_repo_has_config_and_prompts():
    root = Path(__file__).resolve().parents[1]
    assert (root / "config.yaml").exists()
    assert (root / "prompts" / "answer_system_prompt.txt").exists()


def test_answer_prompt_has_required_placeholders():
    root = Path(__file__).resolve().parents[1]
    text = (root / "prompts" / "answer_system_prompt.txt").read_text(encoding="utf-8")
    for placeholder in ("{DOMAIN}", "{CAD_METADATA_JSON}", "{CHUNKS_BLOCK}", "{QUESTION}", "{FORMAT}"):
        assert placeholder in text


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
