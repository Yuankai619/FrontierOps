"""OpenAlex works search adapter for bounded, repeatable topic discovery."""

from datetime import datetime, timezone
import json
import os
from time import sleep
from urllib.parse import urlencode

from frontierops.adapters.providers import HttpClient
from frontierops.domain.models import ProviderSourceConfig, SourceBatch, SourceRecord, TopicConfig


def _abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions = {position: word for word, offsets in index.items() for position in offsets}
    return " ".join(positions[position] for position in sorted(positions))


class OpenAlexProvider:
    name = "openalex"
    _fields = (
        "id,doi,title,ids,publication_year,publication_date,abstract_inverted_index,"
        "authorships,primary_location,best_oa_location,cited_by_count,updated_date"
    )

    def __init__(self, settings: ProviderSourceConfig, topics: list[TopicConfig], http: HttpClient) -> None:
        self.settings = settings
        self.topics = [topic for topic in topics if topic.search and self.name in topic.search.providers]
        self.http = http

    def fetch(self, cursor: dict) -> SourceBatch:
        del cursor  # Re-query bounded scope: OpenAlex created/updated-date sync is paid.
        records: dict[str, SourceRecord] = {}
        scopes: list[dict] = []
        for topic in self.topics:
            search = topic.search
            assert search is not None
            page_cursor = "*"
            seen = 0
            total_matched = None
            while page_cursor and seen < self.settings.max_results:
                limit = min(self.settings.page_size, self.settings.max_results - seen, 100)
                filters = []
                if search.published_from:
                    filters.append(f"from_publication_date:{search.published_from}")
                if search.published_to:
                    filters.append(f"to_publication_date:{search.published_to}")
                params = {"search.title_abstract_keywords": search.query, "per_page": limit,
                          "cursor": page_cursor, "select": self._fields}
                if filters:
                    params["filter"] = ",".join(filters)
                base = self.settings.base_url or "https://api.openalex.org/works"
                headers = {"User-Agent": self.settings.user_agent}
                if self.settings.api_key_env and os.getenv(self.settings.api_key_env):
                    headers["Authorization"] = f"Bearer {os.environ[self.settings.api_key_env]}"
                response = json.loads(self.http.get(
                    f"{base}?{urlencode(params)}", headers, self.settings.request_timeout_seconds
                ))
                total_matched = response.get("meta", {}).get("count", total_matched)
                page = response.get("results", [])
                for work in page:
                    record = self._record(work, topic.id)
                    existing = records.get(record.external_id)
                    if existing:
                        record.payload["topic_ids"] = sorted(set(existing.payload["topic_ids"] + [topic.id]))
                    records[record.external_id] = record
                seen += len(page)
                page_cursor = response.get("meta", {}).get("next_cursor") if page else None
                if page_cursor and seen < self.settings.max_results:
                    sleep(self.settings.request_delay_seconds)
            scopes.append({"topic_id": topic.id, "fetched": seen,
                           "total_matched": total_matched,
                           "truncated": bool(page_cursor) and (total_matched is None or seen < total_matched)})
        return SourceBatch(records=list(records.values()), next_cursor={"scopes": scopes})

    def _record(self, work: dict, topic_id: str) -> SourceRecord:
        location = work.get("primary_location") or {}
        oa = work.get("best_oa_location") or {}
        source = location.get("source") or {}
        paper_id = work["id"].rsplit("/", 1)[-1]
        published = work.get("publication_date")
        updated = work.get("updated_date") or published
        timestamp = datetime.fromisoformat(updated.replace("Z", "+00:00")) if updated else datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        payload = {
            "title": work.get("title") or "", "abstract": _abstract(work.get("abstract_inverted_index")),
            "authors": [entry.get("author", {}).get("display_name", "") for entry in work.get("authorships", [])],
            "year": work.get("publication_year"), "published_at": published,
            "citationCount": work.get("cited_by_count"), "venue": source.get("display_name"),
            "url": location.get("landing_page_url") or work["id"],
            "pdf_url": oa.get("pdf_url") or location.get("pdf_url"),
            "externalIds": {"DOI": work.get("doi"), "OpenAlex": paper_id},
            "topic_ids": [topic_id],
        }
        return SourceRecord(provider=self.name, external_id=paper_id, updated_at=timestamp, payload=payload)
