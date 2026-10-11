import json
from pathlib import Path
import tempfile
import unittest

from frontierops.rank import run_rank
from frontierops.sync import run_sync


class RankIntegrationTests(unittest.TestCase):
    def test_yaml_gates_change_eligibility_with_trace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = [{
                "provider": "arxiv", "external_id": "2510.05096", "version": "v2",
                "updated_at": "2025-10-09T17:29:00Z",
                "payload": {"title": "Paper2Video research presentation", "abstract": "paper video",
                            "year": 2025, "citationCount": 29},
            }]
            (root / "papers.json").write_text(json.dumps(fixture), encoding="utf-8")
            config = """\
project: {id: rank-demo, name: Rank Demo, workspace_dir: .frontier}
profile: {keywords: {include: [paper video]}}
sources: {arxiv: {enabled: true, mode: fixture, fixture_path: papers.json}}
ranking:
  gates:
    - {id: citations, type: citation, minimum_count: 30, on_fail: exclude}
  source_reliability: {arxiv: 0.8}
"""
            config_path = root / "frontier.yaml"
            config_path.write_text(config, encoding="utf-8")
            first = run_rank(run_sync(config_path))
            excluded = [json.loads(line) for line in
                        (first / "02-rank/excluded-candidates.jsonl").read_text().splitlines()]
            self.assertEqual(excluded[0]["gate_trace"][0]["reason"], "citations=29")

            changed = config.replace("minimum_count: 30", "minimum_count: 20")
            changed = changed.replace("workspace_dir: .frontier", "workspace_dir: .frontier-2")
            config_path.write_text(changed, encoding="utf-8")
            second = run_rank(run_sync(config_path))
            report = json.loads((second / "02-rank/ranking-report.json").read_text())
            self.assertEqual(report["counts"]["eligible"], 1)
            self.assertEqual(report["ranking"][0]["eligible"], True)
            discovery = root / "frontier_output/discoveries" / f"{second.name}.html"
            self.assertTrue(discovery.is_file())
            self.assertIn("Paper2Video research presentation", discovery.read_text())
            self.assertIn("citations", discovery.read_text())
            self.assertEqual(json.loads((second / "run-manifest.json").read_text())["outputs"]["public_discovery_html"], str(discovery))
            explanations = [json.loads(line) for line in
                            (second / "02-rank/paper-explanations.jsonl").read_text().splitlines()]
            self.assertEqual(explanations[0]["title"], "Paper2Video research presentation")
            for section in explanations[0]["paper_explanation"].values():
                if isinstance(section, dict) and section["kind"] == "factual":
                    self.assertTrue(section["evidence_ids"])
