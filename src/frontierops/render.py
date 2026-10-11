"""Composition root and persistence boundary for Render."""

from datetime import datetime, timezone
from pathlib import Path

from frontierops.adapters.html import StaticHtmlRenderer
from frontierops.adapters.render_assets import materialize_local_evidence
from frontierops.adapters.slides import StaticSlideRenderer
from frontierops.adapters.storage import FileArtifactStore
from frontierops.application.render import RenderService
from frontierops.domain.models import BriefingSpec, Evidence, StageResult


def run_render(run_dir: Path) -> Path:
    store = FileArtifactStore(run_dir)
    briefing = BriefingSpec.model_validate(
        store.read_json(Path("04-review/briefing.approved.json"))
    )
    evidence = [Evidence.model_validate(item) for item in
                store.read_jsonl(Path("02-rank/evidence.jsonl"))]
    resolution = store.read_json(Path("00-build/config-resolution.json"))
    evidence, assets = materialize_local_evidence(
        evidence, Path(resolution["source_path"]).parent, run_dir / "05-render"
    )
    started = datetime.now(timezone.utc)
    output = RenderService().execute(
        briefing, evidence, [StaticHtmlRenderer(), StaticSlideRenderer()]
    )
    paths = {"html": "05-render/briefing.html", "slides": "05-render/slides.html"}
    for target, document in output.documents.items():
        store.write_text(Path(paths[target]), document)
    status = "partial" if output.missing_targets else "success"
    render_result = {
        "schema_version": "0.1", "briefing_id": briefing.artifact_id,
        "outputs": {target: paths[target] for target in output.documents},
        "claim_fingerprints": output.claim_fingerprints,
        "missing_targets": output.missing_targets,
    }
    store.write_json(Path("05-render/render-result.json"), render_result)
    store.write_json(Path("05-render/assets-manifest.json"), {"assets": assets})
    result = StageResult(
        run_id=run_dir.name, stage="render", status=status, started_at=started,
        finished_at=datetime.now(timezone.utc),
        input_refs=["04-review/briefing.approved.json", "02-rank/evidence.jsonl"],
        outputs={**render_result["outputs"], "result": "05-render/render-result.json",
                 "assets": "05-render/assets-manifest.json"},
        counts={"outputs": len(output.documents), "claims": len(output.claim_fingerprints)},
        warnings=[f"renderer unavailable: {target}" for target in output.missing_targets],
        next_stage_allowed=not output.missing_targets,
    )
    store.write_json(Path("05-render/stage-result.json"), result.model_dump(mode="json"))
    manifest = store.read_json(Path("run-manifest.json"))
    manifest["stages"]["render"] = "05-render/stage-result.json"
    manifest["status"] = "partial_success" if output.missing_targets else "success"
    manifest["outputs"].update(render_result["outputs"])
    manifest["outputs"]["render_result"] = "05-render/render-result.json"
    manifest["outputs"]["render_assets"] = "05-render/assets-manifest.json"
    manifest["warnings"] = list(dict.fromkeys([*manifest["warnings"], *result.warnings]))
    store.write_json(Path("run-manifest.json"), manifest)
    return run_dir
