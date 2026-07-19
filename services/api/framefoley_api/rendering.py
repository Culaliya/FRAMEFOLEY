"""Authoritative fixed-array FFmpeg preview rendering."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from framefoley_api.errors import PublicError
from framefoley_api.models import (
    FrameFoleyProject,
    GenerationCandidate,
    MixRender,
    ProjectState,
    SoundEvent,
)
from framefoley_api.repository import ProjectRepository
from framefoley_api.state import transition
from framefoley_spike.provenance import sanitize_text


def _approved_candidate(
    project: FrameFoleyProject, event_id: str
) -> tuple[SoundEvent, GenerationCandidate]:
    event = next((item for item in project.events if item.id == event_id), None)
    if event is None or not event.approved_candidate_id:
        raise PublicError("APPROVALS_REQUIRED", "Every event needs one approval.", status_code=409)
    candidate = next(
        (item for item in event.candidates if item.id == event.approved_candidate_id), None
    )
    if candidate is None or candidate.status != "ready" or not candidate.approved_wav_key:
        raise PublicError(
            "APPROVED_CANDIDATE_INVALID",
            "Approved candidate is not render-ready.",
            status_code=409,
        )
    return event, candidate


def render_mix(
    project: FrameFoleyProject,
    repository: ProjectRepository,
    gains_db: dict[str, float],
) -> FrameFoleyProject:
    if project.source is None:
        raise PublicError("SOURCE_REQUIRED", "Project source video is missing.", status_code=409)
    if len(project.events) == 0:
        raise PublicError("EVENT_COUNT_INVALID", "At least one event is required.", status_code=409)
    approved = [_approved_candidate(project, event.id) for event in project.events]
    bounded_gains: dict[str, float] = {}
    for event, _candidate in approved:
        gain = float(gains_db.get(event.id, 0.0))
        if not -12 <= gain <= 6:
            raise PublicError(
                "GAIN_INVALID",
                "Event gain must be between -12 and +6 dB.",
                status_code=422,
            )
        bounded_gains[event.id] = gain

    transition(project, ProjectState.RENDERING)
    project.render = MixRender(status="rendering", gains_db=bounded_gains)
    repository.save(project)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise PublicError("MEDIA_TOOL_MISSING", "ffmpeg is not installed.", status_code=503)

    try:
        with TemporaryDirectory(prefix="framefoley-render-") as temporary:
            root = Path(temporary)
            source_path = root / "source.mp4"
            output_path = root / "mixed-preview.mp4"
            source_path.write_bytes(repository.get_object(project.id, project.source.preview_key))
            audio_paths: list[Path] = []
            filter_parts: list[str] = []
            mix_inputs: list[str] = []
            mix_events: list[dict[str, object]] = []
            for index, (event, candidate) in enumerate(approved, start=1):
                audio_path = root / f"candidate-{index}.wav"
                audio_path.write_bytes(
                    repository.get_object(project.id, str(candidate.approved_wav_key))
                )
                audio_paths.append(audio_path)
                delay_ms = round(event.timestamp_seconds * 1000)
                gain = bounded_gains[event.id]
                label = f"sfx{index}"
                filter_parts.append(
                    f"[{index}:a]volume={gain:.3f}dB,adelay={delay_ms}:all=1[{label}]"
                )
                mix_inputs.append(f"[{label}]")
                mix_events.append(
                    {
                        "eventId": event.id,
                        "candidateId": candidate.id,
                        "timestampSeconds": event.timestamp_seconds,
                        "gainDb": gain,
                        "assetSha256": candidate.qc_after.sha256 if candidate.qc_after else None,
                    }
                )
            filter_parts.append(
                "".join(mix_inputs)
                + f"amix=inputs={len(mix_inputs)}:normalize=0:duration=longest,"
                + f"apad=pad_dur={project.source.duration_seconds:.3f},"
                + f"atrim=duration={project.source.duration_seconds:.3f},"
                + "alimiter=limit=0.891251:attack=5:release=50[aout]"
            )
            command = [ffmpeg, "-y", "-v", "error", "-i", str(source_path)]
            for audio_path in audio_paths:
                command.extend(["-i", str(audio_path)])
            command.extend(
                [
                    "-filter_complex",
                    ";".join(filter_parts),
                    "-map",
                    "0:v:0",
                    "-map",
                    "[aout]",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "20",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                    str(output_path),
                ]
            )
            completed = subprocess.run(command, check=False, capture_output=True, timeout=120)
            if completed.returncode != 0:
                error = sanitize_text(completed.stderr.decode("utf-8", errors="replace"))
                raise PublicError(
                    "RENDER_FAILED",
                    f"Preview render failed: {error[:180]}",
                    status_code=500,
                )
            output_bytes = output_path.read_bytes()
            render_hash = hashlib.sha256(output_bytes).hexdigest()
            mix_map = {
                "schemaVersion": 1,
                "sourceSha256": project.source.sha256,
                "events": mix_events,
                "renderSha256": render_hash,
            }
            preview_key = repository.put_object(
                project.id,
                "render/mixed-preview.mp4",
                output_bytes,
                content_type="video/mp4",
            )
            mix_map_key = repository.put_object(
                project.id,
                "render/mix-map.json",
                (json.dumps(mix_map, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                content_type="application/json",
            )
        project.render = MixRender(
            status="ready",
            preview_key=preview_key,
            mix_map_key=mix_map_key,
            duration_seconds=project.source.duration_seconds,
            sha256=render_hash,
            gains_db=bounded_gains,
        )
        transition(project, ProjectState.RENDER_READY)
    except PublicError:
        project.render = MixRender(status="failed", gains_db=bounded_gains)
        transition(project, ProjectState.RENDER_FAILED)
        repository.save(project)
        raise
    repository.save(project)
    return project
