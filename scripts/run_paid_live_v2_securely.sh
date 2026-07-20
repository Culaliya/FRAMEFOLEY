#!/usr/bin/env bash

set -Eeuo pipefail

FRAMEFOLEY_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEFOLEY_REPO_DIR="$(cd "${FRAMEFOLEY_SCRIPT_DIR}/.." && pwd)"
cd "${FRAMEFOLEY_REPO_DIR}"

if [[ ! -x ".venv/bin/python" ]]; then
  printf 'ERROR: .venv is missing. Run `make install` first.\n' >&2
  exit 2
fi

cleanup_paid_live_inputs() {
  unset B2_KEY_ID B2_APP_KEY B2_BUCKET B2_REGION ELEVENLABS_API_KEY
  unset FRAMEFOLEY_ALLOW_LIVE_CALLS FRAMEFOLEY_ALLOW_PROOF_PUBLISH
  unset FRAMEFOLEY_OWNER_PAID_RIGHTS_CONFIRMED
  unset FRAMEFOLEY_INPUT_B2_KEY_ID FRAMEFOLEY_INPUT_B2_APP_KEY
  unset FRAMEFOLEY_INPUT_B2_BUCKET FRAMEFOLEY_INPUT_B2_REGION
  unset FRAMEFOLEY_INPUT_ELEVENLABS_API_KEY FRAMEFOLEY_CONFIRMATION
  unset FRAMEFOLEY_PROMPT FRAMEFOLEY_VARIABLE_NAME FRAMEFOLEY_VALUE FRAMEFOLEY_STATUS
}

pause_for_owner() {
  if [[ -t 0 ]]; then
    IFS= read -r -p "$1" _owner_pause
    printf '\n'
  fi
}

on_error() {
  FRAMEFOLEY_STATUS="$?"
  printf '\nPaid LIVE v2 remediation stopped safely (exit code %s).\n' "${FRAMEFOLEY_STATUS}" >&2
  printf 'No partial result may be represented as verified proof v2.\n' >&2
  pause_for_owner 'Press Return when you are ready to close this session: '
  exit "${FRAMEFOLEY_STATUS}"
}

read_hidden() {
  FRAMEFOLEY_PROMPT="$1"
  FRAMEFOLEY_VARIABLE_NAME="$2"
  FRAMEFOLEY_VALUE=""
  while [[ -z "${FRAMEFOLEY_VALUE}" ]]; do
    IFS= read -r -s -p "${FRAMEFOLEY_PROMPT}" FRAMEFOLEY_VALUE
    printf '\n'
    if [[ -z "${FRAMEFOLEY_VALUE}" ]]; then
      printf 'Value cannot be empty. Please try again.\n' >&2
    fi
  done
  printf -v "${FRAMEFOLEY_VARIABLE_NAME}" '%s' "${FRAMEFOLEY_VALUE}"
  FRAMEFOLEY_VALUE=""
}

read_required() {
  FRAMEFOLEY_PROMPT="$1"
  FRAMEFOLEY_VARIABLE_NAME="$2"
  FRAMEFOLEY_VALUE=""
  while [[ -z "${FRAMEFOLEY_VALUE}" ]]; do
    IFS= read -r -p "${FRAMEFOLEY_PROMPT}" FRAMEFOLEY_VALUE
    if [[ -z "${FRAMEFOLEY_VALUE}" ]]; then
      printf 'Value cannot be empty. Please try again.\n' >&2
    fi
  done
  printf -v "${FRAMEFOLEY_VARIABLE_NAME}" '%s' "${FRAMEFOLEY_VALUE}"
  FRAMEFOLEY_VALUE=""
}

trap cleanup_paid_live_inputs EXIT
trap 'exit 130' INT TERM
trap on_error ERR

printf 'FRAMEFOLEY paid-plan LIVE proof v2 remediation\n'
printf 'Scope: one event, two initial ElevenLabs SFX candidates, B2 storage, immutable proof/live/v2.\n'
printf 'The existing proof/live/v1 prefix is read-only and will not be modified.\n'
printf 'Secrets stay process-local, are hidden where appropriate, and are never written to disk.\n\n'

read_hidden 'B2_KEY_ID: ' FRAMEFOLEY_INPUT_B2_KEY_ID
read_hidden 'B2_APP_KEY: ' FRAMEFOLEY_INPUT_B2_APP_KEY
read_required 'B2_BUCKET: ' FRAMEFOLEY_INPUT_B2_BUCKET
read_required 'B2_REGION: ' FRAMEFOLEY_INPUT_B2_REGION
read_hidden 'ELEVENLABS_API_KEY: ' FRAMEFOLEY_INPUT_ELEVENLABS_API_KEY

printf '\nOwner confirmation: Starter is active, applicable terms were accepted by the owner,\n'
printf 'and Sound Effects Explore sharing was disabled before this generation.\n'
printf 'Type RUN PAID LIVE V2 to authorize the bounded provider calls and proof publication: '
IFS= read -r FRAMEFOLEY_CONFIRMATION
if [[ "${FRAMEFOLEY_CONFIRMATION}" != "RUN PAID LIVE V2" ]]; then
  printf 'Stopped safely: confirmation did not match. No provider call was authorized.\n' >&2
  pause_for_owner 'Press Return when you are ready to close this session: '
  exit 3
fi

export B2_KEY_ID="${FRAMEFOLEY_INPUT_B2_KEY_ID}"
export B2_APP_KEY="${FRAMEFOLEY_INPUT_B2_APP_KEY}"
export B2_BUCKET="${FRAMEFOLEY_INPUT_B2_BUCKET}"
export B2_REGION="${FRAMEFOLEY_INPUT_B2_REGION}"
export ELEVENLABS_API_KEY="${FRAMEFOLEY_INPUT_ELEVENLABS_API_KEY}"
export FRAMEFOLEY_ALLOW_LIVE_CALLS=1
export FRAMEFOLEY_ALLOW_PROOF_PUBLISH=1
export FRAMEFOLEY_OWNER_PAID_RIGHTS_CONFIRMED=1

make paid-live-v2
make secret-scan

printf '\nPaid LIVE proof v2 completed and passed the no-secret scan.\n'
printf 'Sanitized source evidence: evidence/paid-live-v2/\n'
printf 'Immutable B2 prefix: framefoley/proof/live/v2/\n'
pause_for_owner 'Press Return after you have read the result: '
