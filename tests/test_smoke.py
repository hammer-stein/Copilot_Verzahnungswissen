from pathlib import Path


def test_repo_has_config_and_prompt():
    root = Path(__file__).resolve().parents[1]
    assert (root / "config.yaml").exists()
    assert (root / "schemas" / "gears.yaml").exists()
    assert (root / "prompts" / "answer_system_prompt.txt").exists()

