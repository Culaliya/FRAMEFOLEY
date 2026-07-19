"""Secret-safe environment configuration for the Phase 0 spike."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version

B2_ENV_NAMES = ("B2_KEY_ID", "B2_APP_KEY", "B2_BUCKET", "B2_REGION")
LIVE_ENV_NAMES = (*B2_ENV_NAMES, "ELEVENLABS_API_KEY")
PACKAGE_NAMES = ("genblaze-core", "genblaze-s3", "genblaze-elevenlabs")


class ConfigError(RuntimeError):
    """Configuration failure that carries names, never secret values."""

    def __init__(self, code: str, missing: tuple[str, ...]) -> None:
        self.code = code
        self.missing = missing
        joined = ", ".join(missing)
        super().__init__(f"{code}: missing required environment variables: {joined}")


@dataclass(frozen=True, repr=False)
class SpikeConfig:
    """Owner-supplied configuration. Repr is disabled to prevent accidental leaks."""

    b2_key_id: str | None
    b2_app_key: str | None
    b2_bucket: str | None
    b2_region: str | None
    elevenlabs_api_key: str | None

    @classmethod
    def from_env(cls) -> SpikeConfig:
        return cls(
            b2_key_id=os.getenv("B2_KEY_ID") or None,
            b2_app_key=os.getenv("B2_APP_KEY") or None,
            b2_bucket=os.getenv("B2_BUCKET") or None,
            b2_region=os.getenv("B2_REGION") or None,
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY") or None,
        )

    def presence(self) -> dict[str, bool]:
        return {
            "B2_KEY_ID": bool(self.b2_key_id),
            "B2_APP_KEY": bool(self.b2_app_key),
            "B2_BUCKET": bool(self.b2_bucket),
            "B2_REGION": bool(self.b2_region),
            "ELEVENLABS_API_KEY": bool(self.elevenlabs_api_key),
        }

    def missing_b2(self) -> tuple[str, ...]:
        present = self.presence()
        return tuple(name for name in B2_ENV_NAMES if not present[name])

    def missing_live(self) -> tuple[str, ...]:
        present = self.presence()
        return tuple(name for name in LIVE_ENV_NAMES if not present[name])

    def require_b2(self) -> None:
        missing = self.missing_b2()
        if missing:
            raise ConfigError("b2_configuration_incomplete", missing)

    def require_live(self) -> None:
        missing = self.missing_live()
        if missing:
            raise ConfigError("live_configuration_incomplete", missing)


def resolved_package_versions() -> dict[str, str]:
    """Return exact resolved versions without importing provider clients."""

    resolved: dict[str, str] = {}
    for package in PACKAGE_NAMES:
        try:
            resolved[package] = version(package)
        except PackageNotFoundError:
            resolved[package] = "not-installed"
    return resolved


def ffmpeg_version() -> str:
    executable = shutil.which("ffmpeg")
    if executable is None:
        return "not-installed"
    completed = subprocess.run(
        [executable, "-version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    first_line = completed.stdout.splitlines()[0] if completed.stdout else "unavailable"
    return first_line.strip()


def preflight_lines(config: SpikeConfig) -> list[str]:
    """The deliberately bounded, secret-free preflight output."""

    presence = config.presence()
    versions = resolved_package_versions()
    b2_credentials_present = presence["B2_KEY_ID"] and presence["B2_APP_KEY"]
    ffmpeg_available = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
    return [
        f"B2 credentials present: {'yes' if b2_credentials_present else 'no'}",
        f"B2 bucket configured: {'yes' if presence['B2_BUCKET'] else 'no'}",
        f"B2 region configured: {'yes' if presence['B2_REGION'] else 'no'}",
        f"ElevenLabs key present: {'yes' if presence['ELEVENLABS_API_KEY'] else 'no'}",
        f"ffmpeg available: {'yes' if ffmpeg_available else 'no'}",
        f"Python version: {platform.python_version()}",
        "resolved package versions: "
        + ", ".join(f"{name}={value}" for name, value in versions.items()),
    ]
