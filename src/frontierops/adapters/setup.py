"""Filesystem adapter for workspace setup."""

from pathlib import Path


class LocalWorkspaceFiles:
    def exists(self, path: Path) -> bool:
        return path.exists()

    def make_directory(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
