"""Composition root and persistence boundary for Brief."""

from datetime import datetime, timezone
from pathlib import Path

from frontierops.adapters.config import YamlConfigAdapter
from frontierops.adapters.storage import FileArtifactStore
from frontierops.application.brief import BriefService
from frontierops.domain.models import BriefingCandidate, FrontierConfig, StageResult


def run_brief(run_dir: Path) -> Path:
    store = FileArtifactStore(run_dir)
    config = FrontierConfig.model_validate(
        YamlConfigAdapter().read(run_dir / "00-build/resolved-config.yaml")
    )
    candidates = [BriefingCandidate.model_validate(item) for item in
                  store.read_jsonl(Path("02-rank/briefing-candidates.jsonl"))]
    workspace = run_dir.parent.parent
    state = FileArtifactStore(workspace / "state")
    history = state.read_jsonl(Path("development-index.jsonl"))
    started = datetime.now(timezone.utc)
    output = BriefService().execute(config, candidates, history, run_dir.name, started)
    store.write_jsonl(Path("03-brief/research-developments.jsonl"),
                      [item.model_dump(mode="json") for item in output.developments])
    store.write_json(Path("03-brief/development-link-report.json"), output.link_report)
    store.write_json(Path("03-brief/briefing.draft.json"), output.briefing.model_dump(mode="json"))
    store.write_text(Path("03-brief/briefing.draft.md"), output.markdown)
    store.write_json(Path("03-brief/narration-script.json"), {
        "sections": [{"id": item.id, "duration_seconds": item.duration_seconds,
                      "script": item.narration_script} for item in output.briefing.sections]
    })
    store.write_json(Path("03-brief/assets-manifest.json"), {"assets": []})
    result = StageResult(
        run_id=run_dir.name, stage="brief", status="success", started_at=started,
        finished_at=datetime.now(timezone.utc),
        input_refs=["02-rank/briefing-candidates.jsonl", "02-rank/evidence.jsonl"],
        outputs={"briefing": "03-brief/briefing.draft.json",
                 "developments": "03-brief/research-developments.jsonl"},
        counts={"developments": len(output.developments),
                "selected": len(output.briefing.sections)}, next_stage_allowed=True,
    )
    store.write_json(Path("03-brief/stage-result.json"), result.model_dump(mode="json"))
    manifest = store.read_json(Path("run-manifest.json"))
    manifest["stages"]["brief"] = "03-brief/stage-result.json"
    manifest["outputs"]["briefing_draft"] = "03-brief/briefing.draft.json"
    store.write_json(Path("run-manifest.json"), manifest)
    state.write_jsonl(Path("development-index.jsonl"), output.history)
    return run_dir
