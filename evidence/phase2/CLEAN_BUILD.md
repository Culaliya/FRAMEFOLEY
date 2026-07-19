# Clean-clone install

Evidence label: **OWNER-VERIFIED**
Status: **PASS**
Source commit: `8f5a8efc0f4b3f60395f97bcc415be3d109f9966`

A temporary no-hardlinks clone ran `make install`. Python used
`requirements.lock --require-hashes`; pnpm used `--frozen-lockfile`.
The temporary checkout and its dependency cache were not added to evidence.
