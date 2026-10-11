"""YAML, filesystem, clock, and environment adapters for Build."""

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
from typing import Any, Mapping

import yaml

from frontierops import __version__


class FileRunRepository:
    def save(self, workspace: Path, run_id: str, files: Mapping[str, Any]) -> Path:
        run_dir = workspace / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        for relative, payload in files.items():
            path = run_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            text = (yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
                    if path.suffix == ".yaml"
                    else json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(text, encoding="utf-8")
            temporary.replace(path)
        return run_dir


class SystemEnvironment:
    def read(self) -> Mapping[str, str]:
        return {"frontierops_version": __version__, "python_version": platform.python_version(),
                "platform": platform.platform()}


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
