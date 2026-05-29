"""LangChain tools wrapping static analyzers."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool

from localize_agent.analyzers.correlator import build_analysis_evidence
from localize_agent.analyzers.pmd import PmdAnalyzer, PmdNotAvailableError
from localize_agent.analyzers.treesitter_java import JavaTreeSitterAnalyzer
from localize_agent.models import CodeFact, PmdFinding, StructuralAnalysis
from localize_agent.tools.code_analysis import run_structural_analysis


@tool
def run_pmd(file_path: str) -> str:
    """Run PMD design-rule analysis on a Java file or directory path."""
    path = Path(file_path).resolve()
    try:
        findings = PmdAnalyzer().analyze_path(path)
    except PmdNotAvailableError as exc:
        return json.dumps({"error": str(exc), "findings": []})
    except Exception as exc:
        return json.dumps({"error": str(exc), "findings": []})
    return json.dumps([finding.model_dump(mode="json") for finding in findings])


@tool
def run_treesitter(file_path: str) -> str:
    """Extract Java class and method facts from a file using Tree-sitter."""
    path = Path(file_path).resolve()
    facts = JavaTreeSitterAnalyzer().analyze_file(path)
    return json.dumps(facts.model_dump(mode="json"))


@tool
def run_structural_metrics(file_path: str) -> str:
    """Compute fan-in/out, call relationships, variable usage, and class coupling."""
    path = Path(file_path).resolve()
    source = path.read_text(encoding="utf-8")
    structural = run_structural_analysis(source, file_path=str(path))
    return json.dumps(structural.model_dump(mode="json"))


@tool
def correlate_evidence(
    pmd_findings_json: str,
    code_facts_json: str,
    structural_analysis_json: str,
    source_code: str,
    file_path: str,
) -> str:
    """Correlate PMD findings with Tree-sitter and structural metrics into evidence."""
    pmd_data = json.loads(pmd_findings_json)
    pmd_findings = [
        PmdFinding.model_validate(item) for item in (pmd_data if isinstance(pmd_data, list) else [])
    ]
    code_facts = (
        CodeFact.model_validate(json.loads(code_facts_json))
        if code_facts_json.strip()
        else None
    )
    structural = (
        StructuralAnalysis.model_validate(json.loads(structural_analysis_json))
        if structural_analysis_json.strip()
        else None
    )
    evidence = build_analysis_evidence(
        language="java",
        file_path=file_path,
        project_path=None,
        source_code=source_code,
        pmd_findings=pmd_findings,
        code_facts=code_facts,
        structural_analysis=structural,
    )
    return json.dumps(
        {
            "pmd_findings": [f.model_dump(mode="json") for f in evidence.pmd_findings],
            "code_facts": (
                evidence.code_facts.model_dump(mode="json") if evidence.code_facts else None
            ),
            "structural_analysis": (
                evidence.structural_analysis.model_dump(mode="json")
                if evidence.structural_analysis
                else None
            ),
            "correlated_findings": [
                {
                    "pmd": item.pmd.model_dump(mode="json"),
                    "class": (
                        item.class_fact.model_dump(mode="json") if item.class_fact else None
                    ),
                    "method": (
                        item.method_fact.model_dump(mode="json") if item.method_fact else None
                    ),
                    "summary": item.summary,
                }
                for item in evidence.correlated_findings
            ],
            "evidence_text": evidence.evidence_text,
        }
    )


EVIDENCE_TOOLS = [run_pmd, run_treesitter, run_structural_metrics, correlate_evidence]
