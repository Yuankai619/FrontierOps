import json
from pathlib import Path
import tempfile
import unittest

from frontierops.build import run_build


CONFIG = """\
schema_version: "0.1"
project:
  id: integration-demo
  name: Integration Demo
  workspace_dir: .frontier
sync:
  trigger_mode: manual
  baseline: last_successful_sync
brief:
  target_duration_seconds: 300
  maximum_developments: 5
  outputs: [html, slides, video]
"""


class BuildIntegrationTests(unittest.TestCase):
    def test_build_creates_two_independent_inspectable_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "frontier.yaml"
            config_path.write_text(CONFIG, encoding="utf-8")

            first = run_build(config_path)
            second = run_build(config_path)

            self.assertNotEqual(first, second)
            for run_dir in (first, second):
                manifest = json.loads((run_dir / "run-manifest.json").read_text())
                result = json.loads((run_dir / "00-build/stage-result.json").read_text())
                self.assertEqual(manifest["status"], "success")
                self.assertEqual(result["stage"], "build")
                self.assertTrue(result["next_stage_allowed"])
                self.assertTrue((run_dir / "00-build/resolved-config.yaml").exists())
