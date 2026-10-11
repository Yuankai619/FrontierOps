"""Create page-level primary Evidence from an external paper-reading tool."""

from datetime import datetime
from hashlib import sha256

from frontierops.domain.models import Evidence


def page_evidence(run_id: str, source_ref: str, source_uri: str,
                  pages: list[tuple[int, str]], now: datetime) -> list[Evidence]:
    return [Evidence(
        artifact_id="evidence_" + sha256(
            f"{run_id}:{source_ref}:{number}:{text}".encode()
        ).hexdigest()[:24],
        run_id=run_id, created_at=now, producer="alphaxiv:answer_pdf_queries",
        input_refs=[source_ref], source_ref=source_ref, source_uri=source_uri,
        locator={"type": "page", "page": number}, content=text,
        evidence_tier="primary_fulltext",
    ) for number, text in pages]
