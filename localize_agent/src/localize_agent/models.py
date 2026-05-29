"""Typed contracts for analysis evidence and localization results."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DesignIssueType(str, Enum):
    MODULARITY = "modularity"
    COMPLEXITY = "complexity"
    INFORMATION_HIDING = "information hiding"


class RefactoringType(str, Enum):
    MOVE_METHOD = "move method"
    PARAMETERIZE_VARIABLE = "parameterize variable"
    INLINE_VARIABLE = "inline variable"
    INLINE_METHOD = "inline method"


# PMD rule names used by LocalizeAgent
PMD_DESIGN_RULES: tuple[str, ...] = (
    "GodClass",
    "CouplingBetweenObjects",
    "DataClass",
    "LawOfDemeter",
    "ExcessiveParameterList",
    "TooManyMethods",
    "ExcessivePublicCount",
    "CyclomaticComplexity",
)


class CodeLocation(BaseModel):
    file_path: str
    start_line: int
    end_line: int | None = None
    start_column: int | None = None
    end_column: int | None = None


class PmdFinding(BaseModel):
    rule: str
    message: str
    file_path: str
    line: int
    priority: int | None = None
    end_line: int | None = None
    class_name: str | None = None
    method_name: str | None = None


class MethodFact(BaseModel):
    class_name: str
    name: str
    signature: str | None = None
    start_line: int
    end_line: int
    parameter_count: int = 0
    is_public: bool = False
    fan_in: int | None = None
    fan_out: int | None = None


class ClassFact(BaseModel):
    name: str
    start_line: int
    end_line: int
    method_count: int = 0
    field_count: int = 0
    public_member_count: int = 0
    referenced_types: list[str] = Field(default_factory=list)
    methods: list[MethodFact] = Field(default_factory=list)


class CodeFact(BaseModel):
    language: str
    file_path: str
    classes: list[ClassFact] = Field(default_factory=list)
    total_methods: int = 0


class FanMetrics(BaseModel):
    method_key: str
    class_name: str
    method_name: str
    fan_in: int = 0
    fan_out: int = 0
    file_path: str | None = None


class CallRelationship(BaseModel):
    """Direct call dependency between methods (ACR)."""

    caller: str
    callee: str
    file_path: str | None = None


class MethodVariableUsage(BaseModel):
    method_name: str
    local_variable_count: int = 0


class ClassVariableUsage(BaseModel):
    """Field vs local variable usage per class (AVU)."""

    class_name: str
    field_count: int = 0
    methods: list[MethodVariableUsage] = Field(default_factory=list)


class ClassCoupling(BaseModel):
    """Class-level type dependencies (ACC)."""

    class_name: str
    referenced_types: list[str] = Field(default_factory=list)
    coupling_degree: int = 0
    file_path: str | None = None


class StructuralAnalysis(BaseModel):
    """Results from fan-in/out, ACR, AVU, and ACC tools."""

    file_path: str | None = None
    fan_metrics: list[FanMetrics] = Field(default_factory=list)
    call_relationships: list[CallRelationship] = Field(default_factory=list)
    variable_usage: list[ClassVariableUsage] = Field(default_factory=list)
    class_coupling: list[ClassCoupling] = Field(default_factory=list)


class MetricFinding(BaseModel):
    name: str
    value: float | int | str
    unit: str | None = None
    related_class: str | None = None
    related_method: str | None = None


class CorrelatedFinding(BaseModel):
    pmd: PmdFinding
    class_fact: ClassFact | None = None
    method_fact: MethodFact | None = None
    metrics: list[MetricFinding] = Field(default_factory=list)
    summary: str | None = None


class RefactoringTarget(BaseModel):
    class_name: str
    function_name: str
    function_signature: str | None = None
    refactoring_type: str
    rationale: str
    rank: int | None = None
    pmd_rules: list[str] = Field(default_factory=list)


class AnalysisEvidence(BaseModel):
    language: str
    file_path: str | None = None
    project_path: str | None = None
    source_code: str | None = None
    pmd_findings: list[PmdFinding] = Field(default_factory=list)
    code_facts: CodeFact | None = None
    structural_analysis: StructuralAnalysis | None = None
    correlated_findings: list[CorrelatedFinding] = Field(default_factory=list)
    metrics: list[MetricFinding] = Field(default_factory=list)
    evidence_text: str | None = None


class LocalizationResult(BaseModel):
    evidence: AnalysisEvidence
    design_issues: list[str] = Field(default_factory=list)
    refactoring: str | None = None
    targets: list[RefactoringTarget] = Field(default_factory=list)
    raw_llm_output: str | None = None
    reports: dict[str, str] = Field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
