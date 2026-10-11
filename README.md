# FrontierOps

FrontierOps is an agent-agnostic harness that turns user-triggered research deltas into grounded paper explanations and reusable briefings.

The first increment provides versioned contracts, validated YAML configuration, a CLI, and reproducible Build runs. See [the system spec](docs/system-spec.md).

## Quick start

```bash
uv sync --locked
uv run frontier build --config frontier.yaml.example
uv run --locked python -m unittest discover -s tests
```

## Contribution rules

All changes use pull requests. Titles are English, descriptions are Traditional Chinese, and each PR is limited to 600 counted lines. See [AGENTS.md](AGENTS.md).
