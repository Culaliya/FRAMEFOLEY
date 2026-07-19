from __future__ import annotations

import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from framefoley_api.errors import PublicError
from framefoley_api.generation import GenerationService
from framefoley_api.main import create_app
from framefoley_api.models import FrameFoleyProject, GenerationCandidate, SoundEvent
from framefoley_api.repository import project_prefix
from framefoley_api.settings import Settings
from framefoley_api.storage import LocalObjectStore


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        repo_root=Path(__file__).resolve().parents[3],
        data_dir=tmp_path,
        generation_mode="demo",
        storage_mode="local",
        live_generation_enabled=False,
        hmac_secret="test-only-framefoley-secret",
        project_ttl_hours=24,
        max_concurrent_generation=1,
        project_retry_budget=2,
        frontend_origin="http://localhost:3000",
        b2_key_id=None,
        b2_app_key=None,
        b2_bucket=None,
        b2_region=None,
        elevenlabs_api_key=None,
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_demo(client: TestClient) -> tuple[str, str]:
    response = client.post("/v1/projects/demo")
    assert response.status_code == 201, response.text
    payload = response.json()
    return str(payload["projectId"]), str(payload["projectToken"])


def _queue_demo_events(client: TestClient, project_id: str, token: str) -> dict[str, object]:
    response = client.get(f"/v1/projects/{project_id}", headers=_auth(token))
    assert response.status_code == 200, response.text
    project = response.json()["project"]
    queued = client.put(
        f"/v1/projects/{project_id}/events",
        headers=_auth(token),
        json={"style": project["style"], "events": project["events"]},
    )
    assert queued.status_code == 200, queued.text
    assert queued.json()["project"]["state"] == "generation_queued"
    return queued.json()["project"]


