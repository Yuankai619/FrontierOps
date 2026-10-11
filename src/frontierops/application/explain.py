"""Deterministic, evidence-linked paper explanation enrichment."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import re

from frontierops.domain.models import (
    BriefingCandidate, Evidence, GroundedStatement, PaperExplanation, ResearchSignal,
)


@dataclass(frozen=True)
class ExplanationOutput:
    candidates: list[BriefingCandidate]
    evidence: list[Evidence]
    explanations: list[dict]


class ExplanationService:
    def execute(
        self,
        candidates: list[BriefingCandidate],
        signals: list[ResearchSignal],
        evidence: list[Evidence],
        now: datetime,
        top_k: int,
        max_pages: int,
    ) -> ExplanationOutput:
        signal_by_id = {signal.artifact_id: signal for signal in signals}
        local_signals = [item for item in signals if item.source_provider == "local_library"]
        evidence_by_source: dict[str, list[Evidence]] = {}
        for item in evidence:
            evidence_by_source.setdefault(item.source_ref, []).append(item)

        extra_evidence: list[Evidence] = []
        explanations: list[dict] = []
        enriched: list[BriefingCandidate] = []
        eligible = [
            item for item in candidates
            if not any(decision.result == "exclude" for decision in item.gate_trace)
        ]
        selected_ids = {item.artifact_id for item in eligible[:top_k]}
        for candidate in candidates:
            if candidate.artifact_id not in selected_ids:
                enriched.append(candidate)
                continue
            source = signal_by_id[candidate.research_signal_ids[0]]
            items = list(evidence_by_source.get(source.artifact_id, []))
            for document in _matching_documents(candidate.title, local_signals):
                for section in document.payload.get("sections", [])[:max_pages]:
                    if not section.get("text"):
                        continue
                    item = _page_evidence(candidate, document, section, now)
                    items.append(item)
                    extra_evidence.append(item)
            explanation = _explain(source, items)
            evidence_ids = list(dict.fromkeys(candidate.evidence_ids + [item.artifact_id for item in items]))
            enriched_candidate = candidate.model_copy(update={
                "evidence_ids": evidence_ids,
                "paper_explanation": explanation,
            })
            enriched.append(enriched_candidate)
            explanations.append({
                "candidate_id": candidate.artifact_id,
                "subject_id": candidate.subject_id,
                "title": candidate.title,
                "paper_explanation": explanation.model_dump(mode="json"),
            })
        return ExplanationOutput(enriched, extra_evidence, explanations)


def _matching_documents(
    title: str, documents: list[ResearchSignal]
) -> list[ResearchSignal]:
    normalized = _normalize(title)
    return [
        item for item in documents
        if len(_normalize(str(item.payload.get("title", "")))) >= 8
        and _normalize(str(item.payload.get("title", ""))) in normalized
    ]


def _normalize(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _page_evidence(
    candidate: BriefingCandidate,
    document: ResearchSignal,
    section: dict,
    now: datetime,
) -> Evidence:
    locator = section["locator"]
    digest = sha256(
        f"{candidate.artifact_id}:{document.artifact_id}:{locator}".encode()
    ).hexdigest()[:24]
    return Evidence(
        artifact_id=f"evidence_{digest}",
        run_id=candidate.run_id,
        created_at=now,
        producer="rank:fulltext",
        input_refs=[document.artifact_id],
        source_ref=document.artifact_id,
        source_uri=str(document.payload.get("path", document.external_id)),
        locator=locator,
        content=section["text"],
        evidence_tier="primary_fulltext",
    )


def _explain(source: ResearchSignal, evidence: list[Evidence]) -> PaperExplanation:
    corpus = [(sentence, item.artifact_id) for item in evidence for sentence in _sentences(item.content)]
    if not corpus:
        raise ValueError(f"candidate source has no explainable evidence: {source.artifact_id}")
    return PaperExplanation(
        problem=_select(corpus, ("challenge", "labor-intensive", "however", "problem")),
        core_idea=_select(corpus, ("introduce", "propose", "present")),
        method=_select(corpus, ("integrates", "method", "framework", "module")),
        novelty=_select(corpus, ("first", "novel", "new")),
        experiments=_select(corpus, ("experiment", "result", "outperform", "accuracy")),
        limitations=_select_or_interpretation(
            corpus, ("our limitation", "a limitation", "future work")
        ),
        why_it_matters=_select(corpus, ("practical", "essential", "enable", "impact")),
        resources=[str(value) for key, value in source.payload.items()
                   if key in {"pdf_url", "url", "abstract_url"} and value],
    )


def _sentences(text: str) -> list[str]:
    compact = " ".join(text.split())
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", compact) if len(item) >= 5]


def _select(corpus: list[tuple[str, str]], keywords: tuple[str, ...]) -> GroundedStatement:
    for keyword in keywords:
        for sentence, evidence_id in corpus:
            if keyword in sentence.lower():
                return GroundedStatement(text=sentence, evidence_ids=[evidence_id])
    sentence, evidence_id = corpus[0]
    return GroundedStatement(text=sentence, evidence_ids=[evidence_id])


def _select_or_interpretation(
    corpus: list[tuple[str, str]], keywords: tuple[str, ...]
) -> GroundedStatement:
    for keyword in keywords:
        for sentence, evidence_id in corpus:
            if keyword in sentence.lower():
                return GroundedStatement(text=sentence, evidence_ids=[evidence_id])
    return GroundedStatement(
        text="The available evidence does not explicitly state limitations.",
        kind="interpretation",
    )
