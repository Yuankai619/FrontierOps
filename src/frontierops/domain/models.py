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
    output_dir: Path = Path("frontier_output")


class SyncConfig(StrictModel):
    trigger_mode: Literal["manual"] = "manual"
    baseline: Literal["last_successful_sync"] = "last_successful_sync"
    default_lookback_days: int = Field(default=14, ge=0)
    on_provider_error: Literal["fail", "partial"] = "fail"
    preserve_raw_responses: bool = True


class ProviderSourceConfig(StrictModel):
    enabled: bool = False
    mode: Literal["fixture", "live"] = "fixture"
    fixture_path: Path | None = None
    overlap_days: int = Field(default=3, ge=0)
    api_key_env: str | None = None
    base_url: str | None = None
    user_agent: str = "FrontierOps/0.1"
    request_timeout_seconds: int = Field(default=30, gt=0)
    request_delay_seconds: float = Field(default=3.0, ge=0)
    page_size: int = Field(default=100, gt=0, le=1000)
    max_results: int = Field(default=100, gt=0)
    paper_ids: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class LocalLibraryConfig(StrictModel):
    enabled: bool = False
    roots: list[Path] = Field(default_factory=list)
    recursive: bool = True
    allowed_extensions: list[Literal[".pdf", ".md", ".txt"]] = Field(
        default_factory=lambda: [".pdf", ".md", ".txt"]
    )
    allow_outside_project_root: bool = False


class OpenReviewSourceConfig(StrictModel):
    enabled: bool = False
    mode: Literal["fixture", "live"] = "fixture"
    fixture_path: Path | None = None
    base_url: str = "https://api2.openreview.net"
    username_env: str = "OPENREVIEW_USERNAME"
    password_env: str = "OPENREVIEW_PASSWORD"
    token_env: str = "OPENREVIEW_TOKEN"
    include_replies: bool = True


class SourcesConfig(StrictModel):
    semantic_scholar: ProviderSourceConfig = Field(default_factory=ProviderSourceConfig)
    arxiv: ProviderSourceConfig = Field(default_factory=ProviderSourceConfig)
    local_library: LocalLibraryConfig = Field(default_factory=LocalLibraryConfig)
    openreview: OpenReviewSourceConfig = Field(default_factory=OpenReviewSourceConfig)


class TopicConfig(StrictModel):
    id: str
    description: str
    weight: float = Field(default=1.0, ge=0)


class KeywordsConfig(StrictModel):
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class ProfileConfig(StrictModel):
    topics: list[TopicConfig] = Field(default_factory=list)
    keywords: KeywordsConfig = Field(default_factory=KeywordsConfig)


class GateConfig(StrictModel):
    id: str
    type: Literal["publication_year", "citation", "relevance"]
    enabled: bool = True
    on_fail: Literal["exclude", "warn"] = "exclude"
    min_year: int | None = None
    minimum_count: int | None = Field(default=None, ge=0)
    exempt_if_age_days_lte: int = Field(default=0, ge=0)
    minimum: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def required_threshold_is_present(self) -> "GateConfig":
        required = {
            "publication_year": self.min_year,
            "citation": self.minimum_count,
            "relevance": self.minimum,
        }
        if required[self.type] is None:
            raise ValueError(f"{self.type} gate requires its threshold")
        return self


class FeatureConfig(StrictModel):
    enabled: bool = True
    weight: float = Field(default=0.0, ge=0)


class RankingFeatures(StrictModel):
    lexical_relevance: FeatureConfig = Field(
        default_factory=lambda: FeatureConfig(weight=0.55)
    )
    citation: FeatureConfig = Field(default_factory=lambda: FeatureConfig(weight=0.15))
    freshness: FeatureConfig = Field(default_factory=lambda: FeatureConfig(weight=0.15))
    reliability: FeatureConfig = Field(default_factory=lambda: FeatureConfig(weight=0.15))


class RankingConfig(StrictModel):
    gates: list[GateConfig] = Field(default_factory=list)
    features: RankingFeatures = Field(default_factory=RankingFeatures)
    citation_scale: int = Field(default=100, gt=0)
    freshness_half_life_days: int = Field(default=180, gt=0)
    source_reliability: dict[str, float] = Field(default_factory=dict)
    deep_enrich_top_k: int = Field(default=5, gt=0)
    max_fulltext_pages: int = Field(default=20, gt=0)


class BriefConfig(StrictModel):
    target_duration_seconds: int = Field(default=300, gt=0)
    maximum_developments: int = Field(default=5, gt=0)
    maximum_seconds_per_development: int = Field(default=75, gt=0)
    narration_words_per_minute: int = Field(default=140, gt=0)
    outputs: list[Literal["html", "slides", "video"]] = Field(
        default_factory=lambda: ["html", "slides", "video"]
    )


class ReviewConfig(StrictModel):
    required: bool = True
    fail_on_missing_evidence: bool = True
    fail_on_broken_source: bool = True
    fail_on_unsupported_number: bool = True
    fail_on_duration_over_budget: bool = True
    fail_on_duplicate_development: bool = True
    auto_fix: Literal["none", "safe_only"] = "safe_only"


