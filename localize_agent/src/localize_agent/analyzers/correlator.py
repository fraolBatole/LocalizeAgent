"""Join PMD findings with Tree-sitter code facts."""

from __future__ import annotations

from localize_agent.models import (
    AnalysisEvidence,
    ClassFact,
    CodeFact,
    CorrelatedFinding,
    MetricFinding,
    MethodFact,
    PmdFinding,
    StructuralAnalysis,
)


def correlate_evidence(
    pmd_findings: list[PmdFinding],
    code_facts: CodeFact | None,
) -> list[CorrelatedFinding]:
    if not pmd_findings:
        return []

    classes_by_name: dict[str, ClassFact] = {}
    methods_by_key: dict[str, MethodFact] = {}
    methods_by_line: list[tuple[int, MethodFact]] = []

    if code_facts:
        for cls in code_facts.classes:
            classes_by_name[cls.name] = cls
            for method in cls.methods:
                key = f"{cls.name}.{method.name}"
                methods_by_key[key] = method
                methods_by_line.append((method.start_line, method))

    correlated: list[CorrelatedFinding] = []
    for finding in pmd_findings:
        class_fact = _resolve_class(finding, classes_by_name, code_facts)
        method_fact = _resolve_method(
            finding, class_fact, methods_by_key, methods_by_line
        )
        metrics = _build_metrics(finding, class_fact, method_fact)
        summary = _build_summary(finding, class_fact, method_fact, metrics)
        correlated.append(
            CorrelatedFinding(
                pmd=finding,
                class_fact=class_fact,
                method_fact=method_fact,
                metrics=metrics,
                summary=summary,
            )
        )
    return correlated


def build_analysis_evidence(
    *,
    language: str,
    file_path: str | None,
    project_path: str | None,
    source_code: str | None,
    pmd_findings: list[PmdFinding],
    code_facts: CodeFact | None,
    structural_analysis: StructuralAnalysis | None = None,
) -> AnalysisEvidence:
    correlated = correlate_evidence(pmd_findings, code_facts)
    metrics: list[MetricFinding] = []
    if code_facts:
        metrics.append(
            MetricFinding(name="total_methods", value=code_facts.total_methods)
        )
        for cls in code_facts.classes:
            metrics.append(
                MetricFinding(
                    name="class_method_count",
                    value=cls.method_count,
                    related_class=cls.name,
                )
            )

    return AnalysisEvidence(
        language=language,
        file_path=file_path,
        project_path=project_path,
        source_code=source_code,
        pmd_findings=pmd_findings,
        code_facts=code_facts,
        structural_analysis=structural_analysis,
        correlated_findings=correlated,
        metrics=metrics,
        evidence_text=format_evidence_text(
            correlated, code_facts, structural_analysis
        ),
    )


def format_evidence_text(
    correlated: list[CorrelatedFinding],
    code_facts: CodeFact | None,
    structural_analysis: StructuralAnalysis | None = None,
) -> str:
    lines: list[str] = ["# Analysis Evidence", ""]
    if code_facts:
        lines.append(f"File: {code_facts.file_path}")
        lines.append(f"Total methods: {code_facts.total_methods}")
        lines.append("")

    if structural_analysis:
        lines.extend(_format_structural_analysis(structural_analysis))
        lines.append("")

    for item in correlated:
        f = item.pmd
        lines.append(f"## {f.rule} (line {f.line})")
        lines.append(f"Message: {f.message}")
        if item.class_fact:
            lines.append(
                f"Class: {item.class_fact.name} "
                f"(methods={item.class_fact.method_count}, "
                f"fields={item.class_fact.field_count})"
            )
        if item.method_fact:
            lines.append(
                f"Method: {item.method_fact.name} "
                f"(params={item.method_fact.parameter_count}, "
                f"fan_in={item.method_fact.fan_in}, "
                f"fan_out={item.method_fact.fan_out})"
            )
        for m in item.metrics:
            lines.append(f"Metric {m.name}: {m.value}")
        if item.summary:
            lines.append(f"Summary: {item.summary}")
        lines.append("")

    return "\n".join(lines)


