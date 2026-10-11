from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

from frontierops.domain.models import (
    BriefConfig, FeatureConfig, GateConfig, KeywordsConfig, LocalLibraryConfig,
    OpenReviewSourceConfig, ProfileConfig, ProjectConfig, ProviderSourceConfig,
    RankingConfig, RankingFeatures, ReviewConfig, ScholarTracker, SyncConfig,
    TopicConfig, TopicSearchConfig, VenueTracker, VideoPreviewConfig,
)


DOCS = Path(__file__).resolve().parents[2] / "docs"


class PageLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])


def parse(page: Path) -> PageLinks:
    parser = PageLinks()
    parser.feed(page.read_text(encoding="utf-8"))
    return parser


class DocsSiteTests(unittest.TestCase):
    def test_local_links_and_anchors_resolve(self) -> None:
        for source in DOCS.glob("*.html"):
            with self.subTest(page=source.name):
                for href in parse(source).links:
                    if href.startswith(("https://", "http://", "mailto:")):
                        continue
                    path, _, fragment = href.partition("#")
                    destination = (source.parent / path).resolve() if path else source
                    self.assertTrue(destination.is_relative_to(DOCS))
                    self.assertTrue(destination.is_file(), href)
                    if fragment and destination.suffix == ".html":
                        self.assertIn(fragment, parse(destination).ids, href)

    def test_each_guide_topic_is_a_separate_page(self) -> None:
        for filename in ("quick-start.html", "steps.html", "configuration.html",
                         "credentials.html", "commands.html", "outputs.html"):
            with self.subTest(page=filename):
                self.assertTrue((DOCS / filename).is_file())
                self.assertIn('class="docs-nav"', (DOCS / filename).read_text())

    def test_public_navigation_does_not_link_to_old_example(self) -> None:
        for source in DOCS.glob("*.html"):
            with self.subTest(page=source.name):
                self.assertNotIn("example.html", source.read_text(encoding="utf-8"))

    def test_landing_output_links_and_footer(self) -> None:
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="https://github.com/open-slide/open-slide"', html)
        self.assertIn("<h3>Video</h3>", html)
        self.assertNotIn("Narrated preview", html)
        self.assertNotIn("System spec", html.split("<footer", 1)[1])

    def test_public_pages_are_english(self) -> None:
        for source in DOCS.glob("*.html"):
            with self.subTest(page=source.name):
                html = source.read_text(encoding="utf-8")
                self.assertIn('lang="en"', html)
                self.assertIsNone(re.search(r"[\u4e00-\u9fff]", html))

    def test_linked_markdown_documentation_is_english(self) -> None:
        for source in (DOCS / "system-spec.md", DOCS / "user-manual.md", DOCS.parent / "README.md"):
            with self.subTest(page=source.name):
                self.assertIsNone(re.search(r"[\u4e00-\u9fff]", source.read_text(encoding="utf-8")))

    def test_config_reference_covers_every_nested_schema_field(self) -> None:
        html = (DOCS / "configuration.html").read_text(encoding="utf-8")
        models = (
            (ProjectConfig, "project."), (ProviderSourceConfig, ""),
            (LocalLibraryConfig, "sources.local_library."),
            (OpenReviewSourceConfig, "sources.openreview."),
            (ScholarTracker, "tracking.scholars[]."),
            (VenueTracker, "tracking.venues[]."),
            (TopicConfig, "profile.topics[]."),
            (TopicSearchConfig, "profile.topics[].search."),
            (KeywordsConfig, "profile.keywords."),
            (GateConfig, "ranking.gates[]."),
            (RankingConfig, "ranking."),
            (RankingFeatures, "ranking.features."),
            (FeatureConfig, "ranking.features.*."),
            (SyncConfig, "sync."), (BriefConfig, "brief."),
            (ReviewConfig, "review."),
            (VideoPreviewConfig, "rendering.video."),
        )
        for model, prefix in models:
            for field in model.model_fields:
                with self.subTest(field=f"{prefix}{field}"):
                    self.assertIn(f"<code>{prefix}{field}</code>", html)


if __name__ == "__main__":
    unittest.main()
