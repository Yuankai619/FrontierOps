from datetime import datetime, timezone
import unittest

from frontierops.application.review import ReviewService
from frontierops.domain.models import Evidence, ReviewConfig


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def evidence() -> Evidence:
    return Evidence(
        artifact_id="evidence-1", run_id="run-1", created_at=NOW, producer="test",
        source_ref="signal-1", source_uri="paper.pdf",
        locator={"type": "pdf_page", "page": 1},
        content="The benchmark contains 101 papers and improves accuracy by 10%.",
        evidence_tier="primary_fulltext",
    )


def briefing(text: str, evidence_id: str = "evidence-1") -> dict:
    return {
        "schema_version": "0.1", "artifact_id": "brief-1", "run_id": "run-1",
        "created_at": NOW.isoformat(), "producer": "test", "input_refs": [],
        "title": "Demo", "language": "zh-TW", "target_duration_seconds": 60,
        "render_targets": ["html", "slides", "video"],
        "sections": [{
            "id": "paper-1", "duration_seconds": 60, "headline": "Paper2Video",
            "development_id": "development-1",
            "claims": [{"text": text, "kind": "factual", "evidence_ids": [evidence_id]}],
        }],
    }


class ReviewServiceTests(unittest.TestCase):
    def test_blocks_broken_reference_and_unsupported_number(self) -> None:
        service = ReviewService()
        broken = service.execute(
            briefing("The method improves accuracy by 999%.", "missing"),
            [evidence()], ReviewConfig(), "run-1", NOW,
        )
        self.assertEqual(broken.report.decision, "blocked")
        self.assertIn("broken_evidence", {item.code for item in broken.report.issues})

        unsupported = service.execute(
            briefing("The method improves accuracy by 999%."),
            [evidence()], ReviewConfig(), "run-1", NOW,
        )
        self.assertIn("unsupported_number", {item.code for item in unsupported.report.issues})
        self.assertIsNone(unsupported.approved)

    def test_corrected_claim_is_approved(self) -> None:
        output = ReviewService().execute(
            briefing("The benchmark contains 101 papers and improves accuracy by 10%."),
            [evidence()], ReviewConfig(), "run-1", NOW,
        )
        self.assertEqual(output.report.decision, "approved")
        self.assertIsNotNone(output.approved)
        self.assertEqual(output.report.counts["errors"], 0)

    def test_number_must_match_a_complete_evidence_token(self) -> None:
        item = evidence().model_copy(update={"content": "The benchmark contains 101 papers."})
        output = ReviewService().execute(
            briefing("The benchmark contains 10 papers."),
            [item], ReviewConfig(), "run-1", NOW,
        )
        self.assertEqual(output.claim_checks[0].status, "unsupported_number")

    def test_highlighted_quote_must_exist_in_evidence(self) -> None:
        draft = briefing("The benchmark contains 101 papers and improves accuracy by 10%.")
        draft["sections"][0]["source_excerpts"] = [{
            "evidence_id": "evidence-1", "quote": "The benchmark contains 101 papers",
        }]
        accepted = ReviewService().execute(draft, [evidence()], ReviewConfig(), "run-1", NOW)
        self.assertEqual(accepted.report.decision, "approved")
        draft["sections"][0]["source_excerpts"][0]["quote"] = "This text does not occur in the source"
        rejected = ReviewService().execute(draft, [evidence()], ReviewConfig(), "run-1", NOW)
        self.assertIn("invalid_source_excerpt", {item.code for item in rejected.report.issues})
