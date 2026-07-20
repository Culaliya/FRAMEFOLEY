# Clean-clone install

Evidence label: **OWNER-VERIFIED**
Status: **PASS**
Source commit: `f6d3ba3dc8e1dcd17a4c70d556c7e00f9f0aff25`

A temporary no-hardlinks clone ran `make install`. Python used
`requirements.lock --require-hashes`; pnpm used `--frozen-lockfile`.
The temporary checkout and its dependency cache were not added to evidence.
