import json
from pathlib import Path
import tempfile
import unittest

from frontierops.sync import run_sync


CONFIG = """\
schema_version: "0.1"
project: {id: sync-demo, name: Sync Demo, workspace_dir: .frontier}
sources:
  arxiv: {enabled: true, mode: fixture, fixture_path: papers.json}
sync: {trigger_mode: manual, baseline: last_successful_sync}
"""


class SyncIntegrationTests(unittest.TestCase):
    def test_second_fixture_sync_has_no_duplicate_signal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "frontier.yaml").write_text(CONFIG, encoding="utf-8")
            fixture = [{
                "provider": "arxiv",
                "external_id": "2510.05096",
                "version": "v2",
                "updated_at": "2025-10-09T17:29:00Z",
                "payload": {"title": "Paper2Video"},
            }]
            (root / "papers.json").write_text(json.dumps(fixture), encoding="utf-8")

            first = run_sync(root / "frontier.yaml")
            second = run_sync(root / "frontier.yaml")

            first_signals = (first / "01-sync/research-signals.jsonl").read_text().splitlines()
            second_signals = (second / "01-sync/research-signals.jsonl").read_text().splitlines()
            second_summary = json.loads((second / "01-sync/delta-summary.json").read_text())
            self.assertEqual(len(first_signals), 1)
            self.assertEqual(second_signals, [])
            self.assertEqual(second_summary, {"fetched": 1, "produced": 0, "skipped_duplicate": 1})
            self.assertTrue((root / ".frontier/cache/raw/arxiv").is_dir())
            manifest = json.loads((second / "run-manifest.json").read_text())
            self.assertEqual(manifest["stages"]["sync"], "01-sync/stage-result.json")

            fixture[0]["version"] = "v3"
            fixture[0]["payload"]["title"] = "Paper2Video revised"
            (root / "papers.json").write_text(json.dumps(fixture), encoding="utf-8")
            changed = run_sync(root / "frontier.yaml")
            unchanged = run_sync(root / "frontier.yaml")
            changed_signal = json.loads(
                (changed / "01-sync/research-signals.jsonl").read_text().strip()
            )
            self.assertEqual(changed_signal["kind"], "paper.updated")
            self.assertEqual(
                (unchanged / "01-sync/research-signals.jsonl").read_text(), ""
            )

    def test_provider_and_local_document_share_one_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "papers").mkdir()
            (root / "papers/paper.txt").write_text("Method and result evidence", encoding="utf-8")
            (root / "papers.json").write_text(json.dumps([{
                "provider": "arxiv", "external_id": "2510.05096", "version": "v2",
                "updated_at": "2025-10-09T17:29:00Z", "payload": {"title": "Paper2Video"},
            }]), encoding="utf-8")
            config = CONFIG.replace(
                "sync:", "  local_library: {enabled: true, roots: [papers]}\nsync:"
            )
            (root / "frontier.yaml").write_text(config, encoding="utf-8")
            run_dir = run_sync(root / "frontier.yaml")
            signals = [json.loads(line) for line in
                       (run_dir / "01-sync/research-signals.jsonl").read_text().splitlines()]
            self.assertEqual({item["source_provider"] for item in signals},
                             {"arxiv", "local_library"})
            local = next(item for item in signals if item["source_provider"] == "local_library")
            self.assertEqual(local["payload"]["sections"][0]["locator"]["type"], "line_range")
            (root / "papers/paper.txt").touch()
            unchanged = run_sync(root / "frontier.yaml")
            self.assertEqual(
                (unchanged / "01-sync/research-signals.jsonl").read_text(), ""
            )
