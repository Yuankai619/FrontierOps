# FrontierOps Living System Spec

## Product goal

After user-triggered Sync, FrontierOps explains new research. Briefings default to 300 seconds but remain configurable; one approved `BriefingSpec` drives HTML, slides, and narrated video.

## Hexagonal architecture

- **Domain** owns pure configuration and artifact contracts; it imports no outer layer.
- **Application** owns use cases and the ports required from infrastructure.
- **Adapters** implement ports for YAML, filesystems, clocks, providers, renderers, and user interfaces.
- `frontierops.build` is a composition root; CLI is a driving adapter and never contains business rules.
- Dependencies point inward: `adapters -> application -> domain`. Future stages follow the same boundary.

## Pipeline

`Build -> Sync -> Rank -> Brief -> Review -> Render`

- **Build:** validate config and initialize a reproducible run.
- **Sync:** compare sources with the last successful state; no built-in scheduler.
- **Rank:** apply configured eligibility gates and decomposable scores.
- **Brief:** explain problem, method, novelty, experiments, limitations, and relevance.
- **Review:** block unsupported claims, broken evidence, duplicates, or duration overflow.
- **Render:** generate all formats from one approved spec.

## Core artifacts

| Artifact | Responsibility |
|---|---|
| `ResearchSignal` | A new or changed paper, decision, release, benchmark, or local document |
| `Evidence` | A source-grounded fragment with a stable locator |
| `BriefingCandidate` | A normalized, scored candidate with an eligibility trace |
| `ResearchDevelopment` | A cross-source, cross-run research development |
| `BriefingSpec` | Renderer-neutral, timed, evidence-linked briefing content |
| `RunManifest` | Inputs, outputs, versions, stages, warnings, and failures for one run |

## Persistence and policy

- `.frontier/runs/` is append-only; `.frontier/state/` holds cursors; `.frontier/cache/raw/` holds immutable source snapshots.
- JSON/JSONL artifacts are inspectable sources of truth; SQLite is a rebuildable query index.
- Failed Sync runs remain inspectable but never advance the last-successful cursor.
- `frontier.yaml` owns domain policy; unknown fields fail and secrets are only environment references.
- Gates pass, exclude, warn, or exempt candidates; scores only order eligible candidates.

## Configuration lifecycle

- `schema` and `inspect` expose machine-readable contracts and effective defaults.
- `validate` rejects unknown fields before any external work begins.
- `diff` compares materialized configs using stable paths rather than YAML formatting.
- `draft` writes a temporary candidate; `apply` validates it before an atomic replacement.
- Coding-agent Skills must use these commands instead of editing active configuration blindly.
- Scholar and venue resolvers return stable IDs plus disambiguation metadata.
- Offline fixtures define the contract; live provider adapters can replace them without changing use cases.
- Multiple identity candidates require explicit user confirmation before config apply.
- `skills/frontier-config/SKILL.md` is the canonical portable natural-language configuration workflow.
- The Skill delegates reasoning to the host coding agent and composes Harness commands; it does not embed an LLM client or agent framework.
- Its safe mutation sequence is `schema/inspect -> draft -> resolve -> validate -> diff -> apply`; preview-only requests and unresolved identities stop before apply.

## Runtime and acceptance

- Python 3.12 and `uv` are required; `uv.lock` and `uv sync --locked` make installs reproducible.
- `frontier build --config <path>` creates standard stage output and a `RunManifest`.
- Build initializes state files and SQLite idempotently without overwriting prior state.
- Unit and integration tests run through `uv run --locked`.
- Repeated Build runs are independent, and unknown configuration fields fail visibly.
- Sync is manually triggered, preserves raw snapshots, and compares stable source IDs plus content hashes against shared last-successful state.
- Replaying an unchanged fixture produces no new `ResearchSignal` while retaining the new inspectable run.
