# localize-design

CLI to localize Java design issues using **PMD**, **Tree-sitter**, and autonomous **LangGraph** agents.

## Install

From [PyPI](https://pypi.org/project/localize-design/):

```bash
pip install localize-design
# or
uv pip install localize-design
```

You also need **PMD** on your PATH for full analysis (optional but recommended):

```bash
brew install pmd
```

Set your OpenAI API key:

```env
OPENAI_API_KEY=...
MODEL=gpt-4o-mini
```

## Usage

```bash
# Run LangGraph agents — produces a ranked refactoring report
localize-design --file path/to/File.java

# Shorthand alias
ldesign --file path/to/File.java

# Save output as JSON
localize-design --file path/to/File.java --format json -o report.json

# Text report to stdout
localize-design --file path/to/File.java --format text
```

## Development

```bash
git clone https://github.com/fraolBatole/LocalizeAgent.git
cd LocalizeAgent
uv sync
```

Add `.env` in the repo root with your `OPENAI_API_KEY`.

Run from source:

```bash
uv run localize-design --file tests/fixtures/test_input2.java
```

## How it works

Three autonomous agents run in sequence, each calling tools as needed:

1. **Evidence collector** — calls `run_pmd`, `run_treesitter`, `run_structural_metrics`, `correlate_evidence`
2. **Issue localizer** — inspects correlated findings, identifies design issues and refactoring targets
3. **Ranker** — ranks targets by impact, produces a final markdown report

## Project layout

```
src/
  cli.py              entry point
  models.py           Pydantic types
  config/             PMD ruleset
  utils/              static analysis (pmd, treesitter, structural, correlator)
  agent/              LangGraph workflow, nodes, LLM tools
tests/
  fixtures/           sample Java files
```

## Tests

```bash
uv run pytest
```

## Publish to PyPI

Maintainers only:

```bash
uv build
uv publish
```
