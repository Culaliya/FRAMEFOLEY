"""Deterministic, bounded SFX prompt construction."""

from __future__ import annotations

import unicodedata

from framefoley_api.errors import PublicError
from framefoley_api.models import SoundEvent, StyleProfile

STYLE_PRESETS: dict[str, tuple[str, str]] = {
    "lunar_arcade": (
        "LUNAR ARCADE",
        "Luminous, tactile, playful, slightly glassy. Dry close perspective. Clear transients.",
    ),
    "rubber_dungeon": (
        "RUBBER DUNGEON",
        "Squishy, warm, tactile, comic. Soft weight, close room, no giant tail.",
    ),
    "rust_bloom": (
        "RUST BLOOM",
        "Dry metal, dusty mechanisms, restrained weight. Mechanical detail without "
        "trailer-scale impact.",
    ),
    "paper_signal": (
        "PAPER SIGNAL",
        "Papery, wooden, handmade, soft transient. Small-room intimacy and readable motion.",
    ),
}

VARIANT_MODIFIERS = {
    "clean": "Clean, compact, readable, minimal tail.",
    "character": "More character and texture, slightly elastic, controlled tail.",
}

EVENT_WINDOWS = {
    "ui": (0.08, 0.80),
    "impact": (0.15, 1.50),
    "creature": (0.25, 2.50),
    "ambience": (3.00, 8.00),
}

RETRY_INSTRUCTIONS = {
    "effectively_silent": "Regenerate with an immediate audible onset and clear energy.",
    "duration_outside_spike_window": "Regenerate tightly inside the requested duration.",
    "decode_failed": "Regenerate as a standard decodable sound-effect file.",
    "repair_did_not_pass": "Regenerate with controlled level, short silence, and a compact tail.",
}


def normalize_custom_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip()
    if any(unicodedata.category(character).startswith("C") for character in normalized):
        raise PublicError(
            "CUSTOM_TEXT_INVALID",
            "Custom text cannot contain control or invisible formatting characters.",
            status_code=422,
        )
    if len(normalized) > 180:
        raise PublicError(
            "CUSTOM_TEXT_TOO_LONG", "Custom text is limited to 180 characters.", status_code=422
        )
    return normalized or None


def normalize_style(style: StyleProfile) -> StyleProfile:
    if style.id == "custom":
        custom = normalize_custom_text(style.custom_text)
        if not custom:
            raise PublicError(
                "CUSTOM_STYLE_REQUIRED",
                "Custom style requires a short description.",
                status_code=422,
            )
        return StyleProfile(
            id="custom",
            title="CUSTOM",
            prompt_prefix="User-provided bounded style note.",
            custom_text=custom,
        )
    title, prompt_prefix = STYLE_PRESETS[str(style.id)]
    return StyleProfile(id=style.id, title=title, prompt_prefix=prompt_prefix)


def validate_event_target(event: SoundEvent) -> None:
    minimum, maximum = EVENT_WINDOWS[str(event.type)]
    if not minimum <= event.target_duration_seconds <= maximum:
        raise PublicError(
            "EVENT_DURATION_INVALID",
            f"{event.type} target duration must be between "
            f"{minimum:.2f} and {maximum:.2f} seconds.",
            status_code=422,
        )


def build_prompt(
    event: SoundEvent,
    style: StyleProfile,
    variant: str,
    *,
    retry_reason: str | None = None,
) -> str:
    validate_event_target(event)
    if variant not in VARIANT_MODIFIERS:
        raise ValueError("unsupported candidate variant")
    material = normalize_custom_text(event.material_note)
    event_line = f"{event.title}. Type: {event.type}. Intensity: {event.intensity}."
    if material:
        event_line += f" Material note: {material}"
    style_line = style.prompt_prefix
    if style.custom_text:
        style_line += f" Custom note: {normalize_custom_text(style.custom_text)}"
    retry_line = ""
    if retry_reason:
        instruction = RETRY_INSTRUCTIONS.get(
            retry_reason, RETRY_INSTRUCTIONS["repair_did_not_pass"]
        )
        retry_line = (
            f"\n[CONTROLLED RETRY]\nPrevious technical result: {retry_reason}. {instruction}"
        )
    return (
        f"[EVENT]\n{event_line}\n\n"
        f"[STYLE]\n{style_line}\n\n"
        f"[VARIANT]\n{VARIANT_MODIFIERS[variant]}\n\n"
        "[CONSTRAINTS]\n"
        "Sound effect only. No speech. No music. No cinematic trailer boom. "
        f"Target duration: {event.target_duration_seconds:.2f} seconds."
        f"{retry_line}"
    )
