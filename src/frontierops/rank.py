"""Composition root and filesystem boundary for Rank."""

from datetime import datetime, timezone
from pathlib import Path

from frontierops.adapters.config import YamlConfigAdapter
from frontierops.adapters.storage import FileArtifactStore
from frontierops.application.rank import RankService
from frontierops.domain.models import FrontierConfig, ResearchSignal, StageResult


def run_rank(run_dir: Path) -> Path:
    store = FileArtifactStore(run_dir)
    config = FrontierConfig.model_validate(
        YamlConfigAdapter().read(run_dir / "00-build/resolved-config.yaml")
    )
    signals = [
        ResearchSignal.model_validate(item)
        for item in store.read_jsonl(Path("01-sync/research-signals.jsonl"))
    ]
    started = datetime.now(timezone.utc)
    output = RankService().execute(config, signals, started)
    store.write_jsonl(Path("02-rank/evidence.jsonl"), [item.model_dump(mode="json") for item in output.evidence])
    store.write_jsonl(Path("02-rank/briefing-candidates.jsonl"), [item.model_dump(mode="json") for item in output.candidates])
    store.write_jsonl(Path("02-rank/excluded-candidates.jsonl"), [item.model_dump(mode="json") for item in output.excluded])
    store.write_json(Path("02-rank/ranking-report.json"), output.report)
    result = StageResult(
        run_id=run_dir.name, stage="rank", status="success", started_at=started,
        finished_at=datetime.now(timezone.utc), input_refs=["01-sync/research-signals.jsonl"],
        outputs={"candidates": "02-rank/briefing-candidates.jsonl",
                 "evidence": "02-rank/evidence.jsonl", "report": "02-rank/ranking-report.json"},
        counts=output.report["counts"], next_stage_allowed=True,
    )
    store.write_json(Path("02-rank/stage-result.json"), result.model_dump(mode="json"))
    manifest = store.read_json(Path("run-manifest.json"))
    manifest["stages"]["rank"] = "02-rank/stage-result.json"
    manifest["outputs"]["briefing_candidates"] = "02-rank/briefing-candidates.jsonl"
    store.write_json(Path("run-manifest.json"), manifest)
    return run_dir
