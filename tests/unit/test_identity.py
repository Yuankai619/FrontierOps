import unittest

from frontierops.adapters.identity import FixtureIdentityResolver


class FixtureIdentityResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = FixtureIdentityResolver()

    def test_resolves_alias_and_preserves_stable_id(self) -> None:
        result = self.resolver.resolve_scholars("A. Researcher", "semantic_scholar")
        self.assertEqual(result[0].stable_id, "fixture-author-1001")

    def test_returns_ambiguous_scholar_candidates(self) -> None:
        result = self.resolver.resolve_scholars("Alex Kim", "semantic_scholar")
        self.assertEqual([candidate.stable_id for candidate in result], [
            "fixture-author-2001", "fixture-author-2002"
        ])

    def test_resolves_venue_by_year(self) -> None:
        result = self.resolver.resolve_venues("ICLR", 2026, "openreview")
        self.assertEqual(result[0].stable_id, "ICLR.cc/2026/Conference")
