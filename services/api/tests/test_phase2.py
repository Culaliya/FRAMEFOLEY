from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from framefoley_api.generation import GenerationService
from framefoley_api.live_proof import PROOF_PREFIX
from framefoley_api.main import create_app
from framefoley_api.models import LiveProofIndexV1
from framefoley_api.security import TokenSigner
from framefoley_api.settings import Settings
from framefoley_api.storage import LocalObjectStore
from pydantic import ValidationError
from starlette.requests import Request

from scripts.build_test_live_proof_fixture import build as build_test_proof


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        repo_root=Path(__file__).resolve().parents[3],
        data_dir=tmp_path,
        generation_mode="demo",
        storage_mode="local",
        live_generation_enabled=False,
        hmac_secret="phase2-unit-test-secret",
        project_ttl_hours=72,
        max_concurrent_generation=1,
        project_retry_budget=2,
        frontend_origin="http://localhost:3000",
        b2_key_id=None,
        b2_app_key=None,
        b2_bucket=None,
        b2_region=None,
        elevenlabs_api_key=None,
    )


def _proof_store(tmp_path: Path) -> LocalObjectStore:
    root = tmp_path / "objects"
    build_test_proof(root)
    return LocalObjectStore(root)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _replace_bundle_object(store: LocalObjectStore, relative: str, payload: bytes) -> None:
    store.put(PROOF_PREFIX + relative, payload, content_type="application/octet-stream")
    lines = store.get(PROOF_PREFIX + "checksums.sha256").decode().splitlines()
    digest = hashlib.sha256(payload).hexdigest()
    rewritten = [
        f"{digest}  {relative}" if line.endswith(f"  {relative}") else line for line in lines
    ]
    store.put(
        PROOF_PREFIX + "checksums.sha256",
        ("\n".join(rewritten) + "\n").encode(),
        content_type="text/plain",
    )


def test_capabilities_are_server_owned_truthful_and_secret_free(tmp_path: Path) -> None:
    store = _proof_store(tmp_path)
    with TestClient(create_app(_settings(tmp_path), store=store)) as client:
        response = client.get("/v1/capabilities")
        assert response.status_code == 200
        payload = response.json()
        assert payload == {
            "schemaVersion": 1,
            "generationMode": "demo",
            "storage": "MOCKED LOCAL STORAGE",
            "customUploadCanComplete": False,
            "liveProofReplayAvailable": True,
            "anonymousProviderSpendEnabled": False,
            "projectTtlHours": 72,
        }
        serialized = response.text.lower()
        assert all(
            forbidden not in serialized
            for forbidden in ("bucket", "keyid", "appkey", "credential", "elevenlabsapikey")
        )
        assert response.headers["cache-control"].startswith("public, max-age=15")


def test_sse_origin_disables_buffering_with_public_companion_header(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "sse-objects")
    app = create_app(_settings(tmp_path), store=store)
    with TestClient(app) as client:
        created = client.post("/v1/projects/demo").json()
        route = next(
            item
            for item in app.routes
            if getattr(item, "path", None) == "/v1/projects/{project_id}/stream"
        )
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": f"/v1/projects/{created['projectId']}/stream",
                "headers": [
                    (
                        b"authorization",
                        f"Bearer {created['projectToken']}".encode(),
                    )
                ],
            }
        )
        response = asyncio.run(route.endpoint(project_id=created["projectId"], request=request))
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"
        assert response.headers["x-framefoley-buffering"] == "disabled"


