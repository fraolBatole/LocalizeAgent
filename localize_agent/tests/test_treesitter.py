from pathlib import Path

from localize_agent.analyzers.treesitter_java import JavaTreeSitterAnalyzer
from localize_agent.pipeline import collect_evidence_from_path

SAMPLE = Path(__file__).resolve().parents[1] / "src/localize_agent/test_inputs/test_input.java"


def test_analyze_test_input_file():
    facts = JavaTreeSitterAnalyzer().analyze_file(SAMPLE)
    assert facts.language == "java"
    assert facts.total_methods >= 5
    assert any(c.name == "InputProcessor" for c in facts.classes)


def test_method_fan_metrics_present():
    evidence = collect_evidence_from_path(SAMPLE, run_pmd=False)
    processor = next(
        c for c in evidence.code_facts.classes if c.name == "InputProcessor"
    )
    assert len(processor.methods) >= 5
    assert any(m.fan_out is not None for m in processor.methods)
