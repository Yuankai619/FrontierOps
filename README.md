# FrontierOps

FrontierOps is an agent-agnostic harness that turns user-triggered research deltas into grounded paper explanations and reusable briefings.

## Current milestone

Week 1 establishes versioned contracts, validated YAML configuration, a CLI skeleton, and reproducible empty Build runs. See [the living system spec](docs/system-spec.md).

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
frontier build --config frontier.yaml.example
python -m unittest discover -s tests
```

Build outputs are written beneath the configured `.frontier/runs/<run-id>/` directory and must not be committed.

## Contribution rules

All changes use pull requests. Titles are English, descriptions are Traditional Chinese, and each PR is limited to 600 changed lines excluding generated dependency artifacts. See [AGENTS.md](AGENTS.md).
