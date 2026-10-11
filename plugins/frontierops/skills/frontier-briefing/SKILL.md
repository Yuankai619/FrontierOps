---
name: frontier-briefing
description: Explain selected new research papers and publish reviewed interactive HTML, OpenSlide slides, and optional narrated HyperFrames preview. Use when a researcher asks for a paper briefing or presentation.
---

# FrontierOps Briefing

This is the researcher-facing entry point for internal Brief → Review → Render. If no Discovery Run exists, ask whether to invoke `frontier-discover` now; do not sync implicitly. If several Runs exist, clarify which one. Use the same Run path throughout.

Before editing a paper explanation or presentation, read [paper-briefing.md](references/paper-briefing.md). It defines the source checks and editorial shape expected for a CS paper briefing.

1. Inspect the selected Run's discovery HTML, candidates, Evidence, and optional `02-rank/briefing-selection.json`. A saved selection from the Discover page applies automatically; do not ask the researcher to repeat it. If no selection exists and several papers qualify, ask which ones to cover; if one qualifies, use it. Ask about depth or output format only if neither the user's request nor `frontier.yaml` settles it. The goal is to explain each paper's problem, method, experimental support, and limitations.
2. Run `frontier brief --run <run-path>`. Check `03-brief/briefing.draft.json` against the paper/PDF. The deterministic first draft is a scaffold, not publication-ready analysis. Correct the problem, contribution, mechanism, experiment and limitation against primary pages; keep source facts separate from interpretation. Fill verified `paper_metadata` and, when no suitable figure exists, exact `source_excerpts`. Never invent a benchmark result, paper figure or venue. Preserve schema, Evidence IDs, timing and narration.
3. Run `frontier review --run <run-path>`. If it fails, use `04-review/review-report.json` and claim checks to correct the draft and rerun Review. Never forge `briefing.approved.json` or publish a failed draft.
4. Run `frontier render --run <run-path>`. Read `05-render/render-result.json` and the public `manifest.json`. Each selected paper has its own `papers/paper-N/html/` and `papers/paper-N/slides/`; the root aggregate output is for backwards compatibility, not the primary handoff. Give the researcher the exact per-paper paths rather than implying five papers are one deck.
5. For each paper's slides, work inside that OpenSlide project. Install its JS dependencies, run `npm run sync:skills`, then follow the framework's `/slide-authoring` skill to improve a one-claim-per-slide academic deck; `npm run build` verifies it. For video, follow the installed HyperFrames skill only if enabled, inspect scenes and captions, and distinguish a narrated preview from a rendered MP4. Do not render/upload an MP4 or incur TTS cost without the researcher's approval. Test one HTML interaction and one source link.

The HTML, slides, and video should agree on facts and cite the same approved Evidence. Return concrete paths and a short explanation of what the paper does, with unresolved limitations.
