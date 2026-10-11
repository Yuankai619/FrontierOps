"""Composition root and persistence boundary for Render."""

from datetime import datetime, timezone
from pathlib import Path
import shutil

from frontierops.adapters.config import YamlConfigAdapter
from frontierops.adapters.html import StaticHtmlRenderer
from frontierops.adapters.publish import FilesystemOutputPublisher
from frontierops.adapters.render_assets import materialize_local_evidence
from frontierops.adapters.slides import OpenSlideRenderer
from frontierops.adapters.storage import FileArtifactStore
from frontierops.adapters.video import HeyGenNarrator, HyperFramesPreviewRenderer, infer_tts_language
from frontierops.adapters.visuals import extract_paper_visuals
from frontierops.application.render import RenderService
from frontierops.domain.models import BriefingSpec, Evidence, FrontierConfig, StageResult


def run_render(run_dir: Path) -> Path:
    store = FileArtifactStore(run_dir)
    config = FrontierConfig.model_validate(
        YamlConfigAdapter().read(run_dir / "00-build/resolved-config.yaml")
    )
    briefing = BriefingSpec.model_validate(
        store.read_json(Path("04-review/briefing.approved.json"))
    )
    evidence = [Evidence.model_validate(item) for item in
                store.read_jsonl(Path("02-rank/evidence.jsonl"))]
    resolution = store.read_json(Path("00-build/config-resolution.json"))
    evidence, assets = materialize_local_evidence(
        evidence, Path(resolution["source_path"]).parent, run_dir / "05-render"
    )
    visuals = extract_paper_visuals(
        briefing, evidence, run_dir / "05-render", config.ranking.max_fulltext_pages
    )
    started = datetime.now(timezone.utc)
    output = RenderService().execute(
        briefing, evidence, [StaticHtmlRenderer(visuals), OpenSlideRenderer(visuals)]
    )
    paths = {"html": "05-render/briefing.html",
             "slides": "05-render/open-slide/slides/frontier-briefing/index.tsx"}
    for target, document in output.documents.items():
        store.write_text(Path(paths[target]), document)
    if "slides" in output.documents:
        for relative, document in OpenSlideRenderer.project_files().items():
            store.write_text(Path("05-render/open-slide") / relative, document)
        for visual in visuals.values():
            source = run_dir / "05-render" / str(visual["uri"])
            target = run_dir / "05-render/open-slide/assets" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    paper_outputs = _render_paper_outputs(briefing, evidence, visuals, run_dir)
    preview_path = _prepare_video_preview(config, briefing, evidence, visuals, run_dir, resolution)
    status = "partial" if output.missing_targets else "success"
    render_result = {
        "schema_version": "0.1", "briefing_id": briefing.artifact_id,
        "outputs": {target: paths[target] for target in output.documents},
        "claim_fingerprints": output.claim_fingerprints,
        "missing_targets": output.missing_targets,
        "papers": paper_outputs,
    }
    if preview_path:
        render_result["outputs"]["video_preview"] = preview_path
    output_root = config.project.output_dir
    if not output_root.is_absolute():
        output_root = Path(resolution["source_path"]).parent / output_root
    public_dir = FilesystemOutputPublisher().publish(
        run_dir, output_root, render_result["outputs"], paper_outputs
    )
    render_result["public_output_dir"] = str(public_dir)
    store.write_json(Path("05-render/render-result.json"), render_result)
    store.write_json(Path("05-render/assets-manifest.json"), {"assets": assets, "visuals": visuals})
    result = StageResult(
        run_id=run_dir.name, stage="render", status=status, started_at=started,
        finished_at=datetime.now(timezone.utc),
        input_refs=["04-review/briefing.approved.json", "02-rank/evidence.jsonl"],
        outputs={**render_result["outputs"], "result": "05-render/render-result.json",
                 "assets": "05-render/assets-manifest.json"},
        counts={"outputs": len(output.documents), "claims": len(output.claim_fingerprints)},
        warnings=[
            "video awaiting preview approval" if target == "video" and preview_path
            else f"renderer unavailable: {target}" for target in output.missing_targets
        ],
        next_stage_allowed=not output.missing_targets,
    )
    store.write_json(Path("05-render/stage-result.json"), result.model_dump(mode="json"))
    manifest = store.read_json(Path("run-manifest.json"))
    manifest["stages"]["render"] = "05-render/stage-result.json"
    manifest["status"] = "partial_success" if output.missing_targets else "success"
    manifest["outputs"].update(render_result["outputs"])
    manifest["outputs"]["public_output_dir"] = str(public_dir)
    manifest["outputs"]["render_result"] = "05-render/render-result.json"
    manifest["outputs"]["render_assets"] = "05-render/assets-manifest.json"
    manifest["warnings"] = list(dict.fromkeys([*manifest["warnings"], *result.warnings]))
    store.write_json(Path("run-manifest.json"), manifest)
    return run_dir


