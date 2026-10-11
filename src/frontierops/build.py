"""Composition root for the Build use case."""

from pathlib import Path

from frontierops.adapters.build import FileRunRepository, SystemClock, SystemEnvironment, YamlConfigReader
from frontierops.application.build import BuildUseCase


def run_build(config_path: Path) -> Path:
    return BuildUseCase(
        YamlConfigReader(), FileRunRepository(), SystemEnvironment(), SystemClock()
    ).execute(config_path)
