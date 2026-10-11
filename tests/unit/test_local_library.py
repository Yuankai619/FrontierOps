from pathlib import Path
import tempfile
import unittest

import pymupdf

from frontierops.adapters.local_library import LocalLibraryProvider, ParserRouter
from frontierops.domain.models import LocalLibraryConfig


class LocalLibraryTests(unittest.TestCase):
    def test_pdf_has_page_locator_and_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "papers"
            library.mkdir()
            document = pymupdf.open()
            page = document.new_page()
            page.insert_text((72, 72), "Paper2Video method and limitation")
            document.save(library / "paper.pdf")
            document.close()

            provider = LocalLibraryProvider(
                LocalLibraryConfig(enabled=True, roots=[Path("papers")]),
                root,
                ParserRouter(),
            )
            record = provider.fetch({}).records[0]
            self.assertEqual(record.external_id, "papers/paper.pdf")
            self.assertEqual(record.payload["parser"], "pymupdf")
            self.assertEqual(record.payload["sections"][0]["locator"]["page"], 1)
            self.assertIn("Paper2Video", record.payload["sections"][0]["text"])

    def test_root_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            provider = LocalLibraryProvider(
                LocalLibraryConfig(enabled=True, roots=[Path("..")]), root, ParserRouter()
            )
            with self.assertRaisesRegex(ValueError, "escapes project"):
                provider.fetch({})