def test_project_response_reports_b2_storage_label(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = LocalObjectStore(tmp_path / "objects")
    store.label = "BACKBLAZE B2"
    with TestClient(create_app(settings, store=store)) as client:
        project_id, token = _create_demo(client)

        response = client.get(f"/v1/projects/{project_id}", headers=_auth(token))

    assert response.status_code == 200, response.text
    assert response.json()["storageLabel"] == "BACKBLAZE B2"


def test_project_load_does_not_depend_on_head_exists(tmp_path: Path) -> None:
    class HeadDeniedStore(LocalObjectStore):
        def exists(self, key: str) -> bool:
            del key
            return False

    store = HeadDeniedStore(tmp_path / "head-denied-objects")
    with TestClient(create_app(_settings(tmp_path), store=store)) as client:
        created = client.post("/v1/projects/demo").json()
        loaded = client.get(
            f"/v1/projects/{created['projectId']}",
            headers=_auth(created["projectToken"]),
        )
        assert loaded.status_code == 200
        assert loaded.json()["project"]["id"] == created["projectId"]


def test_demo_project_completes_end_to_end(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = LocalObjectStore(tmp_path / "objects")
    with TestClient(create_app(settings, store=store)) as client:
        project_id, token = _create_demo(client)
        queued = _queue_demo_events(client, project_id, token)

        generated = client.post(
            f"/v1/projects/{project_id}/generate",
            headers={**_auth(token), "Idempotency-Key": "demo-generation-1"},
        )
        assert generated.status_code == 200, generated.text
        payload = generated.json()
        project = payload["project"]
        assert project["state"] == "audition_ready"
        assert len(project["events"]) == 3
        assert all(len(event["candidates"]) == 2 for event in project["events"])
        candidates = [candidate for event in project["events"] for candidate in event["candidates"]]
        assert len(candidates) == 6
        assert all(candidate["status"] == "ready" for candidate in candidates)
        assert all(candidate["sourceLabel"] == "CACHED DEMO" for candidate in candidates)
        assert all(candidate["manifestVerified"] is False for candidate in candidates)
        assert all(candidate["qcAfter"]["verdict"] == "pass" for candidate in candidates)
        assert any(candidate["repairs"] for candidate in candidates)

        source_url = payload["assetUrls"][project["source"]["previewKey"]]
        ranged = client.get(source_url, headers={"Range": "bytes=0-31"})
        assert ranged.status_code == 206
        assert len(ranged.content) == 32
        assert ranged.headers["content-range"].startswith("bytes 0-31/")

        repeated = client.post(
            f"/v1/projects/{project_id}/generate",
            headers={**_auth(token), "Idempotency-Key": "demo-generation-1"},
        )
        assert repeated.status_code == 200
        repeated_ids = [
            candidate["id"]
            for event in repeated.json()["project"]["events"]
            for candidate in event["candidates"]
        ]
        assert repeated_ids == [candidate["id"] for candidate in candidates]

        for event in project["events"]:
            approved = client.post(
                f"/v1/projects/{project_id}/events/{event['id']}/approve",
                headers=_auth(token),
                json={"candidateId": event["candidates"][0]["id"]},
            )
            assert approved.status_code == 200, approved.text
        approved_project = approved.json()["project"]
        assert approved_project["state"] == "approvals_complete"
        keys_after_approval = store.list_keys(project_prefix(project_id))
        assert f"{project_prefix(project_id)}source/source-metadata.json" in keys_after_approval
        assert all(
            f"{project_prefix(project_id)}events/{event['id']}/event.json" in keys_after_approval
            for event in project["events"]
        )
        assert all(
            f"{project_prefix(project_id)}approved/{event['slug']}.wav" in keys_after_approval
            for event in project["events"]
        )
        assert all(
            f"{project_prefix(project_id)}approved/{event['slug']}.ogg" in keys_after_approval
            for event in project["events"]
        )

        gains = {event["id"]: 0 for event in queued["events"]}
        rendered = client.post(
            f"/v1/projects/{project_id}/render",
            headers=_auth(token),
            json={"gainsDb": gains},
        )
        assert rendered.status_code == 200, rendered.text
        rendered_project = rendered.json()["project"]
        assert rendered_project["state"] == "render_ready"
        assert rendered_project["render"]["status"] == "ready"
        assert len(rendered_project["render"]["sha256"]) == 64
        mix_map = json.loads(store.get(f"{project_prefix(project_id)}render/mix-map.json"))
        assert mix_map["sourceSha256"] == rendered_project["source"]["sha256"]
        assert mix_map["renderSha256"] == rendered_project["render"]["sha256"]
        assert len(mix_map["events"]) == 3
        assert all(
            set(record)
            == {
                "eventId",
                "candidateId",
                "timestampSeconds",
                "gainDb",
                "assetSha256",
            }
            for record in mix_map["events"]
        )

        exported = client.post(f"/v1/projects/{project_id}/export", headers=_auth(token))
        assert exported.status_code == 200, exported.text
        exported_project = exported.json()["project"]
        assert exported_project["state"] == "complete"
        assert exported_project["export"]["status"] == "ready"
        assert exported_project["export"]["inventory"] == sorted(
            exported_project["export"]["inventory"]
        )

        download = client.get(f"/v1/projects/{project_id}/download", headers=_auth(token))
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
            names = set(archive.namelist())
            required = {
                "README.md",
                "framefoley-project.json",
                "soundpack.json",
                "provenance-index.json",
                "preview/mixed-preview.mp4",
                "sfx/glass-landing.wav",
                "sfx/glass-landing.ogg",
                "sfx/bubble-pop.wav",
                "sfx/route-confirm.wav",
            }
            assert required <= names
            provenance = json.loads(archive.read("provenance-index.json"))
            assert len(provenance["candidates"]) == 6
            assert {record["candidate"]["sourceLabel"] for record in provenance["candidates"]} == {
                "CACHED DEMO"
            }

        provenance_response = client.get(
            f"/v1/projects/{project_id}/provenance", headers=_auth(token)
        )
        assert provenance_response.status_code == 200
        assert provenance_response.json()["projectId"] == project_id


def test_custom_upload_and_project_token_isolation(tmp_path: Path) -> None:
    settings = replace(
        _settings(tmp_path),
        generation_mode="live",
        storage_mode="b2",
        live_generation_enabled=True,
        b2_key_id="test-key-id",
        b2_app_key="test-app-key-value",
        b2_bucket="test-private-bucket",
        b2_region="us-test-001",
        elevenlabs_api_key="test-provider-key",
    )
    with TestClient(create_app(settings, store=LocalObjectStore(tmp_path / "objects"))) as client:
        first = client.post("/v1/projects", json={"title": "Private upload"})
        assert first.status_code == 201
        first_id = first.json()["projectId"]
        first_token = first.json()["projectToken"]

        second = client.post("/v1/projects", json={"title": "Other project"})
        second_token = second.json()["projectToken"]
        forbidden = client.get(f"/v1/projects/{first_id}", headers=_auth(second_token))
        assert forbidden.status_code == 403
        assert forbidden.json()["code"] == "PROJECT_TOKEN_SCOPE"
        assert "Traceback" not in forbidden.text

        video = (settings.repo_root / "demo" / "jelly-relay.mp4").read_bytes()
        upload = client.post(
            f"/v1/projects/{first_id}/upload-url",
            headers=_auth(first_token),
            json={
                "filename": "quiet-gameplay.mp4",
                "mimeType": "video/mp4",
                "sizeBytes": len(video),
            },
        )
        assert upload.status_code == 200, upload.text
        upload_payload = upload.json()
        stored = client.put(
            upload_payload["uploadUrl"],
            headers={"Content-Type": "video/mp4"},
            content=video,
        )
        assert stored.status_code == 204, stored.text
        completed = client.post(
            f"/v1/projects/{first_id}/source/complete",
            headers=_auth(first_token),
            json={"objectKey": upload_payload["objectKey"]},
        )
        assert completed.status_code == 200, completed.text
        source = completed.json()["project"]["source"]
        assert source["origin"] == "upload"
        assert source["sourceAudioStripped"] is True
        assert source["durationSeconds"] == 12
        assert completed.json()["project"]["state"] == "source_ready"


def test_public_errors_are_typed_and_sanitized(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        project_id, _token = _create_demo(client)
        response = client.get(
            f"/v1/projects/{project_id}", headers={"Authorization": "Bearer altered.token"}
        )
        assert response.status_code == 401
        payload = response.json()
        assert set(payload) == {"code", "message", "retryable", "requestId"}
        assert payload["code"] == "PROJECT_TOKEN_INVALID"
        assert payload["requestId"].startswith("req_")
        assert "secret" not in response.text.lower()


def test_project_recovers_after_api_process_restart(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as first_process:
        project_id, token = _create_demo(first_process)
        first_snapshot = first_process.get(
            f"/v1/projects/{project_id}", headers=_auth(token)
        ).json()["project"]
    with TestClient(create_app(settings)) as restarted_process:
        recovered = restarted_process.get(f"/v1/projects/{project_id}", headers=_auth(token))
        assert recovered.status_code == 200, recovered.text
        assert recovered.json()["project"]["id"] == first_snapshot["id"]
        assert recovered.json()["project"]["source"]["sha256"] == first_snapshot["source"]["sha256"]


def test_generation_disabled_mode_fails_closed_but_demo_source_remains_viewable(
    tmp_path: Path,
) -> None:
    settings = replace(_settings(tmp_path), generation_mode="disabled")
    with TestClient(create_app(settings)) as client:
        project_id, token = _create_demo(client)
        _queue_demo_events(client, project_id, token)
        generated = client.post(
            f"/v1/projects/{project_id}/generate",
            headers={**_auth(token), "Idempotency-Key": "disabled-generation"},
        )
        assert generated.status_code == 503
        assert generated.json()["code"] == "LIVE_GENERATION_DISABLED"
        still_viewable = client.get(f"/v1/projects/{project_id}", headers=_auth(token))
        assert still_viewable.status_code == 200
        assert still_viewable.json()["project"]["source"]["origin"] == "demo"


def test_live_mode_requires_kill_switch_b2_and_credentials(tmp_path: Path) -> None:
    settings = replace(
        _settings(tmp_path),
        generation_mode="live",
        live_generation_enabled=False,
    )
    with TestClient(create_app(settings)) as client:
        project_id, token = _create_demo(client)
        _queue_demo_events(client, project_id, token)
        generated = client.post(
            f"/v1/projects/{project_id}/generate",
            headers={**_auth(token), "Idempotency-Key": "closed-live-generation"},
        )
        assert generated.status_code == 503
        assert generated.json()["code"] == "LIVE_CONFIGURATION_INVALID"
        assert "credential" not in generated.text.lower()


def test_partial_candidate_failure_preserves_successful_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = GenerationService._process_cached_candidate

    def fail_one_candidate(
        service: GenerationService,
        project: FrameFoleyProject,
        event: SoundEvent,
        candidate: GenerationCandidate,
    ) -> None:
        if event.slug == "bubble-pop" and candidate.variant == "character":
            raise PublicError(
                "DEMO_INJECTED_FAILURE",
                "Synthetic integration failure.",
                status_code=503,
            )
        original(service, project, event, candidate)

    monkeypatch.setattr(GenerationService, "_process_cached_candidate", fail_one_candidate)
    with TestClient(create_app(_settings(tmp_path))) as client:
        project_id, token = _create_demo(client)
        _queue_demo_events(client, project_id, token)
        generated = client.post(
            f"/v1/projects/{project_id}/generate",
            headers={**_auth(token), "Idempotency-Key": "partial-generation"},
        )
        assert generated.status_code == 200
        project = generated.json()["project"]
        assert project["state"] == "generation_partial"
        candidates = [candidate for event in project["events"] for candidate in event["candidates"]]
        assert sum(candidate["status"] == "ready" for candidate in candidates) == 5
        assert sum(candidate["status"] == "failed" for candidate in candidates) == 1
