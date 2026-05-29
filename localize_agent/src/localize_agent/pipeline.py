"""Deterministic analysis pipeline: PMD + Tree-sitter + evidence correlation."""

from __future__ import annotations

from pathlib import Path

from localize_agent.analyzers.correlator import build_analysis_evidence
from localize_agent.analyzers.pmd import PmdAnalyzer, PmdNotAvailableError
from localize_agent.analyzers.treesitter_java import JavaTreeSitterAnalyzer
from localize_agent.models import AnalysisEvidence, PmdFinding
from localize_agent.tools.code_analysis import (
    merge_fan_metrics_into_code_facts,
    run_structural_analysis,
)


def collect_evidence_from_source(
    source_code: str,
    *,
    language: str = "java",
    file_path: str | None = None,
    run_pmd: bool = True,
) -> AnalysisEvidence:
    """Run Tree-sitter (and optionally PMD) on in-memory source."""
    if language != "java":
        raise ValueError(f"Unsupported language: {language}. Only 'java' is supported.")

    resolved_path = file_path or "<inline>"
    code_facts = JavaTreeSitterAnalyzer().analyze_source(
        source_code, file_path=resolved_path
    )
    structural = run_structural_analysis(source_code, file_path=resolved_path)
    code_facts = merge_fan_metrics_into_code_facts(code_facts, structural)
    pmd_findings = _run_pmd_source(source_code, file_path) if run_pmd else []

    return build_analysis_evidence(
        language=language,
        file_path=file_path,
        project_path=None,
        source_code=source_code,
        pmd_findings=pmd_findings,
        code_facts=code_facts,
        structural_analysis=structural,
    )


def collect_evidence_from_path(
    path: Path,
    *,
    language: str = "java",
    run_pmd: bool = True,
) -> AnalysisEvidence:
    """Run analyzers on a single Java file or project directory."""
    path = path.resolve()
    if language != "java":
        raise ValueError(f"Unsupported language: {language}. Only 'java' is supported.")

    if path.is_file():
        source = path.read_text(encoding="utf-8")
        code_facts = JavaTreeSitterAnalyzer().analyze_file(path)
        structural = run_structural_analysis(source, file_path=str(path))
        code_facts = merge_fan_metrics_into_code_facts(code_facts, structural)
        pmd_findings = _run_pmd_path(path) if run_pmd else []
        return build_analysis_evidence(
            language=language,
            file_path=str(path),
            project_path=None,
            source_code=source,
            pmd_findings=pmd_findings,
            code_facts=code_facts,
            structural_analysis=structural,
        )

    # Directory: aggregate first Java file for tree-sitter snippet; PMD on whole dir
    java_files = sorted(path.rglob("*.java"))
    if not java_files:
        raise FileNotFoundError(f"No .java files found under {path}")

    primary = java_files[0]
    source = primary.read_text(encoding="utf-8")
    code_facts = JavaTreeSitterAnalyzer().analyze_file(primary)
    structural = run_structural_analysis(source, file_path=str(primary))
    code_facts = merge_fan_metrics_into_code_facts(code_facts, structural)
    pmd_findings = _run_pmd_path(path) if run_pmd else []

    return build_analysis_evidence(
        language=language,
        file_path=str(primary),
        project_path=str(path),
        source_code=source,
        pmd_findings=pmd_findings,
        code_facts=code_facts,
        structural_analysis=structural,
    )


def _run_pmd_source(source_code: str, file_path: str | None) -> list[PmdFinding]:
    try:
        return PmdAnalyzer().analyze_source(
            source_code, file_name=Path(file_path or "Source.java").name
        )
    except PmdNotAvailableError:
        return []


def _run_pmd_path(path: Path) -> list[PmdFinding]:
    try:
        return PmdAnalyzer().analyze_path(path)
    except PmdNotAvailableError:
        return []
