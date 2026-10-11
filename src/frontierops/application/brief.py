"""Cross-source development grouping and duration-aware briefing selection."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Any

from frontierops.domain.models import (
    BriefingCandidate, BriefingSection, BriefingSpec, EvidenceClaim, FrontierConfig,
    ResearchDevelopment,
)


@dataclass(frozen=True)
class BriefOutput:
    developments: list[ResearchDevelopment]
    briefing: BriefingSpec
    link_report: dict[str, Any]
    history: list[dict[str, Any]]
    markdown: str


class BriefService:
    def execute(
        self,
        config: FrontierConfig,
        candidates: list[BriefingCandidate],
        history: list[dict[str, Any]],
        run_id: str,
        now: datetime,
        selected_candidate_ids: list[str] | None = None,
    ) -> BriefOutput:
        if selected_candidate_ids is not None:
            by_id = {item.artifact_id: item for item in candidates}
            for candidate_id in selected_candidate_ids:
                candidate = by_id.get(candidate_id)
                if candidate is None or candidate.paper_explanation is None or any(
                    gate.result == "exclude" for gate in candidate.gate_trace
                ):
                    raise ValueError(f"invalid briefing selection: {candidate_id}")
            candidates = [by_id[item] for item in selected_candidate_ids]
        groups = _groups(candidates)
        previous = {item["development_id"]: item for item in history}
        developments: list[ResearchDevelopment] = []
        next_history = dict(previous)
        primary_by_development: dict[str, BriefingCandidate] = {}
        for group in groups:
            primary = max(group, key=lambda item: item.total_score)
            identity = next(
                (item.subject_id for item in group if item.subject_id.startswith("arxiv:")),
                _normalize(primary.title),
            )
            development_id = "development_" + sha256(identity.encode()).hexdigest()[:24]
            fingerprint = _fingerprint(primary.paper_explanation.model_dump(mode="json"))
            prior = previous.get(development_id)
            status = "new" if prior is None else (
                "unchanged" if prior["fingerprint"] == fingerprint else "updated"
            )
            development = ResearchDevelopment(
                artifact_id=development_id,
                run_id=run_id,
                created_at=now,
                producer="brief",
                input_refs=[item.artifact_id for item in group],
                title=primary.title,
                member_candidate_ids=[item.artifact_id for item in group],
                first_seen_run=prior["first_seen_run"] if prior else run_id,
                last_seen_run=run_id,
                status=status,
                delta_summary=("First observed" if status == "new" else
                               "Grounded explanation changed" if status == "updated" else
                               "No material change"),
            )
            developments.append(development)
            primary_by_development[development_id] = primary
            next_history[development_id] = {
                "development_id": development_id,
                "title": primary.title,
                "fingerprint": fingerprint,
                "first_seen_run": development.first_seen_run,
                "last_seen_run": run_id,
            }

        selectable = [item for item in developments if item.status != "unchanged"]
        selectable.sort(
            key=lambda item: -primary_by_development[item.artifact_id].total_score
        )
        selected = selectable[:config.brief.maximum_developments]
        sections = _sections(config, selected, primary_by_development)
        briefing = BriefingSpec(
            artifact_id="briefing_" + sha256(
                f"{run_id}:{[item.artifact_id for item in selected]}".encode()
            ).hexdigest()[:24],
            run_id=run_id,
            created_at=now,
            producer="brief",
            input_refs=[item.artifact_id for item in selected],
            title=config.project.name,
            language=config.project.language,
            target_duration_seconds=config.brief.target_duration_seconds,
            sections=sections,
            render_targets=config.brief.outputs,
        )
        return BriefOutput(
            developments=developments,
            briefing=briefing,
            link_report={
                "groups": [{"development_id": item.artifact_id,
                            "candidate_ids": item.member_candidate_ids,
                            "status": item.status} for item in developments],
                "selected": [item.artifact_id for item in selected],
                "suppressed_unchanged": [item.artifact_id for item in developments
                                         if item.status == "unchanged"],
            },
            history=[next_history[key] for key in sorted(next_history)],
            markdown=_markdown(briefing),
        )


def _groups(candidates: list[BriefingCandidate]) -> list[list[BriefingCandidate]]:
    eligible = [item for item in candidates
                if item.paper_explanation is not None
                and not any(decision.result == "exclude" for decision in item.gate_trace)]
    groups: list[list[BriefingCandidate]] = []
    for candidate in eligible:
        title = _normalize(candidate.title)
        group = next((items for items in groups
                      if _related(title, _normalize(items[0].title))), None)
        if group is None:
            groups.append([candidate])
        else:
            group.append(candidate)
    return groups


def _related(left: str, right: str) -> bool:
    return left == right or (min(len(left), len(right)) >= 8 and (left in right or right in left))


def _normalize(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _fingerprint(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _sections(
    config: FrontierConfig,
    developments: list[ResearchDevelopment],
    primary: dict[str, BriefingCandidate],
) -> list[BriefingSection]:
    sections = []
    remaining = config.brief.target_duration_seconds
    for index, development in enumerate(developments):
        slots = len(developments) - index
        duration = min(config.brief.maximum_seconds_per_development, max(1, remaining // slots))
        candidate = primary[development.artifact_id]
        explanation = candidate.paper_explanation
        claims = [EvidenceClaim(
            text=statement.text,
            kind=statement.kind,
            evidence_ids=statement.evidence_ids,
        ) for name, statement in explanation if name != "resources"]
        script = " ".join(claim.text for claim in claims)
        word_budget = max(1, duration * config.brief.narration_words_per_minute // 60)
        script = " ".join(script.split()[:word_budget])
        sections.append(BriefingSection(
            id=f"paper-{index + 1}",
            duration_seconds=duration,
            headline=development.title,
            claims=claims,
            development_id=development.artifact_id,
            paper_explanation=explanation,
            paper_metadata=candidate.paper_metadata,
            narration_script=script,
            caption_text=script,
            visual_hint="Show the problem, method, experiment, and limitation with evidence links.",
        ))
        remaining -= duration
    return sections


def _markdown(briefing: BriefingSpec) -> str:
    lines = [f"# {briefing.title}", ""]
    for section in briefing.sections:
        lines.extend([f"## {section.headline}", ""])
        for claim in section.claims:
            lines.append(f"- {claim.text} `{' '.join(claim.evidence_ids)}`")
        lines.append("")
    return "\n".join(lines)
