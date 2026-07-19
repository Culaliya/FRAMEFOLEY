#!/bin/bash

set -Eeuo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

cd "$repo_root"

if [[ ! -x ".venv/bin/python" ]]; then
    printf 'ERROR: .venv is missing. Run `make install` first.\n' >&2
    exit 2
fi

cleanup() {
    unset B2_KEY_ID B2_APP_KEY B2_BUCKET B2_REGION ELEVENLABS_API_KEY
    unset FRAMEFOLEY_ALLOW_LIVE_CALLS
}

pause_for_owner() {
    if [[ -t 0 ]]; then
        IFS= read -r -p "$1" _owner_pause
        printf '\n'
    fi
}

on_error() {
    status="$?"
    printf '\nPhase 1 live gate stopped safely (exit code %s).\n' "$status" >&2
    printf 'The sanitized evidence records were not accepted as PASS.\n' >&2
    pause_for_owner 'Press Return when you are ready to close this session: '
    exit "$status"
}

trap cleanup EXIT
trap 'exit 130' INT TERM
trap on_error ERR

read_hidden() {
    prompt="$1"
    variable_name="$2"
    value=""
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
    prompt="$1"
    variable_name="$2"
    value=""
    while [[ -z "$value" ]]; do
        IFS= read -r -p "$prompt" value
        if [[ -z "$value" ]]; then
            printf 'Value cannot be empty. Please try again.\n' >&2
        fi
    done
    printf -v "$variable_name" '%s' "$value"
}

printf 'FRAMEFOLEY Phase 1 final-version LIVE gate\n'
printf 'Secrets are hidden while typing, stay process-local, and are never written to disk.\n'
printf 'This smoke uses one event: 2 initial ElevenLabs SFX candidates.\n'
printf 'Deterministic QC may authorize at most 1 retry for each candidate.\n\n'

read_hidden 'B2_KEY_ID: ' B2_KEY_ID
read_hidden 'B2_APP_KEY: ' B2_APP_KEY
read_required 'B2_BUCKET: ' B2_BUCKET
read_required 'B2_REGION: ' B2_REGION
read_hidden 'ELEVENLABS_API_KEY: ' ELEVENLABS_API_KEY

export B2_KEY_ID B2_APP_KEY B2_BUCKET B2_REGION ELEVENLABS_API_KEY

printf '\nB2 preflight runs before provider generation.\n'
printf 'Type RUN PHASE1 to authorize the bounded live smoke: '
IFS= read -r confirmation
if [[ "$confirmation" != "RUN PHASE1" ]]; then
    printf 'Live gate cancelled. No Phase 1 provider request was authorized.\n'
    pause_for_owner 'Press Return when you are ready to close this session: '
    exit 3
fi

export FRAMEFOLEY_ALLOW_LIVE_CALLS=1
make live-smoke
make secret-scan

printf '\nPhase 1 final-version LIVE gate completed.\n'
printf 'Sanitized evidence is in evidence/final/. No secret was persisted.\n'
pause_for_owner 'Press Return after you have read the result: '
