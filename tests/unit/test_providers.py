import json
import unittest

from frontierops.adapters.providers import ArxivProvider, SemanticScholarProvider
from frontierops.adapters.openalex import OpenAlexProvider
from frontierops.adapters.alphaxiv import AlphaXivProvider, parse_page_xml
from frontierops.domain.models import ProviderSourceConfig, TopicConfig


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
    def test_alphaxiv_wrapped_results_and_page_xml(self) -> None:
        topic = TopicConfig(id="agents", description="agents", search={
            "providers": ["alphaxiv"], "query": "agent harness",
            "keywords": ["agent", "harness", "evaluation"],
        })

        class FakeMcp:
            async def discover(self, arguments: dict) -> dict:
                return {"data": {"papers": [{
                    "arxivId": "2601.12345v2", "title": "A Harness",
                    "publicationDate": "2026-01-03", "abstractPreview": "Agent evaluation",
                }]}}

        batch = AlphaXivProvider(ProviderSourceConfig(enabled=True, mode="live"),
                                [topic], FakeMcp()).fetch({})
        self.assertEqual(batch.records[0].external_id, "2601.12345")
        self.assertEqual(batch.records[0].payload["abstract"], "Agent evaluation")
        self.assertEqual(parse_page_xml(
            '<paper><page num="2">The method <b>compares</b> agents.</page></paper>'
        ), [(2, "The method compares agents.")])
        with self.assertRaises(ValueError):
            parse_page_xml('<paper><page num="1"> </page></paper>')

    def test_alphaxiv_mcp_arguments_and_stable_ids(self) -> None:
        class FakeMcp:
            arguments: dict | None = None

            async def discover(self, arguments: dict) -> dict:
                self.arguments = arguments
                return {"papers": [{"arxiv_id": "2501.12345v2", "title": "Agent Harness",
                                    "publication_date": "2025-02-03", "abstract_preview": "A new agent harness."}]}

        topic = TopicConfig(id="agents", description="AI agent harness", search={
            "providers": ["alphaxiv"], "query": "Agent execution harnesses for coding research",
            "keywords": ["agent harness", "coding agents", "execution environments"],
            "published_from": "2025-01-01", "published_to": "2025-12-31",
        })
        client = FakeMcp()
        batch = AlphaXivProvider(ProviderSourceConfig(enabled=True, mode="live"),
                                [topic], client).fetch({})
        self.assertEqual(client.arguments["published_before"], "2025-12-31")
        self.assertEqual(batch.records[0].external_id, "2501.12345")
        self.assertEqual(batch.records[0].payload["topic_ids"], ["agents"])
        self.assertEqual(batch.next_cursor["scopes"][0]["coverage"], "top_k_only")

    def test_openalex_search_window_paginates_and_reconstructs_abstract(self) -> None:
        work = {
            "id": "https://openalex.org/W123", "title": "Agent Harness Study",
            "publication_year": 2025, "publication_date": "2025-06-01",
            "updated_date": "2026-01-02T00:00:00", "cited_by_count": 7,
            "abstract_inverted_index": {"Agent": [0], "harness": [1], "study": [2]},
            "authorships": [{"author": {"display_name": "Ada"}}],
            "primary_location": {"landing_page_url": "https://example.org/paper", "source": {"display_name": "ICLR"}},
            "ids": {"openalex": "https://openalex.org/W123"},
        }
        http = FakeHttp([
            json.dumps({"results": [work], "meta": {"next_cursor": "page-2"}}).encode(),
            json.dumps({"results": [], "meta": {"next_cursor": None}}).encode(),
        ])
        topic = TopicConfig(id="agents", description="AI agent harness", search={
            "providers": ["openalex"], "query": '"agent harness"',
            "published_from": "2025-01-01", "published_to": "2025-12-31",
        })
        source = ProviderSourceConfig(enabled=True, mode="live", page_size=1, max_results=3,
                                      request_delay_seconds=0)
        batch = OpenAlexProvider(source, [topic], http).fetch({})
        self.assertEqual(batch.records[0].payload["abstract"], "Agent harness study")
        self.assertEqual(batch.records[0].payload["citationCount"], 7)
        self.assertEqual(batch.records[0].payload["topic_ids"], ["agents"])
        self.assertIn("from_publication_date%3A2025-01-01", http.requests[0][0])
        self.assertIn("cursor=page-2", http.requests[1][0])
        self.assertFalse(batch.next_cursor["scopes"][0]["truncated"])

    def test_openalex_reports_truncated_scope(self) -> None:
        http = FakeHttp([json.dumps({"results": [{"id": "https://openalex.org/W1"}],
                                     "meta": {"next_cursor": "more"}}).encode()])
        topic = TopicConfig(id="agents", description="agents", search={"providers": ["openalex"],
                                                                 "query": "agent harness"})
        source = ProviderSourceConfig(enabled=True, mode="live", max_results=1)
        batch = OpenAlexProvider(source, [topic], http).fetch({})
        self.assertTrue(batch.next_cursor["scopes"][0]["truncated"])

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
