"""Shared LangGraph state for the localization workflow."""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field

from models import RefactoringTarget


class AnalysisState(TypedDict, total=False):
    file_path: str
    source_code: str
    pmd_findings: list[dict]
    code_facts: dict | None
    structural_analysis: dict | None
    correlated_findings: list[dict]
    design_issues: list[str]
    refactoring_type: str | None
    targets: list[dict]
    ranked_targets: list[dict]
    final_report: str
    raw_llm_output: str


class LocalizationOutput(BaseModel):
    design_issues: list[str] = Field(
        description='One or more of: "modularity", "complexity", "information hiding"'
    )
    refactoring_type: str = Field(
        description='One of: "move method", "parameterize variable", "inline variable", "inline method"'
    )
    targets: list[RefactoringTarget] = Field(
        description="Specific class/method locations requiring refactoring"
    )


class RankedResult(BaseModel):
    ranked_targets: list[RefactoringTarget]
    final_report: str = Field(
        description="Markdown report summarizing design issues, analysis, and ranked targets"
    )


def initial_state(*, file_path: str, source_code: str) -> AnalysisState:
    return AnalysisState(
        file_path=file_path,
        source_code=source_code,
        pmd_findings=[],
        code_facts=None,
        structural_analysis=None,
        correlated_findings=[],
        design_issues=[],
        refactoring_type=None,
        targets=[],
        ranked_targets=[],
        final_report="",
        raw_llm_output="",
    )
