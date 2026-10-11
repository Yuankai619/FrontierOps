---
name: frontier-discover
description: On researcher request, sync newly available papers and publish an inspectable HTML discovery report with inclusion reasons and ranking scores. Use when asked what new research is worth reading.
---

# FrontierOps Discover

This is the researcher-facing entry point for internal Build → Sync → Rank. There is no scheduler. Resolve the active `<workspace>/frontier.yaml`; if absent, guide Setup/Config first. Confirm that enabled sources match the user's intended scope.

1. Validate config. Run `frontier sync --config <workspace>/frontier.yaml` and capture the single Run path printed by the CLI. Inspect `01-sync/stage-result.json` for new-item count and provider failures. A partial provider failure is not evidence of no new papers.
2. Run `frontier rank --run <same-run-path>`. Inspect `02-rank/ranking-report.json`, `02-rank/briefing-candidates.jsonl`, and `run-manifest.json`. Gates decide eligibility; weighted features sort eligible papers, not their scientific truth.
3. Present the actual `outputs.public_discovery_html` path from the manifest. The report shows this Run beside prior Runs, separates newly discovered from previously seen papers, and allows selecting eligible candidates. To save choices without a database, start `frontier discovery serve --run <same-run-path>` as a local process and give the researcher its loopback URL. The page saves `02-rank/briefing-selection.json` in the Run. If a server cannot stay running, the static page downloads that JSON; place it at the same path after checking its Run ID. Do not suggest that the browser can directly rewrite its own HTML file.
4. If the researcher did not choose any specific paper, leave Briefing unstarted. Do not turn a heuristic problem/core-idea sentence into an asserted summary without checking the source; show paper title, source, delta type and ranking reasons first.

Do not auto-run Brief/Review/Render. Return the Run path for a later `frontier-briefing` request. If no new signals, explain the baseline and errors instead of fabricating recommendations.