class VideoPreviewConfig(StrictModel):
    enabled: bool = False
    provider: Literal["hyperframes"] = "hyperframes"
    tts_provider: Literal["heygen"] = "heygen"
    heygen_tts_script: Path | None = None
    voice_id: str | None = None
    language: str | None = None
    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    fps: Literal[24, 30, 60] = 30
    quality: Literal["draft", "looks", "delivery"] = "looks"

    @model_validator(mode="after")
    def enabled_preview_has_tts_adapter(self) -> "VideoPreviewConfig":
        if self.enabled and self.heygen_tts_script is None:
            raise ValueError("enabled video preview requires heygen_tts_script")
        return self


class RenderingConfig(StrictModel):
    video: VideoPreviewConfig = Field(default_factory=VideoPreviewConfig)


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
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    ranking: RankingConfig = Field(default_factory=RankingConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    brief: BriefConfig = Field(default_factory=BriefConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    rendering: RenderingConfig = Field(default_factory=RenderingConfig)

    @model_validator(mode="after")
    def live_sources_have_targets(self) -> "FrontierConfig":
        arxiv = self.sources.arxiv
        if (
            arxiv.enabled
            and arxiv.mode == "live"
            and not (arxiv.paper_ids or arxiv.queries or arxiv.categories)
        ):
            raise ValueError("live arxiv requires paper_ids, queries, or categories")
        semantic = self.sources.semantic_scholar
        semantic_ids = [
            scholar.identities.get("semantic_scholar")
            for scholar in self.tracking.scholars
            if "semantic_scholar" in scholar.providers
        ]
        if semantic.enabled and semantic.mode == "live" and not any(semantic_ids):
            raise ValueError("live semantic_scholar requires a tracked stable author ID")
        return self


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


class SourceRecord(StrictModel):
    provider: str
    external_id: str
    version: str | None = None
    updated_at: datetime
    payload: dict[str, Any]


class SourceBatch(StrictModel):
    records: list[SourceRecord]
    next_cursor: dict[str, Any] = Field(default_factory=dict)


class Evidence(Artifact):
    source_ref: str
    source_uri: str
    locator: dict[str, Any]
    content: str
    evidence_tier: str


class GroundedStatement(StrictModel):
    text: str
    kind: Literal["factual", "interpretation"] = "factual"
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def factual_statement_has_evidence(self) -> "GroundedStatement":
        if self.kind == "factual" and not self.evidence_ids:
            raise ValueError("factual statement requires evidence_ids")
        return self


class PaperExplanation(StrictModel):
    problem: GroundedStatement
    core_idea: GroundedStatement
    method: GroundedStatement
    novelty: GroundedStatement
    experiments: GroundedStatement
    limitations: GroundedStatement
    why_it_matters: GroundedStatement
    resources: list[str] = Field(default_factory=list)


class PaperMetadata(StrictModel):
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    published_at: str | None = None
    publication_venue: str | None = None
    publication_status: Literal["preprint", "conference", "journal", "unknown"] = "unknown"
    source_url: str | None = None
    arxiv_id: str | None = None


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
    paper_explanation: PaperExplanation | None = None
    paper_metadata: PaperMetadata = Field(default_factory=PaperMetadata)


class BriefingSelection(StrictModel):
    schema_version: Literal["0.1"] = "0.1"
    run_id: str
    selected_candidate_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self) -> "BriefingSelection":
        if len(set(self.selected_candidate_ids)) != len(self.selected_candidate_ids):
            raise ValueError("selected candidate IDs must be unique")
        return self


class ResearchDevelopment(Artifact):
    title: str
    member_candidate_ids: list[str]
    first_seen_run: str
    last_seen_run: str
    status: Literal["new", "updated", "unchanged", "resolved"]
    delta_summary: str | None = None


class EvidenceClaim(StrictModel):
    text: str
    kind: Literal["factual", "interpretation"] = "factual"
    evidence_ids: list[str]

    @model_validator(mode="after")
    def factual_claim_has_evidence(self) -> "EvidenceClaim":
        if self.kind == "factual" and not self.evidence_ids:
            raise ValueError("factual claim requires evidence_ids")
        return self


class SourceExcerpt(StrictModel):
    evidence_id: str
    quote: str = Field(min_length=12)
    caption: str | None = None


class BriefingSection(StrictModel):
    id: str
    duration_seconds: int = Field(gt=0)
    headline: str
    claims: list[EvidenceClaim] = Field(default_factory=list)
    development_id: str | None = None
    paper_explanation: PaperExplanation | None = None
    paper_metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    source_excerpts: list[SourceExcerpt] = Field(default_factory=list)
    narration_script: str = ""
    caption_text: str = ""
    visual_hint: str = ""


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
    input_refs: list[str] = Field(default_factory=list)
    outputs: dict[str, str] = Field(default_factory=dict)
    counts: dict[str, int] = Field(default_factory=dict)
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


class ReviewIssue(StrictModel):
    code: str
    severity: Literal["error", "warning", "info"]
    message: str
    section_id: str | None = None
    claim_index: int | None = None


class ClaimCheck(StrictModel):
    section_id: str
    claim_index: int
    status: Literal["supported", "missing_evidence", "broken_evidence", "unsupported_number"]
    evidence_ids: list[str] = Field(default_factory=list)
    details: str = ""


class ReviewReport(Artifact):
    decision: Literal["approved", "blocked"]
    issues: list[ReviewIssue] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
