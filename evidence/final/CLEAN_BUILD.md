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

This proves the committed source itself is locally reproducible. Public clean
clone remains **UNVERIFIED** until owner-authorized repository publication.
Docker CLI is absent on this machine, so the two Dockerfiles and Compose file
are source-reviewed but container builds remain **UNVERIFIED** pending a
Docker-capable host.
