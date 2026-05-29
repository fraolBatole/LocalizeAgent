"""LangGraph node implementations for the localization workflow."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from utils.correlator import build_analysis_evidence
from agent.llm import get_llm
from agent.state import AnalysisState, LocalizationOutput, RankedResult
from agent.tools import EVIDENCE_TOOLS, correlate_evidence
from models import RefactoringTarget
from utils.structural import (
    merge_fan_metrics_into_code_facts,
    run_structural_analysis,
)
from utils.pmd import PmdAnalyzer, PmdNotAvailableError
from utils.treesitter import JavaTreeSitterAnalyzer


def _message_text(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            return str(message.content)
    return ""


def _tool_results(messages: list[Any]) -> dict[str, str]:
    results: dict[str, str] = {}
    for message in messages:
        if isinstance(message, ToolMessage) and message.name:
            results[message.name] = str(message.content)
    return results


def _parse_json(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def _apply_correlated_payload(state: AnalysisState, payload: dict[str, Any]) -> AnalysisState:
    return AnalysisState(
        pmd_findings=payload.get("pmd_findings", []),
        code_facts=payload.get("code_facts"),
        structural_analysis=payload.get("structural_analysis"),
        correlated_findings=payload.get("correlated_findings", []),
        raw_llm_output=state.get("raw_llm_output", "") + "\n" + (payload.get("evidence_text") or ""),
    )


def _collect_evidence_deterministic(state: AnalysisState) -> AnalysisState:
    file_path = state["file_path"]
    source_code = state["source_code"]

    code_facts = JavaTreeSitterAnalyzer().analyze_source(
        source_code, file_path=file_path
    )
    structural = run_structural_analysis(source_code, file_path=file_path)
    code_facts = merge_fan_metrics_into_code_facts(code_facts, structural)

    try:
        pmd_findings = PmdAnalyzer().analyze_source(
            source_code, file_name=file_path.rsplit("/", 1)[-1]
        )
    except PmdNotAvailableError:
        pmd_findings = []

    evidence = build_analysis_evidence(
        language="java",
        file_path=file_path,
        project_path=None,
        source_code=source_code,
        pmd_findings=pmd_findings,
        code_facts=code_facts,
        structural_analysis=structural,
    )
    payload = json.loads(
        correlate_evidence.invoke(
            {
                "pmd_findings_json": json.dumps(
                    [f.model_dump(mode="json") for f in evidence.pmd_findings]
                ),
                "code_facts_json": json.dumps(
                    evidence.code_facts.model_dump(mode="json")
                    if evidence.code_facts
                    else {}
                ),
                "structural_analysis_json": json.dumps(
                    evidence.structural_analysis.model_dump(mode="json")
                    if evidence.structural_analysis
                    else {}
                ),
                "source_code": source_code,
                "file_path": file_path,
            }
        )
    )
    return _apply_correlated_payload(state, payload)


def _extract_evidence_from_messages(
    state: AnalysisState, messages: list[Any]
) -> AnalysisState:
    results = _tool_results(messages)
    update: AnalysisState = AnalysisState(
        raw_llm_output=state.get("raw_llm_output", "") + "\n" + _message_text(messages)
    )

    if "correlate_evidence" in results:
        payload = _parse_json(results["correlate_evidence"])
        if isinstance(payload, dict):
            merged = _apply_correlated_payload(state, payload)
            return AnalysisState(**{**state, **merged, **update})

    pmd_json = results.get("run_pmd")
    treesitter_json = results.get("run_treesitter")
    structural_json = results.get("run_structural_metrics")

    if pmd_json or treesitter_json or structural_json:
        pmd_data = _parse_json(pmd_json or "[]")
        if isinstance(pmd_data, dict):
            pmd_data = pmd_data.get("findings", [])
        payload = _parse_json(
            correlate_evidence.invoke(
                {
                    "pmd_findings_json": json.dumps(pmd_data or []),
                    "code_facts_json": treesitter_json or "{}",
                    "structural_analysis_json": structural_json or "{}",
                    "source_code": state["source_code"],
                    "file_path": state["file_path"],
                }
            )
        )
        if isinstance(payload, dict):
            merged = _apply_correlated_payload(state, payload)
            return AnalysisState(**{**state, **merged, **update})

    if not state.get("correlated_findings"):
        return _collect_evidence_deterministic(state)
    return AnalysisState(**{**state, **update})


def evidence_collector_node(state: AnalysisState) -> AnalysisState:
    llm = get_llm()
    agent = create_react_agent(llm, EVIDENCE_TOOLS)
    prompt = (
        "Collect static analysis evidence for the Java file.\n"
        f"file_path: {state['file_path']}\n"
        "Call run_pmd, run_treesitter, and run_structural_metrics on the file_path, "
        "then call correlate_evidence with their JSON outputs plus source_code and file_path.\n"
        "Use all tools before finishing."
    )
    result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    extracted = _extract_evidence_from_messages(state, result["messages"])
    return AnalysisState(**{**state, **extracted})


def _make_localizer_tools(state: AnalysisState):
    from langchain_core.tools import tool

    @tool
    def get_correlated_findings() -> str:
        """Return correlated PMD and structural findings from collected evidence."""
        return json.dumps(state.get("correlated_findings", []), indent=2)

    @tool
    def get_class_details(class_name: str) -> str:
        """Return Tree-sitter class facts for a class name."""
        code_facts = state.get("code_facts") or {}
        for cls in code_facts.get("classes", []):
            if cls.get("name") == class_name:
                return json.dumps(cls, indent=2)
        return json.dumps({"error": f"Class not found: {class_name}"})

    @tool
    def get_method_details(class_name: str, method_name: str) -> str:
        """Return method facts including fan-in/out for a class.method pair."""
        code_facts = state.get("code_facts") or {}
        for cls in code_facts.get("classes", []):
            if cls.get("name") != class_name:
                continue
            for method in cls.get("methods", []):
                if method.get("name") == method_name:
                    return json.dumps(method, indent=2)
        return json.dumps({"error": f"Method not found: {class_name}.{method_name}"})

    return [get_correlated_findings, get_class_details, get_method_details]


def issue_localizer_node(state: AnalysisState) -> AnalysisState:
    llm = get_llm()
    tools = _make_localizer_tools(state)
    agent = create_react_agent(llm, tools)
    prompt = (
        "Analyze the collected evidence and identify Java design issues.\n"
        "Allowed design issue types: modularity, complexity, information hiding.\n"
        "Allowed refactoring types: move method, parameterize variable, inline variable, inline method.\n"
        "Use the tools to inspect correlated findings and class/method details.\n"
        f"Source code:\n{state['source_code'][:8000]}"
    )
    result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    exploration = _message_text(result["messages"])

    structured = llm.with_structured_output(LocalizationOutput).invoke(
        [
            HumanMessage(
                content=(
                    "Based on the evidence exploration below, return structured localization output.\n"
                    f"Evidence summary:\n{json.dumps(state.get('correlated_findings', [])[:10], indent=2)}\n\n"
                    f"Agent exploration:\n{exploration}\n\n"
                    "Return design_issues, refactoring_type, and concrete targets with rationale."
                )
            )
        ]
    )

    targets = [target.model_dump(mode="json") for target in structured.targets]
    return AnalysisState(
        **{
            **state,
            "design_issues": structured.design_issues,
            "refactoring_type": structured.refactoring_type,
            "targets": targets,
            "raw_llm_output": state.get("raw_llm_output", "") + "\n" + exploration,
        }
    )


def ranker_node(state: AnalysisState) -> AnalysisState:
    llm = get_llm()
    structured = llm.with_structured_output(RankedResult).invoke(
        [
            HumanMessage(
                content=(
                    "Rank refactoring targets by impact and produce a final markdown report.\n"
                    f"Design issues: {state.get('design_issues', [])}\n"
                    f"Refactoring type: {state.get('refactoring_type')}\n"
                    f"Targets:\n{json.dumps(state.get('targets', []), indent=2)}\n"
                    f"Evidence:\n{json.dumps(state.get('correlated_findings', [])[:15], indent=2)}"
                )
            )
        ]
    )

    ranked = [target.model_dump(mode="json") for target in structured.ranked_targets]
    return AnalysisState(
        **{
            **state,
            "ranked_targets": ranked,
            "final_report": structured.final_report,
            "targets": ranked,
            "raw_llm_output": state.get("raw_llm_output", "") + "\n" + structured.final_report,
        }
    )


def targets_from_state(state: AnalysisState) -> list[RefactoringTarget]:
    ranked = state.get("ranked_targets") or state.get("targets") or []
    return [RefactoringTarget.model_validate(item) for item in ranked]
