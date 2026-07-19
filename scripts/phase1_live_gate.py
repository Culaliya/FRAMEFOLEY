"""Explicitly gated final-version Genblaze -> B2 live evidence runner."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from framefoley_api.main import create_app
from framefoley_api.settings import Settings
from framefoley_api.storage import B2ObjectStore

from framefoley_spike.provenance import sanitize_text


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _package_versions() -> dict[str, str]:
    names = (
        "fastapi",
        "genblaze-core",
        "genblaze-elevenlabs",
        "genblaze-s3",
        "elevenlabs",
    )
    return {name: importlib.metadata.version(name) for name in names}


def _hash_objects(store: B2ObjectStore, keys: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key in keys:
        data = store.get(key)
        records.append(
            {
                "key": key,
                "sha256": hashlib.sha256(data).hexdigest(),
                "sizeBytes": len(data),
            }
        )
    return records


def run(event_count: int) -> int:
    if os.getenv("FRAMEFOLEY_ALLOW_LIVE_CALLS") != "1":
        print(
            "ERROR: set FRAMEFOLEY_ALLOW_LIVE_CALLS=1 to authorize this bounded live gate.",
            file=sys.stderr,
        )
        return 2

    settings = Settings.from_env()
    settings.require_live()
    evidence_root = settings.repo_root / "evidence" / "final"
    store = B2ObjectStore(settings)
    project_id = "UNAVAILABLE"
    try:
        with TestClient(create_app(settings, store=store)) as client:
            created = client.post("/v1/projects/demo")
            created.raise_for_status()
            creation = created.json()
            project_id = str(creation["projectId"])
            token = str(creation["projectToken"])

            snapshot = client.get(f"/v1/projects/{project_id}", headers=_headers(token)).json()[
                "project"
            ]
            selected_events = snapshot["events"][:event_count]
            queued = client.put(
                f"/v1/projects/{project_id}/events",
                headers=_headers(token),
                json={"style": snapshot["style"], "events": selected_events},
            )
            queued.raise_for_status()
            generated = client.post(
                f"/v1/projects/{project_id}/generate",
                headers={
                    **_headers(token),
                    "Idempotency-Key": f"phase1-live-gate-{event_count}-{project_id}",
                },
            )
            generated.raise_for_status()
            project = generated.json()["project"]

        candidates = [candidate for event in project["events"] for candidate in event["candidates"]]
        verified = [
            candidate
            for candidate in candidates
            if candidate["status"] == "ready"
            and candidate["sourceLabel"] == "LIVE"
            and candidate["manifestVerified"] is True
        ]
        prefix = f"framefoley/v1/projects/{project_id}/"
        keys = store.list_keys(prefix)
        now = datetime.now(UTC).isoformat()
        calls = {
            "schemaVersion": 1,
            "evidenceLabel": "LIVE",
            "recordedAt": now,
            "projectId": project_id,
            "requestedEventCount": event_count,
            "candidateCount": len(candidates),
            "providerCallCount": project["liveCallCount"],
            "readyVerifiedCandidateCount": len(verified),
            "provider": "elevenlabs-sfx",
            "model": "eleven_text_to_sound_v2",
            "actualCostUsd": round(
                sum(float(candidate.get("costUsd") or 0) for candidate in candidates), 8
            ),
            "costReporting": "provider-reported when available; zero is not a spend-cap claim",
            "packages": _package_versions(),
            "candidates": [
                {
                    "candidateId": candidate["id"],
                    "status": candidate["status"],
                    "sourceLabel": candidate["sourceLabel"],
                    "runId": candidate.get("genblazeRunId"),
                    "parentRunId": candidate.get("parentRunId"),
                    "manifestVerified": candidate["manifestVerified"],
                    "manifestHash": candidate.get("manifestHash"),
                    "assetSha256": candidate.get("assetSha256"),
                    "qcBefore": candidate.get("qcBefore", {}).get("verdict"),
                    "qcAfter": candidate.get("qcAfter", {}).get("verdict"),
                    "repairs": candidate.get("repairs", []),
                    "retryCount": candidate["retryCount"],
                    "startedAt": candidate.get("startedAt"),
                    "endedAt": candidate.get("endedAt"),
                    "latencySeconds": candidate.get("latencySeconds"),
                    "costUsd": candidate.get("costUsd"),
                    "error": candidate.get("error"),
                }
                for candidate in candidates
            ],
        }
        manifest_evidence = {
            "schemaVersion": 1,
            "evidenceLabel": "LIVE",
            "recordedAt": now,
            "projectId": project_id,
            "allReadyLiveCandidatesVerified": bool(verified)
            and all(candidate["manifestVerified"] for candidate in verified),
            "records": [
                {
                    "candidateId": candidate["id"],
                    "runId": candidate.get("genblazeRunId"),
                    "manifestObjectKey": candidate.get("manifestUri"),
                    "manifestCanonicalHash": candidate.get("manifestHash"),
                    "manifestVerifyReturned": candidate["manifestVerified"],
                }
                for candidate in candidates
            ],
        }
        object_map = {
            "schemaVersion": 1,
            "evidenceLabel": "LIVE",
            "recordedAt": now,
            "projectId": project_id,
            "prefix": prefix,
            "objectCount": len(keys),
            "objects": _hash_objects(store, keys),
        }
        _write_json(evidence_root / "LIVE_CALLS_SANITIZED.json", calls)
        _write_json(evidence_root / "MANIFEST_VERIFICATION.json", manifest_evidence)
        _write_json(evidence_root / "B2_OBJECT_MAP.json", object_map)

        if len(verified) < 1:
            print(
                f"LIVE gate failed safely: 0 verified candidates; calls={project['liveCallCount']}",
                file=sys.stderr,
            )
            return 1
        print(
            "LIVE gate PASS: "
            f"project={project_id} calls={project['liveCallCount']} "
            f"verified={len(verified)} b2Objects={len(keys)}"
        )
        return 0
    finally:
        store.backend.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, choices=(1, 3), required=True)
    args = parser.parse_args()
    try:
        return run(args.events)
    except Exception as exc:
        print(
            f"LIVE gate stopped safely: {type(exc).__name__}: {sanitize_text(str(exc))}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
