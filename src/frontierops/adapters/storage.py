"""Inspectable artifact storage and rebuildable SQLite state index."""

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping


class FileArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _target(self, relative: Path) -> Path:
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("artifact path must stay within store root")
        return target

    def _write(self, relative: Path, text: str) -> None:
        target = self._target(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(target)

    def write_json(self, path: Path, payload: Any) -> None:
        self._write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    def write_jsonl(self, path: Path, records: Iterable[Mapping[str, Any]]) -> None:
        self._write(path, "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records))

    def write_text(self, path: Path, text: str) -> None:
        self._write(path, text)

    def read_json(self, path: Path) -> Any:
        return json.loads(self._target(path).read_text(encoding="utf-8"))

    def read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        lines = self._target(path).read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line]


class SQLiteStateIndex:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        manifest_path TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS artifacts (
        artifact_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        artifact_type TEXT NOT NULL,
        path TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """

    def _database(self, workspace: Path) -> Path:
        return workspace / "state" / "index.sqlite3"

    def initialize(self, workspace: Path) -> None:
        state = workspace / "state"
        state.mkdir(parents=True, exist_ok=True)
        store = FileArtifactStore(state)
        if not (state / "source-cursors.json").exists():
            store.write_json(Path("source-cursors.json"), {"schema_version": "0.1", "providers": {}})
        for name in ("identity-map.jsonl", "development-index.jsonl"):
            if not (state / name).exists():
                store.write_jsonl(Path(name), [])
        with sqlite3.connect(self._database(workspace)) as database:
            database.executescript(self.SCHEMA)

    def record_run(
        self, workspace: Path, run_id: str, status: str, manifest_path: Path, created_at: datetime
    ) -> None:
        with sqlite3.connect(self._database(workspace)) as database:
            database.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?)",
                (run_id, status, str(manifest_path), created_at.isoformat()),
            )
