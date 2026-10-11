"""alphaXiv MCP discovery adapter; intentionally a top-k supplement, not a corpus sync."""

import asyncio
from datetime import datetime, timezone
import json
import os
import re
from typing import Any, Protocol
import xml.etree.ElementTree as ET

from frontierops.domain.models import ProviderSourceConfig, SourceBatch, SourceRecord, TopicConfig


class PaperDiscovery(Protocol):
    async def discover(self, arguments: dict[str, Any]) -> Any: ...


class AlphaXivMcpClient:
    def __init__(self, endpoint: str, api_key: str, timeout: int) -> None:
        self.endpoint, self.api_key, self.timeout = endpoint, api_key, timeout

    async def discover(self, arguments: dict[str, Any]) -> Any:
        result = await self._call("discover_papers", arguments)
        if result.structured_content is not None:
            return result.structured_content
        text = "\n".join(block.text for block in result.content if block.type == "text")
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError("alphaXiv returned non-JSON discovery content; cannot sync stable IDs") from error

    async def answer_pdf_queries(self, paper: str, queries: list[str]) -> str:
        result = await self._call("answer_pdf_queries", {"paper": paper, "queries": queries})
        text = "\n".join(block.text for block in result.content if block.type == "text")
        if not text:
            raise ValueError("alphaXiv returned no page-level PDF text")
        return text

    async def _call(self, name: str, arguments: dict[str, Any]) -> Any:
        try:
            import httpx2
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client
        except ImportError as error:
            raise RuntimeError("alphaXiv requires uv sync --extra alphaxiv") from error
        async with httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"}, timeout=self.timeout
        ) as http:
            async with streamable_http_client(self.endpoint, http_client=http) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
                    if result.is_error:
                        raise RuntimeError(f"alphaXiv {name} returned an MCP error")
                    return result


class AlphaXivProvider:
    name = "alphaxiv"

    def __init__(self, settings: ProviderSourceConfig, topics: list[TopicConfig],
                 client: PaperDiscovery | None = None) -> None:
        self.settings = settings
        self.topics = [topic for topic in topics if topic.search and self.name in topic.search.providers]
        if client is None:
            key_name = settings.api_key_env or "ALPHAXIV_API_KEY"
            key = os.getenv(key_name)
            if not key:
                raise ValueError(f"alphaXiv live mode requires {key_name} in the environment")
            client = AlphaXivMcpClient(
                settings.base_url or "https://api.alphaxiv.org/mcp/v1", key,
                settings.request_timeout_seconds,
            )
        self.client = client

    def fetch(self, cursor: dict) -> SourceBatch:
        del cursor
        return asyncio.run(self._fetch())

    async def _fetch(self) -> SourceBatch:
        records: dict[str, SourceRecord] = {}
        scopes: list[dict] = []
        for topic in self.topics:
            search = topic.search
            assert search is not None
            arguments: dict[str, Any] = {
                "keywords": search.keywords, "question": search.query,
                "difficulty": search.alphaxiv_difficulty, "prioritize": "recency",
            }
            if search.published_from:
                arguments["published_after"] = search.published_from.isoformat()
            if search.published_to:
                arguments["published_before"] = search.published_to.isoformat()
            papers = _papers(await self.client.discover(arguments))
            for paper in papers[:self.settings.max_results]:
                record = _record(paper, topic.id)
                prior = records.get(record.external_id)
                if prior:
                    record.payload["topic_ids"] = sorted(set(prior.payload["topic_ids"] + [topic.id]))
                records[record.external_id] = record
            scopes.append({"topic_id": topic.id, "fetched": len(papers), "coverage": "top_k_only"})
        return SourceBatch(records=list(records.values()), next_cursor={"scopes": scopes})


def _papers(result: Any) -> list[dict]:
    if isinstance(result, dict) and isinstance(result.get("data"), (list, dict)):
        result = result["data"]
    if isinstance(result, dict):
        for key in ("papers", "results", "items"):
            if isinstance(result.get(key), list):
                result = result[key]
                break
    if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
        raise ValueError("alphaXiv discovery must return a structured paper list")
    return result


def _record(paper: dict, topic_id: str) -> SourceRecord:
    url = paper.get("url") or paper.get("paper_url") or paper.get("paperUrl") or ""
    arxiv_id = paper.get("arxiv_id") or paper.get("arxivId")
    if not arxiv_id:
        match = re.search(r"(?:arxiv\.org|alphaxiv\.org)/(?:abs|pdf)/([^/?#]+)", url)
        arxiv_id = match.group(1) if match else None
    identifier = arxiv_id or paper.get("universal_paper_id") or paper.get("universalPaperId")
    if not identifier:
        raise ValueError("alphaXiv paper lacks a stable arXiv/universal ID")
    identifier = re.sub(r"v\d+$", "", str(identifier))
    arxiv_id = re.sub(r"v\d+$", "", str(arxiv_id)) if arxiv_id else None
    published = (paper.get("publication_date") or paper.get("publicationDate") or
                 paper.get("published_at"))
    when = datetime.fromisoformat(str(published).replace("Z", "+00:00")) if published else datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    payload = {
        "title": paper.get("title") or "", "abstract": (paper.get("abstract") or
                 paper.get("abstract_preview") or paper.get("abstractPreview") or ""),
        "published_at": published, "year": when.year if published else None,
        "authors": paper.get("authors") or [],
        "url": url or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""),
        "pdf_url": (paper.get("pdf_url") or paper.get("pdfUrl") or
                    (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None)),
        "arxiv_id": arxiv_id, "topic_ids": [topic_id],
        "organizations": paper.get("contributing_organizations") or [],
    }
    return SourceRecord(provider="alphaxiv", external_id=identifier, updated_at=when, payload=payload)


def parse_page_xml(payload: str) -> list[tuple[int, str]]:
    root = ET.fromstring(payload)
    if root.tag != "paper":
        raise ValueError("alphaXiv page response must have a paper root")
    pages = []
    for node in root.findall("page"):
        number = int(node.attrib["num"])
        text = "".join(node.itertext()).strip()
        if number < 1 or not text:
            continue
        pages.append((number, text))
    if not pages:
        raise ValueError("alphaXiv returned no cited PDF pages")
    return pages
