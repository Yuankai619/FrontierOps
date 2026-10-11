"""Composition root for manual Sync."""

from pathlib import Path

from frontierops.adapters.build import SystemClock
from frontierops.adapters.config import YamlConfigAdapter
from frontierops.adapters.sync import FileSyncRepository, JsonFixtureProvider
from frontierops.application.sync import SyncUseCase
from frontierops.build import run_build
from frontierops.domain.models import FrontierConfig


def run_sync(config_path: Path) -> Path:
    config = FrontierConfig.model_validate(YamlConfigAdapter().read(config_path))
    run_dir = run_build(config_path)
    providers = {}
    for name in ("semantic_scholar", "arxiv"):
        settings = getattr(config.sources, name)
        if not settings.enabled:
            continue
        if settings.mode != "fixture" or settings.fixture_path is None:
            raise ValueError(f"{name} requires fixture_path until a live adapter is configured")
        path = settings.fixture_path
        if not path.is_absolute():
            path = config_path.resolve().parent / path
        providers[name] = JsonFixtureProvider(name, path)
    return SyncUseCase(providers, FileSyncRepository(), SystemClock()).execute(config, run_dir)
