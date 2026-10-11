"""Compare immutable topic snapshots without conflating scope changes with new publications."""

from dataclasses import dataclass
from datetime import datetime, date

from frontierops.domain.models import BriefingCandidate, FrontierConfig


@dataclass(frozen=True)
class TopicBaseline:
    run_id: str
    started_at: datetime
    search: dict
    gates: list[dict]
    candidates: list[BriefingCandidate]
    coverage: list[dict]


def _eligible(candidate: BriefingCandidate) -> bool:
    return not any(gate.result == "exclude" for gate in candidate.gate_trace)


def _gates(candidate: BriefingCandidate) -> dict[str, str]:
    return {gate.gate: gate.result for gate in candidate.gate_trace}


def _canonical(subject_id: str) -> str:
    if subject_id.startswith("doi:10.48550/arxiv."):
        return "arxiv:" + subject_id.removeprefix("doi:10.48550/arxiv.")
    return subject_id


def compare_topics(config: FrontierConfig, candidates: list[BriefingCandidate],
                   baselines: dict[str, TopicBaseline], coverage: dict[str, list[dict]]) -> dict:
    topics = []
    for topic in config.profile.topics:
        if topic.search is None:
            continue
        previous = baselines.get(topic.id)
        current = [item for item in candidates if topic.id in item.topic_ids]
        prior = ([item for item in previous.candidates if topic.id in item.topic_ids]
                 if previous else [])
        prior_by_id = {_canonical(item.subject_id): (index + 1, item)
                       for index, item in enumerate(prior)}
        current_ids = {_canonical(item.subject_id) for item in current}
        scope_changed = bool(previous and previous.search != topic.search.model_dump(mode="json"))
        policy_changed = bool(previous and previous.gates != [
            gate.model_dump(mode="json") for gate in config.ranking.gates
        ])
        entries = []
        for index, item in enumerate(current, 1):
            old = prior_by_id.get(_canonical(item.subject_id))
            if old is None:
                published = item.paper_metadata.published_at
                published_date = None
                if published:
                    try:
                        published_date = date.fromisoformat(published[:10])
                    except ValueError:
                        pass
                if previous is None:
                    status = "baseline"
                elif scope_changed:
                    status = "new_in_scope"
                elif published_date and published_date > previous.started_at.date():
                    status = "published_since_last_run"
                else:
                    status = "newly_observed"
            else:
                previous_item = old[1]
                if not _eligible(previous_item) and _eligible(item):
                    status = "newly_eligible"
                elif _eligible(previous_item) and not _eligible(item):
                    status = "newly_excluded"
                elif previous_item.total_score != item.total_score or _gates(previous_item) != _gates(item):
                    status = "ranking_changed"
                else:
                    status = "unchanged"
            entries.append({
                "subject_id": item.subject_id, "title": item.title, "status": status,
                "published_at": item.paper_metadata.published_at,
                "current_rank": index, "previous_rank": old[0] if old else None,
                "current_score": item.total_score,
                "previous_score": old[1].total_score if old else None,
                "current_gates": _gates(item),
                "previous_gates": _gates(old[1]) if old else None,
            })
        for index, item in enumerate(prior, 1):
            if _canonical(item.subject_id) not in current_ids:
                entries.append({"subject_id": item.subject_id, "title": item.title,
                                "status": "not_returned", "published_at": item.paper_metadata.published_at,
                                "previous_rank": index, "current_rank": None,
                                "previous_score": item.total_score, "current_score": None,
                                "previous_gates": _gates(item), "current_gates": None})
        counts = {status: sum(entry["status"] == status for entry in entries)
                  for status in sorted({entry["status"] for entry in entries})}
        sources = [scope for provider in topic.search.providers
                   for scope in coverage.get(provider, []) if scope.get("topic_id") == topic.id]
        topics.append({
            "topic_id": topic.id, "previous_run": previous.run_id if previous else None,
            "scope_changed": scope_changed, "policy_changed": policy_changed,
            "coverage": sources, "previous_coverage": previous.coverage if previous else [],
            "counts": counts, "entries": entries,
        })
    return {"schema_version": "0.1", "topics": topics}
