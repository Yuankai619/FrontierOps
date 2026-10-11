"""Idempotent user-workspace initialization without installation side effects."""

from dataclasses import dataclass
from pathlib import Path
import re

from frontierops.application.ports import ConfigReader, ConfigWriter, WorkspaceFiles
from frontierops.domain.models import BriefConfig, FrontierConfig, ProjectConfig


@dataclass(frozen=True)
class SetupResult:
    config_path: Path
    output_dir: Path
    created_config: bool


@dataclass(frozen=True)
class SetupUseCase:
    reader: ConfigReader
    writer: ConfigWriter
    files: WorkspaceFiles

    def execute(self, workspace: Path, name: str | None = None) -> SetupResult:
        root = workspace.resolve()
        if root == root.parent:
            raise ValueError("setup workspace cannot be a filesystem root")
        config_path = root / "frontier.yaml"
        created = not self.files.exists(config_path)
        if created:
            project_name = name or root.name
            slug = re.sub(r"[^a-z0-9]+", "-", project_name.lower()).strip("-")
            config = FrontierConfig(project=ProjectConfig(
                id=slug or "research-project", name=project_name
            ), brief=BriefConfig(outputs=["html", "slides"]))
            self.files.make_directory(root)
            self.writer.write(config_path, config.model_dump(mode="json"))
        else:
            config = FrontierConfig.model_validate(self.reader.read(config_path))
        output_dir = config.project.output_dir
        if not output_dir.is_absolute():
            output_dir = root / output_dir
        self.files.make_directory(output_dir)
        return SetupResult(config_path, output_dir, created)
