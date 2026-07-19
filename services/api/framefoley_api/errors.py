"""Typed, sanitized public API failures."""

from __future__ import annotations

from dataclasses import dataclass

from framefoley_spike.provenance import sanitize_text


@dataclass
class PublicError(Exception):
    code: str
    message: str
    retryable: bool = False
    status_code: int = 400

    def __post_init__(self) -> None:
        self.message = sanitize_text(self.message)[:240]
        super().__init__(self.message)
