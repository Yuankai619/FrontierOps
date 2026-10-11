from datetime import datetime, timezone
import unittest

from frontierops.application.brief import BriefService
from frontierops.domain.models import (
    BriefingCandidate, FrontierConfig, GroundedStatement, PaperExplanation,
)


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def candidate(identifier: str, title: str, subject: str, score: float) -> BriefingCandidate:
    statement = GroundedStatement(text="Grounded research statement.", evidence_ids=["evidence-1"])
    explanation = PaperExplanation(
        problem=statement, core_idea=statement, method=statement, novelty=statement,
        experiments=statement, limitations=statement, why_it_matters=statement,
    )
    return BriefingCandidate(
        artifact_id=identifier, run_id="run-1", created_at=NOW, producer="test",
        subject_id=subject, title=title, research_signal_ids=[identifier],
        evidence_ids=["evidence-1"], features={}, gate_trace=[], total_score=score,
        paper_explanation=explanation,
    )


class BriefServiceTests(unittest.TestCase):
    def test_groups_sources_and_respects_duration_budgets(self) -> None:
        candidates = [
            candidate("remote", "Paper2Video: Automatic Video Generation", "arxiv:2510.05096", 1.0),
            candidate("local", "paper2video", "local:paper2video.pdf", 0.5),
        ]
        for duration in (120, 300, 600):
            config = FrontierConfig.model_validate({
                "project": {"id": "demo", "name": "Demo"},
                "brief": {"target_duration_seconds": duration,
                          "maximum_seconds_per_development": 75},
            })
            output = BriefService().execute(config, candidates, [], "run-1", NOW)
            self.assertEqual(len(output.developments), 1)
            self.assertEqual(output.developments[0].member_candidate_ids, ["remote", "local"])
            self.assertLessEqual(
                sum(section.duration_seconds for section in output.briefing.sections), duration
            )
            self.assertTrue(output.briefing.sections[0].claims[0].evidence_ids)

    def test_unchanged_development_is_suppressed(self) -> None:
        item = candidate("remote", "Paper2Video", "arxiv:2510.05096", 1.0)
        config = FrontierConfig.model_validate({"project": {"id": "demo", "name": "Demo"}})
        first = BriefService().execute(config, [item], [], "run-1", NOW)
        second = BriefService().execute(config, [item], first.history, "run-2", NOW)
        self.assertEqual(second.developments[0].status, "unchanged")
        self.assertEqual(second.briefing.sections, [])
        empty = BriefService().execute(config, [], second.history, "run-3", NOW)
        self.assertEqual(empty.history, second.history)
