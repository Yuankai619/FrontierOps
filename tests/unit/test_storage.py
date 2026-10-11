from pathlib import Path
import tempfile
import unittest

from frontierops.adapters.storage import FileArtifactStore, SQLiteStateIndex


class FileArtifactStoreTests(unittest.TestCase):
    def test_json_and_jsonl_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = FileArtifactStore(Path(directory))
            store.write_json(Path("item.json"), {"name": "論文"})
            store.write_jsonl(Path("items.jsonl"), [{"id": 1}, {"id": 2}])
            self.assertEqual(store.read_json(Path("item.json"))["name"], "論文")
            self.assertEqual([item["id"] for item in store.read_jsonl(Path("items.jsonl"))], [1, 2])
            with self.assertRaises(ValueError):
                store.write_json(Path("../escape.json"), {})


class SQLiteStateIndexTests(unittest.TestCase):
    def test_initialize_is_idempotent_and_preserves_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / ".frontier"
            index = SQLiteStateIndex()
            index.initialize(workspace)
            identities = workspace / "state" / "identity-map.jsonl"
            identities.write_text('{"id":"author-1"}\n', encoding="utf-8")
            index.initialize(workspace)
            self.assertEqual(identities.read_text(), '{"id":"author-1"}\n')
            self.assertTrue((workspace / "state" / "index.sqlite3").exists())
