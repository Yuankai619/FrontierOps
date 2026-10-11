"""Composition root for configuration use cases."""

from frontierops.adapters.config import YamlConfigAdapter
from frontierops.application.config import ConfigService


def config_service() -> ConfigService:
    adapter = YamlConfigAdapter()
    return ConfigService(adapter, adapter)
