---
name: frontier-setup
description: Install the FrontierOps harness with uv and initialize a research workspace with a real frontier.yaml and output directory. Use when a researcher asks to set up or load FrontierOps.
---

# FrontierOps Setup

The installed plugin supplies instructions, not the Python executable. Perform this one guided setup for the researcher's chosen workspace; do not pretend plugin installation alone installed the Harness.

1. With a bare `setup` request, use the current research directory as the workspace and its folder name as the project name. Ask only if there is no clear current project or more than one plausible target. Check `uv --version`, `git --version`, and, for slides/video, `node --version` and `npm --version`. If `uv` is absent, link to the [official installer](https://docs.astral.sh/uv/getting-started/installation/) and stop; do not run an unreviewed shell installer.
2. If this is a local FrontierOps development checkout, use `uv sync --locked` there and invoke `uv run --locked frontier` from it. This runs the library from that checkout's virtual environment; it does not copy source files into the research workspace. Otherwise install the Harness with `uv tool install git+https://github.com/Yuankai619/FrontierOps.git`. This installs a packaged Python tool in uv's tool environment, not a source checkout in the research workspace. For a private repository, use existing Git credentials; never request or print a token. Confirm the executable with `frontier --help`, using `uv tool dir --bin` to locate it if needed. Do not replace an unrelated existing `frontier` executable silently.
3. Run `frontier setup --workspace <workspace-path> --name <research-project-name>`. This creates `frontier.yaml` and `frontier_output/`; it does not overwrite an existing config. Inspect the reported `created_config` before editing anything. If an existing config fails validation, report it and use the Config skill only with the user's approval.
4. Check `frontier config validate --config <workspace-path>/frontier.yaml`. The new config intentionally has live sources disabled until Config identifies a topic/source. Do not claim papers were synced.
5. For slides, Node/npm are prerequisites; the generated OpenSlide project receives its framework skills using `npm run sync:skills` **inside that deck** after `npm install`. Do not copy OpenSlide skills into this plugin or generate an unrelated deck during setup. For video, HyperFrames and its skills are optional: only when requested, use the framework's `npx hyperframes skills update` and `npx hyperframes skills check`; verify installation scope and never upload media or spend TTS credits without approval.

If the researcher will use alphaXiv live discovery, install its optional MCP client with `uv sync --locked --extra alphaxiv` in a development checkout, or `uv tool install --with 'mcp>=2,<3' git+https://github.com/Yuankai619/FrontierOps.git` for a packaged tool. The alphaXiv API key must be supplied only as `ALPHAXIV_API_KEY` (or the configured environment-variable name), never in YAML or artifacts. OpenAlex's basic API can be used without a key.

Return actual config/output paths, dependency checks, installed vs. missing optional capabilities, and the next suggested action: describe research interests to `frontier-config`. Distinguish a completed base setup from optional deck/video setup.
