from datetime import datetime, timezone
import unittest

from frontierops.application.explain import ExplanationService
from frontierops.domain.models import BriefingCandidate, Evidence, ResearchSignal


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class ExplanationServiceTests(unittest.TestCase):
    def test_links_fulltext_limitations_to_page_evidence(self) -> None:
        remote = ResearchSignal(
            artifact_id="signal_remote", run_id="run_1", created_at=NOW, producer="test",
            kind="paper.new", source_provider="arxiv", external_id="2510.05096",
            observed_at=NOW, payload={
                "title": "Paper2Video: Automatic Video Generation from Scientific Papers",
                "abstract": "Producing videos is labor-intensive. We introduce PaperTalker. Experiments show strong results.",
                "pdf_url": "https://arxiv.org/pdf/2510.05096",
            },
        )
        local = ResearchSignal(
            artifact_id="signal_local", run_id="run_1", created_at=NOW, producer="test",
            kind="paper.new", source_provider="local_library", external_id="paper2video.pdf",
            observed_at=NOW, payload={"title": "paper2video", "path": "paper2video.pdf", "sections": [{
                "text": "A limitation is the cost of talking-head rendering.",
                "locator": {"type": "pdf_page", "page": 18},
            }]},
        )
        abstract = Evidence(
            artifact_id="evidence_abstract", run_id="run_1", created_at=NOW, producer="test",
            source_ref="signal_remote", source_uri="https://arxiv.org/abs/2510.05096",
            locator={"type": "json_pointer", "pointer": "/abstract"},
            content=remote.payload["abstract"], evidence_tier="author_reported",
        )
        candidate = BriefingCandidate(
            artifact_id="candidate_1", run_id="run_1", created_at=NOW, producer="test",
            subject_id="arxiv:2510.05096", title=remote.payload["title"],
            research_signal_ids=["signal_remote"], evidence_ids=["evidence_abstract"],
            features={}, gate_trace=[], total_score=1.0,
        )
        output = ExplanationService().execute(
            [candidate], [remote, local], [abstract], NOW, top_k=1, max_pages=20
        )
        explanation = output.candidates[0].paper_explanation
        self.assertIn("cost", explanation.limitations.text)
        self.assertEqual(output.evidence[0].locator["page"], 18)
        for name, statement in explanation:
            if name != "resources" and statement.kind == "factual":
                self.assertTrue(statement.evidence_ids)
