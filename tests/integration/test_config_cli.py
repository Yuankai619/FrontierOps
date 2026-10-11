import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from frontierops.adapters.cli import main


BASE = """\
project:
  id: demo
  name: Demo
"""

CHANGED = """\
project:
  id: demo
  name: Demo
brief:
  target_duration_seconds: 600
"""


class ConfigCliTests(unittest.TestCase):
    def invoke(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_config_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old, new = root / "old.yaml", root / "new.yaml"
            draft, target = root / "draft.yaml", root / "frontier.yaml"
            old.write_text(BASE, encoding="utf-8")
            new.write_text(CHANGED, encoding="utf-8")

            code, output, _ = self.invoke(["config", "validate", "--config", str(old)])
            self.assertEqual(code, 0)
            self.assertIn("valid:", output)

            code, output, _ = self.invoke([
                "config", "diff", "--old", str(old), "--new", str(new)
            ])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)[0]["path"], "brief.target_duration_seconds")

            self.assertEqual(self.invoke([
                "config", "draft", "--config", str(old), "--output", str(draft)
            ])[0], 0)
            self.assertIn("target_duration_seconds: 300", draft.read_text())

            self.assertEqual(self.invoke([
                "config", "apply", "--candidate", str(new), "--config", str(target)
            ])[0], 0)
            self.assertIn("target_duration_seconds: 600", target.read_text())

    def test_schema_and_invalid_config(self) -> None:
        code, output, _ = self.invoke(["schema", "config", "--format", "json"])
        self.assertEqual(code, 0)
        self.assertIn("project", json.loads(output)["properties"])
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.yaml"
            invalid.write_text(BASE + "unexpected: true\n", encoding="utf-8")
            code, _, error = self.invoke(["config", "validate", "--config", str(invalid)])
            self.assertEqual(code, 2)
            self.assertIn("Extra inputs are not permitted", error)
