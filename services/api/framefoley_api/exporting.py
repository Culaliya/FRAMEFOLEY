"""Deterministic ZIP and human-readable provenance export."""

from __future__ import annotations

import hashlib
import html
import io
import json
import zipfile
from datetime import UTC, datetime
from typing import Any

from framefoley_api.errors import PublicError
from framefoley_api.models import ExportBundle, FrameFoleyProject, ProjectState
from framefoley_api.repository import ProjectRepository
from framefoley_api.state import transition

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def build_provenance(project: FrameFoleyProject) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for event in project.events:
        for candidate in event.candidates:
            candidates.append(
                {
                    "event": {
                        "id": event.id,
                        "title": event.title,
                        "timestampSeconds": event.timestamp_seconds,
                    },
                    "candidate": candidate.model_dump(
                        mode="json", by_alias=True, exclude_none=True
                    ),
                    "approvalStatus": candidate.id == event.approved_candidate_id,
                }
            )
    return {
        "schemaVersion": 1,
        "projectId": project.id,
        "generatedAt": project.updated_at.isoformat(),
        "sourceLabelPolicy": {
            "LIVE": "Canonical Genblaze manifest required and verified.",
            "CACHED DEMO": "Original bundled cache; never represented as a live generation.",
            "MOCKED": "Test-only behavior; never represented as production evidence.",
        },
        "project": project.model_dump(mode="json", by_alias=True, exclude_none=True),
        "candidates": candidates,
    }


def _provenance_html(provenance: dict[str, Any]) -> bytes:
    rows: list[str] = []
    for record in provenance["candidates"]:
        event = record["event"]
        candidate = record["candidate"]
        rows.append(
            "<article><h2>"
            + html.escape(str(event["title"]))
            + " · "
            + html.escape(str(candidate["variant"]).upper())
            + "</h2><dl>"
            + f"<dt>Source</dt><dd>{html.escape(str(candidate['sourceLabel']))}</dd>"
            + f"<dt>Provider/model</dt><dd>{html.escape(str(candidate['provider']))} / "
            + f"{html.escape(str(candidate['model']))}</dd>"
            + f"<dt>Manifest verified</dt><dd>{candidate['manifestVerified']}</dd>"
            + "<dt>SHA-256</dt><dd><code>"
            + html.escape(str(candidate.get("assetSha256", "unavailable")))
            + "</code></dd>"
            + f"<dt>Prompt</dt><dd>{html.escape(str(candidate['prompt']))}</dd>"
            + "</dl></article>"
        )
    document = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FRAMEFOLEY provenance</title><style>
