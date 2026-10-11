import json
import unittest

from frontierops.adapters.providers import ArxivProvider, SemanticScholarProvider
from frontierops.domain.models import ProviderSourceConfig


ATOM = b"""\
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>https://arxiv.org/abs/2510.05096v2</id>
    <updated>2025-10-09T17:29:00Z</updated><published>2025-10-06T17:58:02Z</published>
    <title> Paper2Video: Automatic Video Generation </title>
    <summary> A benchmark and an agent. </summary>
    <author><name>Zeyu Zhu</name></author><category term="cs.CV" />
    <link rel="alternate" href="https://arxiv.org/abs/2510.05096" />
    <link title="pdf" href="https://arxiv.org/pdf/2510.05096" />
  </entry>
</feed>
"""


class FakeHttp:
    def __init__(self, responses: list[bytes]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, dict[str, str]]] = []

    def get(self, url: str, headers: dict[str, str], timeout: int) -> bytes:
        self.requests.append((url, dict(headers)))
        return self.responses.pop(0)


class LiveProviderContractTests(unittest.TestCase):
    def test_arxiv_preserves_base_id_version_and_locators(self) -> None:
        http = FakeHttp([ATOM])
        settings = ProviderSourceConfig(
            enabled=True, mode="live", paper_ids=["2510.05096"], page_size=1
        )
        batch = ArxivProvider(settings, http).fetch({})
        record = batch.records[0]
        self.assertEqual((record.external_id, record.version), ("2510.05096", "v2"))
        self.assertEqual(record.payload["pdf_url"], "https://arxiv.org/pdf/2510.05096")
        self.assertIn("id_list=2510.05096", http.requests[0][0])

    def test_semantic_scholar_paginates_and_deduplicates_authors(self) -> None:
        first = {"data": [{
            "paperId": "paper-1", "title": "One", "year": 2025,
            "publicationDate": "2025-01-02",
        }]}
        empty = {"data": []}
        http = FakeHttp([json.dumps(first).encode(), json.dumps(empty).encode()])
        settings = ProviderSourceConfig(
            enabled=True, mode="live", page_size=1, max_results=2,
            api_key_env="UNSET_TEST_KEY",
        )
        batch = SemanticScholarProvider(settings, ["author-1"], http).fetch({})
        self.assertEqual([record.external_id for record in batch.records], ["paper-1"])
        self.assertIn("offset=1", http.requests[1][0])
        self.assertNotIn("x-api-key", http.requests[0][1])
