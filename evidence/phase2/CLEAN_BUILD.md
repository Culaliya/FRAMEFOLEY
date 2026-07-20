# Clean-clone install

Evidence label: **OWNER-VERIFIED**
Status: **PASS**
Source commit: `284f9270cea80a567832c0309ee78b4c99708b9a`

A temporary no-hardlinks clone ran `make install`. Python used
`requirements.lock --require-hashes`; pnpm used `--frozen-lockfile`.
The temporary checkout and its dependency cache were not added to evidence.
