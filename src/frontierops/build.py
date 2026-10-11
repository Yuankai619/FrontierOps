"""Composition root for the Build use case."""

from pathlib import Path

from frontierops.adapters.build import FileRunRepository, SystemClock, SystemEnvironment
from frontierops.adapters.config import YamlConfigAdapter
from frontierops.application.build import BuildUseCase


def run_build(config_path: Path) -> Path:
    return BuildUseCase(
        YamlConfigAdapter(), FileRunRepository(), SystemEnvironment(), SystemClock()
    ).execute(config_path)
