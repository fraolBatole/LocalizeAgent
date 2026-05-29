# LocalizeAgent

CLI to localize Java design issues using **PMD**, **Tree-sitter**, and autonomous **LangGraph** agents.

## Setup

```bash
cd localize_agent
uv sync
brew install pmd   # optional but recommended
```

Add `.env` in the repo root:

```env
OPENAI_API_KEY=...
MODEL=gpt-4o-mini
```

## Usage

```bash
# Run LangGraph agents — produces a ranked refactoring report
uv run localize-agent --file path/to/File.java

# Save output as JSON
uv run localize-agent --file src/localize_agent/test_inputs/test_input2.java --format json -o report.json

# Text report to stdout
uv run localize-agent --file path/to/File.java --format text
```

## How it works

Three autonomous agents run in sequence, each calling tools as needed:

1. **Evidence collector** — calls `run_pmd`, `run_treesitter`, `run_structural_metrics`, `correlate_evidence`
2. **Issue localizer** — inspects correlated findings, identifies design issues and refactoring targets
3. **Ranker** — ranks targets by impact, produces a final markdown report

## Tests

```bash
cd localize_agent && uv run pytest
```
