SHELL := /bin/bash

PYTHON_BIN ?= $(shell command -v python3.13 2>/dev/null || command -v python3.12 2>/dev/null || command -v python3.11 2>/dev/null || if test -x "$$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"; then printf '%s' "$$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"; else command -v python3 2>/dev/null; fi)
VENV_PYTHON := .venv/bin/python

.PHONY: install preflight test local-manifest b2-smoke live-sfx qc evidence format-check lint type contracts build browser-test secret-scan check live-smoke full-demo-generation api web

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

check: contracts format-check lint type test build secret-scan
