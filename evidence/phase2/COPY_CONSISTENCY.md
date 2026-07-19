# Copy consistency

Automated tests scan public UI and submission copy for contradictory labels.
The public vocabulary is `CACHED DEMO`, `LIVE EVIDENCE REPLAY`, and `LIVE`.
`MOCKED` is limited to tests/local development. Public copy does not call a
replay current live generation, call LIVE bytes cached, show PHASE 1, or expose
an active upload path when the capability contract says it cannot complete.
