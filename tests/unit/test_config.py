from pathlib import Path
import unittest

from pydantic import ValidationError

from frontierops.application.config import ConfigService


class MemoryConfigAdapter:
    def __init__(self, documents: dict[str, dict]) -> None:
        self.documents = documents

    def read(self, path: Path) -> dict:
        return self.documents[str(path)]

    def write(self, path: Path, payload: dict) -> None:
        self.documents[str(path)] = dict(payload)


class ConfigServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = MemoryConfigAdapter({
            "old": {"project": {"id": "demo", "name": "Demo"}},
            "new": {
                "project": {"id": "demo", "name": "Demo"},
                "brief": {"target_duration_seconds": 600},
            },
        })
        self.service = ConfigService(self.adapter, self.adapter)

    def test_diff_compares_materialized_configuration(self) -> None:
        changes = self.service.diff(Path("old"), Path("new"))
        self.assertEqual([change.path for change in changes], ["brief.target_duration_seconds"])
        self.assertEqual((changes[0].before, changes[0].after), (300, 600))

    def test_apply_validates_before_writing(self) -> None:
        self.adapter.documents["bad"] = {
            "project": {"id": "demo", "name": "Demo"}, "unknown": True
        }
        with self.assertRaises(ValidationError):
            self.service.apply(Path("bad"), Path("target"))
        self.assertNotIn("target", self.adapter.documents)

    def test_apply_materializes_defaults(self) -> None:
        self.service.apply(Path("old"), Path("target"))
        self.assertEqual(self.adapter.documents["target"]["brief"]["target_duration_seconds"], 300)

    def test_enabled_video_preview_requires_an_external_tts_adapter(self) -> None:
        self.adapter.documents["bad-video"] = {
            "project": {"id": "demo", "name": "Demo"},
            "rendering": {"video": {"enabled": True}},
        }
        with self.assertRaisesRegex(ValidationError, "heygen_tts_script"):
            self.service.inspect(Path("bad-video"))

    def test_topic_search_rejects_reversed_window_and_missing_alphaxiv_terms(self) -> None:
        self.adapter.documents["bad-topic"] = {
            "project": {"id": "demo", "name": "Demo"},
            "sources": {"alphaxiv": {"enabled": True, "mode": "live"}},
            "profile": {"topics": [{"id": "agents", "description": "agents", "search": {
                "providers": ["alphaxiv"], "query": "agent harness",
                "published_from": "2026-01-01", "published_to": "2025-12-31",
                "keywords": ["agent harness"],
            }}]},
        }
        with self.assertRaises(ValidationError):
            self.service.inspect(Path("bad-topic"))
