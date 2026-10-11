# FrontierOps Living System Spec

## Product goal

After a user runs Sync, FrontierOps compares current research sources with the last successful state and explains what new papers do. The default briefing duration is 300 seconds but is configurable. One approved `BriefingSpec` drives HTML, slides, and narrated video.

## MVP pipeline

```text
Build -> Sync -> Rank -> Brief -> Review -> Render
```

- **Build:** validate and materialize config; initialize a reproducible run.
- **Sync:** user-triggered delta collection; no built-in scheduler.
- **Rank:** apply configured eligibility gates and decomposable scores.
- **Brief:** explain problem, method, novelty, experiments, limitations, and relevance.
- **Review:** block unsupported claims, broken evidence, duplicates, or duration overflow.
- **Render:** generate HTML, slides, narration, captions, and video from one approved spec.

## Core artifacts

| Artifact | Responsibility |
|---|---|
| `ResearchSignal` | A new or changed paper, review decision, release, benchmark, or local document |
| `Evidence` | A source-grounded fragment with a stable locator |
| `BriefingCandidate` | A normalized and scored candidate with an eligibility trace |
| `ResearchDevelopment` | A cross-source, cross-run research development |
| `BriefingSpec` | Renderer-neutral, timed, evidence-linked briefing content |
| `RunManifest` | Config, versions, stages, inputs, outputs, warnings, and failures for one run |

## History model

- `.frontier/runs/<run-id>/` is append-only and stores every stage result plus resolved config.
- `.frontier/state/` stores current cursors, identity aliases, and development continuity.
- `.frontier/cache/raw/` stores immutable content-addressed provider snapshots.
- Failed Sync runs are retained but never advance the last-successful cursor.

## Configuration rules

- `frontier.yaml` is the domain-policy source of truth; unknown fields fail validation.
- Secrets are referenced by environment-variable name and never written to artifacts.
- Citation thresholds, freshness exemptions, weights, paths, duration, and render targets are configurable.
- A gate is a pass/exclude/warn eligibility rule; a score orders candidates that remain eligible.

## Runtime and dependency management

- Python 3.12 is the development and CI baseline.
- `uv` is the only supported environment and dependency manager; `uv.lock` makes installs reproducible.
- CI installs with `uv sync --locked` and executes checks with `uv run --locked`.

## Week 1 acceptance

- Versioned Pydantic models exist for config and the six core artifacts.
- `frontier build --config <path>` validates config and creates standard stage output plus `RunManifest`.
- Build is safe to run repeatedly and unknown config keys fail visibly.
- Unit and integration tests run with the Python standard test runner.
