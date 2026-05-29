from pathlib import Path

from utils.treesitter import JavaTreeSitterAnalyzer
from utils.structural import merge_fan_metrics_into_code_facts, run_structural_analysis

SAMPLE = Path(__file__).resolve().parent / "fixtures/test_input.java"


def test_analyze_test_input_file():
    facts = JavaTreeSitterAnalyzer().analyze_file(SAMPLE)
    assert facts.language == "java"
    assert facts.total_methods >= 5
    assert any(c.name == "InputProcessor" for c in facts.classes)


def test_method_fan_metrics_present():
    source = SAMPLE.read_text(encoding="utf-8")
    code_facts = JavaTreeSitterAnalyzer().analyze_file(SAMPLE)
    structural = run_structural_analysis(source, file_path=str(SAMPLE))
    code_facts = merge_fan_metrics_into_code_facts(code_facts, structural)
    processor = next(c for c in code_facts.classes if c.name == "InputProcessor")
    assert len(processor.methods) >= 5
    assert any(m.fan_out is not None for m in processor.methods)