def _render_paper_outputs(briefing: BriefingSpec, evidence: list[Evidence],
                          visuals: dict[str, dict], run_dir: Path) -> list[dict[str, str]]:
    """Keep a separate portable HTML and OpenSlide project for each paper."""
    store = FileArtifactStore(run_dir)
    result: list[dict[str, str]] = []
    targets = [target for target in briefing.render_targets if target in {"html", "slides"}]
    for section in briefing.sections:
        paper_spec = briefing.model_copy(update={
            "artifact_id": f"{briefing.artifact_id}-{section.id}",
            "title": section.headline, "sections": [section], "render_targets": targets,
        })
        documents = RenderService().execute(
            paper_spec, evidence, [StaticHtmlRenderer(visuals), OpenSlideRenderer(visuals)]
        ).documents
        base = Path("05-render/papers") / section.id
        output = {"section_id": section.id, "title": section.headline}
        if "html" in documents:
            path = base / "briefing.html"
            store.write_text(path, documents["html"])
            output["html"] = str(path)
        if "slides" in documents:
            project = base / "open-slide"
            path = project / "slides/frontier-briefing/index.tsx"
            store.write_text(path, documents["slides"])
            for relative, content in OpenSlideRenderer.project_files().items():
                store.write_text(project / relative, content)
            visual = visuals.get(section.id)
            if visual:
                source = run_dir / "05-render" / str(visual["uri"])
                target = run_dir / project / "assets" / source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            output["slides"] = str(path)
        result.append(output)
    return result


def _prepare_video_preview(
    config: FrontierConfig, briefing: BriefingSpec, evidence: list[Evidence],
    visuals: dict[str, dict], run_dir: Path, resolution: dict,
) -> str | None:
    settings = config.rendering.video
    if not settings.enabled or "video" not in briefing.render_targets:
        return None
    assert settings.heygen_tts_script is not None
    source_dir = Path(resolution["source_path"]).parent
    adapter = settings.heygen_tts_script
    adapter = adapter if adapter.is_absolute() else source_dir / adapter
    project = run_dir / "05-render/hyperframes"
    script = "\n\n".join(section.narration_script for section in briefing.sections).strip()
    if not script:
        raise ValueError("video preview requires a non-empty narration script")
    language = settings.language or infer_tts_language(script)
    narration = HeyGenNarrator(adapter.resolve(), settings.voice_id).synthesize(
        script, project, language
    )
    documents = HyperFramesPreviewRenderer(visuals).render(
        briefing, narration, settings.width, settings.height, evidence
    )
    store = FileArtifactStore(run_dir)
    for relative_path, document in documents.items():
        store.write_text(Path("05-render/hyperframes") / relative_path, document)
    for visual in visuals.values():
        source = run_dir / "05-render" / str(visual["uri"])
        target = project / "assets" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return "05-render/hyperframes/index.html"
