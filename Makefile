SHELL := /bin/bash

PYTHON_BIN ?= $(shell command -v python3.13 2>/dev/null || command -v python3.12 2>/dev/null || command -v python3.11 2>/dev/null || if test -x "$$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"; then printf '%s' "$$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"; else command -v python3 2>/dev/null; fi)
VENV_PYTHON := .venv/bin/python

.PHONY: install preflight test local-manifest b2-smoke live-sfx qc evidence format-check lint type contracts build browser-test secret-scan check live-smoke full-demo-generation paid-live-v2 landing-preview publish-live-proof phase2-proof-test verify-public phase2-evidence capture-phase2-video build-phase2-video api web

install:
	$(PYTHON_BIN) -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
	$(PYTHON_BIN) -m venv .venv
	$(VENV_PYTHON) -m pip install --require-hashes -r requirements.lock
	$(VENV_PYTHON) -m pip install --no-deps --no-build-isolation -e .
	pnpm install --frozen-lockfile

preflight:
	$(VENV_PYTHON) -m framefoley_spike.cli preflight

test:
	$(VENV_PYTHON) -m pytest -q
	pnpm test

local-manifest:
	$(VENV_PYTHON) -m framefoley_spike.cli local-manifest

b2-smoke:
	$(VENV_PYTHON) -m framefoley_spike.cli b2-smoke

live-sfx:
	$(VENV_PYTHON) -m framefoley_spike.cli live-sfx

qc:
	$(VENV_PYTHON) -m framefoley_spike.cli qc

evidence:
	$(VENV_PYTHON) -m framefoley_spike.cli evidence

format-check:
	$(VENV_PYTHON) -m ruff format --check src scripts tests services/api

lint:
	$(VENV_PYTHON) -m ruff check src scripts tests services/api
	pnpm lint

type:
	$(VENV_PYTHON) -m mypy
	pnpm typecheck

contracts:
	pnpm contracts:check

build:
	$(VENV_PYTHON) -m compileall -q src services/api/framefoley_api
	pnpm build

browser-test:
	pnpm test:e2e

secret-scan:
	$(VENV_PYTHON) scripts/secret_scan.py

api:
	$(VENV_PYTHON) -m framefoley_api.main

web:
	pnpm dev:web

live-smoke:
	@test "$$FRAMEFOLEY_ALLOW_LIVE_CALLS" = "1" || (echo "ERROR: set FRAMEFOLEY_ALLOW_LIVE_CALLS=1" >&2; exit 2)
	FRAMEFOLEY_STORAGE_MODE=b2 GENERATION_MODE=live LIVE_GENERATION_ENABLED=true $(VENV_PYTHON) scripts/phase1_live_gate.py --events 1

full-demo-generation:
	@test "$$FRAMEFOLEY_ALLOW_LIVE_CALLS" = "1" || (echo "ERROR: set FRAMEFOLEY_ALLOW_LIVE_CALLS=1" >&2; exit 2)
	FRAMEFOLEY_STORAGE_MODE=b2 GENERATION_MODE=live LIVE_GENERATION_ENABLED=true $(VENV_PYTHON) scripts/phase1_live_gate.py --events 3

paid-live-v2:
	@test "$$FRAMEFOLEY_ALLOW_LIVE_CALLS" = "1" || (echo "ERROR: set FRAMEFOLEY_ALLOW_LIVE_CALLS=1" >&2; exit 2)
	@test "$$FRAMEFOLEY_ALLOW_PROOF_PUBLISH" = "1" || (echo "ERROR: set FRAMEFOLEY_ALLOW_PROOF_PUBLISH=1" >&2; exit 2)
	@test "$$FRAMEFOLEY_OWNER_PAID_RIGHTS_CONFIRMED" = "1" || (echo "ERROR: set FRAMEFOLEY_OWNER_PAID_RIGHTS_CONFIRMED=1" >&2; exit 2)
	FRAMEFOLEY_STORAGE_MODE=b2 GENERATION_MODE=live LIVE_GENERATION_ENABLED=true $(VENV_PYTHON) scripts/phase1_live_gate.py --events 1 --evidence-dir evidence/paid-live-v2
	FRAMEFOLEY_STORAGE_MODE=b2 $(VENV_PYTHON) scripts/publish_live_proof.py --source-evidence evidence/paid-live-v2 --proof-version live-v2

landing-preview:
	$(VENV_PYTHON) scripts/build_landing_preview.py

publish-live-proof:
	@test "$$FRAMEFOLEY_ALLOW_PROOF_PUBLISH" = "1" || (echo "ERROR: set FRAMEFOLEY_ALLOW_PROOF_PUBLISH=1" >&2; exit 2)
	$(VENV_PYTHON) scripts/publish_live_proof.py

phase2-proof-test:
	$(VENV_PYTHON) -m pytest -q services/api/tests/test_phase2.py tests/test_phase2_copy.py
	pnpm --filter @framefoley/web exec vitest run lib/readiness.test.ts lib/api.test.ts

verify-public:
	$(VENV_PYTHON) scripts/verify_public_submission.py

phase2-evidence:
	$(VENV_PYTHON) scripts/build_phase2_evidence.py

capture-phase2-video:
	@test "$$FRAMEFOLEY_ALLOW_PUBLIC_CAPTURE" = "1" || (echo "ERROR: set FRAMEFOLEY_ALLOW_PUBLIC_CAPTURE=1" >&2; exit 2)
	PUBLIC_BASE_URL=https://framefoley-culaliya.onrender.com PUBLIC_SUBMISSION_VERIFY=1 CAPTURE_PHASE2_MASTER=1 pnpm --filter @framefoley/web exec playwright test e2e/phase2-video.spec.ts --project=desktop --workers=1

build-phase2-video:
	$(VENV_PYTHON) scripts/build_phase2_video.py

check: contracts format-check lint type test build secret-scan
