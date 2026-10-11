import json
from pathlib import Path
import tempfile
import unittest

from frontierops.evidence import run_evidence
from frontierops.rank import run_rank
from frontierops.sync import run_sync


class AlphaXivEvidenceIntegrationTests(unittest.TestCase):
    def test_enriches_selected_candidate_without_replacing_abstract_evidence(self) -> None:
        class FakeMcp:
            calls: list[tuple[str, list[str]]] = []

            async def answer_pdf_queries(self, paper: str, queries: list[str]) -> str:
                self.calls.append((paper, queries))
                return '<paper><page num="3">Our method uses a guarded execution loop.</page></paper>'

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "frontier.yaml"
            config.write_text('''project: {id: harness, name: Agent Harness, workspace_dir: .frontier}
sources:
  openalex: {enabled: true, mode: fixture, fixture_path: papers.json}
profile:
  topics:
    - id: agents
      description: agent harness
      search: {providers: [openalex], query: "agent harness"}
''', encoding="utf-8")
            (root / "papers.json").write_text(json.dumps([{
                "provider": "openalex", "external_id": "W123",
                "updated_at": "2026-05-01T00:00:00Z", "payload": {
                    "title": "Agent Harness", "abstract": "A guarded agent harness method.",
                    "published_at": "2026-05-01", "year": 2026,
                    "topic_ids": ["agents"], "arxiv_id": "2605.12345",
                    "pdf_url": "https://arxiv.org/pdf/2605.12345",
                    "externalIds": {"OpenAlex": "W123", "ArXiv": "2605.12345"},
                },
            }]), encoding="utf-8")
            run = run_rank(run_sync(config))
            candidates_file = run / "02-rank/briefing-candidates.jsonl"
            candidate = json.loads(candidates_file.read_text().splitlines()[0])
            previous_evidence = (run / "02-rank/evidence.jsonl").read_text().splitlines()
            client = FakeMcp()
            run_evidence(run, candidate["artifact_id"], ["What is the method?"], client)
            self.assertEqual(client.calls, [
                ("https://arxiv.org/pdf/2605.12345", ["What is the method?"])
            ])
            evidence = [json.loads(line) for line in
                        (run / "02-rank/evidence.jsonl").read_text().splitlines()]
            self.assertEqual(len(evidence), len(previous_evidence) + 1)
            page = next(item for item in evidence if item["producer"] == "alphaxiv:answer_pdf_queries")
            self.assertEqual(page["locator"], {"type": "page", "page": 3})
            self.assertEqual(page["evidence_tier"], "primary_fulltext")
            self.assertIn(page["artifact_id"], json.loads(candidates_file.read_text())["evidence_ids"])
            self.assertIn("alphaxiv_enrichment", json.loads((run / "run-manifest.json").read_text())["outputs"])
            run_evidence(run, candidate["artifact_id"], ["What is the method?"], client)
            self.assertEqual(len((run / "02-rank/evidence.jsonl").read_text().splitlines()), len(evidence))
            self.assertEqual(len((run / "02-rank/alphaxiv-enrichment.jsonl").read_text().splitlines()), 1)
