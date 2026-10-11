"""Transparent gate and feature ranking application service."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import log1p
import re
from typing import Any

from frontierops.domain.models import (
    BriefingCandidate, Evidence, FrontierConfig, GateConfig, GateDecision, ResearchSignal,
)


@dataclass(frozen=True)
class RankOutput:
    evidence: list[Evidence]
    candidates: list[BriefingCandidate]
    excluded: list[BriefingCandidate]
    report: dict[str, Any]


def _id(prefix: str, payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode()
    return f"{prefix}_{sha256(encoded).hexdigest()[:24]}"


class RankService:
    def execute(
        self, config: FrontierConfig, signals: list[ResearchSignal], now: datetime
    ) -> RankOutput:
        query_terms = _query_terms(config)
        evidence: list[Evidence] = []
        candidates: list[BriefingCandidate] = []
        weights = config.ranking.features.model_dump()
        enabled = {
            name: settings["weight"] for name, settings in weights.items() if settings["enabled"]
        }
        denominator = sum(enabled.values()) or 1.0
        for signal in signals:
            item_evidence = _evidence(signal, now)
            evidence.extend(item_evidence)
            title = str(signal.payload.get("title") or signal.external_id)
            text = f"{title} {signal.payload.get('abstract', '')}"
            age_days = _age_days(signal.payload, now)
            citations = signal.payload.get("citationCount")
            features = {
                "lexical_relevance": _lexical_relevance(text, query_terms, config),
                "citation": min(1.0, log1p(citations or 0) / log1p(config.ranking.citation_scale)),
                "freshness": (
                    0.0 if age_days is None
                    else 0.5 ** (age_days / config.ranking.freshness_half_life_days)
                ),
                "reliability": config.ranking.source_reliability.get(signal.source_provider, 0.0),
            }
            gates = [
                _gate(gate, signal, features, citations, age_days)
                for gate in config.ranking.gates
            ]
            total = sum(features[name] * weight for name, weight in enabled.items()) / denominator
            candidates.append(BriefingCandidate(
                artifact_id=_id("candidate", [signal.artifact_id, features, gates]),
                run_id=signal.run_id,
                created_at=now,
                producer="rank",
                input_refs=[signal.artifact_id],
                subject_id=_subject_id(signal),
                title=title,
                research_signal_ids=[signal.artifact_id],
                evidence_ids=[item.artifact_id for item in item_evidence],
                features=features,
                gate_trace=gates,
                total_score=round(total, 6),
            ))
        candidates.sort(key=lambda item: (-item.total_score, item.artifact_id))
        excluded = [item for item in candidates if any(g.result == "exclude" for g in item.gate_trace)]
        return RankOutput(
            evidence=evidence,
            candidates=candidates,
            excluded=excluded,
            report={
                "counts": {"signals": len(signals), "candidates": len(candidates),
                           "eligible": len(candidates) - len(excluded), "excluded": len(excluded)},
                "weights": weights,
                "gates": [gate.model_dump(mode="json") for gate in config.ranking.gates],
                "ranking": [{"candidate_id": item.artifact_id, "title": item.title,
                             "score": item.total_score,
                             "eligible": item not in excluded} for item in candidates],
            },
        )


def _query_terms(config: FrontierConfig) -> dict[str, float]:
    terms = {
        term: 1.0
        for keyword in config.profile.keywords.include
        for term in re.findall(r"[a-z0-9]{3,}", keyword.lower())
    }
    for topic in config.profile.topics:
        for term in re.findall(r"[a-z0-9]{3,}", topic.description.lower()):
            terms[term] = max(terms.get(term, 0.0), topic.weight)
    return terms


def _lexical_relevance(
    text: str, terms: dict[str, float], config: FrontierConfig
) -> float:
    lowered = text.lower()
    if any(term.lower() in lowered for term in config.profile.keywords.exclude):
        return 0.0
    words = set(re.findall(r"[a-z0-9]{3,}", lowered))
    if not terms:
        return 0.0
    return sum(weight for term, weight in terms.items() if term in words) / sum(terms.values())


def _age_days(payload: dict[str, Any], now: datetime) -> int | None:
    value = payload.get("publicationDate") or payload.get("published_at")
    if value:
        published = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    elif payload.get("year"):
        published = datetime(int(payload["year"]), 1, 1, tzinfo=timezone.utc)
    else:
        return None
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return max(0, (now - published).days)


def _gate(
    gate: GateConfig, signal: ResearchSignal, features: dict[str, float],
    citations: int | None, age_days: int | None,
) -> GateDecision:
    if not gate.enabled:
        return GateDecision(gate=gate.id, result="exempt", reason="disabled by config")
    if gate.type == "publication_year":
        year = signal.payload.get("year")
        if not year and signal.payload.get("published_at"):
            year = str(signal.payload["published_at"])[:4]
        passed, reason = bool(year) and int(year) >= gate.min_year, f"year={year or 'unknown'}"
    elif gate.type == "citation":
        if citations is None:
            return GateDecision(gate=gate.id, result="warn", reason="citation count unavailable")
        if age_days is not None and age_days <= gate.exempt_if_age_days_lte:
            return GateDecision(gate=gate.id, result="exempt", reason=f"age_days={age_days}")
        passed, reason = citations >= gate.minimum_count, f"citations={citations}"
    else:
        score = features["lexical_relevance"]
        passed, reason = score >= gate.minimum, f"lexical_relevance={score:.4f}"
    return GateDecision(gate=gate.id, result="pass" if passed else gate.on_fail, reason=reason)


def _subject_id(signal: ResearchSignal) -> str:
    external = signal.payload.get("externalIds", {})
    if external.get("ArXiv"):
        return f"arxiv:{external['ArXiv']}"
    return f"{signal.source_provider}:{signal.external_id}"


def _evidence(signal: ResearchSignal, now: datetime) -> list[Evidence]:
    abstract = signal.payload.get("abstract")
    if not abstract:
        return []
    evidence_id = _id("evidence", [signal.artifact_id, "abstract", abstract])
    uri = (signal.payload.get("pdf_url") or signal.payload.get("url")
           or signal.payload.get("abstract_url") or signal.payload.get("path") or signal.external_id)
    return [Evidence(
        artifact_id=evidence_id, run_id=signal.run_id, created_at=now, producer="rank",
        input_refs=[signal.artifact_id], source_ref=signal.artifact_id, source_uri=str(uri),
        locator={"type": "json_pointer", "pointer": "/payload/abstract"},
        content=str(abstract), evidence_tier="author_reported",
    )]
