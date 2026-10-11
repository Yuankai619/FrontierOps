"""Validated configuration lifecycle use cases."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from frontierops.application.ports import ConfigReader, ConfigWriter
from frontierops.domain.models import FrontierConfig


@dataclass(frozen=True)
class ConfigChange:
    path: str
    before: Any
    after: Any


@dataclass(frozen=True)
class ConfigService:
    reader: ConfigReader
    writer: ConfigWriter

    def inspect(self, path: Path) -> dict[str, Any]:
        return FrontierConfig.model_validate(self.reader.read(path)).model_dump(mode="json")

    def schema(self) -> dict[str, Any]:
        return FrontierConfig.model_json_schema()

    def diff(self, old: Path, new: Path) -> list[ConfigChange]:
        before, after = self.inspect(old), self.inspect(new)
        left, right = _flatten(before), _flatten(after)
        return [
            ConfigChange(key, left.get(key), right.get(key))
            for key in sorted(left.keys() | right.keys())
            if left.get(key) != right.get(key)
        ]

    def draft(self, source: Path, output: Path) -> None:
        self.writer.write(output, self.inspect(source))

    def apply(self, candidate: Path, target: Path) -> None:
        self.writer.write(target, self.inspect(candidate))


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value}
    flattened: dict[str, Any] = {}
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        flattened.update(_flatten(child, path))
    return flattened
