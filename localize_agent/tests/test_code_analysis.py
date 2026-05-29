from pathlib import Path

from localize_agent.pipeline import collect_evidence_from_path
from localize_agent.tools.code_analysis import run_structural_analysis

SAMPLE = Path(__file__).resolve().parents[1] / "src/localize_agent/test_inputs/test_input.java"


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


def test_pipeline_includes_structural_analysis():
    evidence = collect_evidence_from_path(SAMPLE, run_pmd=False)
    assert evidence.structural_analysis is not None
    assert evidence.structural_analysis.fan_metrics
    assert "Fan-in / Fan-out" in (evidence.evidence_text or "")
    processor = next(
        c for c in evidence.code_facts.classes if c.name == "InputProcessor"
    )
    process_input = next(m for m in processor.methods if m.name == "processInput")
    assert process_input.fan_in is not None and process_input.fan_in >= 1