def test_custom_upload_is_blocked_in_public_demo_but_available_in_live_contract(
    tmp_path: Path,
) -> None:
    demo_store = LocalObjectStore(tmp_path / "demo-objects")
    with TestClient(create_app(_settings(tmp_path), store=demo_store)) as client:
        created = client.post("/v1/projects", json={"title": "Impossible public upload"}).json()
        blocked = client.post(
            f"/v1/projects/{created['projectId']}/upload-url",
            headers=_auth(created["projectToken"]),
            json={"filename": "clip.mp4", "mimeType": "video/mp4", "sizeBytes": 10},
        )
        assert blocked.status_code == 409
        assert blocked.json()["code"] == "CUSTOM_UPLOAD_UNAVAILABLE"

    live_settings = replace(
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
    live_store = LocalObjectStore(tmp_path / "live-objects")
    with TestClient(create_app(live_settings, store=live_store)) as client:
        capability = client.get("/v1/capabilities").json()
        assert capability["customUploadCanComplete"] is True
        created = client.post("/v1/projects", json={"title": "Self-hosted upload"}).json()
        ticket = client.post(
            f"/v1/projects/{created['projectId']}/upload-url",
            headers=_auth(created["projectToken"]),
            json={"filename": "clip.mp4", "mimeType": "video/mp4", "sizeBytes": 10},
        )
        assert ticket.status_code == 200


def test_live_proof_replay_makes_zero_provider_calls_and_completes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _proof_store(tmp_path)

    def provider_must_not_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("provider path was invoked while opening proof replay")

    monkeypatch.setattr(GenerationService, "_generate_live", provider_must_not_run)
    with TestClient(create_app(_settings(tmp_path), store=store)) as client:
        created = client.post("/v1/projects/live-proof")
        assert created.status_code == 201, created.text
        project_id = created.json()["projectId"]
        token = created.json()["projectToken"]
        envelope = client.get(f"/v1/projects/{project_id}", headers=_auth(token)).json()
        project = envelope["project"]
        assert project["evidenceLabel"] == "LIVE EVIDENCE REPLAY"
        assert project["liveCallCount"] == 0
        assert project["proofReplay"]["recordedProviderCallCount"] == 2
        assert project["proofReplay"]["replayProviderCallCount"] == 0
        event = project["events"][0]
        assert len(event["candidates"]) == 2
        assert {item["sourceLabel"] for item in event["candidates"]} == {"LIVE"}
        assert all(item["manifestVerified"] is True for item in event["candidates"])

        approved = client.post(
            f"/v1/projects/{project_id}/events/{event['id']}/approve",
            headers=_auth(token),
            json={"candidateId": event["candidates"][0]["id"]},
        )
        assert approved.status_code == 200, approved.text
        rendered = client.post(
            f"/v1/projects/{project_id}/render",
            headers=_auth(token),
            json={"gainsDb": {event["id"]: 0}},
        )
        assert rendered.status_code == 200, rendered.text
        exported = client.post(f"/v1/projects/{project_id}/export", headers=_auth(token))
        assert exported.status_code == 200, exported.text
        assert exported.json()["project"]["state"] == "complete"
        provenance = client.get(
            f"/v1/projects/{project_id}/provenance", headers=_auth(token)
        ).json()
        assert provenance["projectEvidenceLabel"] == "LIVE EVIDENCE REPLAY"
        assert "zero provider calls" in provenance["proofReplayDisclosure"]
        assert provenance["candidates"][0]["approvalStatus"] is True


def test_live_proof_manifest_tampering_fails_closed(tmp_path: Path) -> None:
    store = _proof_store(tmp_path)
    relative = "manifests/clean.json"
    manifest = json.loads(store.get(PROOF_PREFIX + relative))
    manifest["canonical_hash"] = "0" * 64
    _replace_bundle_object(
        store,
        relative,
        (json.dumps(manifest, separators=(",", ":")) + "\n").encode(),
    )
    with TestClient(create_app(_settings(tmp_path), store=store)) as client:
        response = client.post("/v1/projects/live-proof")
        assert response.status_code == 503
        assert response.json()["code"] == "LIVE_PROOF_INVALID"
        assert "canonical_hash" not in response.text


def test_live_proof_downloaded_asset_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    store = _proof_store(tmp_path)
    relative = "candidates/character/raw-audio.mp3"
    _replace_bundle_object(store, relative, store.get(PROOF_PREFIX + relative) + b"tampered")
    with TestClient(create_app(_settings(tmp_path), store=store)) as client:
        response = client.post("/v1/projects/live-proof")
        assert response.status_code == 503
        assert response.json()["code"] == "LIVE_PROOF_INVALID"


@pytest.mark.parametrize("invalid_label", ["CACHED DEMO", "MOCKED"])
def test_non_live_records_cannot_enter_proof_bundle(tmp_path: Path, invalid_label: str) -> None:
    store = _proof_store(tmp_path)
    index_key = PROOF_PREFIX + "proof-index.json"
    payload = json.loads(store.get(index_key))
    payload["sourceLabel"] = invalid_label
    with pytest.raises(ValidationError):
        LiveProofIndexV1.model_validate(payload)
    _replace_bundle_object(
        store,
        "proof-index.json",
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(),
    )
    with TestClient(create_app(_settings(tmp_path), store=store)) as client:
        response = client.post("/v1/projects/live-proof")
        assert response.status_code == 503


def test_proof_projects_are_token_isolated_and_signed_assets_expire(tmp_path: Path) -> None:
    store = _proof_store(tmp_path)
    settings = _settings(tmp_path)
    with TestClient(create_app(settings, store=store)) as client:
        first = client.post("/v1/projects/live-proof").json()
        second = client.post("/v1/projects/live-proof").json()
        forbidden = client.get(
            f"/v1/projects/{first['projectId']}", headers=_auth(second["projectToken"])
        )
        assert forbidden.status_code == 403
        first_project = client.get(
            f"/v1/projects/{first['projectId']}", headers=_auth(first["projectToken"])
        ).json()["project"]
        asset_key = first_project["source"]["previewKey"]
        expired = TokenSigner.from_secret(settings.hmac_secret).object_token(
            first["projectId"], asset_key, int(time.time()) - 1
        )
        response = client.get(f"/v1/assets/{expired}")
        assert response.status_code == 401


def test_live_proof_replay_survives_api_restart(tmp_path: Path) -> None:
    store = _proof_store(tmp_path)
    settings = _settings(tmp_path)
    with TestClient(create_app(settings, store=store)) as first_process:
        created = first_process.post("/v1/projects/live-proof").json()
    with TestClient(create_app(settings, store=store)) as restarted_process:
        recovered = restarted_process.get(
            f"/v1/projects/{created['projectId']}", headers=_auth(created["projectToken"])
        )
        assert recovered.status_code == 200
        project = recovered.json()["project"]
        assert project["evidenceLabel"] == "LIVE EVIDENCE REPLAY"
        assert project["liveCallCount"] == 0


def test_duplicate_generation_submit_uses_the_existing_idempotency_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalObjectStore(tmp_path / "idempotency-objects")
    calls = 0
    original = GenerationService._process_cached_candidate

    def counted(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(GenerationService, "_process_cached_candidate", counted)
    with TestClient(create_app(_settings(tmp_path), store=store)) as client:
        created = client.post("/v1/projects/demo").json()
        project_id = created["projectId"]
        token = created["projectToken"]
        project = client.get(f"/v1/projects/{project_id}", headers=_auth(token)).json()["project"]
        queued = client.put(
            f"/v1/projects/{project_id}/events",
            headers=_auth(token),
            json={"style": project["style"], "events": project["events"]},
        )
        assert queued.status_code == 200
        headers = {**_auth(token), "Idempotency-Key": "same-submit-key"}
        first = client.post(f"/v1/projects/{project_id}/generate", headers=headers)
        second = client.post(f"/v1/projects/{project_id}/generate", headers=headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert calls == 6
        assert second.json()["project"]["state"] == "audition_ready"
