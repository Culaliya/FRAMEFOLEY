# Clean build evidence

Status: **PASS — LOCAL CLEAN-COPY**

A new source-only temporary directory was created without `.venv`,
`node_modules`, `.next`, `.data`, caches, browser reports, or final evidence.
The following commands completed from that directory:

```text
make install       PASS
make check         PASS
make browser-test  PASS
```

Verified inside the clean copy:

- Python 3.12 bootstrap and hash-locked `requirements.lock` install;
- frozen pnpm lock install with the explicit native-build allowlist;
- generated JSON Schema/TypeScript contract match;
- Ruff format/lint across `src`, `scripts`, `tests`, and `services/api`;
- mypy strict and TypeScript checks;
- 38 Python tests and 10 web unit tests;
- Python bytecode compile and Next production build;
- source/evidence secret scan;
- 5 browser checks across desktop/tablet/phone, with 0 failures and no console
  errors.

The source directory is not yet a git repository, so this proves a clean source
copy rather than a public clean clone. Docker CLI is absent on this machine, so
the two Dockerfiles and Compose file are source-reviewed but container builds
remain **UNVERIFIED** pending a Docker-capable host.
