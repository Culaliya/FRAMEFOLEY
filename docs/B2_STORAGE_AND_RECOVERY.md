# B2 storage and recovery

## Production role

Backblaze B2 is the private, durable production system of record. Local object
storage is a development/test adapter labeled `MOCKED LOCAL STORAGE`; it is not
deployment evidence.

Every project is isolated under:

```text
framefoley/v1/projects/{project_id}/
```

## Object layout

```text
project.json
source/original.* or incoming/source-*
source/preview.mp4
source/thumbnail.webp
source/source-metadata.json
events/{event_id}/event.json
events/{event_id}/candidates/{candidate_id}/
  raw-audio.*
  approved-audio.wav
  approved-audio.ogg
  waveform.png
  qc-before.json
  qc-after.json
  derivative.json
approved/{event_slug}.wav
approved/{event_slug}.ogg
approved/{event_slug}.json
genblaze/runs/.../manifest.json
genblaze/runs/.../{provider_asset}
render/mixed-preview.mp4
render/mix-map.json
export/framefoley-{project_slug}.zip
provenance/index.json
provenance/index.html
```

Cached demo candidates use `cache-manifest.json`, explicitly non-canonical.
Canonical Genblaze objects stay unmodified under their hierarchical subtree.

## Restart recovery

The API writes a schema v1 `project.json` after every material state/candidate
change. On load it validates JSON, version, shared schema, and Pydantic model.
Malformed or future-version state returns `PROJECT_RECOVERY_FAILED`; the API
does not guess migrations. Integration tests create a project, destroy the app
instance, start a new instance against the same store, and recover the source
hash and state.

## Access model

- B2 credentials exist only in API environment variables.
- A project HMAC token is scoped to exactly one project ID and expiry.
- Short-lived object tokens embed an already validated object key.
- Canonical provenance stores object keys/URIs, never signed query strings.
- Browser upload uses a short-lived project object token in the local/API path.
  A deployment may replace this with B2 presigning only after verifying the same
  prefix and redaction guarantees.

## Anonymous lifecycle policy

The app default project expiry is 72 hours. Production should configure a B2
lifecycle rule to hide/delete `framefoley/v1/projects/` objects after the chosen
anonymous retention period, with a short recovery window if desired. This rule
is **OWNER-VERIFIED** only after it is visible in the B2 bucket configuration;
source code cannot prove the external rule is active.

Recommended owner setting:

```text
anonymous project objects: hide after 3 days, permanently delete after 7 days
```

Do not claim this retention policy publicly until the bucket rule is enabled and
captured without account-identifying information.
