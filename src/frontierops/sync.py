"""Composition root for manual Sync."""

from pathlib import Path

from frontierops.adapters.build import SystemClock
from frontierops.adapters.config import YamlConfigAdapter
from frontierops.adapters.sync import FileSyncRepository, JsonFixtureProvider
from frontierops.adapters.providers import ArxivProvider, SemanticScholarProvider, UrlLibHttpClient
from frontierops.adapters.local_library import LocalLibraryProvider, ParserRouter
from frontierops.application.sync import SyncUseCase
from frontierops.build import run_build
from frontierops.domain.models import FrontierConfig


def run_sync(config_path: Path) -> Path:
    config = FrontierConfig.model_validate(YamlConfigAdapter().read(config_path))
    run_dir = run_build(config_path)
    providers = {}
    http = UrlLibHttpClient()
    for name in ("semantic_scholar", "arxiv"):
        settings = getattr(config.sources, name)
        if not settings.enabled:
            continue
        if settings.mode == "fixture":
            if settings.fixture_path is None:
                raise ValueError(f"{name} fixture mode requires fixture_path")
            path = settings.fixture_path
            if not path.is_absolute():
                path = config_path.resolve().parent / path
            providers[name] = JsonFixtureProvider(name, path)
        elif name == "arxiv":
            providers[name] = ArxivProvider(settings, http)
        else:
            author_ids = [
                identity
                for scholar in config.tracking.scholars
                if "semantic_scholar" in scholar.providers
                for identity in [scholar.identities.get("semantic_scholar")]
                if identity
            ]
            providers[name] = SemanticScholarProvider(settings, author_ids, http)
    local = config.sources.local_library
    if local.enabled:
        providers["local_library"] = LocalLibraryProvider(
            local, config_path.resolve().parent, ParserRouter()
        )
    return SyncUseCase(providers, FileSyncRepository(), SystemClock()).execute(config, run_dir)
