from pathlib import Path

from localize_agent.pipeline import collect_evidence_from_path, collect_evidence_from_source

SAMPLE = Path(__file__).resolve().parents[1] / "src/localize_agent/test_inputs/test_input.java"


def test_collect_evidence_from_source_no_pmd():
    evidence = collect_evidence_from_source(
        SAMPLE.read_text(encoding="utf-8"),
        file_path=str(SAMPLE),
        run_pmd=False,
    )
    assert evidence.code_facts is not None
    assert evidence.code_facts.total_methods >= 5
    assert evidence.evidence_text


def test_collect_evidence_from_file_no_pmd():
    evidence = collect_evidence_from_path(SAMPLE, run_pmd=False)
    assert evidence.file_path == str(SAMPLE.resolve())
    assert len(evidence.correlated_findings) == 0 or evidence.pmd_findings == []
