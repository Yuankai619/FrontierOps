"""Composition root for workspace setup."""

from pathlib import Path

from frontierops.adapters.config import YamlConfigAdapter
from frontierops.adapters.setup import LocalWorkspaceFiles
from frontierops.application.setup import SetupResult, SetupUseCase


def run_setup(workspace: Path, name: str | None = None) -> SetupResult:
    return SetupUseCase(YamlConfigAdapter(), YamlConfigAdapter(), LocalWorkspaceFiles()).execute(
        workspace, name
    )
