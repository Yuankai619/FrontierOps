"""Composition root and filesystem boundary for Rank."""

from datetime import datetime, timezone
from pathlib import Path

from frontierops.adapters.config import YamlConfigAdapter
from frontierops.adapters.discovery_html import render_discovery
from frontierops.adapters.storage import FileArtifactStore
from frontierops.application.rank import RankService
from frontierops.application.explain import ExplanationService
from frontierops.application.topic_delta import TopicBaseline, compare_topics
from frontierops.domain.models import BriefingCandidate, FrontierConfig, ResearchSignal, StageResult


def run_rank(run_dir: Path) -> Path:
    store = FileArtifactStore(run_dir)
    config = FrontierConfig.model_validate(
        YamlConfigAdapter().read(run_dir / "00-build/resolved-config.yaml")
    )
    changes = [
        ResearchSignal.model_validate(item)
        for item in store.read_jsonl(Path("01-sync/research-signals.jsonl"))
    ]
    observations = [
        ResearchSignal.model_validate(item)
        for item in store.read_jsonl(Path("01-sync/topic-observations.jsonl"))
    ]
    signals = [item for item in changes if not item.payload.get("topic_ids")] + observations
    started = datetime.now(timezone.utc)
    output = RankService().execute(config, signals, started)
    explanations = ExplanationService().execute(
        output.candidates, signals, output.evidence, started,
        config.ranking.deep_enrich_top_k, config.ranking.max_fulltext_pages,
    )
    evidence = output.evidence + explanations.evidence
    candidate_by_id = {item.artifact_id: item for item in explanations.candidates}
    excluded = [candidate_by_id[item.artifact_id] for item in output.excluded]
    store.write_jsonl(Path("02-rank/evidence.jsonl"), [item.model_dump(mode="json") for item in evidence])
    store.write_jsonl(Path("02-rank/briefing-candidates.jsonl"), [item.model_dump(mode="json") for item in explanations.candidates])
    store.write_jsonl(Path("02-rank/excluded-candidates.jsonl"), [item.model_dump(mode="json") for item in excluded])
    store.write_jsonl(Path("02-rank/paper-explanations.jsonl"), explanations.explanations)
    output.report["counts"]["explained"] = len(explanations.explanations)
    store.write_json(Path("02-rank/ranking-report.json"), output.report)
    cursors = store.read_json(Path("01-sync/source-cursors.after.json"))
    coverage = {name: item.get("cursor", {}).get("scopes", [])
                for name, item in cursors.get("providers", {}).items()}
    topic_delta = compare_topics(config, explanations.candidates,
                                 _topic_baselines(run_dir, config), coverage)
    store.write_json(Path("02-rank/topic-delta.json"), topic_delta)
    history, previous, config_changed = _discovery_history(run_dir, store, signals)
    discovery_html = render_discovery(
        explanations.candidates, output.report["weights"], run_id=run_dir.name,
        history=history, previous=previous, config_changed=config_changed,
        topic_delta=topic_delta,
    )
    store.write_text(Path("02-rank/discovery.html"), discovery_html)
    resolution = store.read_json(Path("00-build/config-resolution.json"))
    public_root = config.project.output_dir
    if not public_root.is_absolute():
        public_root = Path(resolution["source_path"]).parent / public_root
    public_html = public_root / "discoveries" / f"{run_dir.name}.html"
    FileArtifactStore(public_root).write_text(
        Path("discoveries") / public_html.name, discovery_html
    )
    result = StageResult(
        run_id=run_dir.name, stage="rank", status="success", started_at=started,
        finished_at=datetime.now(timezone.utc), input_refs=["01-sync/research-signals.jsonl"],
        outputs={"candidates": "02-rank/briefing-candidates.jsonl",
                 "evidence": "02-rank/evidence.jsonl",
                 "explanations": "02-rank/paper-explanations.jsonl",
                 "report": "02-rank/ranking-report.json",
                 "topic_delta": "02-rank/topic-delta.json",
                 "discovery_html": "02-rank/discovery.html"},
        counts=output.report["counts"], next_stage_allowed=True,
    )
    store.write_json(Path("02-rank/stage-result.json"), result.model_dump(mode="json"))
    manifest = store.read_json(Path("run-manifest.json"))
    manifest["stages"]["rank"] = "02-rank/stage-result.json"
    manifest["outputs"]["briefing_candidates"] = "02-rank/briefing-candidates.jsonl"
    manifest["outputs"]["topic_delta"] = "02-rank/topic-delta.json"
    manifest["outputs"]["public_discovery_html"] = str(public_html)
    store.write_json(Path("run-manifest.json"), manifest)
    return run_dir


