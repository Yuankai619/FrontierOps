import json
from pathlib import Path
import tempfile
import unittest

from frontierops.rank import run_rank
from frontierops.sync import run_sync


def _config(year: int, citation_floor: int = 1) -> str:
    return f'''project: {{id: harness, name: Agent Harness, workspace_dir: .frontier}}
sources:
  openalex: {{enabled: true, mode: fixture, fixture_path: papers.json}}
profile:
  topics:
    - id: ai-agent-harness
      description: AI agent harness execution environment
      search:
        providers: [openalex]
        query: '"agent harness"'
        published_from: {year}-01-01
        published_to: {year}-12-31
ranking:
  gates:
    - {{id: citations, type: citation, minimum_count: {citation_floor}, on_fail: exclude}}
'''


def _paper(identifier: str, year: int) -> list[dict]:
    return [{
        "provider": "openalex", "external_id": identifier,
        "updated_at": f"{year}-07-01T00:00:00Z",
        "payload": {
            "title": f"AI Agent Harness {identifier}",
            "abstract": "We propose a harness for AI agent execution and evaluate the method.",
            "published_at": f"{year}-06-01", "year": year, "citationCount": 2,
            "topic_ids": ["ai-agent-harness"], "externalIds": {"OpenAlex": identifier},
        },
    }]


class TopicDeltaIntegrationTests(unittest.TestCase):
    def test_year_scope_change_then_same_scope_and_gate_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "frontier.yaml"
            fixture = root / "papers.json"
            config.write_text(_config(2025), encoding="utf-8")
            fixture.write_text(json.dumps(_paper("W2025", 2025)), encoding="utf-8")
            first = run_rank(run_sync(config))
            first_report = json.loads((first / "02-rank/topic-delta.json").read_text())
            self.assertEqual(first_report["topics"][0]["entries"][0]["status"], "baseline")

            config.write_text(_config(2026), encoding="utf-8")
            fixture.write_text(json.dumps(_paper("W2026", 2026)), encoding="utf-8")
            second = run_rank(run_sync(config))
            second_topic = json.loads((second / "02-rank/topic-delta.json").read_text())["topics"][0]
            self.assertTrue(second_topic["scope_changed"])
            self.assertEqual({item["status"] for item in second_topic["entries"]},
                             {"new_in_scope", "not_returned"})
            html = (second / "02-rank/discovery.html").read_text()
            self.assertIn("新納入查詢範圍", html)
            self.assertIn("AI Agent Harness W2026", html)
            self.assertIn("citations: pass", html)

            third = run_rank(run_sync(config))
            self.assertEqual((third / "01-sync/research-signals.jsonl").read_text(), "")
            self.assertEqual(len((third / "02-rank/briefing-candidates.jsonl").read_text().splitlines()), 1)
            third_topic = json.loads((third / "02-rank/topic-delta.json").read_text())["topics"][0]
            self.assertEqual(third_topic["entries"][0]["status"], "unchanged")

            config.write_text(_config(2026, citation_floor=5), encoding="utf-8")
            fourth = run_rank(run_sync(config))
            fourth_topic = json.loads((fourth / "02-rank/topic-delta.json").read_text())["topics"][0]
            self.assertTrue(fourth_topic["policy_changed"])
            self.assertEqual(fourth_topic["entries"][0]["status"], "newly_excluded")
            self.assertEqual(fourth_topic["entries"][0]["current_gates"]["citations"], "exclude")
