# Owner setup for the Phase 0 live gate

Codex must not create these accounts, buckets, or keys. Complete the following
steps manually, keep the values outside the repository, and load them into the
terminal environment only when you are ready for the live smoke.

## 1. Backblaze B2

Official starting points:

- Account and B2 setup: <https://www.backblaze.com/sign-up/cloud-storage>
- B2 console: <https://secure.backblaze.com/b2_buckets.htm>
- Official integration setup: <https://www.backblaze.com/docs/cloud-storage-get-started-with-a-backblaze-integration>
- S3-compatible application-key rules: <https://www.backblaze.com/docs/cloud-storage-s3-compatible-app-keys>

### Create the private bucket

1. Sign in to Backblaze and enable **B2 Cloud Storage** if it is not enabled.
2. Open **B2 Cloud Storage → Buckets → Create a Bucket**.
3. Give it a globally unique name and set **Files in Bucket: Private**.
4. Do not enable public access. Record the bucket name and the S3 endpoint shown
   beside it.

Map the bucket fields as follows:

| Environment variable | Backblaze value |
| --- | --- |
| `B2_BUCKET` | Exact bucket name from the Buckets page |
| `B2_REGION` | Region slug inside the endpoint; for `s3.us-west-004.backblazeb2.com`, use `us-west-004` |

### Create the restricted application key

1. Open **B2 Cloud Storage → Application Keys → Add a New Application Key**.
2. Name it `framefoley-phase0`.
3. Restrict it to the private FRAMEFOLEY bucket.
4. Restrict the file-name prefix to `framefoley/`.
5. Grant read, write, and list access required for upload, HEAD/list, and
   download. Enable **Allow List All Bucket Names** for S3-compatible SDK
   compatibility with a bucket-restricted key.
6. Do not use the master application key. Omit delete capability if the console
   offers granular capabilities; use lifecycle settings for later cleanup.
7. Create the key and immediately save both returned values in a password
   manager. The secret application key is shown only once.

Map the key fields as follows:

| Environment variable | Backblaze value |
| --- | --- |
| `B2_KEY_ID` | `keyID` from the newly created application key |
| `B2_APP_KEY` | `applicationKey` shown once at key creation |

The B2 master key is not supported by the S3-compatible API. A
bucket-restricted key may also need `listAllBucketNames`; this does not grant
file access to other buckets.

## 2. ElevenLabs

Official starting points:

- Create/sign in to an account: <https://elevenlabs.io/sign-up>
- API key settings: <https://elevenlabs.io/app/settings/api-keys>
- Official API key guidance: <https://elevenlabs.io/docs/overview/administration/workspaces/api-keys>

1. Sign in and open **Developers → API Keys** (or use the direct settings link).
2. Create a restricted user API key named `framefoley-phase0`.
3. Enable the Sound Effects / sound-generation capability needed by
   `POST /v1/sound-generation`.
4. Set a small credit quota for the spike. Only one successful 0.8-second SFX
   call is authorized by the Phase 0 command.
5. Copy the full key when it is first shown and save it in a password manager.

Map it as follows:

| Environment variable | ElevenLabs value |
| --- | --- |
| `ELEVENLABS_API_KEY` | Newly created restricted API key |

## 3. Load secrets without writing them to the repository

Use a private shell session or a local `.env` ignored by Git. Do not paste real
values into `.env.example`, reports, chat, screenshots, or terminal logs.

The recommended path for this repository is the no-echo wrapper. It already
supplies the Phase 0 bucket and region, holds the three entered values only in
the current process, and asks for a final `RUN` acknowledgement immediately
before the one authorized provider call:

```bash
./scripts/run_phase0_live_securely.sh
```

The manual environment method below remains available when the wrapper cannot
be used.

```bash
export B2_KEY_ID='...'
export B2_APP_KEY='...'
export B2_BUCKET='...'
export B2_REGION='...'
export ELEVENLABS_API_KEY='...'
```

Then run:

```bash
make preflight
make b2-smoke
FRAMEFOLEY_ALLOW_LIVE_CALL=1 make live-sfx
make evidence
make check
```

`make preflight` prints presence only; it never prints credential values.
