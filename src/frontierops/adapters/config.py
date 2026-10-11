"""YAML configuration adapter."""

from pathlib import Path
from typing import Any, Mapping

import yaml


class YamlConfigAdapter:
    def read(self, path: Path) -> Mapping[str, Any]:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("configuration must be a YAML mapping")
        return payload

    def write(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            yaml.safe_dump(dict(payload), sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        temporary.replace(path)
