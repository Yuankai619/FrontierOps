from pathlib import Path
import tempfile
import unittest

import pymupdf

from frontierops.adapters.visuals import extract_paper_visuals
from tests.unit.test_render import briefing, evidence


class VisualEvidenceTests(unittest.TestCase):
    def test_extracts_verifiable_figure_crop_from_claimed_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            document = pymupdf.open()
            page = document.new_page(width=612, height=792)
            page.draw_rect(pymupdf.Rect(110, 70, 500, 140), color=(0, 0, 0))
            page.insert_text((110, 175), "Figure 1: Method overview")
            document.save(root / "assets/paper.pdf")
            document.close()
            local = evidence().model_copy(update={"source_uri": "assets/paper.pdf"})
            visuals = extract_paper_visuals(briefing(), [local], root)
            self.assertEqual(visuals["paper-1"]["page"], 1)
            self.assertEqual(visuals["paper-1"]["label"], "Figure 1")
            self.assertTrue((root / str(visuals["paper-1"]["uri"])).is_file())

    def test_does_not_invent_visual_when_pdf_has_no_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            document = pymupdf.open()
            document.new_page().insert_text((100, 100), "No figure in this paper")
            document.save(root / "assets/paper.pdf")
            document.close()
            local = evidence().model_copy(update={"source_uri": "assets/paper.pdf"})
            self.assertEqual(extract_paper_visuals(briefing(), [local], root), {})


if __name__ == "__main__":
    unittest.main()
