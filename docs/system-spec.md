# FrontierOps System Specification

This document describes the current experimental harness and its design boundaries. It is not a claim that every field accepted by the configuration schema is already operational; [Configuration](configuration.html) marks reserved or partially implemented fields.

## Product goal and boundary

FrontierOps helps a researcher understand new work after an explicitly requested Discovery run. The default briefing budget is 300 seconds, but the researcher can set another duration. Interactive HTML, OpenSlide source, and an optional narrated preview derive from one reviewed `BriefingSpec`. The harness uses an existing coding agent through portable Skills; it does not embed an LLM client, agent framework, or background scheduler.

The researcher-facing actions are `Setup → Config → Discover → Briefing`. The reproducible internal stages are `Build → Sync → Rank → Brief → Review → Render`. Setup initializes a real `frontier.yaml`; Config proposes and validates changes; Discover runs manual Sync and Rank; Briefing handles source checking, Brief, Review, and Render. Researchers need not chain the internal commands themselves.

## Hexagonal architecture

- `domain/` owns strict configuration and artifact contracts, independent of infrastructure.
- `application/` owns use cases and ports; policy such as Gate decisions and briefing selection belongs here.
- `adapters/` implements YAML, filesystem persistence, clocks, source APIs, renderers, and the CLI.
- Top-level `frontierops.build`, `frontierops.sync`, and similar modules are composition roots that wire ports to adapters.
- Dependencies point inward: adapters → application → domain. A renderer or API client must not define domain policy.

## Internal stages and files

| Stage | Input | Output and decision |
|---|---|---|
| Build | Active YAML | Validated configuration snapshot, environment report, Run manifest, state initialization. |
| Sync | Resolved config, source state | Provider records, new/updated signals, topical observations, cursor snapshot. Runs only when invoked. |
| Rank | This Run's signals and policy | Candidates, Gate traces, scores, Evidence, topic delta, Discovery HTML. |
| Brief | Candidates and optional saved selection | Development links, editable paper explanations, timed draft and narration. |
| Review | Edited draft and this Run's Evidence | Claim checks, issue report, approved spec only if blocking issues are absent. |
| Render | Approved spec and Evidence | Per-paper HTML and OpenSlide projects; optional Run-level narrated preview. |

`frontier sync --config PATH` creates Build as part of the same Run. A standalone `frontier build` is a diagnostic command and creates a different Run; it is not a prerequisite to Sync. Later stages use the exact path returned by Sync.

## Artifact contracts

| Artifact | Meaning |
|---|---|
| `ResearchSignal` | A normalized observation from a provider, with stable external ID, source, payload, and new/updated/unchanged status. Current live adapters focus on papers and submissions; release and benchmark feeds remain future extensions. |
| `Evidence` | Source content with a locator: abstract JSON pointer, PDF page/bounding box, text line range, or alphaXiv page number. Its tier distinguishes author-reported abstract text from primary full text. |
| `BriefingCandidate` | A signal transformed into a ranked paper candidate with features, Gate decisions, source IDs, metadata, and Evidence IDs. |
| `ResearchDevelopment` | A persistent cross-run grouping of related candidates with first/last seen and new/updated/unchanged status. |
| `BriefingSpec` | Renderer-neutral, timed sections, claims, Evidence references, metadata, narration, and target formats. The reviewed version is the only Render input. |
| `RunManifest` | Run ID, schema version, config hash, stage-result paths, output paths, status, and warnings. |

JSON/JSONL files are inspectable artifacts. SQLite is a rebuildable index, not the authority for briefing content. Each Run has its own directory under `.frontier/runs/`; stage files within that Run are written as the pipeline proceeds. `.frontier/state/` stores the latest successful provider state, and `.frontier/cache/raw/` currently stores normalized source-record snapshots keyed by hash. Public outputs are separate under `project.output_dir`, defaulting to `frontier_output/`. A later Run does not overwrite an earlier one.

## Configuration lifecycle

`frontier.yaml` is the active policy file. Unknown fields fail validation; secret values are not part of the schema. The Config Skill follows `schema/inspect → draft → resolve ambiguity → validate → diff → apply`. Candidate YAML under `.frontier/config-drafts/` is a proposal only. A preview-only or unresolved request must stop before Apply. The CLI's `config apply` validates and atomically writes the active file; the agent is responsible for showing the diff before invoking it.

Setup does not replace an existing YAML file. Newly created workspaces start with live sources disabled and HTML/slides selected. The committed `frontier.yaml.example` is an offline fixture, not an active workspace configuration. Stable author and venue identifiers matter more than display names; an ambiguous resolver result requires researcher confirmation. The current resolver uses offline fixtures and must not be represented as a live identity verification service.

All domain thresholds, source selections, and output preferences are represented in YAML. Some accepted fields are not yet wired into behavior: source `overlap_days`, scholar `backfill_days` and `always_include_new_publications`, Sync `default_lookback_days` and `on_provider_error: partial`, and video `fps`/`quality`. `sync.preserve_raw_responses` does not currently control caching. `review.required: false` does not bypass Review. The [configuration reference](configuration.html) documents these limits field by field; the harness must not silently claim they work.

## Ingestion and identity

