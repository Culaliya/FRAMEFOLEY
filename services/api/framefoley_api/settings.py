"""Environment-backed API settings without secret logging."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

GenerationMode = Literal["live", "demo", "disabled"]
StorageMode = Literal["local", "b2"]


def _boolean(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _integer(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = int(raw)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    data_dir: Path
    generation_mode: GenerationMode
    storage_mode: StorageMode
    live_generation_enabled: bool
    hmac_secret: str
    project_ttl_hours: int
    max_concurrent_generation: int
    project_retry_budget: int
    frontend_origin: str
    b2_key_id: str | None
    b2_app_key: str | None
    b2_bucket: str | None
    b2_region: str | None
    elevenlabs_api_key: str | None

    @classmethod
    def from_env(cls) -> Settings:
        repo_root = Path(__file__).resolve().parents[3]
        data_setting = Path(os.getenv("FRAMEFOLEY_DATA_DIR", ".data"))
        data_dir = data_setting if data_setting.is_absolute() else repo_root / data_setting
        generation_mode = os.getenv("GENERATION_MODE", "demo").strip().lower()
        if generation_mode not in {"live", "demo", "disabled"}:
            raise ValueError("GENERATION_MODE must be live, demo, or disabled")
        storage_mode = os.getenv("FRAMEFOLEY_STORAGE_MODE", "local").strip().lower()
        if storage_mode not in {"local", "b2"}:
            raise ValueError("FRAMEFOLEY_STORAGE_MODE must be local or b2")
        environment = os.getenv("FRAMEFOLEY_ENV", "development").strip().lower()
        default_secret = "framefoley-development-only-secret"
        hmac_secret = os.getenv("FRAMEFOLEY_HMAC_SECRET", default_secret)
        if environment == "production" and hmac_secret == default_secret:
            raise ValueError("FRAMEFOLEY_HMAC_SECRET is required in production")
        return cls(
            repo_root=repo_root,
            data_dir=data_dir.resolve(),
            generation_mode=cast(GenerationMode, generation_mode),
            storage_mode=cast(StorageMode, storage_mode),
            live_generation_enabled=_boolean("LIVE_GENERATION_ENABLED", False),
            hmac_secret=hmac_secret,
            project_ttl_hours=_integer("FRAMEFOLEY_PROJECT_TTL_HOURS", 72, minimum=1, maximum=720),
            max_concurrent_generation=_integer(
                "FRAMEFOLEY_MAX_CONCURRENT_GENERATION", 1, minimum=1, maximum=4
            ),
            project_retry_budget=_integer(
                "FRAMEFOLEY_PROJECT_RETRY_BUDGET", 2, minimum=0, maximum=6
            ),
            frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
            b2_key_id=os.getenv("B2_KEY_ID") or None,
            b2_app_key=os.getenv("B2_APP_KEY") or None,
            b2_bucket=os.getenv("B2_BUCKET") or None,
            b2_region=os.getenv("B2_REGION") or None,
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY") or None,
        )

    def require_b2(self) -> None:
        missing = [
            name
            for name, value in (
                ("B2_KEY_ID", self.b2_key_id),
                ("B2_APP_KEY", self.b2_app_key),
                ("B2_BUCKET", self.b2_bucket),
                ("B2_REGION", self.b2_region),
            )
            if not value
        ]
        if missing:
            raise ValueError("B2 storage configuration missing: " + ", ".join(missing))

    def require_live(self) -> None:
        if self.generation_mode != "live" or not self.live_generation_enabled:
            raise ValueError("live generation is disabled")
        if self.storage_mode != "b2":
            raise ValueError("live generation requires B2 storage mode")
        self.require_b2()
        if not self.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY is required for live generation")
