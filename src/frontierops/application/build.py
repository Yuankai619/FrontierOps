"""Build application use case; depends only on domain models and ports."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from frontierops.application.ports import Clock, ConfigReader, EnvironmentReader, RunRepository
from frontierops.domain.models import FrontierConfig, RunManifest, StageResult


@dataclass(frozen=True)
class BuildUseCase:
    config_reader: ConfigReader
    runs: RunRepository
    environment: EnvironmentReader
    clock: Clock

    def execute(self, config_path: Path) -> Path:
        started_at = self.clock.now()
        config = FrontierConfig.model_validate(self.config_reader.read(config_path))
        resolved = config.model_dump(mode="json")
        encoded = json.dumps(resolved, sort_keys=True, separators=(",", ":")).encode()
        config_hash = sha256(encoded).hexdigest()
        run_id = started_at.strftime("run_%Y%m%dT%H%M%S%fZ_") + config_hash[:8]
        workspace = config.project.workspace_dir
        if not workspace.is_absolute():
            workspace = config_path.resolve().parent / workspace

        result = StageResult(
            run_id=run_id,
            stage="build",
            status="success",
            started_at=started_at,
            finished_at=self.clock.now(),
            outputs={"resolved_config": "00-build/resolved-config.yaml"},
            next_stage_allowed=True,
        )
        manifest = RunManifest(
            run_id=run_id,
            status="success",
            config_sha256=config_hash,
            stages={"build": "00-build/stage-result.json"},
            outputs={"resolved_config": "00-build/resolved-config.yaml"},
        )
        files = {
            "00-build/resolved-config.yaml": resolved,
            "00-build/config-resolution.json": {
                "source_path": str(config_path.resolve()), "sha256": config_hash
            },
            "00-build/environment-report.json": dict(self.environment.read()),
            "00-build/stage-result.json": result.model_dump(mode="json"),
            "run-manifest.json": manifest.model_dump(mode="json"),
        }
        return self.runs.save(workspace, run_id, files)
