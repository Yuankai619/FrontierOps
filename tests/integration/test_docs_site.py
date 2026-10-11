from html.parser import HTMLParser
from pathlib import Path
import unittest


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


if __name__ == "__main__":
    unittest.main()
