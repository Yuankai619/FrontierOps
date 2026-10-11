---
name: frontier-briefing
description: Explain selected new research papers and publish reviewed interactive HTML, OpenSlide slides, and optional narrated HyperFrames preview. Use when a researcher asks for a paper briefing or presentation.
---

# FrontierOps Briefing

This is the researcher-facing entry point for internal Brief → Review → Render. If no Discovery Run exists, ask whether to invoke `frontier-discover` now; do not sync implicitly. If several Runs exist, clarify which one. Use the same Run path throughout.

1. Inspect the selected Run's discovery HTML, candidates, and Evidence. Agree on paper(s) and explanation depth. The goal is to explain each paper's problem, method, experimental support, and limitations, not recite titles or scores. Respect the active YAML duration and requested formats.
2. Run `frontier brief --run <run-path>`. Check `03-brief/briefing.draft.json` against the paper/PDF. Separate a sourced fact from interpretation. Prefer a cited figure or passage; never invent a benchmark result, paper figure, or numerical claim. Edit the draft only when the correction is supported and preserves the schema, Evidence IDs, timing, and narration.
3. Run `frontier review --run <run-path>`. If it fails, use `04-review/review-report.json` and claim checks to correct the draft and rerun Review. Never forge `briefing.approved.json` or publish a failed draft.
4. Run `frontier render --run <run-path>`. Read `05-render/render-result.json` and `run-manifest.json`; report the actual `public_output_dir`, normally `frontier_output/briefings/<run-id>/`, and which targets are generated, missing, or previews.
5. For slides, work inside the generated OpenSlide project. Install its JS dependencies, run `npm run sync:skills`, then follow the framework's `/slide-authoring` skill to improve a one-claim-per-slide academic deck; `npm run build` verifies it. For video, follow the installed HyperFrames skill only if enabled, inspect scenes and captions, and distinguish a narrated preview from a rendered MP4. Do not render/upload an MP4 or incur TTS cost without the researcher's approval. Test one HTML interaction and one source link.

The HTML, slides, and video should agree on facts and cite the same approved Evidence. Avoid decorative uppercase eyebrows, pill grids, fake paper visuals, and repeated generic cards. Return concrete paths and a short explanation of what the paper does, with unresolved limitations.
