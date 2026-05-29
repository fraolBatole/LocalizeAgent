"""Run PMD with the LocalizeAgent design ruleset and normalize findings."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from models import PMD_DESIGN_RULES, PmdFinding

_RULESET_NAME = "pmd_design_ruleset.xml"


class PmdNotAvailableError(RuntimeError):
    """Raised when the PMD CLI is not installed or not on PATH."""


def _ruleset_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / _RULESET_NAME


def _pmd_on_path() -> str | None:
    return shutil.which("pmd")


class PmdAnalyzer:
    """Execute PMD against a file or directory."""

    def __init__(self, pmd_executable: str | None = None, ruleset: Path | None = None):
        self.pmd_executable = pmd_executable or _pmd_on_path()
        self.ruleset = ruleset or _ruleset_path()

    def ensure_available(self) -> None:
        if not self.pmd_executable:
            raise PmdNotAvailableError(
                "PMD is not on PATH. Install PMD 7+ and ensure `pmd` is available."
            )
        if not self.ruleset.is_file():
            raise FileNotFoundError(f"PMD ruleset not found: {self.ruleset}")

    def analyze_path(self, target: Path) -> list[PmdFinding]:
        self.ensure_available()
        target = target.resolve()
        if target.is_file():
            return self._run_pmd_on_file(target)
        return self._run_pmd_on_directory(target)

    def analyze_source(
        self, source_code: str, *, file_name: str = "Source.java"
    ) -> list[PmdFinding]:
        """Analyze in-memory source by writing to a temp file."""
        self.ensure_available()
        with tempfile.TemporaryDirectory(prefix="localize_agent_pmd_") as tmp:
            java_file = Path(tmp) / file_name
            java_file.write_text(source_code, encoding="utf-8")
            return self._run_pmd_on_file(java_file)

    def _run_pmd_on_file(self, java_file: Path) -> list[PmdFinding]:
        return self._invoke_pmd(java_file.parent, single_file=java_file.name)

    def _run_pmd_on_directory(self, directory: Path) -> list[PmdFinding]:
        return self._invoke_pmd(directory, single_file=None)

    def _invoke_pmd(
        self, directory: Path, *, single_file: str | None
    ) -> list[PmdFinding]:
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, prefix="pmd_out_"
        ) as out_file:
            out_path = Path(out_file.name)

        input_path = str(directory / single_file) if single_file else str(directory)
        cmd = [
            self.pmd_executable,
            "check",
            "-d",
            input_path,
            "-R",
            str(self.ruleset),
            "-f",
            "json",
            "-r",
            str(out_path),
            "--no-progress",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("PMD execution timed out") from exc
        finally:
            if out_path.exists() and out_path.stat().st_size == 0:
                out_path.unlink(missing_ok=True)

        findings: list[PmdFinding] = []
        if out_path.exists() and out_path.stat().st_size > 0:
            findings = self._parse_json_report(out_path.read_text(encoding="utf-8"))
            out_path.unlink(missing_ok=True)

        if not findings and result.stdout.strip():
            findings = self._parse_json_report(result.stdout)

        if not findings and result.returncode != 0:
            alt = self._invoke_pmd_xml(directory, single_file=single_file)
            if alt:
                return alt
            detail = (result.stderr or result.stdout or "").strip()
            if detail:
                raise RuntimeError(
                    f"PMD exited with code {result.returncode}: {detail[:500]}"
                )

        return [f for f in findings if f.rule in PMD_DESIGN_RULES or self._rule_allowed(f.rule)]

    def _rule_allowed(self, rule: str) -> bool:
        base = rule.split(".")[-1]
        return base in PMD_DESIGN_RULES

    def _invoke_pmd_xml(
        self, directory: Path, *, single_file: str | None
    ) -> list[PmdFinding]:
        with tempfile.NamedTemporaryFile(
            suffix=".xml", delete=False, prefix="pmd_out_"
        ) as out_file:
            out_path = Path(out_file.name)

        input_path = str(directory / single_file) if single_file else str(directory)
        cmd = [
            self.pmd_executable,
            "check",
            "-d",
            input_path,
            "-R",
            str(self.ruleset),
            "-f",
            "xml",
            "-r",
            str(out_path),
            "--no-progress",
        ]

        subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
        if not out_path.exists():
            return []
        text = out_path.read_text(encoding="utf-8")
        out_path.unlink(missing_ok=True)
        return self._parse_xml_report(text)

    def _parse_json_report(self, raw: str) -> list[PmdFinding]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []

        findings: list[PmdFinding] = []
        files = data.get("files", data)
        if isinstance(files, dict):
            for file_path, file_data in files.items():
                violations = file_data.get("violations", [])
                for v in violations:
                    findings.append(self._violation_to_finding(file_path, v))
        elif isinstance(files, list):
            for entry in files:
                path = entry.get("filename", entry.get("file", ""))
                for v in entry.get("violations", []):
                    findings.append(self._violation_to_finding(path, v))
        return findings

    def _violation_to_finding(self, file_path: str, violation: dict) -> PmdFinding:
        rule = violation.get("rule", violation.get("ruleName", "Unknown"))
        if "." in rule:
            rule = rule.split(".")[-1]
        begin = violation.get("beginline", violation.get("beginLine", 1))
        end = violation.get("endline", violation.get("endLine"))
        class_name, method_name = _extract_symbols_from_message(
            violation.get("description", violation.get("message", ""))
        )
        return PmdFinding(
            rule=rule,
            message=violation.get("description", violation.get("message", "")),
            file_path=file_path,
            line=int(begin) if begin else 1,
            end_line=int(end) if end else None,
            priority=violation.get("priority"),
            class_name=class_name,
            method_name=method_name,
        )

    def _parse_xml_report(self, raw: str) -> list[PmdFinding]:
        findings: list[PmdFinding] = []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return findings

        for file_elem in root.findall(".//file"):
            file_path = file_elem.get("name", "")
            for violation in file_elem.findall("violation"):
                rule = violation.get("rule", "Unknown")
                if "." in rule:
                    rule = rule.split(".")[-1]
                begin = int(violation.get("beginline", 1))
                end_line = violation.get("endline")
                msg = (violation.text or "").strip()
                class_name, method_name = _extract_symbols_from_message(msg)
                findings.append(
                    PmdFinding(
                        rule=rule,
                        message=msg,
                        file_path=file_path,
                        line=begin,
                        end_line=int(end_line) if end_line else None,
                        priority=int(violation.get("priority"))
                        if violation.get("priority")
                        else None,
                        class_name=class_name,
                        method_name=method_name,
                    )
                )
        return findings


def _extract_symbols_from_message(message: str) -> tuple[str | None, str | None]:
    class_match = re.search(r"class\s+['\"]?(\w+)['\"]?", message, re.I)
    method_match = re.search(r"method\s+['\"]?(\w+)['\"]?", message, re.I)
    return (
        class_match.group(1) if class_match else None,
        method_match.group(1) if method_match else None,
    )
