"""Renderer-neutral publication use case."""

from dataclasses import dataclass
from hashlib import sha256
import json

from frontierops.application.ports import BriefingRenderer
from frontierops.domain.models import BriefingSpec, Evidence


@dataclass(frozen=True)
class RenderOutput:
    documents: dict[str, str]
    claim_fingerprints: list[str]
    missing_targets: list[str]


class RenderService:
    def execute(
        self,
        briefing: BriefingSpec,
        evidence: list[Evidence],
        renderers: list[BriefingRenderer],
    ) -> RenderOutput:
        expected = claim_fingerprints(briefing)
        documents: dict[str, str] = {}
        available = {renderer.target: renderer for renderer in renderers}
        for target in briefing.render_targets:
            renderer = available.get(target)
            if renderer is not None:
                documents[target] = renderer.render(briefing, evidence)
        return RenderOutput(
            documents=documents,
            claim_fingerprints=expected,
            missing_targets=sorted(set(briefing.render_targets) - set(documents)),
        )


def claim_fingerprints(briefing: BriefingSpec) -> list[str]:
    return [
        sha256(json.dumps(claim.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
        for section in briefing.sections
        for claim in section.claims
    ]
