from pathlib import Path
import json
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

    def test_pdf_sidecar_supplies_bibliography_and_changes_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "papers"
            library.mkdir()
            document = pymupdf.open()
            document.new_page().insert_text((72, 72), "Research paper")
            pdf = library / "paper.pdf"
            document.save(pdf)
            document.close()
            provider = LocalLibraryProvider(
                LocalLibraryConfig(enabled=True, roots=[Path("papers")]), root, ParserRouter()
            )
            original = provider.fetch({}).records[0]
            sidecar = pdf.with_name("paper.pdf.json")
            sidecar.write_text(json.dumps({
                "title": "Real paper title", "authors": ["A. Scholar"],
                "affiliations": ["Example University"], "arxiv_id": "2605.31468",
                "publication_status": "preprint", "source_url": "https://arxiv.org/abs/2605.31468",
            }), encoding="utf-8")
            updated = provider.fetch({}).records[0]
            self.assertNotEqual(original.version, updated.version)
            self.assertEqual(updated.payload["title"], "Real paper title")
            self.assertEqual(updated.payload["metadata"]["affiliations"], ["Example University"])
