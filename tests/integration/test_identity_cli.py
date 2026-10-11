import contextlib
import io
import json
import unittest

from frontierops.adapters.cli import main


class IdentityCliTests(unittest.TestCase):
    def invoke(self, arguments: list[str]) -> tuple[int, list[dict]]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(arguments)
        return code, json.loads(output.getvalue())

    def test_scholar_resolve_keeps_ambiguity_visible(self) -> None:
        code, candidates = self.invoke([
            "scholar", "resolve", "--name", "Alex Kim", "--provider", "semantic_scholar"
        ])
        self.assertEqual(code, 0)
        self.assertEqual(len(candidates), 2)

    def test_venue_resolve_returns_stable_id(self) -> None:
        code, candidates = self.invoke([
            "venue", "resolve", "--name", "ICLR", "--year", "2026"
        ])
        self.assertEqual(code, 0)
        self.assertEqual(candidates[0]["stable_id"], "ICLR.cc/2026/Conference")
