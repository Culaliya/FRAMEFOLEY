"""HMAC project and object tokens with strict project-prefix isolation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, cast

from framefoley_api.errors import PublicError


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    decoded = base64.urlsafe_b64decode(value + padding)
    if _encode(decoded) != value:
        raise ValueError("non-canonical base64url encoding")
    return decoded


@dataclass(frozen=True)
class TokenSigner:
    secret: bytes

    @classmethod
    def from_secret(cls, secret: str) -> TokenSigner:
        if len(secret) < 16:
            raise ValueError("HMAC secret must contain at least 16 characters")
        return cls(secret.encode("utf-8"))

    def _sign(self, payload: dict[str, Any]) -> str:
        encoded_payload = _encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature = _encode(
            hmac.new(self.secret, encoded_payload.encode("ascii"), hashlib.sha256).digest()
        )
        return f"v1.{encoded_payload}.{signature}"

    def _verify(self, token: str, *, kind: str) -> dict[str, Any]:
        try:
            version, encoded_payload, encoded_signature = token.split(".", 2)
            if version != "v1":
                raise ValueError("unsupported version")
            expected = hmac.new(
                self.secret, encoded_payload.encode("ascii"), hashlib.sha256
            ).digest()
            actual = _decode(encoded_signature)
            if not hmac.compare_digest(expected, actual):
                raise ValueError("signature mismatch")
            raw_payload: object = json.loads(_decode(encoded_payload))
            if not isinstance(raw_payload, dict):
                raise ValueError("payload is not an object")
            payload = cast(dict[str, Any], raw_payload)
            if payload.get("kind") != kind or int(payload["exp"]) < int(time.time()):
                raise ValueError("expired or wrong token kind")
            return payload
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PublicError(
                "PROJECT_TOKEN_INVALID",
                "Project access token is invalid or expired.",
                status_code=401,
            ) from exc

    def project_token(self, project_id: str, expires_at: int) -> str:
        return self._sign({"kind": "project", "projectId": project_id, "exp": expires_at})

    def verify_project_token(self, token: str, expected_project_id: str) -> None:
        payload = self._verify(token, kind="project")
        if payload.get("projectId") != expected_project_id:
            raise PublicError(
                "PROJECT_TOKEN_SCOPE",
                "Project token cannot access this project.",
                status_code=403,
            )

    def object_token(self, project_id: str, key: str, expires_at: int) -> str:
        expected_prefix = f"framefoley/v1/projects/{project_id}/"
        if not key.startswith(expected_prefix):
            raise ValueError("object key is outside the project prefix")
        return self._sign(
            {"kind": "object", "projectId": project_id, "key": key, "exp": expires_at}
        )

    def verify_object_token(self, token: str) -> tuple[str, str]:
        payload = self._verify(token, kind="object")
        project_id = str(payload["projectId"])
        key = str(payload["key"])
        if not key.startswith(f"framefoley/v1/projects/{project_id}/"):
            raise PublicError(
                "PROJECT_TOKEN_SCOPE",
                "Object token has an invalid project scope.",
                status_code=403,
            )
        return project_id, key
