from pathlib import Path

from app.implementations.cad_processor_local import LocalCadProcessorAdapter


def test_local_cad_processor_adapter_imports_parser_and_returns_dict(tmp_path):
    cad_dir = tmp_path / "cad_processor"
    src_dir = cad_dir / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "step_parser.py").write_text(
        """
from pathlib import Path

class Params:
    def __init__(self, source):
        self.source = source

    def to_dict(self):
        return {"source_file": self.source, "gear_type": {"value": "spur"}}

def parse_step_file(input_path, output_path):
    Path(output_path).write_text("{}", encoding="utf-8")
    return Params(Path(input_path).name)
""",
        encoding="utf-8",
    )
    step_file = tmp_path / "gear.step"
    step_file.write_text("ISO-10303-21;", encoding="utf-8")

    adapter = LocalCadProcessorAdapter(cad_processor_dir=cad_dir)
    result = adapter.extract(step_file)

    assert result["source_file"] == "gear.step"
    assert result["gear_type"]["value"] == "spur"
    assert result["filename"] == "gear.step"