def _format_structural_analysis(structural: StructuralAnalysis) -> list[str]:
    lines: list[str] = ["## Fan-in / Fan-out Analysis", ""]
    for fan in structural.fan_metrics:
        lines.append(
            f"- {fan.method_key}: fan_in={fan.fan_in}, fan_out={fan.fan_out}"
        )

    lines.extend(["", "## Call Relationships (ACR)", ""])
    for edge in structural.call_relationships:
        lines.append(f"- {edge.caller} -> {edge.callee}")

    lines.extend(["", "## Variable Usage (AVU)", ""])
    for usage in structural.variable_usage:
        lines.append(
            f"- {usage.class_name}: fields={usage.field_count}, "
            f"methods={len(usage.methods)}"
        )
        for method in usage.methods:
            if method.local_variable_count:
                lines.append(
                    f"  - {method.method_name}: "
                    f"local_variables={method.local_variable_count}"
                )

    lines.extend(["", "## Class Coupling (ACC)", ""])
    for coupling in structural.class_coupling:
        refs = ", ".join(coupling.referenced_types) or "(none)"
        lines.append(
            f"- {coupling.class_name}: coupling_degree={coupling.coupling_degree}, "
            f"referenced_types=[{refs}]"
        )
    return lines


def _resolve_class(
    finding: PmdFinding,
    classes_by_name: dict[str, ClassFact],
    code_facts: CodeFact | None,
) -> ClassFact | None:
    if finding.class_name and finding.class_name in classes_by_name:
        return classes_by_name[finding.class_name]

    if code_facts:
        for cls in code_facts.classes:
            if cls.start_line <= finding.line <= cls.end_line:
                return cls
    return None


def _resolve_method(
    finding: PmdFinding,
    class_fact: ClassFact | None,
    methods_by_key: dict[str, MethodFact],
    methods_by_line: list[tuple[int, MethodFact]],
) -> MethodFact | None:
    if finding.class_name and finding.method_name:
        key = f"{finding.class_name}.{finding.method_name}"
        if key in methods_by_key:
            return methods_by_key[key]

    if class_fact and finding.method_name:
        for method in class_fact.methods:
            if method.name == finding.method_name:
                return method

    candidate: MethodFact | None = None
    for start_line, method in sorted(methods_by_line, key=lambda x: x[0], reverse=True):
        if start_line <= finding.line:
            if class_fact is None or method.class_name == class_fact.name:
                candidate = method
                break
    return candidate


def _build_metrics(
    finding: PmdFinding,
    class_fact: ClassFact | None,
    method_fact: MethodFact | None,
) -> list[MetricFinding]:
    metrics: list[MetricFinding] = [
        MetricFinding(name="pmd_rule", value=finding.rule),
        MetricFinding(name="pmd_line", value=finding.line),
    ]
    if class_fact:
        metrics.extend(
            [
                MetricFinding(
                    name="method_count",
                    value=class_fact.method_count,
                    related_class=class_fact.name,
                ),
                MetricFinding(
                    name="field_count",
                    value=class_fact.field_count,
                    related_class=class_fact.name,
                ),
                MetricFinding(
                    name="public_member_count",
                    value=class_fact.public_member_count,
                    related_class=class_fact.name,
                ),
                MetricFinding(
                    name="coupling_references",
                    value=len(class_fact.referenced_types),
                    related_class=class_fact.name,
                ),
            ]
        )
    if method_fact:
        metrics.extend(
            [
                MetricFinding(
                    name="parameter_count",
                    value=method_fact.parameter_count,
                    related_class=method_fact.class_name,
                    related_method=method_fact.name,
                ),
                MetricFinding(
                    name="fan_in",
                    value=method_fact.fan_in or 0,
                    related_class=method_fact.class_name,
                    related_method=method_fact.name,
                ),
                MetricFinding(
                    name="fan_out",
                    value=method_fact.fan_out or 0,
                    related_class=method_fact.class_name,
                    related_method=method_fact.name,
                ),
            ]
        )
    return metrics


def _build_summary(
    finding: PmdFinding,
    class_fact: ClassFact | None,
    method_fact: MethodFact | None,
    metrics: list[MetricFinding],
) -> str:
    parts = [f"PMD rule {finding.rule} at line {finding.line}."]
    if class_fact:
        parts.append(
            f"Class {class_fact.name} has {class_fact.method_count} methods "
            f"and {class_fact.field_count} fields."
        )
    if method_fact:
        parts.append(
            f"Method {method_fact.name} has {method_fact.parameter_count} parameters."
        )
    return " ".join(parts)
