# Third-party notices

Recorded: 2026-07-20 (Asia/Taipei)

FRAMEFOLEY's original media and visual assets are documented in
`docs/ASSET_PROVENANCE.md`. This file records the dependency notices that are
most relevant to the public competition repository. It is not a replacement
for each package's complete license text.

## Direct runtime dependencies

| Package | Pinned version | Declared license |
| --- | --- | --- |
| Next.js | `16.2.10` | MIT |
| React / React DOM | `19.2.7` | MIT |
| Lucide React | `1.25.0` | ISC, with specified Feather-derived icons under MIT |
| FastAPI | `0.139.2` | MIT |
| Genblaze Core | `0.3.4` | MIT |
| Genblaze ElevenLabs adapter | `0.3.1` | MIT |
| Genblaze S3 adapter | `0.3.4` | MIT |
| jsonschema | `4.26.0` | MIT |
| Pillow | `12.3.0` | MIT-CMU |
| python-multipart | `0.0.32` | Apache-2.0 |
| Uvicorn | `0.51.0` | BSD-3-Clause |

The Lucide package retains this notice in its installed `LICENSE` file:
copyright (c) 2026 Lucide Icons and Contributors. Icons identified by Lucide as
Feather-derived retain the Feather MIT notice, copyright (c) 2013-present Cole
Bemis. See <https://lucide.dev/license>.

## Notable transitive terms

- `caniuse-lite@1.0.30001806` declares CC-BY-4.0. Browser-support data is from
  the Can I Use project; see <https://github.com/browserslist/caniuse-lite> and
  <https://creativecommons.org/licenses/by/4.0/>.
- the Sharp/libvips platform package declares LGPL-3.0-or-later for libvips;
  Sharp itself declares Apache-2.0. See <https://sharp.pixelplumbing.com/license/>.
- Python's `certifi==2026.6.17` and `pathspec==1.1.1` retain MPL-2.0 license
  files inside their installed distributions.

FRAMEFOLEY does not copy these dependencies' source into its own source files,
remove their package license files, or claim ownership of them.

## Reproducible inventory

The checked-in lockfiles are the package identity source of truth. After the
locked install, the following commands reproduce the local metadata review:

```bash
pnpm licenses list --prod --json

.venv/bin/python - <<'PY'
from importlib.metadata import distributions

for dist in sorted(distributions(), key=lambda item: (item.metadata.get("Name") or "").lower()):
    name = dist.metadata.get("Name") or ""
    expression = dist.metadata.get("License-Expression") or ""
    license_text = dist.metadata.get("License") or ""
    classifiers = [
        value.removeprefix("License :: ")
        for value in (dist.metadata.get_all("Classifier") or [])
        if value.startswith("License :: ")
    ]
    print(name, dist.version, expression or license_text or " | ".join(classifiers), sep="\t")
PY
```

The 2026-07-20 conservative installed-environment review found 62 Node
package/version entries and 67 non-project Python distributions. Every entry
reported license metadata; no GPL or AGPL dependency was reported. LGPL,
MPL-2.0, and CC-BY-4.0 entries are called out above rather than being collapsed
into a generic "open source" claim.
