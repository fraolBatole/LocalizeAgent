"""CLI for LocalizeAgent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from localize_agent.pipeline import collect_evidence_from_path, collect_evidence_from_source
from localize_agent.preflight import PreflightError, run_preflight
from localize_agent.service import localize, localize_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Localize Java design issues (PMD + Tree-sitter + optional CrewAI).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="Verify Tree-sitter and PMD (~1s)")
    p_check.add_argument("--file", "-f", type=Path, required=True)
    p_check.add_argument("--require-pmd", action="store_true")

    p_analyze = sub.add_parser("analyze", help="Collect analysis evidence")
    p_analyze.add_argument("--file", "-f", type=Path)
    p_analyze.add_argument("--project", "-p", type=Path)
    p_analyze.add_argument("--stdin", action="store_true")
    p_analyze.add_argument("--no-pmd", action="store_true")
    p_analyze.add_argument("--format", choices=("json", "text"), default="json")
    p_analyze.add_argument("-o", type=Path)

    p_loc = sub.add_parser("localize", help="Analyze and optionally run CrewAI ranking")
    p_loc.add_argument("--file", "-f", type=Path)
    p_loc.add_argument("--project", "-p", type=Path)
    p_loc.add_argument("--stdin", action="store_true")
    p_loc.add_argument("--no-pmd", action="store_true")
    p_loc.add_argument("--no-crew", action="store_true")
    p_loc.add_argument("--format", choices=("json", "text"), default="json")
    p_loc.add_argument("-o", type=Path)

    args = parser.parse_args(argv)
    if args.cmd == "check":
        return _cmd_check(args)
    if args.cmd == "analyze":
        return _cmd_analyze(args)
    return _cmd_localize(args)


def _cmd_check(args: argparse.Namespace) -> int:
    source = args.file.read_text(encoding="utf-8")
    try:
        result = run_preflight(
            source, file_path=str(args.file.resolve()), require_pmd=args.require_pmd
        )
    except PreflightError as exc:
        _print_stderr(exc.result.summary_lines())
        return 1
    print("\n".join(result.summary_lines()))
    return 0 if result.ok else 1


def _cmd_analyze(args: argparse.Namespace) -> int:
    evidence = _collect(args, run_pmd=not args.no_pmd)
    out = (
        json.dumps(evidence.model_dump(mode="json"), indent=2)
        if args.format == "json"
        else (evidence.evidence_text or "")
    )
    _write(out, args.o)
    return 0


def _cmd_localize(args: argparse.Namespace) -> int:
    run_pmd = not args.no_pmd
    run_crew = not args.no_crew

    if run_crew and args.file:
        source = args.file.read_text(encoding="utf-8")
        try:
            pf = run_preflight(
                source, file_path=str(args.file.resolve()), require_pmd=run_pmd
            )
        except PreflightError as exc:
            _print_stderr(exc.result.summary_lines())
            return 1
        _print_stderr(pf.summary_lines())

    try:
        if args.project:
            result = localize_path(args.project, run_pmd=run_pmd, run_crew=run_crew)
        elif args.file:
            result = localize_path(args.file, run_pmd=run_pmd, run_crew=run_crew)
        else:
            source, fp = _read_stdin(args)
            result = localize(source, file_path=fp, run_pmd=run_pmd, run_crew=run_crew)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        out = json.dumps(result.to_json_dict(), indent=2)
    else:
        lines = [
            f"Design issues: {', '.join(result.design_issues)}",
            f"Refactoring: {result.refactoring}",
            "",
            result.evidence.evidence_text or "",
            "",
            "Targets:",
        ]
        lines.extend(
            f"  [{t.rank}] {t.class_name}.{t.function_name} -> {t.refactoring_type}"
            for t in result.targets
        )
        out = "\n".join(lines)
    _write(out, args.o)
    return 0


def _collect(args: argparse.Namespace, *, run_pmd: bool):
    if args.project:
        return collect_evidence_from_path(args.project.resolve(), run_pmd=run_pmd)
    if args.file:
        return collect_evidence_from_path(args.file.resolve(), run_pmd=run_pmd)
    source, fp = _read_stdin(args)
    return collect_evidence_from_source(source, file_path=fp, run_pmd=run_pmd)


def _read_stdin(args: argparse.Namespace) -> tuple[str, str | None]:
    if args.stdin:
        return sys.stdin.read(), None
    raise SystemExit("Provide --file, --project, or --stdin")


def _write(text: str, path: Path | None) -> None:
    if path:
        path.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text + ("" if text.endswith("\n") else "\n"))


def _print_stderr(lines: list[str]) -> None:
    for line in lines:
        print(line, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
