from pathlib import Path

import pytest

from localize_agent.preflight import PreflightError, assert_preflight, run_preflight

SAMPLE = Path(__file__).resolve().parents[1] / "src/localize_agent/test_inputs/test_input.java"


def test_preflight_passes_on_test_input():
    source = SAMPLE.read_text(encoding="utf-8")
    result = run_preflight(source, file_path=str(SAMPLE), require_pmd=False)
    assert result.treesitter_ok is True
    assert result.total_methods >= 5
    assert result.ok is True


def test_assert_preflight_raises_on_empty_source():
    with pytest.raises(PreflightError):
        assert_preflight("not valid java {{{", require_pmd=False)
