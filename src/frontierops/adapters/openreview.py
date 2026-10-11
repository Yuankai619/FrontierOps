"""OpenReview API v2 adapter preserving forum and reply provenance."""

from datetime import datetime, timezone
import os
from typing import Any, Mapping, Protocol

import openreview

from frontierops.domain.models import OpenReviewSourceConfig, SourceBatch, SourceRecord


class OpenReviewClient(Protocol):
    def get_group(self, group_id: str) -> Any: ...
    def get_all_notes(self, **params: Any) -> list[Any]: ...


def authenticated_client(settings: OpenReviewSourceConfig) -> OpenReviewClient:
    token = os.getenv(settings.token_env)
    username = os.getenv(settings.username_env)
    password = os.getenv(settings.password_env)
    if not token and not (username and password):
        raise ValueError(
            f"OpenReview live mode requires {settings.token_env} or "
            f"{settings.username_env} plus {settings.password_env}"
        )
    return openreview.api.OpenReviewClient(
        baseurl=settings.base_url,
        token=token,
        username=username,
        password=password,
    )


class OpenReviewProvider:
    name = "openreview"

    def __init__(
        self,
        settings: OpenReviewSourceConfig,
        venues: Mapping[str, list[str]],
        client: OpenReviewClient,
    ) -> None:
        self.settings = settings
        self.venues = venues
        self.client = client

    def fetch(self, cursor: Mapping[str, object]) -> SourceBatch:
        del cursor
        records: list[SourceRecord] = []
        for venue_id, accepted_decisions in self.venues.items():
            group = self.client.get_group(venue_id)
            submission_name = _value(group.content, "submission_name", "Submission")
            notes = self.client.get_all_notes(
                invitation=f"{venue_id}/-/{submission_name}",
                details="replies" if self.settings.include_replies else None,
            )
            for note in notes:
                payload = note.to_json() if hasattr(note, "to_json") else dict(note)
                content = payload.get("content", {})
                replies = payload.get("details", {}).get("replies", [])
                decision = _decision(replies)
                if accepted_decisions and decision and decision not in accepted_decisions:
                    continue
                modified_ms = payload.get("mdate") or payload.get("cdate") or 0
                external_id = payload.get("forum") or payload["id"]
                records.append(SourceRecord(
                    provider=self.name,
                    external_id=external_id,
                    version=str(modified_ms),
                    updated_at=datetime.fromtimestamp(modified_ms / 1000, timezone.utc),
                    payload={
                        "title": _value(content, "title", "Untitled submission"),
                        "abstract": _value(content, "abstract", ""),
                        "authors": _value(content, "authors", []),
                        "venue_id": venue_id,
                        "forum": payload.get("forum"),
                        "note_id": payload.get("id"),
                        "invitations": payload.get("invitations", []),
                        "decision": decision,
                        "replies": [_reply_summary(reply) for reply in replies],
                    },
                ))
        latest = max((record.updated_at for record in records), default=None)
        return SourceBatch(
            records=records,
            next_cursor={"latest_modified": latest.isoformat() if latest else None},
        )


def _value(content: Mapping[str, Any], key: str, default: Any) -> Any:
    value = content.get(key, default)
    return value.get("value", default) if isinstance(value, dict) else value


def _decision(replies: list[dict[str, Any]]) -> str | None:
    for reply in replies:
        if any(invitation.endswith("Decision") for invitation in reply.get("invitations", [])):
            return _value(reply.get("content", {}), "decision", None)
    return None


def _reply_summary(reply: Mapping[str, Any]) -> dict[str, Any]:
    content = reply.get("content", {})
    return {
        "id": reply.get("id"),
        "invitations": reply.get("invitations", []),
        "rating": _value(content, "rating", None),
        "decision": _value(content, "decision", None),
        "comment": _value(content, "comment", None),
    }
