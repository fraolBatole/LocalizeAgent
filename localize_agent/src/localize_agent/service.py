"""Core localization workflow used by the CLI."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from localize_agent.crew import LocalizeAgent
from localize_agent.models import AnalysisEvidence, LocalizationResult, RefactoringTarget
from localize_agent.pipeline import collect_evidence_from_path, collect_evidence_from_source
from localize_agent.preflight import assert_preflight

REPORT_FILES = (
    "planning_report.md",
    "issue_report.md",
    "analysis_report.md",
    "prompt_report.md",
    "localization_report.md",
    "ranking_report.md",
)


def localize(
    source: str,
    *,
    file_path: str | None = None,
    run_pmd: bool = True,
    run_crew: bool = True,
) -> LocalizationResult:
    if run_crew:
        assert_preflight(source, file_path=file_path, require_pmd=run_pmd)
    evidence = collect_evidence_from_source(
        source, file_path=file_path, run_pmd=run_pmd
    )
    return _build_result(evidence, run_crew=run_crew, source=source)


def localize_path(
    path: Path,
    *,
    run_pmd: bool = True,
    run_crew: bool = True,
) -> LocalizationResult:
    path = path.resolve()
    source = path.read_text(encoding="utf-8") if path.is_file() else ""
    if run_crew and path.is_file():
        assert_preflight(source, file_path=str(path), require_pmd=run_pmd)
    evidence = collect_evidence_from_path(path, run_pmd=run_pmd)
    return _build_result(
        evidence,
        run_crew=run_crew,
        source=source or evidence.source_code or "",
    )


def _build_result(
    evidence: AnalysisEvidence,
    *,
    run_crew: bool,
    source: str,
) -> LocalizationResult:
    design_issues, refactoring = _infer_from_pmd(evidence)
    targets = _targets_from_correlated(evidence)
    raw_output: str | None = None
    reports: dict[str, str] = {}

    if run_crew:
        _load_dotenv()
        _log("Starting CrewAI (6 tasks)...")
        raw_output, reports = _run_crew(source, evidence)
        _log("CrewAI finished.")
        if parsed := _parse_targets(raw_output):
            targets = parsed
        elif ranking := reports.get("ranking_report.md"):
            targets = _parse_targets(ranking)
        if issue := reports.get("issue_report.md"):
            design_issues, refactoring = _parse_issue(issue, design_issues, refactoring)

    return LocalizationResult(
        evidence=evidence,
        design_issues=design_issues,
        refactoring=refactoring,
        targets=targets,
        raw_crew_output=raw_output,
        reports=reports,
    )


def _run_crew(source: str, evidence: AnalysisEvidence) -> tuple[str | None, dict[str, str]]:
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    inputs = {
        "code": source,
        "evidence": evidence.evidence_text or "",
        "pmd_summary": _pmd_summary(evidence),
        "evidence_json": _evidence_json(evidence),
    }
    result = LocalizeAgent().crew().kickoff(inputs=inputs)
    return str(result) if result else None, _load_reports()


def _evidence_json(evidence: AnalysisEvidence) -> str:
    return json.dumps(
        {
            "pmd_findings": [f.model_dump() for f in evidence.pmd_findings],
            "code_facts": evidence.code_facts.model_dump() if evidence.code_facts else None,
            "structural_analysis": (
                evidence.structural_analysis.model_dump()
                if evidence.structural_analysis
                else None
            ),
            "correlated_findings": [
                {
                    "pmd": c.pmd.model_dump(),
                    "class": c.class_fact.model_dump() if c.class_fact else None,
                    "method": c.method_fact.model_dump() if c.method_fact else None,
                    "summary": c.summary,
                }
                for c in evidence.correlated_findings
            ],
        },
        indent=2,
    )


def _pmd_summary(evidence: AnalysisEvidence) -> str:
    lines = [f"PMD findings: {len(evidence.pmd_findings)}"]
    lines.extend(
        f"- {f.rule} @ {f.file_path}:{f.line}: {f.message}"
        for f in evidence.pmd_findings[:20]
    )
    return "\n".join(lines)


def _infer_from_pmd(evidence: AnalysisEvidence) -> tuple[list[str], str | None]:
    rules = {f.pmd.rule for f in evidence.correlated_findings}
    issues: list[str] = []
    if rules & {"GodClass", "CouplingBetweenObjects", "TooManyMethods", "ExcessivePublicCount"}:
        issues.append("modularity")
    if rules & {"CyclomaticComplexity", "ExcessiveParameterList", "TooManyMethods"}:
        issues.append("complexity")
    if rules & {"DataClass", "LawOfDemeter"}:
        issues.append("information hiding")
    if not issues and evidence.pmd_findings:
        issues.append("modularity")

    refactoring = None
    if rules & {"LawOfDemeter", "CouplingBetweenObjects"}:
        refactoring = "move method"
    elif "ExcessiveParameterList" in rules:
        refactoring = "parameterize variable"
    elif "DataClass" in rules:
        refactoring = "inline method"
    elif "CyclomaticComplexity" in rules:
        refactoring = "inline variable"
    return issues, refactoring


def _targets_from_correlated(evidence: AnalysisEvidence) -> list[RefactoringTarget]:
    rule_map = {
        "LawOfDemeter": "move method",
        "CouplingBetweenObjects": "move method",
        "ExcessiveParameterList": "parameterize variable",
        "DataClass": "inline method",
        "CyclomaticComplexity": "inline variable",
        "GodClass": "move method",
        "TooManyMethods": "move method",
    }
    targets: list[RefactoringTarget] = []
    for idx, item in enumerate(evidence.correlated_findings, start=1):
        cls = item.class_fact.name if item.class_fact else (item.pmd.class_name or "Unknown")
        method = item.method_fact.name if item.method_fact else (item.pmd.method_name or "N/A")
        targets.append(
            RefactoringTarget(
                class_name=cls,
                function_name=method,
                function_signature=item.method_fact.signature if item.method_fact else None,
                refactoring_type=rule_map.get(item.pmd.rule, "move method"),
                rationale=item.summary or item.pmd.message,
                rank=idx,
                pmd_rules=[item.pmd.rule],
            )
        )
    return targets


def _parse_targets(raw: str | None) -> list[RefactoringTarget]:
    if not raw:
        return []
    for text in (raw, _extract_json_block(raw, r"\[[\s\S]*\]")):
        if not text:
            continue
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [_to_target(d) for d in data if isinstance(d, dict)]
        except json.JSONDecodeError:
            continue
    return []


def _parse_issue(
    text: str, issues: list[str], refactoring: str | None
) -> tuple[list[str], str | None]:
    block = _extract_json_block(text, r"\{[\s\S]*\}")
    if not block:
        return issues, refactoring
    try:
        data = json.loads(block)
        if isinstance(data, dict):
            return data.get("design_issues", issues), data.get("refactoring", refactoring)
    except json.JSONDecodeError:
        pass
    return issues, refactoring


def _extract_json_block(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return match.group() if match else None


def _to_target(d: dict[str, Any]) -> RefactoringTarget:
    return RefactoringTarget(
        class_name=d.get("Class name", d.get("class_name", "Unknown")),
        function_name=d.get("Function name", d.get("function_name", "N/A")),
        function_signature=d.get("Function signature", d.get("function_signature")),
        refactoring_type=d.get("refactoring_type", "move method"),
        rationale=d.get("rationale", ""),
        rank=d.get("rank"),
    )


def _load_reports() -> dict[str, str]:
    return {
        name: Path(name).read_text(encoding="utf-8")
        for name in REPORT_FILES
        if Path(name).is_file()
    }


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for candidate in (Path.cwd(), Path.cwd().parent):
        env = candidate / ".env"
        if env.is_file():
            load_dotenv(env)
            return


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)