body{margin:0;background:#090b0c;color:#ece7db;font:16px/1.5 system-ui;padding:5vw}
h1{font-size:clamp(2.5rem,8vw,7rem);line-height:.9}
article{border-top:1px solid #59e5e2;padding:2rem 0}
dt{color:#59e5e2;font:700 12px monospace;text-transform:uppercase}
dd{margin:0 0 1rem}code{overflow-wrap:anywhere}
</style><h1>THE SOUND MAY BE SYNTHETIC.<br>THE HISTORY IS NOT.</h1>"""
    return (document + "".join(rows) + "</html>").encode("utf-8")


def _zip_write(archive: zipfile.ZipFile, path: str, data: bytes) -> None:
    info = zipfile.ZipInfo(path, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, data)


def export_project(project: FrameFoleyProject, repository: ProjectRepository) -> FrameFoleyProject:
    if project.render is None or project.render.status != "ready" or not project.render.preview_key:
        raise PublicError(
            "RENDER_REQUIRED",
            "Render the approved mix before exporting.",
            status_code=409,
        )
    for event in project.events:
        if not event.approved_candidate_id:
            raise PublicError(
                "APPROVALS_REQUIRED", "Every event needs one approval.", status_code=409
            )
    transition(project, ProjectState.EXPORTING)
    project.export = ExportBundle(status="packing", inventory=[])
    repository.save(project)
    provenance = build_provenance(project)
    provenance_bytes = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8")
    provenance_html = _provenance_html(provenance)
    provenance_key = repository.put_object(
        project.id, "provenance/index.json", provenance_bytes, content_type="application/json"
    )
    repository.put_object(
        project.id,
        "provenance/index.html",
        provenance_html,
        content_type="text/html",
    )

    files: dict[str, bytes] = {}
    project_document = project.model_dump(mode="json", by_alias=True, exclude_none=True)
    files["framefoley-project.json"] = (
        json.dumps(project_document, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    files["provenance-index.json"] = provenance_bytes
    files["preview/mixed-preview.mp4"] = repository.get_object(
        project.id, str(project.render.preview_key)
    )
    soundpack_events: list[dict[str, Any]] = []
    for event in project.events:
        candidate = next(
            item for item in event.candidates if item.id == event.approved_candidate_id
        )
        assert candidate.approved_wav_key
        assert candidate.approved_ogg_key
        wav_name = f"sfx/{event.slug}.wav"
        ogg_name = f"sfx/{event.slug}.ogg"
        files[wav_name] = repository.get_object(project.id, candidate.approved_wav_key)
        files[ogg_name] = repository.get_object(project.id, candidate.approved_ogg_key)
        if candidate.manifest_uri:
            files[f"manifests/{event.slug}-{candidate.variant}.json"] = repository.get_object(
                project.id, candidate.manifest_uri
            )
        if candidate.qc_before:
            files[f"qc/{event.slug}-{candidate.variant}-before.json"] = (
                json.dumps(
                    candidate.qc_before.model_dump(mode="json", by_alias=True),
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
        if candidate.qc_after:
            files[f"qc/{event.slug}-{candidate.variant}-after.json"] = (
                json.dumps(
                    candidate.qc_after.model_dump(mode="json", by_alias=True),
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
        if candidate.waveform_key:
            files[f"waveforms/{event.slug}-{candidate.variant}.png"] = repository.get_object(
                project.id, candidate.waveform_key
            )
        soundpack_events.append(
            {
                "eventId": event.id,
                "title": event.title,
                "timestampSeconds": event.timestamp_seconds,
                "candidateId": candidate.id,
                "wav": wav_name,
                "ogg": ogg_name,
                "sha256": candidate.qc_after.sha256 if candidate.qc_after else None,
            }
        )
    files["soundpack.json"] = (
        json.dumps({"schemaVersion": 1, "events": soundpack_events}, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    files["README.md"] = f"""# {project.title} — FRAMEFOLEY sound kit

This bundle contains an approved mixed preview, WAV and OGG sound effects,
technical QC reports, waveform images, manifests, and a provenance index.

Provider/model disclosure is recorded per candidate in `provenance-index.json`.
Genblaze orchestrates LIVE candidates and their canonical manifests. Backblaze
B2 is the durable production system of record. Entries labeled CACHED DEMO are
original bundled examples and are not represented as live generations.

Technical QC is deterministic. Creative approval remains a human decision.
This provenance record documents how files were made; it is not independent
legal clearance. Review the provider plan and terms applicable to your use.
""".encode()

    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        for path in sorted(files):
            _zip_write(archive, path, files[path])
    archive_bytes = archive_buffer.getvalue()
    archive_hash = hashlib.sha256(archive_bytes).hexdigest()
    zip_key = repository.put_object(
        project.id,
        f"export/framefoley-{project.slug}.zip",
        archive_bytes,
        content_type="application/zip",
    )
    created_at = datetime.now(UTC)
    project.export = ExportBundle(
        status="ready",
        zip_key=zip_key,
        sha256=archive_hash,
        size_bytes=len(archive_bytes),
        created_at=created_at,
        provenance_index_key=provenance_key,
        inventory=sorted(files),
    )
    transition(project, ProjectState.COMPLETE)
    repository.save(project)
    return project
