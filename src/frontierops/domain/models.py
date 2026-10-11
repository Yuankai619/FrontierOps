"""Versioned configuration and artifact contracts."""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectConfig(StrictModel):
    id: str
    name: str
    timezone: str = "UTC"
    language: str = "en"
    workspace_dir: Path = Path(".frontier")


class SyncConfig(StrictModel):
    trigger_mode: Literal["manual"] = "manual"
    baseline: Literal["last_successful_sync"] = "last_successful_sync"
    default_lookback_days: int = Field(default=14, ge=0)


class BriefConfig(StrictModel):
    target_duration_seconds: int = Field(default=300, gt=0)
    maximum_developments: int = Field(default=5, gt=0)
    outputs: list[Literal["html", "slides", "video"]] = Field(
        default_factory=lambda: ["html", "slides", "video"]
    )


class ScholarTracker(StrictModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    identities: dict[str, str | None]
    providers: list[Literal["semantic_scholar", "arxiv", "google_scholar"]]
    backfill_days: int = Field(default=365, ge=0)
    always_include_new_publications: bool = True


class VenueTracker(StrictModel):
    provider: Literal["openreview"]
    venue_id: str
    decisions: list[str] = Field(default_factory=list)


class TrackingConfig(StrictModel):
    scholars: list[ScholarTracker] = Field(default_factory=list)
    venues: list[VenueTracker] = Field(default_factory=list)


class FrontierConfig(StrictModel):
    schema_version: Literal["0.1"] = "0.1"
    project: ProjectConfig
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    brief: BriefConfig = Field(default_factory=BriefConfig)


class ScholarIdentity(StrictModel):
    provider: str
    stable_id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    affiliation: str | None = None
    paper_count: int | None = Field(default=None, ge=0)
    profile_url: str | None = None


class VenueIdentity(StrictModel):
    provider: str
    stable_id: str
    name: str
    year: int | None = None
    profile_url: str | None = None


class Artifact(StrictModel):
    schema_version: Literal["0.1"] = "0.1"
    artifact_id: str
    run_id: str
    created_at: datetime
    producer: str
    input_refs: list[str] = Field(default_factory=list)


class ResearchSignal(Artifact):
    kind: str
    source_provider: str
    external_id: str
    observed_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class Evidence(Artifact):
    source_ref: str
    source_uri: str
    locator: dict[str, str]
    content: str
    evidence_tier: str


class GateDecision(StrictModel):
    gate: str
    result: Literal["pass", "exclude", "warn", "exempt"]
    reason: str | None = None


class BriefingCandidate(Artifact):
    subject_id: str
    title: str
    research_signal_ids: list[str]
    evidence_ids: list[str]
    features: dict[str, float]
    gate_trace: list[GateDecision]
    total_score: float


class ResearchDevelopment(Artifact):
    title: str
    member_candidate_ids: list[str]
    first_seen_run: str
    last_seen_run: str
    status: Literal["new", "updated", "unchanged", "resolved"]
    delta_summary: str | None = None


class EvidenceClaim(StrictModel):
    text: str
    evidence_ids: list[str]


class BriefingSection(StrictModel):
    id: str
    duration_seconds: int = Field(gt=0)
    headline: str
    claims: list[EvidenceClaim] = Field(default_factory=list)


class BriefingSpec(Artifact):
    title: str
    language: str
    target_duration_seconds: int = Field(gt=0)
    sections: list[BriefingSection]
    render_targets: list[Literal["html", "slides", "video"]]

    @model_validator(mode="after")
    def duration_fits_budget(self) -> "BriefingSpec":
        if sum(section.duration_seconds for section in self.sections) > self.target_duration_seconds:
            raise ValueError("section durations exceed target_duration_seconds")
        return self


class StageResult(StrictModel):
    schema_version: Literal["0.1"] = "0.1"
    run_id: str
    stage: str
    status: Literal["success", "partial", "failed"]
    started_at: datetime
    finished_at: datetime
    outputs: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_stage_allowed: bool


class RunManifest(StrictModel):
    schema_version: Literal["0.1"] = "0.1"
    run_id: str
    status: Literal["success", "partial_success", "failed"]
    config_sha256: str
    stages: dict[str, str]
    outputs: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
