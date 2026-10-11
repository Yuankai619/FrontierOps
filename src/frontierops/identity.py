"""Composition root for identity resolution."""

from frontierops.adapters.identity import FixtureIdentityResolver
from frontierops.application.identity import IdentityService


def identity_service() -> IdentityService:
    resolver = FixtureIdentityResolver()
    return IdentityService(resolver, resolver)
