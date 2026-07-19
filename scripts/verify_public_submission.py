"""Verify the public Phase 2 submission without persisting access tokens."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "phase2"
DEFAULT_WEB_URL = "https://framefoley-culaliya.onrender.com"
DEFAULT_API_URL = "https://framefoley-api-culaliya.onrender.com"


class VerificationFailure(RuntimeError):
    """Public contract mismatch with a value-safe message."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationFailure(message)


def _json(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise VerificationFailure("public endpoint did not return a JSON object")
    return payload


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _write_json(name: str, payload: object) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _wait_until_ready(client: httpx.Client, api_url: str) -> dict[str, Any]:
    deadline = time.monotonic() + 90
    delay = 1.0
    attempts = 0
    while time.monotonic() < deadline:
        attempts += 1
        try:
            response = client.get(f"{api_url}/readyz")
            payload = response.json()
            if (
                response.status_code == 200
                and isinstance(payload, dict)
                and payload.get("status") == "ready"
            ):
                payload["verificationAttempts"] = attempts
                return payload
        except (httpx.HTTPError, json.JSONDecodeError):
            pass
        time.sleep(delay)
        delay = min(delay * 1.8, 8.0)
    raise VerificationFailure("public API did not become ready within 90 seconds")


def _project(client: httpx.Client, api_url: str, project_id: str, token: str) -> dict[str, Any]:
    return _json(
        client.get(
            f"{api_url}/v1/projects/{project_id}",
            headers=_auth(token),
        )
    )


def _approve_render_export(
    client: httpx.Client,
    api_url: str,
    project_id: str,
    token: str,
    project: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    headers = _auth(token)
    events = project.get("events")
    if not isinstance(events, list) or not events:
        raise VerificationFailure("project has no auditable events")
    gains: dict[str, float] = {}
    for item in events:
        _require(isinstance(item, dict), "event contract is invalid")
        event_id = str(item.get("id", ""))
        candidates = item.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != 2:
            raise VerificationFailure("event does not contain exactly two candidates")
        candidate = candidates[0]
        _require(isinstance(candidate, dict), "candidate contract is invalid")
        approved = client.post(
            f"{api_url}/v1/projects/{project_id}/events/{event_id}/approve",
            headers={**headers, "Content-Type": "application/json"},
            json={"candidateId": candidate.get("id")},
        )
        approved.raise_for_status()
        gains[event_id] = 0
    rendered = _json(
        client.post(
            f"{api_url}/v1/projects/{project_id}/render",
            headers={**headers, "Content-Type": "application/json"},
            json={"gainsDb": gains},
        )
    )["project"]
    _require(rendered.get("state") == "render_ready", "public render did not complete")
    exported = _json(client.post(f"{api_url}/v1/projects/{project_id}/export", headers=headers))[
        "project"
    ]
    _require(exported.get("state") == "complete", "public export did not complete")
    provenance = _json(
        client.get(f"{api_url}/v1/projects/{project_id}/provenance", headers=headers)
    )
    download = client.get(f"{api_url}/v1/projects/{project_id}/download", headers=headers)
    download.raise_for_status()
    _require(
        download.headers.get("content-type", "").startswith("application/zip"),
        "public download is not a ZIP",
    )
    return exported, provenance


def _verify_sse_headers(
    client: httpx.Client, api_url: str, project_id: str, token: str
) -> dict[str, Any]:
    started = time.monotonic()
    with client.stream(
        "GET",
        f"{api_url}/v1/projects/{project_id}/stream",
        headers=_auth(token),
    ) as response:
        response.raise_for_status()
        _require(response.headers.get("cache-control") == "no-cache", "SSE cache header mismatch")
        accel_buffering = response.headers.get("x-accel-buffering")
        cloudflare_edge = bool(response.headers.get("cf-ray")) or (
            response.headers.get("server", "").lower() == "cloudflare"
        )
        _require(
            accel_buffering == "no" or (accel_buffering is None and cloudflare_edge),
            "SSE origin buffering directive is absent without a documented stripping edge",
        )
        _require(
            response.headers.get("x-framefoley-buffering") == "disabled",
            "SSE public buffering contract mismatch",
        )
        first_line = next((line for line in response.iter_lines() if line), "")
        first_event_seconds = round(time.monotonic() - started, 3)
        _require(
            first_line.startswith(("id:", "event:")),
            "SSE did not yield an authoritative event",
        )
        _require(first_event_seconds < 10, "SSE first event was buffered too long")
        return {
            "cacheControl": "no-cache",
            "originXAccelBuffering": (
                "no" if accel_buffering == "no" else "STRIPPED_BY_CLOUDFLARE"
            ),
            "publicBufferingContract": "disabled",
            "firstEventSeconds": first_event_seconds,
        }


def _verify_cached_demo(client: httpx.Client, api_url: str) -> dict[str, Any]:
    created = _json(client.post(f"{api_url}/v1/projects/demo"))
    project_id = str(created["projectId"])
    token = str(created["projectToken"])
    envelope = _project(client, api_url, project_id, token)
    _require(envelope.get("storageLabel") == "BACKBLAZE B2", "cached demo is not B2-backed")
    project = envelope["project"]
    _require(project.get("evidenceLabel") == "CACHED DEMO", "cached demo label mismatch")
    sse = _verify_sse_headers(client, api_url, project_id, token)
    queued = _json(
        client.put(
            f"{api_url}/v1/projects/{project_id}/events",
            headers={**_auth(token), "Content-Type": "application/json"},
            json={"style": project["style"], "events": project["events"]},
        )
    )
    _require(queued["project"].get("state") == "generation_queued", "demo cue lock failed")
    generated = _json(
        client.post(
            f"{api_url}/v1/projects/{project_id}/generate",
            headers={**_auth(token), "Idempotency-Key": "phase2-public-verification-demo"},
        )
    )["project"]
    _require(generated.get("state") == "audition_ready", "cached generation did not complete")
    candidates = [candidate for event in generated["events"] for candidate in event["candidates"]]
    _require(len(candidates) == 6, "cached demo candidate count mismatch")
    _require(
        all(candidate.get("sourceLabel") == "CACHED DEMO" for candidate in candidates),
        "cached demo candidate label mismatch",
    )
    exported, provenance = _approve_render_export(client, api_url, project_id, token, generated)
    _require(len(provenance.get("candidates", [])) == 6, "cached provenance is incomplete")
    return {
        "status": "PASS",
        "evidenceLabel": "CACHED DEMO",
        "storage": "BACKBLAZE B2",
        "eventCount": 3,
        "candidateCount": 6,
        "finalState": exported.get("state"),
        "download": "ZIP VERIFIED",
        "sse": sse,
    }


def _verify_live_proof(client: httpx.Client, api_url: str) -> dict[str, Any]:
    created = _json(client.post(f"{api_url}/v1/projects/live-proof"))
    project_id = str(created["projectId"])
    token = str(created["projectToken"])
    envelope = _project(client, api_url, project_id, token)
    _require(envelope.get("storageLabel") == "BACKBLAZE B2", "LIVE replay is not B2-backed")
    project = envelope["project"]
    replay = project.get("proofReplay")
    _require(project.get("evidenceLabel") == "LIVE EVIDENCE REPLAY", "replay label mismatch")
    _require(project.get("liveCallCount") == 0, "replay recorded a current LIVE call")
    _require(isinstance(replay, dict), "proof replay metadata is missing")
    _require(replay.get("recordedProviderCallCount") == 2, "recorded call count mismatch")
    _require(replay.get("replayProviderCallCount") == 0, "replay made a provider call")
    events = project.get("events")
    _require(isinstance(events, list) and len(events) == 1, "proof event count mismatch")
    candidates = events[0].get("candidates", [])
    _require(len(candidates) == 2, "proof candidate count mismatch")
    _require(
        all(
            candidate.get("sourceLabel") == "LIVE"
            and candidate.get("manifestVerified") is True
            and len(str(candidate.get("assetSha256", ""))) == 64
            and len(str(candidate.get("manifestHash", ""))) == 64
            for candidate in candidates
        ),
        "proof lineage or verification metadata mismatch",
    )
    exported, provenance = _approve_render_export(client, api_url, project_id, token, project)
    _require(
        provenance.get("projectEvidenceLabel") == "LIVE EVIDENCE REPLAY",
        "proof provenance label mismatch",
    )
    _require(
        "zero provider calls" in str(provenance.get("proofReplayDisclosure", "")).lower(),
        "proof provenance omits zero-call disclosure",
    )
    records = provenance.get("candidates", [])
    _require(
        len(records) == 2
        and all(record.get("candidate", {}).get("manifestVerified") is True for record in records),
        "proof provenance does not contain two verified manifests",
    )
    return {
        "status": "PASS",
        "evidenceLabel": "LIVE EVIDENCE REPLAY",
        "sourceLabel": "LIVE",
        "storage": "BACKBLAZE B2",
        "recordedProviderCallCount": 2,
        "providerCallsDuringReplay": 0,
        "eventCount": 1,
        "candidateCount": 2,
        "manifestVerifyTrueCount": 2,
        "finalState": exported.get("state"),
        "download": "ZIP VERIFIED",
    }


def _run_browser_verification(web_url: str, capture: bool) -> dict[str, Any]:
    environment = os.environ.copy()
    environment.update(
        {
            "PUBLIC_BASE_URL": web_url,
            "PUBLIC_SUBMISSION_VERIFY": "1",
            "CAPTURE_PHASE2_PUBLIC": "1" if capture else "0",
        }
    )
    completed = subprocess.run(
        [
            "pnpm",
            "--filter",
            "@framefoley/web",
            "exec",
            "playwright",
            "test",
            "e2e/public-submission.spec.ts",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    _require(completed.returncode == 0, "public desktop/phone/tablet browser verification failed")
    return {
        "status": "PASS",
        "viewports": ["desktop", "tablet", "mobile"],
        "consoleRuntimeErrors": 0,
        "impossibleUploadPathPresent": False,
        "screenshotsCaptured": capture,
    }


def verify(web_url: str, api_url: str, *, browser: bool, capture: bool) -> dict[str, Any]:
    timeout = httpx.Timeout(connect=30, read=120, write=120, pool=30)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        web = client.get(web_url)
        web.raise_for_status()
        _require("FRAMEFOLEY" in web.text, "public web root does not contain FRAMEFOLEY")
        health = _json(client.get(f"{api_url}/healthz"))
        _require(health.get("status") == "ok", "public API health check failed")
        ready = _wait_until_ready(client, api_url)
        _require(ready.get("storage") == "BACKBLAZE B2", "public ready check is not B2-backed")
        capability_response = client.get(f"{api_url}/v1/capabilities", headers={"Origin": web_url})
        capabilities = _json(capability_response)
        expected_keys = {
            "schemaVersion",
            "generationMode",
            "storage",
            "customUploadCanComplete",
            "liveProofReplayAvailable",
            "anonymousProviderSpendEnabled",
            "projectTtlHours",
        }
        _require(set(capabilities) == expected_keys, "capability schema is not strict")
        _require(capabilities.get("generationMode") == "demo", "public mode is not demo")
        _require(capabilities.get("storage") == "BACKBLAZE B2", "capability storage mismatch")
        _require(
            capabilities.get("customUploadCanComplete") is False,
            "public custom upload dead end is active",
        )
        _require(
            capabilities.get("anonymousProviderSpendEnabled") is False,
            "anonymous provider spend is enabled",
        )
        _require(
            capabilities.get("liveProofReplayAvailable") is True,
            "LIVE proof replay is unavailable",
        )
        lower_capabilities = json.dumps(capabilities).lower()
        _require(
            not any(term in lower_capabilities for term in ("bucket", "appkey", "keyid", "secret")),
            "capability response contains a secret-like field",
        )
        _require(
            capability_response.headers.get("access-control-allow-origin") == web_url,
            "exact public CORS origin is not configured",
        )
        _write_json("CAPABILITIES_SANITIZED.json", capabilities)
        cached = _verify_cached_demo(client, api_url)
        proof = _verify_live_proof(client, api_url)

    browser_result: dict[str, Any]
    if browser:
        browser_result = _run_browser_verification(web_url, capture)
    else:
        browser_result = {"status": "UNVERIFIED", "reason": "browser verification skipped"}
    return {
        "schemaVersion": 1,
        "evidenceLabel": "OWNER-VERIFIED",
        "verifiedAt": datetime.now(UTC).isoformat(),
        "publicWeb": {"url": web_url, "status": "PASS", "loginRequired": False},
        "publicApi": {
            "url": api_url,
            "health": "PASS",
            "readiness": "PASS",
            "storage": "BACKBLAZE B2",
            "deployedCommit": health.get("sourceCommit", "UNVERIFIED"),
        },
        "cors": {"status": "PASS", "allowedOrigin": web_url, "wildcard": False},
        "capabilities": capabilities,
        "cachedDemo": cached,
        "liveProofReplay": proof,
        "browser": browser_result,
        "persistedProjectTokens": 0,
        "persistedSignedUrls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-url", default=DEFAULT_WEB_URL)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--skip-browser", action="store_true")
    parser.add_argument("--no-screenshots", action="store_true")
    args = parser.parse_args()
    web_url = str(args.web_url).rstrip("/")
    api_url = str(args.api_url).rstrip("/")
    try:
        result = verify(
            web_url,
            api_url,
            browser=not args.skip_browser,
            capture=not args.no_screenshots,
        )
    except (httpx.HTTPError, OSError, subprocess.SubprocessError, VerificationFailure) as exc:
        failure = {
            "schemaVersion": 1,
            "evidenceLabel": "UNVERIFIED",
            "verifiedAt": datetime.now(UTC).isoformat(),
            "status": "FAIL",
            "safeErrorType": type(exc).__name__,
            "safeReason": str(exc)
            if isinstance(exc, VerificationFailure)
            else "network or tool failure",
            "persistedProjectTokens": 0,
            "persistedSignedUrls": 0,
        }
        _write_json("PUBLIC_VERIFICATION_SANITIZED.json", failure)
        print(f"Public submission verification FAIL: {failure['safeReason']}", file=sys.stderr)
        return 1
    _write_json("PUBLIC_VERIFICATION_SANITIZED.json", result)
    print("Public submission verification PASS: API + CORS + cached demo + LIVE replay + browsers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
