#!/bin/bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODE="${1:-run}"

if [[ "$MODE" != "run" && "$MODE" != "--validate-only" ]]; then
    printf 'Usage: %s [--validate-only]\n' "$0" >&2
    exit 64
fi

cd "$REPO_ROOT"

if [[ ! -x ".venv/bin/python" ]]; then
    printf 'ERROR: .venv is missing. Run `make install` first.\n' >&2
    exit 2
fi

cleanup() {
    unset B2_KEY_ID B2_APP_KEY B2_BUCKET B2_REGION ELEVENLABS_API_KEY
    unset FRAMEFOLEY_ALLOW_LIVE_CALL
}

pause_for_owner() {
    if [[ -t 0 ]]; then
        IFS= read -r -p "$1" _owner_pause
        printf '\n'
    fi
}

on_error() {
    local status="$?"
    printf '\nPhase 0 stopped before completion (exit code %s).\n' "$status" >&2
    printf 'No GO verdict was recorded. Leave this window open so the error above can be inspected.\n' >&2
    pause_for_owner 'Press Return when you are ready to close this session: '
    exit "$status"
}

trap cleanup EXIT
trap 'exit 130' INT TERM
trap on_error ERR

read_hidden() {
    local prompt="$1"
    local variable_name="$2"
    local value=""

    while [[ -z "$value" ]]; do
        IFS= read -r -s -p "$prompt" value
        printf '\n'
        if [[ -z "$value" ]]; then
            printf 'Value cannot be empty. Please try again.\n' >&2
        fi
    done

    printf -v "$variable_name" '%s' "$value"
}

read_required() {
    local prompt="$1"
    local variable_name="$2"
    local value=""

    while [[ -z "$value" ]]; do
        IFS= read -r -p "$prompt" value
        if [[ -z "$value" ]]; then
            printf 'Value cannot be empty. Please try again.\n' >&2
        fi
    done

    printf -v "$variable_name" '%s' "$value"
}

printf 'FRAMEFOLEY Phase 0 secure credential session\n'
printf 'Secrets are hidden while typing and are not written to disk.\n\n'

read_hidden 'B2_KEY_ID: ' B2_KEY_ID
read_hidden 'B2_APP_KEY: ' B2_APP_KEY
read_required 'B2_BUCKET: ' B2_BUCKET
read_required 'B2_REGION: ' B2_REGION
read_hidden 'ELEVENLABS_API_KEY: ' ELEVENLABS_API_KEY

export B2_KEY_ID B2_APP_KEY B2_BUCKET B2_REGION ELEVENLABS_API_KEY

printf '\nRunning secret-safe preflight...\n'
make preflight

if [[ "$MODE" == "--validate-only" ]]; then
    printf '\nValidation-only mode complete; no external calls were made.\n'
    exit 0
fi

printf '\nRunning the B2 write/read/re-hash smoke before any paid provider call...\n'
make b2-smoke

printf '\nOne 0.8-second ElevenLabs Sound Effects call will now be authorized.\n'
printf 'Its output and all generated derivatives must be uploaded to B2.\n'
printf 'A free account may reject the Sound Effects API; if accepted, account credits will be used.\n'
printf 'No payment card can be charged when none is attached.\n'
IFS= read -r -p 'Type RUN to execute the live Phase 0 call: ' live_confirmation

if [[ "$live_confirmation" != "RUN" ]]; then
    printf 'Live call cancelled. No ElevenLabs request was made.\n'
    pause_for_owner 'Press Return when you are ready to close this session: '
    exit 3
fi

export FRAMEFOLEY_ALLOW_LIVE_CALL=1

make live-sfx
make check

printf '\nPhase 0 live run and verification commands completed.\n'
printf 'Review docs/SPIKE_REPORT.md for the generated verdict.\n'
pause_for_owner 'Press Return after you have read the result: '
