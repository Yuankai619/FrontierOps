"""Deterministic offline identity resolver backed by package fixtures."""

from importlib.resources import files
import json
from pathlib import Path
from typing import Any

from frontierops.domain.models import ScholarIdentity, VenueIdentity


class FixtureIdentityResolver:
    def __init__(self, fixture_path: Path | None = None) -> None:
        if fixture_path:
            text = fixture_path.read_text(encoding="utf-8")
        else:
            text = files("frontierops").joinpath("fixtures/identities.json").read_text(
                encoding="utf-8"
            )
        self.data: dict[str, list[dict[str, Any]]] = json.loads(text)

    def resolve_scholars(self, name: str, provider: str) -> list[ScholarIdentity]:
        query = name.casefold()
        return [
            ScholarIdentity.model_validate(item)
            for item in self.data["scholars"]
            if item["provider"] == provider
            and any(query in value.casefold() for value in [item["name"], *item["aliases"]])
        ]

    def resolve_venues(self, name: str, year: int | None, provider: str) -> list[VenueIdentity]:
        query = name.casefold()
        return [
            VenueIdentity.model_validate(item)
            for item in self.data["venues"]
            if item["provider"] == provider
            and query in item["name"].casefold()
            and (year is None or item["year"] == year)
        ]