- arXiv live search uses its Atom API with configured paper IDs, queries, or categories. It retains base arXiv ID and version.
- Semantic Scholar live mode fetches papers for verified author IDs and paginates author-paper results; the key is optional, subject to upstream limits. It is not a general topic search adapter.
- OpenReview uses the API 2 Python client, preserving forum, invitation, reply, and detected decision context. Credentials come from environment variables. Decision filtering is not guaranteed accepted-only when a note lacks a detected decision.
- OpenAlex searches title, abstract, and keywords for each configured topic and date window. It reconstructs the inverted-index abstract and maps `cited_by_count` to citation policy. It marks results truncated when `max_results` cuts off further pages. Basic search can run without a key.
- alphaXiv MCP supplies a small ranked topical supplement and PDF page query. `discover_papers` is top-k, not a complete sync baseline. The headless client needs an API key. The optional `frontier evidence` call converts `answer_pdf_queries` XML pages into `primary_fulltext` Evidence and saves the raw XML/query history without changing the ranking or selection.
- Local library roots are restricted to the project by default. PDFs are parsed with PyMuPDF and retain page/bounding-box locators; `.md` and `.txt` files retain line locators. A same-name `.pdf.json` sidecar can hold verified bibliographic metadata. Unknown metadata stays unknown; arXiv posting does not imply conference acceptance.

Secrets are passed only through the harness process environment. YAML records environment-variable names, not passwords, tokens, or keys. The [credentials guide](credentials.html) gives the current per-provider setup and the distinction between OpenReview account login and alphaXiv's API key.

## Manual discovery and comparison

Sync compares stable provider IDs and normalized content fingerprints with saved state. It writes changed signals, and for topical queries also writes every observation returned in the current scope—even unchanged papers—so Rank can score the current result set again. There is no timer. A provider failure currently stops Sync; partial recovery is not implemented despite the reserved config value.

The Discovery page is published at `project.output_dir/discoveries/<run-id>.html`. For each stable `profile.topics[].id`, `02-rank/topic-delta.json` compares with the latest earlier Run of that topic. It distinguishes a baseline, papers newly in a changed scope, papers published since the prior Run, papers observed only now, Gate/eligibility changes, rank/score changes, unchanged papers, and papers not returned this time. Changing the year window must not label old papers as newly published; a missing result is not evidence of withdrawal. Truncated OpenAlex pages or alphaXiv's top-k results must be flagged as incomplete coverage. Scores and extracted sentences are heuristics, not validated quality judgments.

`frontier discovery serve --run PATH` binds only to loopback. The local page validates the Run and eligible candidate IDs before writing `02-rank/briefing-selection.json`. A static HTML page cannot modify itself; it can only download a selection file for the agent to apply. The selection file is the auditable Run artifact, not a database table. Brief reads this file automatically when it exists.

## Briefing, evidence, and publication

Brief groups related candidates, records their development history, and normally suppresses unchanged developments. It honors `brief.target_duration_seconds`, `maximum_developments`, and per-development limits. Its deterministic explanation is a scaffold: an agent must check the actual paper's problem, mechanism, experiments, limitations, author/venue metadata, and any selected figures. Claims must cite this Run's Evidence. A paper's exact source excerpt is checked against its cited Evidence; invented quotations, figures, benchmark numbers, or venues are unacceptable.

Review is the publication boundary. It checks schema, duration, duplicate developments, Evidence IDs, missing citations, unsupported numeric strings, and exact excerpts. These checks do not establish semantic truth: the agent or researcher still has to determine whether a page actually supports the claim. Render reads only `04-review/briefing.approved.json`; a failed draft must not be published as approved output.

Render publishes an interactive per-paper HTML explanation and editable OpenSlide project under `project.output_dir/briefings/<run-id>/papers/paper-N/`, with a public `manifest.json` mapping each paper to its files. The aggregate root view remains for compatibility. A repeated Render of one Run creates a numbered public directory rather than replacing the previous publication. HTML presents navigable problem/method/result/limitation content, expandable Evidence, source links, and figures where available. The slide project is OpenSlide v2 React `Page[]` source; `npm run build` produces its static presentation. No automatic PPTX export is claimed.

Source figures from cited local PDFs are preferred over decorative graphics. Extracted visuals are recorded in `assets-manifest.json` with figure/page provenance. Figure extraction may fail without blocking text output; absence of a usable figure must be stated, not disguised with a fabricated paper figure. Slides should separate a dense figure from its explanation and keep notes specific to each page.

The optional video path uses an external HeyGen TTS adapter and HyperFrames preview composition. FrontierOps does not implement the TTS client or store its credentials. The preview is Run-level and inspectable; it is not a final MP4. Until the preview is explicitly reviewed and a separate export is authorized, `video` remains a missing target and the Run is not reported as fully rendered. Do not incur TTS or export costs without researcher approval.

## Runtime and verification

Python 3.12 and `uv >=0.12.20,<0.14` are supported. CI tests uv 0.12 and 0.13 with the checked-in lockfile. Unit tests cover deterministic policy; integration tests cover source adapters, stages, storage, CLI, and the documentation site. Use `uv run --locked python -m unittest discover -s tests` from the repository root. `uv run --locked frontier` also requires running from that checkout; an installed uv tool can be called as `frontier` from a research workspace.

Acceptance of a new source or renderer requires a verified adapter contract, inspectable stage artifact, explicit failure state, and a real source link. Full end-to-end quality of a scientific explanation cannot be inferred from a passing structural Review or renderer build alone.
