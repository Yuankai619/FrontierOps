import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from frontierops.adapters.cli import main
from frontierops.adapters.config import YamlConfigAdapter


class SetupTests(unittest.TestCase):
    def invoke(self, root: Path) -> tuple[int, dict]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["setup", "--workspace", str(root), "--name", "Research Lab"])
        return code, json.loads(output.getvalue())

    def test_creates_active_config_and_output_without_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "lab"
            code, result = self.invoke(root)
            self.assertEqual(code, 0)
            self.assertTrue(result["created_config"])
            self.assertEqual(result["output_dir"], str(root / "frontier_output"))
            self.assertTrue((root / "frontier_output").is_dir())
            config = YamlConfigAdapter().read(root / "frontier.yaml")
            self.assertEqual(config["project"]["id"], "research-lab")
            self.assertFalse(config["sources"]["arxiv"]["enabled"])
            self.assertEqual(config["brief"]["outputs"], ["html", "slides"])

    def test_is_idempotent_and_respects_custom_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "lab"
            self.invoke(root)
            path = root / "frontier.yaml"
            config = dict(YamlConfigAdapter().read(path))
            config["project"]["output_dir"] = "papers-out"
            YamlConfigAdapter().write(path, config)
            before = path.read_bytes()
            code, result = self.invoke(root)
            self.assertEqual(code, 0)
            self.assertFalse(result["created_config"])
            self.assertEqual(path.read_bytes(), before)
            self.assertTrue((root / "papers-out").is_dir())
