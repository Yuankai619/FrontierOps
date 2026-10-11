"""Outbound ports owned by the application core."""

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol


class ConfigReader(Protocol):
    def read(self, path: Path) -> Mapping[str, Any]: ...


class ConfigWriter(Protocol):
    def write(self, path: Path, payload: Mapping[str, Any]) -> None: ...


class ArtifactStore(Protocol):
    def write_json(self, path: Path, payload: Any) -> None: ...
    def write_jsonl(self, path: Path, records: Iterable[Mapping[str, Any]]) -> None: ...


class RunRepository(Protocol):
    def save(self, workspace: Path, run_id: str, files: Mapping[str, Any]) -> Path: ...


class StateIndex(Protocol):
    def initialize(self, workspace: Path) -> None: ...
    def record_run(
        self, workspace: Path, run_id: str, status: str, manifest_path: Path, created_at: datetime
    ) -> None: ...


class EnvironmentReader(Protocol):
    def read(self) -> Mapping[str, str]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
