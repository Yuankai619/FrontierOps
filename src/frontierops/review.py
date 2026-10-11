"""Composition root and persistence boundary for Review."""

from datetime import datetime, timezone
from pathlib import Path

from frontierops.adapters.config import YamlConfigAdapter
from frontierops.adapters.storage import FileArtifactStore
from frontierops.application.review import ReviewService
from frontierops.domain.models import Evidence, FrontierConfig, StageResult


def run_review(run_dir: Path) -> Path:
    store = FileArtifactStore(run_dir)
    config = FrontierConfig.model_validate(
        YamlConfigAdapter().read(run_dir / "00-build/resolved-config.yaml")
    )
    draft = store.read_json(Path("03-brief/briefing.draft.json"))
    evidence = [Evidence.model_validate(item) for item in
                store.read_jsonl(Path("02-rank/evidence.jsonl"))]
    started = datetime.now(timezone.utc)
    output = ReviewService().execute(draft, evidence, config.review, run_dir.name, started)
    store.write_json(Path("04-review/review-report.json"), output.report.model_dump(mode="json"))
    store.write_jsonl(Path("04-review/claim-checks.jsonl"),
                      [item.model_dump(mode="json") for item in output.claim_checks])
    outputs = {"report": "04-review/review-report.json",
               "claim_checks": "04-review/claim-checks.jsonl"}
    if output.approved:
        store.write_json(Path("04-review/briefing.approved.json"),
                         output.approved.model_dump(mode="json"))
        store.write_text(Path("04-review/briefing.approved.md"),
                         (run_dir / "03-brief/briefing.draft.md").read_text(encoding="utf-8"))
        outputs["approved_briefing"] = "04-review/briefing.approved.json"
    else:
        store.remove(Path("04-review/briefing.approved.json"))
        store.remove(Path("04-review/briefing.approved.md"))
    result = StageResult(
        run_id=run_dir.name, stage="review",
        status="success" if output.approved else "failed", started_at=started,
        finished_at=datetime.now(timezone.utc), input_refs=["03-brief/briefing.draft.json"],
        outputs=outputs, counts=output.report.counts,
        errors=[item.message for item in output.report.issues if item.severity == "error"],
        warnings=[item.message for item in output.report.issues if item.severity == "warning"],
        next_stage_allowed=output.approved is not None,
    )
    store.write_json(Path("04-review/stage-result.json"), result.model_dump(mode="json"))
    manifest = store.read_json(Path("run-manifest.json"))
    manifest["stages"]["review"] = "04-review/stage-result.json"
    manifest["status"] = "success" if output.approved else "failed"
    if not output.approved:
        manifest["outputs"].pop("approved_briefing", None)
    manifest["outputs"].update(outputs)
    store.write_json(Path("run-manifest.json"), manifest)
    if not output.approved:
        raise ValueError("review blocked; inspect 04-review/review-report.json")
    return run_dir
