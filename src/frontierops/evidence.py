"""Composition root for optional alphaXiv page evidence enrichment."""

import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path

from frontierops.adapters.alphaxiv import AlphaXivMcpClient, parse_page_xml
from frontierops.adapters.config import YamlConfigAdapter
from frontierops.adapters.storage import FileArtifactStore
from frontierops.application.evidence import page_evidence
from frontierops.domain.models import BriefingCandidate, FrontierConfig, ResearchSignal


def run_evidence(run_dir: Path, candidate_id: str, queries: list[str],
                 client: AlphaXivMcpClient | None = None) -> Path:
    if not queries or any(not query.strip() for query in queries):
        raise ValueError("at least one non-empty PDF query is required")
    store = FileArtifactStore(run_dir)
    config = FrontierConfig.model_validate(
        YamlConfigAdapter().read(run_dir / "00-build/resolved-config.yaml")
    )
    candidates = [BriefingCandidate.model_validate(item) for item in
                  store.read_jsonl(Path("02-rank/briefing-candidates.jsonl"))]
    candidate = next((item for item in candidates if item.artifact_id == candidate_id), None)
    if candidate is None:
        raise ValueError("candidate does not belong to this Discovery Run")
    signals = [ResearchSignal.model_validate(item) for item in
               store.read_jsonl(Path("01-sync/research-signals.jsonl")) +
               store.read_jsonl(Path("01-sync/topic-observations.jsonl"))]
    source = next((item for item in signals if item.artifact_id in candidate.research_signal_ids), None)
    if source is None:
        raise ValueError("candidate source signal is unavailable")
    arxiv_id = candidate.paper_metadata.arxiv_id
    source_uri = source.payload.get("pdf_url") or (
        f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None
    )
    if not source_uri:
        raise ValueError("selected paper needs a verified arXiv ID or PDF URL")
    if client is None:
        settings = config.sources.alphaxiv
        key_name = settings.api_key_env or "ALPHAXIV_API_KEY"
        key = os.getenv(key_name)
        if not key:
            raise ValueError(f"alphaXiv page evidence requires {key_name} in the environment")
        client = AlphaXivMcpClient(
            settings.base_url or "https://api.alphaxiv.org/mcp/v1", key,
            settings.request_timeout_seconds,
        )
    raw = asyncio.run(client.answer_pdf_queries(source_uri, queries))
    pages = page_evidence(run_dir.name, source.artifact_id, source_uri,
                          parse_page_xml(raw), datetime.now(timezone.utc))
    existing = store.read_jsonl(Path("02-rank/evidence.jsonl"))
    by_id = {item["artifact_id"]: item for item in existing}
    by_id.update({item.artifact_id: item.model_dump(mode="json") for item in pages})
    store.write_jsonl(Path("02-rank/evidence.jsonl"), by_id.values())
    updated = [item.model_copy(update={"evidence_ids": list(dict.fromkeys(
        item.evidence_ids + [page.artifact_id for page in pages]
    ))}) if item.artifact_id == candidate_id else item for item in candidates]
    store.write_jsonl(Path("02-rank/briefing-candidates.jsonl"),
                      [item.model_dump(mode="json") for item in updated])
    raw_name = sha256(raw.encode()).hexdigest()[:24] + ".xml"
    store.write_text(Path("02-rank/alphaxiv-pages") / raw_name, raw)
    enrichment = {
        "candidate_id": candidate_id, "queries": queries, "source_uri": source_uri,
        "raw_response": f"02-rank/alphaxiv-pages/{raw_name}",
        "evidence_ids": [item.artifact_id for item in pages],
    }
    history_path = Path("02-rank/alphaxiv-enrichment.jsonl")
    history = store.read_jsonl(history_path) if (run_dir / history_path).exists() else []
    if enrichment not in history:
        store.write_jsonl(history_path, [*history, enrichment])
    store.write_json(Path("02-rank/alphaxiv-enrichment.json"), enrichment)
    manifest = store.read_json(Path("run-manifest.json"))
    manifest["outputs"]["alphaxiv_enrichment"] = "02-rank/alphaxiv-enrichment.json"
    manifest["outputs"]["alphaxiv_enrichment_history"] = str(history_path)
    store.write_json(Path("run-manifest.json"), manifest)
    return run_dir
