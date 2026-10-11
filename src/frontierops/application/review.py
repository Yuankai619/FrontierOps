"""Deterministic publication gate for evidence-grounded briefings."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import re
from typing import Any

from pydantic import ValidationError

from frontierops.domain.models import (
    BriefingSpec, ClaimCheck, Evidence, ReviewConfig, ReviewIssue, ReviewReport,
)


@dataclass(frozen=True)
class ReviewOutput:
    report: ReviewReport
    claim_checks: list[ClaimCheck]
    approved: BriefingSpec | None


class ReviewService:
    def execute(
        self,
        raw_briefing: dict[str, Any],
        evidence: list[Evidence],
        policy: ReviewConfig,
        run_id: str,
        now: datetime,
    ) -> ReviewOutput:
        raw = _safe_normalize(raw_briefing) if policy.auto_fix == "safe_only" else raw_briefing
        evidence_by_id = {item.artifact_id: item for item in evidence}
        issues: list[ReviewIssue] = []
        checks: list[ClaimCheck] = []
        sections = raw.get("sections", [])
        target = raw.get("target_duration_seconds", 0)
        total = sum(item.get("duration_seconds", 0) for item in sections)
        if total > target:
            issues.append(_issue(
                "duration_over_budget", policy.fail_on_duration_over_budget,
                f"section duration {total}s exceeds target {target}s",
            ))

        development_ids: set[str] = set()
        headlines: set[str] = set()
        for section in sections:
            section_id = section.get("id", "unknown")
            development_id = section.get("development_id")
            headline = section.get("headline", "").casefold().strip()
            if (development_id and development_id in development_ids) or headline in headlines:
                issues.append(_issue(
                    "duplicate_development", policy.fail_on_duplicate_development,
                    "development ID or headline is duplicated", section_id,
                ))
            if development_id:
                development_ids.add(development_id)
            headlines.add(headline)
            for index, claim in enumerate(section.get("claims", [])):
                check, claim_issues = _check_claim(
                    section_id, index, claim, evidence_by_id, policy
                )
                checks.append(check)
                issues.extend(claim_issues)

        approved = None
        try:
            validated = BriefingSpec.model_validate(raw)
        except ValidationError as error:
            issues.append(ReviewIssue(
                code="schema_invalid", severity="error", message=str(error)
            ))
        else:
            if not any(item.severity == "error" for item in issues):
                approved = validated
        decision = "approved" if approved else "blocked"
        report = ReviewReport(
            artifact_id="review_" + sha256(
                f"{run_id}:{raw.get('artifact_id')}:{decision}".encode()
            ).hexdigest()[:24],
            run_id=run_id,
            created_at=now,
            producer="review",
            input_refs=[str(raw.get("artifact_id", "briefing-draft"))],
            decision=decision,
            issues=issues,
            counts={
                "claims": len(checks),
                "supported": sum(item.status == "supported" for item in checks),
                "errors": sum(item.severity == "error" for item in issues),
                "warnings": sum(item.severity == "warning" for item in issues),
            },
        )
        return ReviewOutput(report, checks, approved)


def _check_claim(
    section_id: str,
    index: int,
    claim: dict[str, Any],
    evidence: dict[str, Evidence],
    policy: ReviewConfig,
) -> tuple[ClaimCheck, list[ReviewIssue]]:
    refs = claim.get("evidence_ids", [])
    factual = claim.get("kind", "factual") == "factual"
    if factual and not refs:
        issue = _issue("missing_evidence", policy.fail_on_missing_evidence,
                       "factual claim has no Evidence", section_id, index)
        return ClaimCheck(section_id=section_id, claim_index=index,
                          status="missing_evidence", details=issue.message), [issue]
    broken = [item for item in refs if item not in evidence]
    if broken:
        issue = _issue("broken_evidence", policy.fail_on_broken_source,
                       f"unknown Evidence IDs: {broken}", section_id, index)
        return ClaimCheck(section_id=section_id, claim_index=index,
                          status="broken_evidence", evidence_ids=refs,
                          details=issue.message), [issue]
    numbers = set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?%?", claim.get("text", "")))
    support = " ".join(evidence[item].content for item in refs)
    support_numbers = set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?%?", support))
    unsupported = sorted(numbers - support_numbers)
    if factual and unsupported:
        issue = _issue("unsupported_number", policy.fail_on_unsupported_number,
                       f"numbers absent from cited Evidence: {unsupported}", section_id, index)
        return ClaimCheck(section_id=section_id, claim_index=index,
                          status="unsupported_number", evidence_ids=refs,
                          details=issue.message), [issue]
    return ClaimCheck(section_id=section_id, claim_index=index, status="supported",
                      evidence_ids=refs), []


def _issue(
    code: str, blocks: bool, message: str,
    section_id: str | None = None, claim_index: int | None = None,
) -> ReviewIssue:
    return ReviewIssue(code=code, severity="error" if blocks else "warning",
                       message=message, section_id=section_id, claim_index=claim_index)


def _safe_normalize(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(raw)
    for section in normalized.get("sections", []):
        section["headline"] = section.get("headline", "").strip()
        for claim in section.get("claims", []):
            claim["text"] = claim.get("text", "").strip()
            claim["evidence_ids"] = list(dict.fromkeys(claim.get("evidence_ids", [])))
    return normalized
