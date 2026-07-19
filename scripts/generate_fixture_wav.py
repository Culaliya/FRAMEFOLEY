"""Generate FRAMEFOLEY's deterministic original Phase 0 WAV fixture."""

from __future__ import annotations

import argparse
from pathlib import Path

from framefoley_spike.fixture import generate_fixture


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", default="artifacts/phase0/work/fixture.wav")
    args = parser.parse_args()
    generate_fixture(Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
