from pathlib import Path

from utils.correlator import build_analysis_evidence
from utils.treesitter import JavaTreeSitterAnalyzer
from utils.structural import merge_fan_metrics_into_code_facts, run_structural_analysis

SAMPLE = Path(__file__).resolve().parent / "fixtures/test_input.java"


def test_fan_metrics_on_test_input():
    source = SAMPLE.read_text(encoding="utf-8")
    structural = run_structural_analysis(source, file_path=str(SAMPLE))
    fan = {m.method_key: m for m in structural.fan_metrics}
    assert "InputProcessor.processInputs" in fan
    assert fan["InputProcessor.processInputs"].fan_out >= 1
    assert fan["InputProcessor.processInput"].fan_in >= 1


def test_call_relationships_acr():
    source = SAMPLE.read_text(encoding="utf-8")
    structural = run_structural_analysis(source, file_path=str(SAMPLE))
    edges = {(e.caller, e.callee) for e in structural.call_relationships}
    assert ("InputProcessor.processInputs", "processInput") in edges
    assert ("InputProcessor.addAndProcess", "addInput") in edges


def test_variable_usage_avu():
    source = SAMPLE.read_text(encoding="utf-8")
    structural = run_structural_analysis(source, file_path=str(SAMPLE))
    usage = next(u for u in structural.variable_usage if u.class_name == "InputProcessor")
    assert usage.field_count == 3
    assert len(usage.methods) >= 5


def test_class_coupling_acc():
    source = SAMPLE.read_text(encoding="utf-8")
    structural = run_structural_analysis(source, file_path=str(SAMPLE))
    coupling = next(c for c in structural.class_coupling if c.class_name == "InputProcessor")
    assert "ArrayList" in coupling.referenced_types or "List" in coupling.referenced_types
    assert coupling.coupling_degree >= 1


def test_structural_analysis_merged_into_code_facts():
    source = SAMPLE.read_text(encoding="utf-8")
    code_facts = JavaTreeSitterAnalyzer().analyze_file(SAMPLE)
    structural = run_structural_analysis(source, file_path=str(SAMPLE))
    code_facts = merge_fan_metrics_into_code_facts(code_facts, structural)
    evidence = build_analysis_evidence(
        language="java",
        file_path=str(SAMPLE),
        project_path=None,
        source_code=source,
        pmd_findings=[],
        code_facts=code_facts,
        structural_analysis=structural,
    )
    assert evidence.structural_analysis is not None
    assert evidence.structural_analysis.fan_metrics
    assert "Fan-in / Fan-out" in (evidence.evidence_text or "")
    processor = next(c for c in evidence.code_facts.classes if c.name == "InputProcessor")
    process_input = next(m for m in processor.methods if m.name == "processInput")
    assert process_input.fan_in is not None and process_input.fan_in >= 1
