"""Build stage: validate config and initialize an inspectable run."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
from typing import Any

import yaml

from frontierops import __version__
from frontierops.models import FrontierConfig, RunManifest, StageResult


def load_config(path: Path) -> FrontierConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("configuration must be a YAML mapping")
    return FrontierConfig.model_validate(payload)


def _write_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_build(config_path: Path) -> Path:
    started_at = datetime.now(timezone.utc)
    config = load_config(config_path)
    resolved = config.model_dump(mode="json")
    encoded = json.dumps(resolved, sort_keys=True, separators=(",", ":")).encode()
    config_hash = sha256(encoded).hexdigest()
    run_id = started_at.strftime("run_%Y%m%dT%H%M%S%fZ_") + config_hash[:8]

    workspace = config.project.workspace_dir
    if not workspace.is_absolute():
        workspace = config_path.resolve().parent / workspace
    stage_dir = workspace / "runs" / run_id / "00-build"
    stage_dir.mkdir(parents=True, exist_ok=False)

    resolved_path = stage_dir / "resolved-config.yaml"
    resolved_path.write_text(yaml.safe_dump(resolved, sort_keys=False, allow_unicode=True), encoding="utf-8")
    _write_json(stage_dir / "config-resolution.json", {
        "source_path": str(config_path.resolve()), "sha256": config_hash
    })
    _write_json(stage_dir / "environment-report.json", {
        "frontierops_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    })

    finished_at = datetime.now(timezone.utc)
    result = StageResult(
        run_id=run_id,
        stage="build",
        status="success",
        started_at=started_at,
        finished_at=finished_at,
        outputs={"resolved_config": "00-build/resolved-config.yaml"},
        next_stage_allowed=True,
    )
    _write_json(stage_dir / "stage-result.json", result.model_dump(mode="json"))
    manifest = RunManifest(
        run_id=run_id,
        status="success",
        config_sha256=config_hash,
        stages={"build": "00-build/stage-result.json"},
        outputs={"resolved_config": "00-build/resolved-config.yaml"},
    )
    _write_json(stage_dir.parent / "run-manifest.json", manifest.model_dump(mode="json"))
    return stage_dir.parent
