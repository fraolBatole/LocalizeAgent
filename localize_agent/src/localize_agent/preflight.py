"""Fast preflight checks for Tree-sitter and PMD before running CrewAI."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from localize_agent.analyzers.pmd import PmdAnalyzer, PmdNotAvailableError
from localize_agent.analyzers.treesitter_java import JavaTreeSitterAnalyzer


class PreflightError(RuntimeError):
    """Raised when required analyzers fail preflight."""

    def __init__(self, result: PreflightResult):
        self.result = result
        detail = "; ".join(result.errors) or "Preflight failed"
        super().__init__(detail)


class PreflightResult(BaseModel):
    ok: bool
    treesitter_ok: bool = False
    pmd_available: bool = False
    pmd_ok: bool = False
    total_methods: int | None = None
    class_count: int | None = None
    pmd_finding_count: int | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def summary_lines(self) -> list[str]:
        lines = [
            f"Tree-sitter: {'OK' if self.treesitter_ok else 'FAIL'}",
            f"PMD available: {'yes' if self.pmd_available else 'no'}",
        ]
        if self.treesitter_ok:
            lines.append(
                f"  classes={self.class_count}, methods={self.total_methods}"
            )
        if self.pmd_available:
            lines.append(
                f"PMD run: {'OK' if self.pmd_ok else 'FAIL'} "
                f"(findings={self.pmd_finding_count})"
            )
        for warning in self.warnings:
            lines.append(f"warning: {warning}")
        for error in self.errors:
            lines.append(f"error: {error}")
        lines.append(f"Overall: {'PASS' if self.ok else 'FAIL'}")
        return lines


def run_preflight(
    source_code: str,
    *,
    file_path: str | None = None,
    require_pmd: bool = False,
) -> PreflightResult:
    """
    Validate analyzers on sample source before starting the slow crew pipeline.

    Tree-sitter is required. PMD is optional unless require_pmd=True.
    """
    errors: list[str] = []
    warnings: list[str] = []
    treesitter_ok = False
    pmd_available = False
    pmd_ok = False
    total_methods: int | None = None
    class_count: int | None = None
    pmd_finding_count: int | None = None

    try:
        facts = JavaTreeSitterAnalyzer().analyze_source(
            source_code, file_path=file_path or "<preflight>"
        )
        treesitter_ok = True
        total_methods = facts.total_methods
        class_count = len(facts.classes)
        if total_methods == 0:
            errors.append("Tree-sitter parsed the file but found zero methods.")
            treesitter_ok = False
    except Exception as exc:
        errors.append(f"Tree-sitter failed: {exc}")

    analyzer = PmdAnalyzer()
    try:
        analyzer.ensure_available()
        pmd_available = True
    except PmdNotAvailableError:
        if require_pmd:
            errors.append(
                "PMD is not on PATH. Install PMD 7+ or run with --no-pmd."
            )
        else:
            warnings.append(
                "PMD is not on PATH; continuing with Tree-sitter evidence only."
            )

    if pmd_available:
        try:
            findings = analyzer.analyze_source(
                source_code,
                file_name=Path(file_path or "Preflight.java").name,
            )
            pmd_ok = True
            pmd_finding_count = len(findings)
        except Exception as exc:
            errors.append(f"PMD execution failed: {exc}")
            if require_pmd:
                pmd_ok = False

    ok = treesitter_ok and (pmd_ok or not require_pmd)
    if require_pmd and not pmd_available:
        ok = False

    return PreflightResult(
        ok=ok,
        treesitter_ok=treesitter_ok,
        pmd_available=pmd_available,
        pmd_ok=pmd_ok,
        total_methods=total_methods,
        class_count=class_count,
        pmd_finding_count=pmd_finding_count,
        errors=errors,
        warnings=warnings,
    )


def assert_preflight(
    source_code: str,
    *,
    file_path: str | None = None,
    require_pmd: bool = False,
) -> PreflightResult:
    result = run_preflight(
        source_code, file_path=file_path, require_pmd=require_pmd
    )
    if not result.ok:
        raise PreflightError(result)
    return result
