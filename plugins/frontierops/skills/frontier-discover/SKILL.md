---
name: frontier-discover
description: On researcher request, sync newly available papers and publish an inspectable HTML discovery report with inclusion reasons and ranking scores. Use when asked what new research is worth reading.
---

# FrontierOps Discover

This is the researcher-facing entry point for internal Build → Sync → Rank. There is no scheduler. Resolve the active `<workspace>/frontier.yaml`; if absent, guide Setup/Config first. Confirm that enabled sources match the user's intended scope.

1. Validate config. Run `frontier sync --config <workspace>/frontier.yaml` and capture the single Run path printed by the CLI. Inspect `01-sync/stage-result.json` for new-item count and provider failures. A partial provider failure is not evidence of no new papers.
2. Run `frontier rank --run <same-run-path>`. Inspect `02-rank/ranking-report.json`, `02-rank/briefing-candidates.jsonl`, and `run-manifest.json`. Gates decide eligibility; weighted features sort eligible papers, not their scientific truth.
3. Present the actual `outputs.public_discovery_html` path from the manifest, normally `frontier_output/discoveries/<run-id>.html`. The HTML allows search, eligible/excluded filtering, and inspection of Gate/score contributions. Summarize a few candidates by research problem and core idea, distinguishing full-text vs. abstract-only Evidence.

Do not auto-run Brief/Review/Render. Return the Run path for a subsequent `frontier-briefing` request. If no new signals, explain the source baseline and errors instead of fabricating recommendations.
