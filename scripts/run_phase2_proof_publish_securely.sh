#!/usr/bin/env bash
set -euo pipefail

FRAMEFOLEY_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEFOLEY_REPO_DIR="$(cd "${FRAMEFOLEY_SCRIPT_DIR}/.." && pwd)"
cd "${FRAMEFOLEY_REPO_DIR}"

printf 'FRAMEFOLEY Phase 2 immutable proof publication\n'
printf 'Scope: B2 read + immutable proof/live/v1 write; ElevenLabs calls: 0\n\n'

read -r -p 'B2_KEY_ID: ' FRAMEFOLEY_INPUT_B2_KEY_ID
read -r -s -p 'B2_APP_KEY (hidden): ' FRAMEFOLEY_INPUT_B2_APP_KEY
printf '\n'
read -r -p 'B2_BUCKET: ' FRAMEFOLEY_INPUT_B2_BUCKET
read -r -p 'B2_REGION: ' FRAMEFOLEY_INPUT_B2_REGION

if [[ -z "${FRAMEFOLEY_INPUT_B2_KEY_ID}" || -z "${FRAMEFOLEY_INPUT_B2_APP_KEY}" || -z "${FRAMEFOLEY_INPUT_B2_BUCKET}" || -z "${FRAMEFOLEY_INPUT_B2_REGION}" ]]; then
  printf 'Stopped: all four B2 values are required.\n' >&2
  exit 2
fi

printf '\nThis command makes zero provider calls. Type RUN PHASE2 PROOF to continue: '
read -r FRAMEFOLEY_CONFIRMATION
if [[ "${FRAMEFOLEY_CONFIRMATION}" != "RUN PHASE2 PROOF" ]]; then
  printf 'Stopped safely: confirmation did not match.\n' >&2
  exit 2
fi

export B2_KEY_ID="${FRAMEFOLEY_INPUT_B2_KEY_ID}"
export B2_APP_KEY="${FRAMEFOLEY_INPUT_B2_APP_KEY}"
export B2_BUCKET="${FRAMEFOLEY_INPUT_B2_BUCKET}"
export B2_REGION="${FRAMEFOLEY_INPUT_B2_REGION}"
export FRAMEFOLEY_STORAGE_MODE=b2
export FRAMEFOLEY_ALLOW_PROOF_PUBLISH=1

cleanup_phase2_inputs() {
  unset B2_KEY_ID B2_APP_KEY B2_BUCKET B2_REGION FRAMEFOLEY_ALLOW_PROOF_PUBLISH
  unset FRAMEFOLEY_INPUT_B2_KEY_ID FRAMEFOLEY_INPUT_B2_APP_KEY
  unset FRAMEFOLEY_INPUT_B2_BUCKET FRAMEFOLEY_INPUT_B2_REGION FRAMEFOLEY_CONFIRMATION
}
trap cleanup_phase2_inputs EXIT

make publish-live-proof
make secret-scan
printf 'Phase 2 proof publication and secret scan completed.\n'
