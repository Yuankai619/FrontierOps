"""Loopback-only selection endpoint for a Discovery Run."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import parse_qs, urlsplit

from frontierops.adapters.storage import FileArtifactStore
from frontierops.domain.models import BriefingCandidate, BriefingSelection


def create_discovery_server(run_dir: Path, port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    run_dir = run_dir.resolve()
    report = (run_dir / "02-rank/discovery.html").read_bytes()
    candidates = [BriefingCandidate.model_validate(item) for item in
                  FileArtifactStore(run_dir).read_jsonl(Path("02-rank/briefing-candidates.jsonl"))]
    eligible = {item.artifact_id for item in candidates if item.paper_explanation is not None
                and not any(gate.result == "exclude" for gate in item.gate_trace)}
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def _authorized(self) -> bool:
            query = parse_qs(urlsplit(self.path).query)
            return secrets.compare_digest(query.get("session", [""])[0], token)

        def _reply(self, code: int, body: bytes, content_type: str = "text/plain") -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if urlsplit(self.path).path != "/" or not self._authorized():
                self._reply(404, b"Not found")
                return
            self._reply(200, report, "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/selection" or not self._authorized():
                self._reply(404, b"Not found")
                return
            origin = self.headers.get("Origin", "")
            host = self.headers.get("Host", "")
            if origin not in {f"http://{host}", ""} or self.headers.get("Content-Type") != "application/json":
                self._reply(403, b"Invalid origin or content type")
                return
            size = int(self.headers.get("Content-Length", "0"))
            if size < 1 or size > 100_000:
                self._reply(413, b"Invalid selection size")
                return
            try:
                selection = BriefingSelection.model_validate_json(self.rfile.read(size))
                if selection.run_id != run_dir.name or not set(selection.selected_candidate_ids) <= eligible:
                    raise ValueError("selection contains another Run or an ineligible paper")
                FileArtifactStore(run_dir).write_json(
                    Path("02-rank/briefing-selection.json"), selection.model_dump(mode="json")
                )
            except (ValueError, json.JSONDecodeError) as exc:
                self._reply(400, str(exc).encode())
                return
            self._reply(200, b'{"saved":true}', "application/json")

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_port}/?session={token}"
    return server, url
