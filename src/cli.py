"""CLI for LocalizeAgent — run LangGraph agents to localize Java design issues."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent.result import state_to_result
from agent.state import initial_state
from agent.workflow import build_graph


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Localize Java design issues using autonomous LangGraph agents."
    )
    parser.add_argument("--file", "-f", type=Path, required=True, help="Java source file to analyze")
    parser.add_argument("--format", choices=("json", "text"), default="text", help="Output format")
    parser.add_argument("-o", type=Path, help="Write output to a file (default: stdout)")

    args = parser.parse_args(argv)

    _load_dotenv()

    file_path = args.file.resolve()
    if not file_path.is_file():
        print(f"Error: {file_path} does not exist or is not a file", file=sys.stderr)
        return 1

    source = file_path.read_text(encoding="utf-8")

    print("Starting Design Issue localization...", file=sys.stderr, flush=True)
    state = build_graph().invoke(initial_state(file_path=str(file_path), source_code=source))
    print("Done.", file=sys.stderr, flush=True)

    result = state_to_result(state)

    if args.format == "json":
        out = json.dumps(result.to_json_dict(), indent=2)
    else:
        out = result.evidence.evidence_text or ""

    _write(out, args.o)
    return 0


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for candidate in (Path.cwd(), Path.cwd().parent):
        env = candidate / ".env"
        if env.is_file():
            load_dotenv(env)
            return


def _write(text: str, path: Path | None) -> None:
    if path:
        path.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text + ("" if text.endswith("\n") else "\n"))


if __name__ == "__main__":
    raise SystemExit(main())
