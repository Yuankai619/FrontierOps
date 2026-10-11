---
name: frontier-config
description: Turn a researcher's natural-language topic, scholars, venues, filters, duration, and outputs into a validated active frontier.yaml. Use for FrontierOps configuration requests, not for syncing papers.
---

# FrontierOps Config

1. Locate the research workspace and active `frontier.yaml`. If missing, invoke `frontier-setup` first. Read `frontier schema config --format json` and `frontier config inspect --config <active-yaml>`; never use `.example` as the active configuration.
2. A bare `config` request means inspect the active YAML and ask what the researcher wants to follow or change. A request such as `config https://arxiv.org/pdf/2605.31468` already identifies one paper; do not demand a longer prompt. If neither a topic nor a source can be inferred, ask one grouped follow-up. Keep existing time and formats unless changed; new workspaces default to 300 seconds and HTML/slides. Do not invent scholar IDs, venue IDs, keys, or citation thresholds.
3. For a specific arXiv PDF URL, validate its ID and host, save the PDF under the workspace `data/library/`, and place a same-name `.pdf.json` sidecar there. Record only verified title, authors, affiliations, date, arXiv ID, `publication_status: preprint` and source URL. A preprint must not be labeled as conference-accepted without evidence. Enable that local library root in YAML so figures and page evidence are available. For a scholar or venue, resolve stable IDs and show ambiguity. Current resolvers are fixtures, not live authority.
4. Create a candidate under `<workspace>/.frontier/config-drafts/` with `frontier config draft --config <active-yaml> --output <candidate>`. Modify only requested fields. The candidate is a reviewable proposed change; `frontier.yaml` remains the sole active config. Do not leave a root-level `frontier.candidate.yaml` beside the active file.
5. Validate and diff the candidate against active YAML. Explain changed source scope, Gates, time budget and formats in ordinary language. If preview-only or identities remain unresolved, stop before apply.
6. For an authorized change, apply the candidate, then inspect the active file. Keep secret **values** out of YAML; store environment variable names only.

For a continuing research topic, retain its stable `profile.topics[].id`. Put the retrieval query, providers, and publication window under `topics[].search`; changing 2025 to 2026 is a scope change, not proof that every returned 2026 paper appeared since the last run. Configure an OpenAlex citation gate only with an explicit user-requested threshold; fresh papers may need an age exemption. If alphaXiv is selected, request 3–4 concise keywords. Do not call a truncated result set complete.

Output: active YAML path, short summary of settings, validation result, diff/remaining questions, and whether the candidate was applied. Configuration never triggers Sync automatically.
