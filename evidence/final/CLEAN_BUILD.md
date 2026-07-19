# Clean build evidence

Status: **PASS — LOCAL CLEAN CLONE**

A fresh clone of implementation commit
`7acd9e687626824ae62865b66d1fa6ef848132fd` was created without `.venv`,
`node_modules`, `.next`, `.data`, caches, or browser reports. The following
commands completed from that clone:

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

This proves the implementation commit itself is locally reproducible. The
repository is now public at <https://github.com/Culaliya/FRAMEFOLEY>.

The final deployed code commit
`4a4d994eeaa07507d4da8189b92ac2f14c4ba586` adds the container-root repair and
B2 display-label regression test. The working tree passed `make check` (40
Python tests and 10 web tests) and `make browser-test` (5 passed) after those
changes. A second fresh-clone run at that exact commit was not performed.

Local Docker CLI remains unavailable, but both production Dockerfiles built and
started successfully on Render Free at the deployed commit. Public health,
readiness, B2-backed demo, render, export, and provenance checks then passed.
