# ElevenLabs paid-rights owner verification

Recorded: 2026-07-20 17:15 CST (Asia/Taipei)

Evidence label: **OWNER-VERIFIED**

This record contains no account identity, billing details, card data, API key,
cookie, or private dashboard capture. It records only the minimum external facts
needed for the bounded submission-rights remediation.

## Verified before new generation

- The owner personally completed the payment and final terms confirmation.
- The signed-in ElevenLabs workspace displayed **Starter plan** and a paid credit
  balance after checkout.
- The Sound Effects product was changed from possible Explore sharing to:
  **generation results will not be shared to Explore for other users to download**.
- The owner explicitly authorized one bounded paid-plan LIVE remediation run and
  immutable `framefoley/proof/live/v2/` publication.
- `framefoley/proof/live/v1/` remains historical and must not be changed.

## Rights boundary

ElevenLabs currently lists a commercial license and Instant Voice Cloning on
Starter. Its publishing guidance says content generated during a paid
subscription may be used commercially, subject to the applicable agreements,
input rights, laws, Terms, and Prohibited Use Policy. This technical record is
not legal advice and does not broaden those terms.

Official references checked:

- <https://elevenlabs.io/pricing>
- <https://help.elevenlabs.io/hc/en-us/articles/13313564601361-Can-I-publish-the-content-I-generate-on-the-platform>
- <https://elevenlabs.io/sound-effects-terms>

## Completion gate

Status: **PAID LIVE V2 GENERATION AND IMMUTABLE PUBLICATION PASS**

The bounded gate subsequently made exactly two provider calls, stored 24 project
objects in B2, and produced two ready candidates whose canonical manifests
returned true from `Manifest.verify()`. Immutable v2 publication returned
`created`; two re-downloaded asset hashes matched and publication made zero
provider calls. This record does not clear the older Free-plan v1 bytes.
