# FrontierOps Agent Guide

## Product boundary

- FrontierOps is an agent-agnostic research briefing harness, not an agent framework.
- Sync is user-triggered and compares with the last successful sync; do not add a background scheduler to the MVP.
- The primary user outcome is a grounded explanation of new papers.
- Domain policy belongs in `frontier.yaml`, never in hidden constants.
- HTML, slides, and narrated video must consume the same approved `BriefingSpec`.

## Change workflow

- Never push implementation changes directly to `main`; every change goes through a pull request.
- Use an English Conventional Commit-style PR title, for example `feat: add build stage`.
- Write the PR description in Traditional Chinese.
- Keep each PR at or below 600 changed source, test, and documentation lines. Lockfiles, caches, and generated package artifacts are excluded.
- Keep each PR focused on one independently reviewable outcome.
- Update `docs/system-spec.md` when behavior, schemas, commands, or architecture change.
- Preserve the dependency direction: adapters -> application -> domain; wire dependencies only at composition roots.

## Engineering quality

- Add unit tests for deterministic logic whenever feasible.
- Add integration tests at stage, adapter, storage, or CLI boundaries whenever feasible.
- Explain untested behavior in the PR description.
- Preserve raw inputs and use stable, versioned artifact contracts.
- Persist resolved scholar and venue IDs; never use a display name as durable identity.
- Keep ambiguous resolver candidates visible for user confirmation.
- Reject unknown config fields. Never materialize secret values in resolved config or run artifacts.
- Do not commit `.frontier/`, virtual environments, caches, rendered media, or credentials.

## Local checks

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests
```
