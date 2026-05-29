from pathlib import Path

from agent.result import state_to_result
from agent.state import initial_state

SAMPLE = Path(__file__).resolve().parent / "fixtures/test_input.java"


def test_state_to_result_empty_state():
    state = initial_state(file_path=str(SAMPLE), source_code=SAMPLE.read_text(encoding="utf-8"))
    result = state_to_result(state)
    assert isinstance(result.to_json_dict(), dict)
    assert result.evidence.language == "java"
    assert result.evidence.file_path == str(SAMPLE)


def test_state_to_result_with_issues():
    state = initial_state(file_path=str(SAMPLE), source_code="")
    state["design_issues"] = ["modularity", "complexity"]
    state["refactoring_type"] = "move method"
    state["final_report"] = "## Report\nMove the method."
    result = state_to_result(state)
    assert result.design_issues == ["modularity", "complexity"]
    assert result.refactoring == "move method"
    assert result.evidence.evidence_text == "## Report\nMove the method."
