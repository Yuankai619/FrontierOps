from datetime import datetime, timezone
import unittest

from pydantic import ValidationError

from frontierops.domain.models import BriefingSection, BriefingSpec, FrontierConfig


class ConfigTests(unittest.TestCase):
    def test_duration_is_configurable(self) -> None:
        config = FrontierConfig.model_validate({
            "schema_version": "0.1",
            "project": {"id": "demo", "name": "Demo"},
            "brief": {"target_duration_seconds": 600},
        })
        self.assertEqual(config.brief.target_duration_seconds, 600)

    def test_unknown_config_key_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            FrontierConfig.model_validate({
                "project": {"id": "demo", "name": "Demo"},
                "hardcoded_threshold": 3,
            })

    def test_tracking_requires_stable_identity(self) -> None:
        config = FrontierConfig.model_validate({
            "project": {"id": "demo", "name": "Demo"},
            "tracking": {"scholars": [{
                "id": "ada", "name": "Ada Researcher",
                "identities": {"semantic_scholar": "fixture-author-1001"},
                "providers": ["semantic_scholar"],
            }]},
        })
        self.assertEqual(config.tracking.scholars[0].identities["semantic_scholar"],
                         "fixture-author-1001")


class BriefingSpecTests(unittest.TestCase):
    def test_sections_must_fit_duration_budget(self) -> None:
        with self.assertRaises(ValidationError):
            BriefingSpec(
                artifact_id="brief_1",
                run_id="run_1",
                created_at=datetime.now(timezone.utc),
                producer="test",
                title="Demo",
                language="zh-TW",
                target_duration_seconds=60,
                sections=[BriefingSection(id="paper", duration_seconds=61, headline="Paper")],
                render_targets=["html", "slides", "video"],
            )
