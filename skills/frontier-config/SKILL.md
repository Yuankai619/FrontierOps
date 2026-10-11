---
name: frontier-config
description: Create or safely update a FrontierOps frontier.yaml from natural-language monitoring, tracker, and briefing requirements by inspecting the schema, resolving identities, validating a candidate, showing a semantic diff, and applying atomically. Use when configuring FrontierOps; do not use it to run Sync or render a briefing.
---

# Frontier Config

Translate a user's natural-language requirements into a reviewable FrontierOps configuration change. Use the host coding agent for reasoning and file editing; do not add an LLM SDK or agent framework.

## Workflow

1. Work from the FrontierOps repository root. Use the existing `frontier.yaml`; if it does not exist, use `frontier.yaml.example` as the source.
2. Read the current contract and effective values:

   ```bash
   uv run --locked frontier schema config --format json
   uv run --locked frontier config inspect --config <source-config>
   ```

3. Create a temporary candidate. Never edit the active configuration directly.

   ```bash
   uv run --locked frontier config draft --config <source-config> --output <candidate-path>
   ```

4. Edit only the candidate to express the request. Preserve unrelated values. Keep policies, thresholds, trackers, duration, and outputs in YAML rather than source code.
5. Resolve every newly requested scholar or venue before adding its tracker:

   ```bash
   uv run --locked frontier scholar resolve --name <name> --provider semantic_scholar
   uv run --locked frontier venue resolve --name <venue> --year <year> --provider openreview
   ```

   - With no candidate, ask for a more precise identity; never invent an ID.
   - With multiple candidates, show `stable_id`, name, affiliation, paper count, and profile URL, then ask the user to choose. Stop before apply.
   - With exactly one candidate, store its stable ID and useful display metadata in the tracker.
   - Resolver fixtures are offline contract data. Do not describe fixture output as live provider verification.

6. Validate and compare the materialized candidate:

   ```bash
   uv run --locked frontier config validate --config <candidate-path>
   uv run --locked frontier config diff --old <source-config> --new <candidate-path>
   ```

7. Present the validation result, semantic JSON-path diff, identity decisions, and assumptions. For a preview request, stop here.
8. Apply only when the user requested a change, validation succeeded, and no identity ambiguity remains:

   ```bash
   uv run --locked frontier config apply --candidate <candidate-path> --config <active-config>
   uv run --locked frontier config inspect --config <active-config>
   ```

## Configuration Rules

- Never place API keys or secret values in YAML; store only environment-variable names.
- Default `brief.target_duration_seconds` to `300` only when the user gives no duration. Accept any positive configured duration.
- Do not use a display name as a durable scholar or venue identity.
- Do not apply on validation failure, unresolved ambiguity, or a diff containing unrelated changes.
- Do not run `frontier sync`, generate content, or render outputs as part of this Skill.

## Response Contract

Report the source and candidate paths, validation status, identity resolution decisions, semantic diff, assumptions, and whether the candidate was applied. If blocked, state exactly which identity or field needs user confirmation.
