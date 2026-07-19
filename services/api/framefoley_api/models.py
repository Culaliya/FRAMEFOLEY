"""Pydantic models mirroring the versioned JSON contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

QcVerdictValue = Literal["pass", "repairable", "regenerate", "failed"]
SseEventType = Literal[
    "project.state",
    "candidate.status",
    "candidate.qc",
    "render.status",
    "export.status",
    "heartbeat",
]


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ContractModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="forbid",
        use_enum_values=True,
    )


class ProjectState(StrEnum):
    CREATED = "created"
    SOURCE_UPLOADING = "source_uploading"
    SOURCE_READY = "source_ready"
    CUEING = "cueing"
    GENERATION_QUEUED = "generation_queued"
    GENERATING = "generating"
    AUDITION_READY = "audition_ready"
    APPROVALS_COMPLETE = "approvals_complete"
    RENDERING = "rendering"
    RENDER_READY = "render_ready"
    EXPORTING = "exporting"
    COMPLETE = "complete"
    SOURCE_FAILED = "source_failed"
    GENERATION_PARTIAL = "generation_partial"
    GENERATION_FAILED = "generation_failed"
    RENDER_FAILED = "render_failed"
    EXPORT_FAILED = "export_failed"


class ProjectPhase(StrEnum):
    SOURCE = "source"
    CUE = "cue"
    GENERATE = "generate"
    AUDITION = "audition"
    RENDER = "render"
    EXPORT = "export"
    COMPLETE = "complete"


class ApiError(ContractModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    message: str = Field(min_length=1, max_length=240)
    retryable: bool
    request_id: str = Field(pattern=r"^req_[a-z0-9]{10,32}$")


class QcReport(ContractModel):
    schema_version: Literal[1] = 1
    verdict: QcVerdictValue
    duration_seconds: float = Field(ge=0)
    sample_rate_hz: int = Field(ge=1)
    channels: int = Field(ge=1, le=8)
    peak_dbfs: float = Field(le=0)
    rms_dbfs: float = Field(le=0)
    leading_silence_ms: float = Field(ge=0)
    trailing_silence_ms: float = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)
    repairs: list[str] = Field(default_factory=list)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class GenerationCandidate(ContractModel):
    id: str = Field(pattern=r"^cand_[a-z0-9]{8,24}$")
    variant: Literal["clean", "character"]
    status: Literal[
        "queued", "generating", "stored", "checking", "repaired", "retrying", "ready", "failed"
    ] = "queued"
    prompt: str = Field(min_length=1, max_length=1200)
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    source_label: Literal["LIVE", "CACHED DEMO", "MOCKED"]
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    latency_seconds: float | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    genblaze_run_id: str | None = None
    parent_run_id: str | None = None
    manifest_uri: str | None = Field(default=None, max_length=1024)
    manifest_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    manifest_verified: bool = False
    raw_asset_key: str | None = None
    approved_wav_key: str | None = None
    approved_ogg_key: str | None = None
    waveform_key: str | None = None
    asset_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    qc_before: QcReport | None = None
    qc_after: QcReport | None = None
    repairs: list[str] = Field(default_factory=list)
    retry_count: int = Field(default=0, ge=0, le=1)
    retry_of_candidate_id: str | None = None
    error: ApiError | None = None


class SoundEvent(ContractModel):
    id: str = Field(pattern=r"^evt_[a-z0-9]{8,24}$")
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=80)
    type: Literal["impact", "creature", "ui", "ambience"]
    timestamp_seconds: float = Field(ge=0, le=15)
    target_duration_seconds: float = Field(ge=0.08, le=8)
    intensity: Literal["soft", "medium", "hard"]
    material_note: str | None = Field(default=None, max_length=180)
    candidates: list[GenerationCandidate] = Field(default_factory=list, max_length=2)
    approved_candidate_id: str | None = None


class StyleProfile(ContractModel):
    id: Literal["lunar_arcade", "rubber_dungeon", "rust_bloom", "paper_signal", "custom"]
    title: str = Field(min_length=1, max_length=48)
    prompt_prefix: str = Field(min_length=1, max_length=360)
    custom_text: str | None = Field(default=None, max_length=180)


class SourceClip(ContractModel):
    b2_key: str
    preview_key: str
    mime_type: Literal["video/mp4", "video/webm"]
    duration_seconds: float = Field(ge=8, le=15)
    width: int = Field(ge=480, le=1920)
    height: int = Field(ge=270, le=1080)
    fps: float = Field(gt=0, le=120)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    thumbnail_key: str
    source_audio_stripped: Literal[True] = True
    origin: Literal["demo", "upload"]


class MixRender(ContractModel):
    status: Literal["queued", "rendering", "ready", "failed"]
    preview_key: str | None = None
    mix_map_key: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    gains_db: dict[str, float] = Field(default_factory=dict)
    error: ApiError | None = None

    @field_validator("gains_db")
    @classmethod
    def validate_gains(cls, value: dict[str, float]) -> dict[str, float]:
        if len(value) > 3 or any(not -12 <= gain <= 6 for gain in value.values()):
            raise ValueError("event gains must contain at most three values from -12 to +6 dB")
        return value


class ExportBundle(ContractModel):
    status: Literal["queued", "packing", "ready", "failed"]
    zip_key: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    size_bytes: int | None = Field(default=None, ge=0)
    created_at: datetime | None = None
    provenance_index_key: str | None = None
    inventory: list[str] = Field(default_factory=list)
    error: ApiError | None = None


class FrameFoleyProject(ContractModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^prj_[a-z0-9]{12,32}$")
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=80)
    state: ProjectState
    phase: ProjectPhase
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    source: SourceClip | None = None
    style: StyleProfile
    events: list[SoundEvent] = Field(default_factory=list, max_length=3)
    render: MixRender | None = None
    export: ExportBundle | None = None
    generation_mode: Literal["live", "demo", "disabled"]
    live_call_count: int = Field(default=0, ge=0, le=12)
    retry_budget_remaining: int = Field(ge=0, le=6)
    generation_request_keys: list[str] = Field(default_factory=list, max_length=16)
    error: ApiError | None = None


class SseEvent(ContractModel):
    type: SseEventType
    project_id: str
    event_id: str | None = None
    candidate_id: str | None = None
    at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class CreateProjectRequest(ContractModel):
    title: str = Field(default="Untitled sound kit", min_length=1, max_length=80)


class ProjectCreationResponse(ContractModel):
    project_id: str
    project_token: str
    phase: Literal["source"]
    expires_at: datetime


class UploadUrlRequest(ContractModel):
    filename: str = Field(min_length=1, max_length=160)
    mime_type: Literal["video/mp4", "video/webm"]
    size_bytes: int = Field(gt=0, le=30 * 1024 * 1024)


class UploadUrlResponse(ContractModel):
    upload_url: str
    method: Literal["PUT"] = "PUT"
    object_key: str
    expires_at: datetime


class SourceCompleteRequest(ContractModel):
    object_key: str


class EventsUpdateRequest(ContractModel):
    style: StyleProfile
    events: list[SoundEvent] = Field(min_length=1, max_length=3)


class ApprovalRequest(ContractModel):
    candidate_id: str


class RenderRequest(ContractModel):
    gains_db: dict[str, float] = Field(default_factory=dict)


class ProjectResponse(ContractModel):
    project: FrameFoleyProject
    asset_urls: dict[str, str] = Field(default_factory=dict)
    storage_label: Literal["BACKBLAZE B2", "MOCKED LOCAL STORAGE"]


class ProvenanceResponse(ContractModel):
    schema_version: Literal[1] = 1
    project_id: str
    generated_at: datetime
    project: FrameFoleyProject
    candidates: list[dict[str, Any]]
