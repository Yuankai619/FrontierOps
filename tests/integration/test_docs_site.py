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
        for filename in ("index.html", "guide.html"):
            with self.subTest(page=filename):
                source = DOCS / filename
                for href in parse(source).links:
                    if href.startswith(("https://", "http://", "mailto:")):
                        continue
                    path, _, fragment = href.partition("#")
                    destination = (source.parent / path).resolve() if path else source
                    self.assertTrue(destination.is_relative_to(DOCS))
                    self.assertTrue(destination.is_file(), href)
                    if fragment and destination.suffix == ".html":
                        self.assertIn(fragment, parse(destination).ids, href)


if __name__ == "__main__":
    unittest.main()
