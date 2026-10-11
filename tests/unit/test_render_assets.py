from pathlib import Path
import tempfile
import unittest

from frontierops.adapters.render_assets import materialize_local_evidence
from tests.unit.test_render import evidence


class RenderAssetTests(unittest.TestCase):
    def test_copies_local_evidence_with_content_addressed_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "paper.pdf").write_bytes(b"paper")
            local = evidence().model_copy(update={
                "source_uri": "paper.pdf", "producer": "rank:fulltext",
            })
            materialized, manifest = materialize_local_evidence(
                [local], root, root / "render"
            )
            self.assertTrue(materialized[0].source_uri.startswith("assets/"))
            self.assertEqual(manifest[0]["evidence_ids"], ["evidence-1"])
            self.assertEqual((root / "render" / materialized[0].source_uri).read_bytes(), b"paper")

    def test_remote_evidence_is_not_copied(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            remote = evidence()
            materialized, manifest = materialize_local_evidence(
                [remote], Path(directory), Path(directory) / "render"
            )
            self.assertEqual(materialized, [remote])
            self.assertEqual(manifest, [])
