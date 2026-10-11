---
name: frontier-config
description: Turn a researcher's natural-language topic, scholars, venues, filters, duration, and outputs into a validated active frontier.yaml. Use for FrontierOps configuration requests, not for syncing papers.
---

# FrontierOps Config

1. Locate the research workspace and active `frontier.yaml`. If missing, invoke `frontier-setup` first. Read `frontier schema config --format json` and `frontier config inspect --config <active-yaml>`; never use `.example` as the active configuration.
2. Interpret the user's description. If the research topic or at least one source (a paper ID, local PDF library, scholar, venue, or provider query) is unclear, ask a concise, grouped follow-up. Ask about desired format or duration only when it materially affects the result; otherwise keep existing values (new workspaces default to 300 seconds and HTML/slides). Do not invent a scholar ID, venue ID, API key, or unstated citation threshold.
3. Create a candidate with `frontier config draft --config <active-yaml> --output <temporary-candidate>`. Modify only requested fields in that candidate. For a scholar or venue, call `frontier scholar resolve` or `frontier venue resolve` and show ambiguous candidates to the user. Current resolvers are fixtures, not live authority; verify a real stable ID before claiming a live subscription. A source can also be a local PDF directory configured under `sources.local_library`.
4. Run `frontier config validate --config <temporary-candidate>` and `frontier config diff --old <active-yaml> --new <temporary-candidate>`. Explain changed monitoring scope, Gates, time budget, formats, and source limitations in ordinary language. If the request was preview-only or identities are unresolved, stop before apply.
5. For an authorized change, run `frontier config apply --candidate <temporary-candidate> --config <active-yaml>`, then inspect the active file. Keep secret **values** out of YAML; store environment variable names only.

Output: active YAML path, short summary of settings, validation result, diff/remaining questions, and whether the candidate was applied. Configuration never triggers Sync automatically.
