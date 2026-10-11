from datetime import datetime, timezone
import json
import re
import unittest

from frontierops.adapters.html import StaticHtmlRenderer
from frontierops.adapters.slides import OpenSlideRenderer
from frontierops.application.render import RenderService, claim_fingerprints
from frontierops.domain.models import BriefingSpec, Evidence


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def briefing() -> BriefingSpec:
    return BriefingSpec.model_validate({
        "artifact_id": "brief-1", "run_id": "run-1", "created_at": NOW,
        "producer": "test", "input_refs": [], "title": "Paper <Two>",
        "language": "zh-TW", "target_duration_seconds": 60,
        "render_targets": ["html", "slides", "video"],
        "sections": [{
            "id": "paper-1", "duration_seconds": 60, "headline": "Paper2Video",
            "claims": [{"text": "101 papers & videos", "kind": "factual",
                        "evidence_ids": ["evidence-1"]}],
        }],
    })


def evidence() -> Evidence:
    return Evidence(
        artifact_id="evidence-1", run_id="run-1", created_at=NOW, producer="test",
        source_ref="signal-1", source_uri="https://example.test/paper?a=1&b=2",
        locator={"type": "pdf_page", "page": 2}, content="101 papers & videos",
        evidence_tier="primary_fulltext",
    )


class RenderServiceTests(unittest.TestCase):
    def test_html_escapes_content_and_preserves_claim_identity(self) -> None:
        spec = briefing()
        output = RenderService().execute(spec, [evidence()], [StaticHtmlRenderer()])
        document = output.documents["html"]
        self.assertIn("Paper &lt;Two&gt;", document)
        self.assertIn("101 papers &amp; videos", document)
        self.assertIn("p. 2", document)
        self.assertIn("a=1&amp;b=2", document)
        self.assertIn('role="tablist"', document)
        self.assertIn('role="tabpanel"', document)
        self.assertIn("查核證據", document)
        self.assertNotIn('class="kicker"', document)
        metadata = re.search(
            r'<script id="frontierops-claims" type="application/json">(.*?)</script>',
            document,
        )
        self.assertIsNotNone(metadata)
        self.assertEqual(json.loads(metadata.group(1))["claim_fingerprints"],
                         claim_fingerprints(spec))
        self.assertEqual(output.missing_targets, ["slides", "video"])

    def test_html_connects_figure_to_original_pdf_page(self) -> None:
        visual = {"paper-1": {"uri": "visuals/figure.png", "source_uri": "assets/paper.pdf",
                              "page": 2, "label": "Figure 1", "caption": "Architecture"}}
        document = StaticHtmlRenderer(visual).render(briefing(), [evidence()])
        self.assertIn('src="visuals/figure.png"', document)
        self.assertIn('href="assets/paper.pdf#page=2"', document)
        self.assertIn("Figure 1 · p. 2 Architecture", document)

    def test_slide_deck_uses_the_same_claim_fingerprints(self) -> None:
        spec = briefing()
        output = RenderService().execute(spec, [evidence()], [OpenSlideRenderer()])
        document = output.documents["slides"]
        metadata = re.search(r'export const frontieropsClaims = (\{.*?\});', document)
        self.assertIsNotNone(metadata)
        self.assertEqual(json.loads(metadata.group(1))["claim_fingerprints"],
                         claim_fingerprints(spec))
        self.assertEqual(document.count('data-claim-fingerprint="'), 1)
        self.assertIn("import type { Page, SlideMeta } from '@open-slide/core'", document)
        self.assertIn("export default [Cover, Paper1Context", document)
        self.assertNotIn("class=\"kicker\"", document)

    def test_openslide_imports_a_source_figure(self) -> None:
        visual = {"paper-1": {"uri": "visuals/figure.png", "source_uri": "assets/paper.pdf",
                              "page": 2, "label": "Figure 1", "caption": "Architecture"}}
        document = OpenSlideRenderer(visual).render(briefing(), [evidence()])
        self.assertIn("import figure1 from '../../assets/figure.png'", document)
        self.assertIn('<img src={figure1}', document)
        self.assertIn("Figure 1 · p. 2", document)
        self.assertIn("export const notes =", document)
