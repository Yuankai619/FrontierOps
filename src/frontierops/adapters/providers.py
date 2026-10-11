"""Live arXiv and Semantic Scholar Sync provider adapters."""

from datetime import datetime, timezone
import json
import os
import re
from time import sleep
from typing import Mapping, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from frontierops.domain.models import ProviderSourceConfig, SourceBatch, SourceRecord


class HttpClient(Protocol):
    def get(self, url: str, headers: Mapping[str, str], timeout: int) -> bytes: ...


class UrlLibHttpClient:
    def get(self, url: str, headers: Mapping[str, str], timeout: int) -> bytes:
        with urlopen(Request(url, headers=dict(headers)), timeout=timeout) as response:
            return response.read()


class ArxivProvider:
    name = "arxiv"
    _atom = "{http://www.w3.org/2005/Atom}"
    _open_search = "{http://a9.com/-/spec/opensearch/1.1/}"

    def __init__(self, settings: ProviderSourceConfig, http: HttpClient) -> None:
        self.settings = settings
        self.http = http

    def fetch(self, cursor: Mapping[str, object]) -> SourceBatch:
        del cursor
        records: list[SourceRecord] = []
        start = 0
        while len(records) < self.settings.max_results:
            limit = min(self.settings.page_size, self.settings.max_results - len(records))
            params: dict[str, str | int] = {
                "start": start,
                "max_results": limit,
                "sortBy": "lastUpdatedDate",
                "sortOrder": "descending",
            }
            if self.settings.paper_ids:
                params["id_list"] = ",".join(self.settings.paper_ids)
            terms = self.settings.queries + [f"cat:{item}" for item in self.settings.categories]
            if terms:
                params["search_query"] = " OR ".join(f"({term})" for term in terms)
            base = self.settings.base_url or "https://export.arxiv.org/api/query"
            body = self.http.get(
                f"{base}?{urlencode(params)}",
                {"User-Agent": self.settings.user_agent},
                self.settings.request_timeout_seconds,
            )
            page, total = self._parse(body)
            records.extend(page)
            start += len(page)
            if not page or start >= total:
                break
            sleep(self.settings.request_delay_seconds)
        latest = max((record.updated_at for record in records), default=None)
        return SourceBatch(
            records=records,
            next_cursor={"latest_updated": latest.isoformat() if latest else None},
        )

    def _parse(self, body: bytes) -> tuple[list[SourceRecord], int]:
        root = ET.fromstring(body)
        total_node = root.find(f"{self._open_search}totalResults")
        total = int(total_node.text or "0") if total_node is not None else 0
        records = []
        for entry in root.findall(f"{self._atom}entry"):
            identifier = self._text(entry, "id").rsplit("/", 1)[-1]
            match = re.match(r"(.+?)(v\d+)?$", identifier)
            base_id = match.group(1) if match else identifier
            version = match.group(2) if match else None
            links = {
                link.attrib.get("title", link.attrib.get("rel", "")): link.attrib.get("href")
                for link in entry.findall(f"{self._atom}link")
            }
            payload = {
                "title": " ".join(self._text(entry, "title").split()),
                "abstract": " ".join(self._text(entry, "summary").split()),
                "authors": [
                    self._text(author, "name")
                    for author in entry.findall(f"{self._atom}author")
                ],
                "categories": [
                    category.attrib["term"]
                    for category in entry.findall(f"{self._atom}category")
                ],
                "published_at": self._text(entry, "published"),
                "abstract_url": links.get("alternate"),
                "pdf_url": links.get("pdf"),
            }
            records.append(SourceRecord(
                provider=self.name,
                external_id=base_id,
                version=version,
                updated_at=datetime.fromisoformat(self._text(entry, "updated").replace("Z", "+00:00")),
                payload=payload,
            ))
        return records, total

    def _text(self, element: ET.Element, name: str) -> str:
        child = element.find(f"{self._atom}{name}")
        return child.text.strip() if child is not None and child.text else ""


class SemanticScholarProvider:
    name = "semantic_scholar"
    _fields = (
        "title,abstract,authors,year,publicationDate,citationCount,"
        "influentialCitationCount,externalIds,venue,openAccessPdf,url"
    )

    def __init__(
        self, settings: ProviderSourceConfig, author_ids: list[str], http: HttpClient
    ) -> None:
        self.settings = settings
        self.author_ids = author_ids
        self.http = http

    def fetch(self, cursor: Mapping[str, object]) -> SourceBatch:
        del cursor
        records: dict[str, SourceRecord] = {}
        for author_id in self.author_ids:
            offset = 0
            while offset < self.settings.max_results:
                limit = min(self.settings.page_size, self.settings.max_results - offset)
                params = urlencode({"offset": offset, "limit": limit, "fields": self._fields})
                base = self.settings.base_url or "https://api.semanticscholar.org/graph/v1"
                headers = {"User-Agent": self.settings.user_agent}
                if self.settings.api_key_env and os.getenv(self.settings.api_key_env):
                    headers["x-api-key"] = os.environ[self.settings.api_key_env]
                body = self.http.get(
                    f"{base}/author/{author_id}/papers?{params}",
                    headers,
                    self.settings.request_timeout_seconds,
                )
                page = json.loads(body)["data"]
                for paper in page:
                    date = paper.get("publicationDate") or f"{paper['year']}-01-01"
                    records[paper["paperId"]] = SourceRecord(
                        provider=self.name,
                        external_id=paper["paperId"],
                        updated_at=datetime.fromisoformat(date).replace(tzinfo=timezone.utc),
                        payload=paper,
                    )
                offset += len(page)
                if len(page) < limit:
                    break
        latest = max((record.updated_at for record in records.values()), default=None)
        return SourceBatch(
            records=list(records.values()),
            next_cursor={"latest_publication": latest.isoformat() if latest else None},
        )
