import json
from pathlib import Path
import tempfile
import unittest

from frontierops.brief import run_brief
from frontierops.rank import run_rank
from frontierops.review import run_review
from frontierops.sync import run_sync


class ReviewIntegrationTests(unittest.TestCase):
    def test_review_persists_approved_publish_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = [{
                "provider": "arxiv", "external_id": "2510.05096", "version": "v2",
                "updated_at": "2025-10-09T17:29:00Z",
                "payload": {
                    "title": "Paper2Video research presentation",
                    "abstract": "Paper2Video presents 101 papers for research video generation.",
                    "year": 2025, "citationCount": 29,
                },
            }]
            (root / "papers.json").write_text(json.dumps(fixture), encoding="utf-8")
            (root / "frontier.yaml").write_text("""\
project: {id: review-demo, name: Review Demo, workspace_dir: .frontier}
profile: {keywords: {include: [Paper2Video]}}
sources: {arxiv: {enabled: true, mode: fixture, fixture_path: papers.json}}
ranking:
  gates: [{id: relevance, type: relevance, minimum: 0.01, on_fail: exclude}]
  source_reliability: {arxiv: 0.8}
""", encoding="utf-8")

            run = run_review(run_brief(run_rank(run_sync(root / "frontier.yaml"))))

            report = json.loads((run / "04-review/review-report.json").read_text())
            manifest = json.loads((run / "run-manifest.json").read_text())
            self.assertEqual(report["decision"], "approved")
            self.assertTrue((run / "04-review/briefing.approved.json").is_file())
            self.assertEqual(manifest["stages"]["review"], "04-review/stage-result.json")
            self.assertEqual(manifest["outputs"]["approved_briefing"],
                             "04-review/briefing.approved.json")

            draft_path = run / "03-brief/briefing.draft.json"
            draft = json.loads(draft_path.read_text())
            draft["sections"][0]["claims"][0]["evidence_ids"] = ["missing"]
            draft_path.write_text(json.dumps(draft), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "review blocked"):
                run_review(run)
            self.assertFalse((run / "04-review/briefing.approved.json").exists())
            manifest = json.loads((run / "run-manifest.json").read_text())
            self.assertEqual(manifest["status"], "failed")
            self.assertNotIn("approved_briefing", manifest["outputs"])
