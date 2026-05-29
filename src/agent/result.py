"""Convert final LangGraph state to a typed LocalizationResult."""

from __future__ import annotations

from agent.state import AnalysisState
from models import (
    AnalysisEvidence,
    ClassFact,
    CodeFact,
    CorrelatedFinding,
    LocalizationResult,
    MethodFact,
    PmdFinding,
    RefactoringTarget,
    StructuralAnalysis,
)


def state_to_result(state: AnalysisState) -> LocalizationResult:
    correlated = [
        CorrelatedFinding(
            pmd=PmdFinding.model_validate(item["pmd"]),
            class_fact=ClassFact.model_validate(item["class"]) if item.get("class") else None,
            method_fact=MethodFact.model_validate(item["method"]) if item.get("method") else None,
            summary=item.get("summary"),
        )
        for item in state.get("correlated_findings", [])
    ]

    code_facts_data = state.get("code_facts")
    structural_data = state.get("structural_analysis")

    evidence = AnalysisEvidence(
        language="java",
        file_path=state.get("file_path"),
        source_code=state.get("source_code"),
        pmd_findings=[PmdFinding.model_validate(f) for f in state.get("pmd_findings", [])],
        code_facts=CodeFact.model_validate(code_facts_data) if code_facts_data else None,
        structural_analysis=(
            StructuralAnalysis.model_validate(structural_data) if structural_data else None
        ),
        correlated_findings=correlated,
        evidence_text=state.get("final_report") or _summarise(correlated),
    )

    ranked = state.get("ranked_targets") or state.get("targets") or []
    targets = [RefactoringTarget.model_validate(t) for t in ranked]

    return LocalizationResult(
        evidence=evidence,
        design_issues=state.get("design_issues", []),
        refactoring=state.get("refactoring_type"),
        targets=targets,
        raw_llm_output=state.get("raw_llm_output"),
    )


def _summarise(correlated: list[CorrelatedFinding]) -> str | None:
    if not correlated:
        return None
    lines = ["# Analysis Evidence", ""]
    for item in correlated:
        f = item.pmd
        lines.append(f"## {f.rule} (line {f.line})")
        lines.append(f"Message: {f.message}")
        if item.summary:
            lines.append(f"Summary: {item.summary}")
        lines.append("")
    return "\n".join(lines)
