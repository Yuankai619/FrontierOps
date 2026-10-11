"""Fixture provider and filesystem persistence for Sync."""

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from frontierops.adapters.storage import FileArtifactStore
from frontierops.domain.models import SourceBatch, SourceRecord


class JsonFixtureProvider:
    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.path = path

    def fetch(self, cursor: Mapping[str, Any]) -> SourceBatch:
        del cursor
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        records = [SourceRecord.model_validate(item) for item in payload]
        return SourceBatch(records=records, next_cursor={"fixture_records": len(records)})


class FileSyncRepository:
    def load_state(self, workspace: Path) -> dict[str, Any]:
        return FileArtifactStore(workspace / "state").read_json(Path("source-cursors.json"))

    def cache_raw(self, workspace: Path, provider: str, payload: Mapping[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        digest = sha256(encoded).hexdigest()
        relative = Path(provider) / f"{digest}.json"
        target = workspace / "cache" / "raw" / relative
        if not target.exists():
            FileArtifactStore(workspace / "cache" / "raw").write_json(relative, payload)
        return str(Path("cache/raw") / relative)

    def save_stage(self, run_dir: Path, files: Mapping[str, Any]) -> None:
        store = FileArtifactStore(run_dir)
        for path, payload in files.items():
            relative = Path(path)
            if relative.suffix == ".jsonl":
                store.write_jsonl(relative, payload)
            else:
                store.write_json(relative, payload)
        manifest = store.read_json(Path("run-manifest.json"))
        manifest["stages"]["sync"] = "01-sync/stage-result.json"
        manifest["outputs"].update({
            "research_signals": "01-sync/research-signals.jsonl",
            "delta_summary": "01-sync/delta-summary.json",
        })
        store.write_json(Path("run-manifest.json"), manifest)

    def commit_state(self, workspace: Path, state: Mapping[str, Any]) -> None:
        FileArtifactStore(workspace / "state").write_json(Path("source-cursors.json"), state)
