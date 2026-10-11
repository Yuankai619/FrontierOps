"""User-triggered, idempotent delta synchronization."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from frontierops.application.ports import Clock, SyncProvider, SyncRepository
from frontierops.domain.models import FrontierConfig, ResearchSignal, StageResult


def _fingerprint(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class SyncUseCase:
    providers: Mapping[str, SyncProvider]
    repository: SyncRepository
    clock: Clock

    def execute(self, config: FrontierConfig, run_dir: Path) -> Path:
        started_at = self.clock.now()
        workspace = run_dir.parent.parent
        state = self.repository.load_state(workspace)
        provider_state = state.setdefault("providers", {})
        signals: list[dict[str, Any]] = []
        snapshots: list[dict[str, Any]] = []
        fetched = skipped = 0

        for name, provider in self.providers.items():
            previous = provider_state.get(name, {"cursor": {}, "records": {}})
            batch = provider.fetch(previous.get("cursor", {}))
            records = dict(previous.get("records", {}))
            for record in batch.records:
                fetched += 1
                raw = record.model_dump(mode="json")
                fingerprint = _fingerprint(raw)
                cache_ref = self.repository.cache_raw(workspace, name, raw)
                snapshots.append({
                    "provider": name,
                    "external_id": record.external_id,
                    "sha256": fingerprint,
                    "cache_ref": cache_ref,
                })
                prior = records.get(record.external_id)
                if prior and prior["sha256"] == fingerprint:
                    skipped += 1
                    continue
                kind = "paper.new" if prior is None else "paper.updated"
                artifact_id = "signal_" + _fingerprint({
                    "provider": name, "external_id": record.external_id, "sha256": fingerprint
                })[:24]
                signal = ResearchSignal(
                    artifact_id=artifact_id,
                    run_id=run_dir.name,
                    created_at=self.clock.now(),
                    producer=f"sync:{name}",
                    input_refs=[cache_ref],
                    kind=kind,
                    source_provider=name,
                    external_id=record.external_id,
                    observed_at=self.clock.now(),
                    payload=record.payload | {
                        "version": record.version,
                        "updated_at": record.updated_at.isoformat(),
                    },
                )
                signals.append(signal.model_dump(mode="json"))
                records[record.external_id] = {"sha256": fingerprint, "version": record.version}
            provider_state[name] = {"cursor": batch.next_cursor, "records": records}

        finished_at = self.clock.now()
        outputs = {
            "research_signals": "01-sync/research-signals.jsonl",
            "delta_summary": "01-sync/delta-summary.json",
            "source_cursors": "01-sync/source-cursors.after.json",
        }
        result = StageResult(
            run_id=run_dir.name,
            stage="sync",
            status="success",
            started_at=started_at,
            finished_at=finished_at,
            input_refs=["00-build/resolved-config.yaml"],
            outputs=outputs,
            counts={"fetched": fetched, "produced": len(signals), "skipped_duplicate": skipped},
            next_stage_allowed=True,
        )
        files = {
            "01-sync/raw-snapshot-index.jsonl": snapshots,
            "01-sync/research-signals.jsonl": signals,
            "01-sync/delta-summary.json": result.counts,
            "01-sync/source-cursors.after.json": state,
            "01-sync/stage-result.json": result.model_dump(mode="json"),
        }
        self.repository.save_stage(run_dir, files)
        self.repository.commit_state(workspace, state)
        return run_dir
