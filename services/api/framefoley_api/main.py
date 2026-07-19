"""FRAMEFOLEY Phase 1 FastAPI application."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import secrets
import shutil
import threading
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import uvicorn
from fastapi import FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import RequestResponseEndpoint

from framefoley_api.errors import PublicError
from framefoley_api.events import EventLog
from framefoley_api.exporting import build_provenance, export_project
from framefoley_api.generation import GenerationService
from framefoley_api.live_proof import LiveProofService
from framefoley_api.media import MAX_SOURCE_BYTES, prepare_source
from framefoley_api.models import (
    ApprovalRequest,
    CapabilityResponse,
    CreateProjectRequest,
    EventsUpdateRequest,
    FrameFoleyProject,
    ProjectCreationResponse,
    ProjectPhase,
    ProjectResponse,
    ProjectState,
    RenderRequest,
    SoundEvent,
    SourceClip,
    SourceCompleteRequest,
    StyleProfile,
    UploadUrlRequest,
    UploadUrlResponse,
)
from framefoley_api.prompting import normalize_style, validate_event_target
from framefoley_api.rendering import render_mix
from framefoley_api.repository import ProjectRepository, project_prefix
from framefoley_api.security import TokenSigner
from framefoley_api.settings import Settings
from framefoley_api.state import transition
from framefoley_api.storage import ObjectStore, content_type_for_key, create_object_store


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "req_unknown0000"))


def _error_payload(error: PublicError, request: Request) -> dict[str, Any]:
    return {
        "code": error.code,
        "message": error.message,
        "retryable": error.retryable,
        "requestId": _request_id(request),
    }


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:56].strip("-") or "sound-kit"


def _default_style() -> StyleProfile:
    return normalize_style(
        StyleProfile(
            id="lunar_arcade",
            title="LUNAR ARCADE",
            prompt_prefix="Luminous, tactile, playful, slightly glassy.",
        )
    )


def _new_project(settings: Settings, title: str) -> FrameFoleyProject:
    now = datetime.now(UTC)
    return FrameFoleyProject(
        id="prj_" + secrets.token_hex(8),
        slug=_slugify(title),
        title=title,
        state=ProjectState.CREATED,
        phase=ProjectPhase.SOURCE,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=settings.project_ttl_hours),
        style=_default_style(),
        generation_mode=settings.generation_mode,
        retry_budget_remaining=settings.project_retry_budget,
    )


def _bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not authorization.startswith(prefix) or not authorization[len(prefix) :].strip():
        raise PublicError(
            "PROJECT_TOKEN_REQUIRED",
            "A project access token is required.",
            status_code=401,
        )
    return authorization[len(prefix) :].strip()


def _read_demo_events(path: Path) -> list[SoundEvent]:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise PublicError(
            "DEMO_ASSET_INVALID", "The built-in demo event file is invalid.", status_code=500
        )
    return [SoundEvent.model_validate(item) for item in payload]


def _model_json_bytes(model: Any) -> bytes:
    payload = model.model_dump(mode="json", by_alias=True, exclude_none=True)
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _store_source_metadata(repository: ProjectRepository, project: FrameFoleyProject) -> None:
    if project.source is None:
        return
    repository.put_object(
        project.id,
        "source/source-metadata.json",
        _model_json_bytes(project.source),
        content_type="application/json",
    )


def _store_event_documents(repository: ProjectRepository, project: FrameFoleyProject) -> None:
    for event in project.events:
        repository.put_object(
            project.id,
            f"events/{event.id}/event.json",
            _model_json_bytes(event),
            content_type="application/json",
        )


def _asset_keys(project: FrameFoleyProject) -> set[str]:
    keys: set[str] = set()
    if project.source:
        keys.update(
            {
                project.source.b2_key,
                project.source.preview_key,
                project.source.thumbnail_key,
            }
        )
    for event in project.events:
        for candidate in event.candidates:
            keys.update(
                key
                for key in (
                    candidate.raw_asset_key,
                    candidate.approved_wav_key,
                    candidate.approved_ogg_key,
                    candidate.waveform_key,
                    candidate.manifest_uri,
                )
                if key
            )
    if project.render:
        keys.update(key for key in (project.render.preview_key, project.render.mix_map_key) if key)
    if project.export:
        keys.update(
            key for key in (project.export.zip_key, project.export.provenance_index_key) if key
        )
    return keys


def _range_response(request: Request, data: bytes, key: str) -> Response:
    content_type = content_type_for_key(key)
    headers = {"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=300"}
    if key.endswith(".zip"):
        headers["Content-Disposition"] = f'attachment; filename="{Path(key).name}"'
    range_header = request.headers.get("range")
    if not range_header:
        return Response(data, media_type=content_type, headers=headers)
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
    if not match:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{len(data)}"})
    start_text, end_text = match.groups()
    if not start_text and not end_text:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{len(data)}"})
    if start_text:
        start = int(start_text)
        end = int(end_text) if end_text else len(data) - 1
    else:
        suffix_length = int(end_text)
        start = max(0, len(data) - suffix_length)
        end = len(data) - 1
    if start >= len(data) or start > end:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{len(data)}"})
    end = min(end, len(data) - 1)
    headers.update(
        {
            "Content-Range": f"bytes {start}-{end}/{len(data)}",
            "Content-Length": str(end - start + 1),
        }
    )
    return Response(
        data[start : end + 1], status_code=206, media_type=content_type, headers=headers
    )


def create_app(
    settings: Settings | None = None,
    *,
    store: ObjectStore | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_env()
    object_store = store or create_object_store(active_settings)
    repository = ProjectRepository(object_store)
    live_proof = LiveProofService(object_store, repository)
    signer = TokenSigner.from_secret(active_settings.hmac_secret)
    events = EventLog()
    generator = GenerationService(active_settings, repository, events)
    generation_slots = threading.BoundedSemaphore(active_settings.max_concurrent_generation)
    capability_lock = threading.Lock()
    capability_proof_checked_at = 0.0
    capability_proof_ready = False

    app = FastAPI(
        title="FRAMEFOLEY API",
        version="1.0.0",
        docs_url="/docs" if os.getenv("FRAMEFOLEY_ENV", "development") != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[active_settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "Last-Event-ID"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = "req_" + secrets.token_hex(8)
        response = await call_next(request)
        response.headers["X-Request-ID"] = _request_id(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(PublicError)
    async def public_error_handler(request: Request, error: PublicError) -> JSONResponse:
        return JSONResponse(_error_payload(error, request), status_code=error.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, _error: RequestValidationError
    ) -> JSONResponse:
        error = PublicError(
            "REQUEST_INVALID",
            "The request did not match the FRAMEFOLEY v1 contract.",
            status_code=422,
        )
        return JSONResponse(_error_payload(error, request), status_code=422)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, _error: Exception) -> JSONResponse:
        error = PublicError(
            "INTERNAL_ERROR",
            "FRAMEFOLEY could not complete the request. No credentials were exposed.",
            retryable=True,
            status_code=500,
        )
        return JSONResponse(_error_payload(error, request), status_code=500)

    def authorized_project(project_id: str, request: Request) -> FrameFoleyProject:
        signer.verify_project_token(_bearer_token(request), project_id)
        project = repository.load(project_id)
        if project.expires_at <= datetime.now(UTC):
            raise PublicError(
                "PROJECT_EXPIRED",
                "This private project has expired.",
                status_code=410,
            )
        return project

    def creation_response(
        project: FrameFoleyProject, *, phase: Literal["source", "generate"] = "source"
    ) -> ProjectCreationResponse:
        token = signer.project_token(project.id, int(project.expires_at.timestamp()))
        return ProjectCreationResponse(
            project_id=project.id,
            project_token=token,
            phase=phase,
            expires_at=project.expires_at,
        )

    def custom_upload_can_complete() -> bool:
        try:
            active_settings.require_live()
        except ValueError:
            return False
        return True

    def live_proof_replay_available() -> bool:
        nonlocal capability_proof_checked_at, capability_proof_ready
        now = time.monotonic()
        with capability_lock:
            if now - capability_proof_checked_at < 15:
                return capability_proof_ready
            try:
                live_proof.verify()
            except PublicError:
                capability_proof_ready = False
            else:
                capability_proof_ready = True
            capability_proof_checked_at = now
            return capability_proof_ready

    def project_response(project: FrameFoleyProject, request: Request) -> ProjectResponse:
        expires_at = min(int(project.expires_at.timestamp()), int(time.time()) + 3600)
        base_url = str(request.base_url).rstrip("/")
        urls = {
            key: f"{base_url}/v1/assets/{signer.object_token(project.id, key, expires_at)}"
            for key in sorted(_asset_keys(project))
        }
        return ProjectResponse(
            project=project,
            asset_urls=urls,
            storage_label=(
                "BACKBLAZE B2" if object_store.label == "BACKBLAZE B2" else "MOCKED LOCAL STORAGE"
            ),
        )

    @app.get("/healthz")
    def health() -> dict[str, str]:
        payload = {"status": "ok", "service": "framefoley-api", "version": "1.0.0"}
        source_commit = os.getenv("RENDER_GIT_COMMIT") or os.getenv("FRAMEFOLEY_SOURCE_COMMIT")
        if source_commit and re.fullmatch(r"[a-f0-9]{40}", source_commit):
            payload["sourceCommit"] = source_commit
        return payload

    @app.get("/readyz")
    def readiness() -> JSONResponse:
        missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
        if missing:
            return JSONResponse(
                {"status": "not_ready", "missing": missing, "storage": object_store.label},
                status_code=503,
            )
        return JSONResponse(
            {
                "status": "ready",
                "generationMode": active_settings.generation_mode,
                "storage": object_store.label,
                "mediaTools": {"ffmpeg": True, "ffprobe": True},
                "storageReady": True,
            }
        )

    @app.get("/v1/capabilities", response_model=CapabilityResponse)
    def capabilities() -> Response:
        storage_label: Literal["BACKBLAZE B2", "MOCKED LOCAL STORAGE"] = (
            "BACKBLAZE B2" if object_store.label == "BACKBLAZE B2" else "MOCKED LOCAL STORAGE"
        )
        payload = CapabilityResponse(
            generation_mode=active_settings.generation_mode,
            storage=storage_label,
            custom_upload_can_complete=custom_upload_can_complete(),
            live_proof_replay_available=live_proof_replay_available(),
            anonymous_provider_spend_enabled=custom_upload_can_complete(),
            project_ttl_hours=active_settings.project_ttl_hours,
        )
        return JSONResponse(
            payload.model_dump(mode="json", by_alias=True),
            headers={"Cache-Control": "public, max-age=15, stale-while-revalidate=15"},
        )

    @app.post("/v1/projects", response_model=ProjectCreationResponse, status_code=201)
    def create_project(body: CreateProjectRequest) -> ProjectCreationResponse:
        project = _new_project(active_settings, body.title)
        repository.save(project)
        return creation_response(project)

    @app.post("/v1/projects/demo", response_model=ProjectCreationResponse, status_code=201)
    def create_demo_project() -> ProjectCreationResponse:
        project = _new_project(active_settings, "JELLY RELAY")
        project.evidence_label = "CACHED DEMO"
        video_path = active_settings.repo_root / "demo" / "jelly-relay.mp4"
        thumbnail_path = active_settings.repo_root / "demo" / "jelly-relay-thumbnail.webp"
        if not video_path.is_file() or not thumbnail_path.is_file():
            raise PublicError(
                "DEMO_ASSET_MISSING",
                "The built-in JELLY RELAY demo is unavailable.",
                status_code=503,
            )
        video = video_path.read_bytes()
        video_key = repository.put_object(
            project.id, "source/original.mp4", video, content_type="video/mp4"
        )
        preview_key = repository.put_object(
            project.id, "source/preview.mp4", video, content_type="video/mp4"
        )
        thumbnail_key = repository.put_object(
            project.id,
            "source/thumbnail.webp",
            thumbnail_path.read_bytes(),
            content_type="image/webp",
        )
        project.source = SourceClip(
            b2_key=video_key,
            preview_key=preview_key,
            mime_type="video/mp4",
            duration_seconds=12,
            width=1280,
            height=720,
            fps=30,
            sha256=hashlib.sha256(video).hexdigest(),
            thumbnail_key=thumbnail_key,
            source_audio_stripped=True,
            origin="demo",
        )
        project.events = _read_demo_events(
            active_settings.repo_root / "demo" / "jelly-relay-events.json"
        )
        transition(project, ProjectState.SOURCE_READY)
        _store_source_metadata(repository, project)
        _store_event_documents(repository, project)
        repository.save(project)
        return creation_response(project)

    @app.post("/v1/projects/live-proof", response_model=ProjectCreationResponse, status_code=201)
    def create_live_proof_project() -> ProjectCreationResponse:
        proof = live_proof.verify()
        project = _new_project(active_settings, "LIVE EVIDENCE REPLAY")
        live_proof.hydrate_project(project, proof)
        return creation_response(project, phase="generate")

    @app.post(
        "/v1/projects/{project_id}/upload-url",
        response_model=UploadUrlResponse,
    )
    def create_upload_url(
        project_id: str, body: UploadUrlRequest, request: Request
    ) -> UploadUrlResponse:
        if not custom_upload_can_complete():
            raise PublicError(
                "CUSTOM_UPLOAD_UNAVAILABLE",
                "Custom clip mode is available in a self-hosted LIVE build.",
                status_code=409,
            )
        project = authorized_project(project_id, request)
        if ProjectState(project.state) not in {ProjectState.CREATED, ProjectState.SOURCE_FAILED}:
            raise PublicError(
                "PROJECT_STATE_INVALID",
                "A source upload cannot start from the current project state.",
                status_code=409,
            )
        if ProjectState(project.state) is ProjectState.SOURCE_FAILED:
            transition(project, ProjectState.SOURCE_UPLOADING)
        else:
            transition(project, ProjectState.SOURCE_UPLOADING)
        suffix = ".mp4" if body.mime_type == "video/mp4" else ".webm"
        key = repository.put_object(
            project.id,
            f"incoming/source-{secrets.token_hex(4)}{suffix}",
            b"",
            content_type=body.mime_type,
        )
        repository.save(project)
        expires_at = min(project.expires_at, datetime.now(UTC) + timedelta(minutes=20))
        upload_token = signer.object_token(project.id, key, int(expires_at.timestamp()))
        return UploadUrlResponse(
            upload_url=f"{str(request.base_url).rstrip('/')}/v1/uploads/{upload_token}",
            object_key=key,
            expires_at=expires_at,
        )

    @app.put("/v1/uploads/{upload_token}", status_code=204)
    async def upload_source(upload_token: str, request: Request) -> Response:
        project_id, key = signer.verify_object_token(upload_token)
        if not key.startswith(project_prefix(project_id) + "incoming/source-"):
            raise PublicError(
                "UPLOAD_TOKEN_SCOPE", "This upload token cannot write that object.", status_code=403
            )
        declared_length = request.headers.get("content-length")
        if declared_length and int(declared_length) > MAX_SOURCE_BYTES:
            raise PublicError(
                "SOURCE_TOO_LARGE", "Video must be no larger than 30 MB.", status_code=413
            )
        payload = bytearray()
        async for chunk in request.stream():
            payload.extend(chunk)
            if len(payload) > MAX_SOURCE_BYTES:
                raise PublicError(
                    "SOURCE_TOO_LARGE", "Video must be no larger than 30 MB.", status_code=413
                )
        object_store.put(key, bytes(payload), content_type=content_type_for_key(key))
        return Response(status_code=204)

    @app.post("/v1/projects/{project_id}/source/complete", response_model=ProjectResponse)
    def complete_source(
        project_id: str, body: SourceCompleteRequest, request: Request
    ) -> ProjectResponse:
        project = authorized_project(project_id, request)
        if ProjectState(project.state) is not ProjectState.SOURCE_UPLOADING:
            raise PublicError(
                "PROJECT_STATE_INVALID",
                "The project is not waiting for a source upload.",
                status_code=409,
            )
        expected_prefix = project_prefix(project.id) + "incoming/source-"
        if not body.object_key.startswith(expected_prefix) or not object_store.exists(
            body.object_key
        ):
            raise PublicError(
                "SOURCE_OBJECT_INVALID",
                "The uploaded source object is missing or outside this project.",
                status_code=422,
            )
        mime_type: Literal["video/mp4", "video/webm"] = (
            "video/mp4" if body.object_key.endswith(".mp4") else "video/webm"
        )
        try:
            prepared = prepare_source(object_store.get(body.object_key), mime_type)
            preview_key = repository.put_object(
                project.id, "source/preview.mp4", prepared.preview, content_type="video/mp4"
            )
            thumbnail_key = repository.put_object(
                project.id,
                "source/thumbnail.webp",
                prepared.thumbnail,
                content_type="image/webp",
            )
            project.source = SourceClip(
                b2_key=body.object_key,
                preview_key=preview_key,
                mime_type=mime_type,
                duration_seconds=prepared.inspection.duration_seconds,
                width=prepared.inspection.width,
                height=prepared.inspection.height,
                fps=prepared.inspection.fps,
                sha256=prepared.sha256,
                thumbnail_key=thumbnail_key,
                source_audio_stripped=True,
                origin="upload",
            )
            transition(project, ProjectState.SOURCE_READY)
            _store_source_metadata(repository, project)
        except PublicError:
            transition(project, ProjectState.SOURCE_FAILED)
            repository.save(project)
            raise
        repository.save(project)
        return project_response(project, request)

    @app.get("/v1/projects/{project_id}", response_model=ProjectResponse)
    def get_project(project_id: str, request: Request) -> ProjectResponse:
        return project_response(authorized_project(project_id, request), request)

    @app.put("/v1/projects/{project_id}/events", response_model=ProjectResponse)
    def update_events(
        project_id: str, body: EventsUpdateRequest, request: Request
    ) -> ProjectResponse:
        project = authorized_project(project_id, request)
        state = ProjectState(project.state)
        if state not in {
            ProjectState.SOURCE_READY,
            ProjectState.GENERATION_QUEUED,
            ProjectState.GENERATION_FAILED,
        }:
            raise PublicError(
                "PROJECT_STATE_INVALID",
                "Cues cannot be edited from the current project state.",
                status_code=409,
            )
        if project.source is None:
            raise PublicError(
                "SOURCE_REQUIRED", "Project source video is missing.", status_code=409
            )
        if len({event.id for event in body.events}) != len(body.events) or len(
            {event.slug for event in body.events}
        ) != len(body.events):
            raise PublicError(
                "EVENT_ID_DUPLICATE", "Event IDs and slugs must be unique.", status_code=422
            )
        clean_events: list[SoundEvent] = []
        for event in body.events:
            validate_event_target(event)
            if event.timestamp_seconds >= project.source.duration_seconds:
                raise PublicError(
                    "EVENT_TIMESTAMP_INVALID",
                    "Every event must occur before the source clip ends.",
                    status_code=422,
                )
            clean_events.append(
                event.model_copy(update={"candidates": [], "approved_candidate_id": None})
            )
        project.style = normalize_style(body.style)
        project.events = clean_events
        project.render = None
        project.export = None
        if state is ProjectState.SOURCE_READY:
            transition(project, ProjectState.CUEING)
            transition(project, ProjectState.GENERATION_QUEUED)
        elif state is ProjectState.GENERATION_FAILED:
            transition(project, ProjectState.GENERATION_QUEUED)
        _store_event_documents(repository, project)
        repository.save(project)
        events.publish(project.id, "project.state", {"state": "generation_queued"})
        return project_response(project, request)

    @app.post("/v1/projects/{project_id}/generate", response_model=ProjectResponse)
    def generate_project(
        project_id: str,
        request: Request,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> ProjectResponse:
        project = authorized_project(project_id, request)
        if not idempotency_key or len(idempotency_key) > 128:
            raise PublicError(
                "IDEMPOTENCY_KEY_REQUIRED",
                "A bounded Idempotency-Key header is required.",
                status_code=400,
            )
        if not repository.claim_generation_request(project, idempotency_key):
            return project_response(repository.load(project.id), request)
        if not generation_slots.acquire(blocking=False):
            raise PublicError(
                "GENERATION_BUSY",
                "Generation capacity is busy. Try the demo again shortly.",
                retryable=True,
                status_code=429,
            )
        try:
            generated = generator.generate(project)
        finally:
            generation_slots.release()
        return project_response(generated, request)

    @app.get("/v1/projects/{project_id}/stream")
    async def stream_project(project_id: str, request: Request) -> StreamingResponse:
        authorized_project(project_id, request)
        last_event = request.headers.get("last-event-id", "0")
        cursor = int(last_event) if last_event.isdigit() else 0

        async def stream() -> AsyncIterator[bytes]:
            nonlocal cursor
            # A standards-compliant SSE comment flushes the connection without
            # inventing a pipeline event or changing authoritative project state.
            yield b": framefoley-stream-ready\n\n"
            idle_ticks = 0
            while True:
                if await request.is_disconnected():
                    return
                batch, new_cursor = events.since(project_id, cursor)
                for offset, event in enumerate(batch, start=cursor + 1):
                    payload = json.dumps(
                        event.model_dump(mode="json", by_alias=True),
                        separators=(",", ":"),
                    )
                    yield f"id: {offset}\nevent: {event.type}\ndata: {payload}\n\n".encode()
                if batch:
                    cursor = new_cursor
                    idle_ticks = 0
                else:
                    idle_ticks += 1
                    if idle_ticks >= 30:
                        yield b"event: heartbeat\ndata: {}\n\n"
                        idle_ticks = 0
                await asyncio.sleep(0.5)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                # Cloudflare intentionally removes X-Accel-Buffering from public
                # responses. Keep the standard origin directive and expose a
                # product-owned, non-secret companion so the public verifier can
                # distinguish documented edge stripping from an application bug.
                "X-FrameFoley-Buffering": "disabled",
            },
        )

    @app.post(
        "/v1/projects/{project_id}/events/{event_id}/approve",
        response_model=ProjectResponse,
    )
    def approve_candidate(
        project_id: str,
        event_id: str,
        body: ApprovalRequest,
        request: Request,
    ) -> ProjectResponse:
        project = authorized_project(project_id, request)
        state = ProjectState(project.state)
        if state not in {
            ProjectState.AUDITION_READY,
            ProjectState.GENERATION_PARTIAL,
            ProjectState.APPROVALS_COMPLETE,
        }:
            raise PublicError(
                "PROJECT_STATE_INVALID",
                "Candidates cannot be approved from the current project state.",
                status_code=409,
            )
        event = next((item for item in project.events if item.id == event_id), None)
        if event is None:
            raise PublicError("EVENT_NOT_FOUND", "The sound event was not found.", status_code=404)
        candidate = next((item for item in event.candidates if item.id == body.candidate_id), None)
        if candidate is None or candidate.status != "ready":
            raise PublicError(
                "CANDIDATE_NOT_READY",
                "Only a ready candidate can be approved.",
                status_code=409,
            )
        if state is ProjectState.GENERATION_PARTIAL:
            transition(project, ProjectState.AUDITION_READY)
        event.approved_candidate_id = candidate.id
        assert candidate.approved_wav_key
        assert candidate.approved_ogg_key
        approved_wav_key = repository.put_object(
            project.id,
            f"approved/{event.slug}.wav",
            repository.get_object(project.id, candidate.approved_wav_key),
            content_type="audio/wav",
        )
        approved_ogg_key = repository.put_object(
            project.id,
            f"approved/{event.slug}.ogg",
            repository.get_object(project.id, candidate.approved_ogg_key),
            content_type="audio/ogg",
        )
        approval_record = {
            "schemaVersion": 1,
            "eventId": event.id,
            "candidateId": candidate.id,
            "approvedAt": datetime.now(UTC).isoformat(),
            "approvedWavKey": approved_wav_key,
            "approvedOggKey": approved_ogg_key,
            "sourceLabel": candidate.source_label,
            "assetSha256": candidate.qc_after.sha256 if candidate.qc_after else None,
        }
        repository.put_object(
            project.id,
            f"approved/{event.slug}.json",
            (json.dumps(approval_record, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            content_type="application/json",
        )
        _store_event_documents(repository, project)
        if (
            all(item.approved_candidate_id for item in project.events)
            and ProjectState(project.state) is ProjectState.AUDITION_READY
        ):
            transition(project, ProjectState.APPROVALS_COMPLETE)
        repository.save(project)
        events.publish(
            project.id,
            "project.state",
            {"state": str(project.state), "approvedCandidateId": candidate.id},
            event_id=event.id,
            candidate_id=candidate.id,
        )
        return project_response(project, request)

    @app.post("/v1/projects/{project_id}/render", response_model=ProjectResponse)
    def render_project(project_id: str, body: RenderRequest, request: Request) -> ProjectResponse:
        project = authorized_project(project_id, request)
        events.publish(project.id, "render.status", {"status": "rendering"})
        try:
            rendered = render_mix(project, repository, body.gains_db)
        except PublicError:
            events.publish(project.id, "render.status", {"status": "failed"})
            raise
        events.publish(
            project.id,
            "render.status",
            {"status": "ready", "sha256": rendered.render.sha256 if rendered.render else None},
        )
        return project_response(rendered, request)

    @app.post("/v1/projects/{project_id}/export", response_model=ProjectResponse)
    def export_bundle(project_id: str, request: Request) -> ProjectResponse:
        project = authorized_project(project_id, request)
        events.publish(project.id, "export.status", {"status": "packing"})
        try:
            exported = export_project(project, repository)
        except PublicError:
            events.publish(project.id, "export.status", {"status": "failed"})
            raise
        events.publish(
            project.id,
            "export.status",
            {"status": "ready", "sha256": exported.export.sha256 if exported.export else None},
        )
        return project_response(exported, request)

    @app.get("/v1/projects/{project_id}/download")
    def download_bundle(project_id: str, request: Request) -> Response:
        project = authorized_project(project_id, request)
        if project.export is None or project.export.status != "ready" or not project.export.zip_key:
            raise PublicError("EXPORT_REQUIRED", "The sound kit is not ready.", status_code=409)
        return _range_response(
            request,
            repository.get_object(project.id, project.export.zip_key),
            project.export.zip_key,
        )

    @app.get("/v1/projects/{project_id}/provenance")
    def provenance(project_id: str, request: Request) -> dict[str, Any]:
        project = authorized_project(project_id, request)
        return build_provenance(project)

    @app.get("/v1/assets/{object_token}")
    def asset(object_token: str, request: Request) -> Response:
        project_id, key = signer.verify_object_token(object_token)
        return _range_response(request, repository.get_object(project_id, key), key)

    return app


app = create_app()


def run() -> None:
    """Run the API without logging credential-bearing object URLs."""

    uvicorn.run(
        "framefoley_api.main:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8000")),
        access_log=False,
    )
