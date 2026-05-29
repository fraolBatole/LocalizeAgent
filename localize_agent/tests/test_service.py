from pathlib import Path

from localize_agent.service import localize

SAMPLE = Path(__file__).resolve().parents[1] / "src/localize_agent/test_inputs/test_input.java"


def test_localize_without_crew():
    source = SAMPLE.read_text(encoding="utf-8")
    result = localize(
        source,
        file_path=str(SAMPLE),
        run_pmd=False,
        run_crew=False,
    )
    assert result.evidence.code_facts is not None
    assert isinstance(result.to_json_dict(), dict)
