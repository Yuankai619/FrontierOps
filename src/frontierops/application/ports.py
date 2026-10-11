"""Outbound ports owned by the application core."""

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

from frontierops.domain.models import BriefingSpec, Evidence, ScholarIdentity, SourceBatch, VenueIdentity


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


class SyncProvider(Protocol):
    name: str

    def fetch(self, cursor: Mapping[str, Any]) -> SourceBatch: ...


class SyncRepository(Protocol):
    def load_state(self, workspace: Path) -> dict[str, Any]: ...
    def cache_raw(self, workspace: Path, provider: str, payload: Mapping[str, Any]) -> str: ...
    def save_stage(self, run_dir: Path, files: Mapping[str, Any]) -> None: ...
    def commit_state(self, workspace: Path, state: Mapping[str, Any]) -> None: ...


class ScholarResolver(Protocol):
    def resolve_scholars(self, name: str, provider: str) -> list[ScholarIdentity]: ...


class VenueResolver(Protocol):
    def resolve_venues(self, name: str, year: int | None, provider: str) -> list[VenueIdentity]: ...


class EnvironmentReader(Protocol):
    def read(self) -> Mapping[str, str]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class BriefingRenderer(Protocol):
    target: str

    def render(self, briefing: BriefingSpec, evidence: list[Evidence]) -> str: ...
