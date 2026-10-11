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
            page.draw_rect(pymupdf.Rect(110, 100, 500, 360), color=(0, 0, 0))
            page.insert_text((110, 420), "Figure 1: Method overview")
            document.save(root / "assets/paper.pdf")
            document.close()
            local = evidence().model_copy(update={"source_uri": "assets/paper.pdf"})
            visuals = extract_paper_visuals(briefing(), [local], root)
            self.assertEqual(visuals["paper-1"]["page"], 1)
            self.assertEqual(visuals["paper-1"]["label"], "Figure 1")
            crop = root / str(visuals["paper-1"]["uri"])
            self.assertTrue(crop.is_file())
            with pymupdf.open(crop) as image:
                self.assertGreater(image[0].rect.height, 450)

            replacement = pymupdf.open()
            replacement_page = replacement.new_page(width=612, height=792)
            replacement_page.draw_rect(pymupdf.Rect(110, 70, 500, 360), color=(0, 0, 0))
            replacement_page.insert_text((110, 420), "Figure 1: Method overview")
            replacement.save(root / "assets/replacement.pdf")
            replacement.close()
            (root / "assets/replacement.pdf").replace(root / "assets/paper.pdf")
            extract_paper_visuals(briefing(), [local], root)
            with pymupdf.open(crop) as image:
                self.assertGreater(image[0].rect.height, 500)

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
