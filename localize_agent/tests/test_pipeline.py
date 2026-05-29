"""Tests for the graph analysis tools (previously tested via pipeline.py)."""

import json
from pathlib import Path

from localize_agent.graph.tools import run_treesitter, run_structural_metrics

SAMPLE = Path(__file__).resolve().parents[1] / "src/localize_agent/test_inputs/test_input.java"


def test_run_treesitter_extracts_facts():
    result = json.loads(run_treesitter.invoke({"file_path": str(SAMPLE)}))
    assert result["total_methods"] >= 5
    assert any(c["name"] == "InputProcessor" for c in result["classes"])


def test_run_structural_metrics_produces_fan_data():
    result = json.loads(run_structural_metrics.invoke({"file_path": str(SAMPLE)}))
    keys = {m["method_key"] for m in result["fan_metrics"]}
    assert "InputProcessor.processInputs" in keys
