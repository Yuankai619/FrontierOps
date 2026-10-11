"""Stable scholar and venue identity resolution use cases."""

from dataclasses import dataclass

from frontierops.application.ports import ScholarResolver, VenueResolver
from frontierops.domain.models import ScholarIdentity, VenueIdentity


@dataclass(frozen=True)
class IdentityService:
    scholars: ScholarResolver
    venues: VenueResolver

    def resolve_scholar(self, name: str, provider: str) -> list[ScholarIdentity]:
        return self.scholars.resolve_scholars(name, provider)

    def resolve_venue(self, name: str, year: int | None, provider: str) -> list[VenueIdentity]:
        return self.venues.resolve_venues(name, year, provider)
