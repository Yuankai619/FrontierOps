"""Composition root for the Build use case."""

from pathlib import Path

from frontierops.adapters.build import FileRunRepository, SystemClock, SystemEnvironment
from frontierops.adapters.config import YamlConfigAdapter
from frontierops.adapters.storage import SQLiteStateIndex
from frontierops.application.build import BuildUseCase


def run_build(config_path: Path) -> Path:
    return BuildUseCase(
        YamlConfigAdapter(), FileRunRepository(), SQLiteStateIndex(), SystemEnvironment(), SystemClock()
    ).execute(config_path)
