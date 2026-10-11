"""Outbound ports owned by the application core."""

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Protocol


class ConfigReader(Protocol):
    def read(self, path: Path) -> Mapping[str, Any]: ...


class RunRepository(Protocol):
    def save(self, workspace: Path, run_id: str, files: Mapping[str, Any]) -> Path: ...


class EnvironmentReader(Protocol):
    def read(self) -> Mapping[str, str]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
