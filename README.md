# LocalizeAgent

CLI to localize Java design issues using **PMD**, **Tree-sitter**, and optional **CrewAI**.

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

`litellm.drop_params` is enabled automatically so newer OpenAI models work without extra config.

## CLI

```bash
# Preflight (~1s)
uv run localize-agent check --file src/localize_agent/test_inputs/test_input2.java

# Evidence only
uv run localize-agent analyze --file src/localize_agent/test_inputs/test_input2.java

# Full pipeline without LLM
uv run localize-agent localize --file src/localize_agent/test_inputs/test_input2.java --no-crew

# With CrewAI (~2–3 min)
uv run localize-agent localize --file src/localize_agent/test_inputs/test_input2.java
```

## Tests

```bash
cd localize_agent && uv run pytest
```
