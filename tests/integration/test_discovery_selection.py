import json
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from frontierops.adapters.discovery_server import create_discovery_server
from frontierops.brief import run_brief
from frontierops.rank import run_rank
from frontierops.sync import run_sync


class DiscoverySelectionTests(unittest.TestCase):
    def test_history_and_saved_selection_drive_brief(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "papers.json"
            config = root / "frontier.yaml"
            config.write_text("""\
project: {id: demo, name: Demo, workspace_dir: .frontier}
sources: {arxiv: {enabled: true, mode: fixture, fixture_path: papers.json}}
brief: {maximum_developments: 5}
""", encoding="utf-8")
            fixture.write_text(json.dumps([_paper("1", "First paper")]), encoding="utf-8")
            first = run_rank(run_sync(config))
            fixture.write_text(json.dumps([_paper("1", "First paper"),
                                           _paper("2", "Second paper"),
                                           _paper("3", "Third paper")]), encoding="utf-8")
            second = run_rank(run_sync(config))
            html = (second / "02-rank/discovery.html").read_text(encoding="utf-8")
            self.assertIn("先前收錄", html)
            self.assertIn("First paper", html)
            self.assertIn(first.name, html)
            candidates = [json.loads(line) for line in
                          (second / "02-rank/briefing-candidates.jsonl").read_text().splitlines()]
            selected = candidates[0]["artifact_id"]
            server, url = create_discovery_server(second)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.assertIn("儲存選取", urlopen(url).read().decode())
                body = {"schema_version": "0.1", "run_id": second.name,
                        "selected_candidate_ids": [selected]}
                request = Request(url.replace("/?", "/selection?"),
                                  data=json.dumps(body).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                self.assertEqual(urlopen(request).status, 200)
                body["selected_candidate_ids"] = ["nonexistent"]
                with self.assertRaises(HTTPError):
                    urlopen(Request(url.replace("/?", "/selection?"),
                                    data=json.dumps(body).encode(),
                                    headers={"Content-Type": "application/json"}, method="POST"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
            run_brief(second)
            draft = json.loads((second / "03-brief/briefing.draft.json").read_text())
            self.assertEqual(len(draft["sections"]), 1)
            self.assertEqual(draft["sections"][0]["headline"], candidates[0]["title"])


def _paper(identifier: str, title: str) -> dict:
    return {"provider": "arxiv", "external_id": identifier, "version": "v1",
            "updated_at": "2026-05-01T00:00:00Z",
            "payload": {"title": title, "abstract": "We propose a research method and show results."}}