def _topic_baselines(run_dir: Path, config: FrontierConfig) -> dict[str, TopicBaseline]:
    wanted = {topic.id for topic in config.profile.topics if topic.search is not None}
    found: dict[str, TopicBaseline] = {}
    for old in sorted(run_dir.parent.iterdir(), reverse=True):
        if old == run_dir or not (old / "02-rank/stage-result.json").is_file():
            continue
        old_store = FileArtifactStore(old)
        old_config = FrontierConfig.model_validate(
            YamlConfigAdapter().read(old / "00-build/resolved-config.yaml")
        )
        old_candidates = [BriefingCandidate.model_validate(item) for item in
                          old_store.read_jsonl(Path("02-rank/briefing-candidates.jsonl"))]
        old_cursors = old_store.read_json(Path("01-sync/source-cursors.after.json"))
        stage = old_store.read_json(Path("00-build/stage-result.json"))
        for topic in old_config.profile.topics:
            if topic.id not in wanted or topic.id in found or topic.search is None:
                continue
            found[topic.id] = TopicBaseline(
                old.name, datetime.fromisoformat(stage["started_at"]),
                topic.search.model_dump(mode="json"),
                [gate.model_dump(mode="json") for gate in old_config.ranking.gates],
                old_candidates,
                [scope for provider in topic.search.providers
                 for scope in old_cursors.get("providers", {}).get(provider, {}).get("cursor", {}).get("scopes", [])
                 if scope.get("topic_id") == topic.id],
            )
        if wanted <= found.keys():
            break
    return found


def _discovery_history(run_dir: Path, store: FileArtifactStore,
                       signals: list[ResearchSignal]) -> tuple[list[dict], list[dict], bool]:
    """Read prior immutable Runs; no separate database or rescore of old papers."""
    previous_by_subject: dict[str, dict] = {}
    timeline: list[dict] = []
    config_hashes: list[str] = []
    for old in sorted(run_dir.parent.iterdir()):
        if old == run_dir or not (old / "02-rank/stage-result.json").is_file():
            continue
        old_store = FileArtifactStore(old)
        old_sync = old_store.read_json(Path("01-sync/stage-result.json"))
        old_manifest = old_store.read_json(Path("run-manifest.json"))
        old_signals = old_store.read_jsonl(Path("01-sync/research-signals.jsonl"))
        timeline.append({"run_id": old.name,
                         "new": sum(s["kind"] == "paper.new" for s in old_signals),
                         "updated": sum(s["kind"] == "paper.updated" for s in old_signals),
                         "unchanged": old_sync["counts"].get("skipped_duplicate", 0)})
        config_hashes.append(old_manifest["config_sha256"])
        for candidate in old_store.read_jsonl(Path("02-rank/briefing-candidates.jsonl")):
            previous_by_subject[candidate["subject_id"]] = {
                "subject_id": candidate["subject_id"], "title": candidate["title"],
            }
    current_sync = store.read_json(Path("01-sync/stage-result.json"))
    timeline.append({"run_id": run_dir.name,
                     "new": sum(s.kind == "paper.new" for s in signals),
                     "updated": sum(s.kind == "paper.updated" for s in signals),
                     "unchanged": current_sync["counts"].get("skipped_duplicate", 0)})
    current_hash = store.read_json(Path("run-manifest.json"))["config_sha256"]
    return timeline, list(previous_by_subject.values()), bool(config_hashes and config_hashes[-1] != current_hash)
