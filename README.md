# FrontierOps

FrontierOps is a local, agent-agnostic harness for tracking research and explaining new papers. A researcher asks a coding agent to set up a workspace, configure a research scope, discover changes, and brief selected papers. The Python library handles reproducible runs, source adapters, ranking, evidence, review, and rendering. It does not run a background scheduler or require a new agent framework.

The primary outcome is an evidence-linked explanation of each paper's question, method, experiments, and limitations. Outputs can include interactive HTML and an editable OpenSlide project. A narrated HyperFrames preview is optional; it is not automatically an exported video file.

[Project site](docs/index.html) · [Documentation](docs/guide.html) · [Configuration reference](docs/configuration.html) · [CLI reference](docs/commands.html) · [System specification](docs/system-spec.md)

## Start with an Agent Skill

Install the FrontierOps plugin in your coding agent. The commands below refer to Claude Code, Codex CLI, and GitHub Copilot CLI; other Copilot surfaces may use different plugin mechanisms. Plugin installation makes the workflows available to the agent but does **not** install the Python package in your research workspace.

```bash
# Claude Code
claude plugin marketplace add Yuankai619/FrontierOps
claude plugin install frontierops@frontierops

# Codex CLI
codex plugin marketplace add Yuankai619/FrontierOps
codex plugin add frontierops@frontierops

# GitHub Copilot CLI
copilot plugin install Yuankai619/FrontierOps:plugins/frontierops
```

Open your research workspace in the agent and ask it to use `frontier-setup` (or simply say `setup`). Setup checks `uv`, installs the Python package as a uv tool when needed, and creates an active `frontier.yaml` and `frontier_output/`. It does not download papers. In a FrontierOps development checkout, use `uv sync --locked` and `uv run --locked frontier`; this executes from the checkout's virtual environment without copying source code into the research workspace.

Then use the four researcher-facing actions:

1. `setup` — initialize the workspace and harness.
2. `config` — describe a topic, author, venue, or paper in natural language. The agent validates a proposed YAML change before applying it. If the request is underspecified, it asks a focused question.
3. `discover` — explicitly run Sync and Rank, inspect the comparison with a previous run, and select papers in the Discovery page. Nothing syncs on a timer.
4. `briefing` — explain selected papers against source evidence, pass Review, and publish per-paper HTML and slides. Video is optional and requires additional configuration.

See the [Quick Start](docs/quick-start.html) for host-specific invocation and installation details, [Workflow](docs/steps.html) for inputs and outputs, and [Credentials](docs/credentials.html) before enabling live sources. For complete YAML fields and defaults, use the [configuration reference](docs/configuration.html) or `frontier schema config --format json`.

`frontier.yaml` is the active configuration. `frontier.yaml.example` is only a checked-in offline fixture for development; Sync does not read it unless explicitly passed with `--config`. Candidate YAML files under `.frontier/config-drafts/` are proposals, not active configuration.

## What the harness stores

Each execution has its own directory under `.frontier/runs/<run-id>/` with its resolved configuration, stage results, evidence, and manifest. Sync state and source snapshots live under `.frontier/state/` and `.frontier/cache/raw/`. Published Discovery and briefing pages live in `frontier_output/`. A later run does not overwrite the earlier run. Discovery distinguishes papers newly published since the last run from papers newly included because the query window changed; incomplete source coverage is labeled.

The architecture follows hexagonal boundaries: `domain/` contains contracts and policy, `application/` contains use cases, and `adapters/` connect APIs, files, and renderers. The agent Skills are the researcher interface; the CLI exposes internal stages for reproducibility and debugging.

## Developer check

Run these from the repository root. The checked-in fixture is offline and needs no API key. Pass the absolute path printed by `sync` to each later stage.

```bash
uv sync --locked
uv run --locked frontier sync --config frontier.yaml.example
uv run --locked frontier rank --run <run-path>
uv run --locked frontier brief --run <run-path>
uv run --locked frontier review --run <run-path>
uv run --locked frontier render --run <run-path>
uv run --locked python -m unittest discover -s tests -v
```

For the OpenSlide project, enter its `slides/` directory and run `npm install`, `npm run sync:skills`, and `npm run build`. HTML and slide source are the standard handoff; MP4 export is not part of this check.

All implementation changes go through a pull request with a concise English title and Traditional Chinese description. Keep each PR under 600 changed source, test, and documentation lines, excluding generated artifacts and lockfiles. See [AGENTS.md](AGENTS.md) for the complete contribution rules.
