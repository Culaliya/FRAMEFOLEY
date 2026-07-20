# YouTube creator-voiceover release

Recorded: 2026-07-20 (Asia/Taipei)

Current public submission video:
<https://youtu.be/Q8F8djVgkgA>

The original proof-v2 upload remains public and unchanged at
<https://youtu.be/8HMfkTeVxXM>. YouTube does not support overwriting an uploaded
video at the same URL, and this channel did not expose a same-language audio
replacement control, so the owner-authorized narration remaster received a new
video ID.

## Bounded change

- Replaced only the English narration with the owner's authorized private
  ElevenLabs Instant Voice Clone using Eleven Multilingual v2.
- Preserved the 176-second 1920x1080 visual stream byte-for-byte at the encoded
  H.264 stream level.
- Preserved the approved Foley cues and proof-v2 content.
- Published a corrected manual English WebVTT track that matches the spoken
  narration while displaying normalized technical terms such as `B2`, `RMS`,
  `QC`, and `FFmpeg`.
- Did not publish the enrollment recording, provider credentials, account
  identifiers, signed URLs, or narration-segment source files.
- Did not modify product code, architecture, proof formats, provider paths, or
  any Phase 3 candidate.

## Local artifact verification

| Artifact | SHA-256 |
| --- | --- |
| Final MP4 | `52510839d67137b522ca4e4f288e128bf3d67461dcff80f1e6f1621cfce675ea` |
| Audio-only M4A | `c8fafd46addc39060eb23bf2af21deef39b45db527f3b3b64c218700283ab581` |
| Manual English WebVTT | `c6a9e57edb1b92ae0f9a5880ec38772aa7ae1700715c6e84eff33b41e80d5f0e` |
| Sanitized local manifest | `08cc0c05b3fc0c1d540f91a72be127f67f87b93417f7e8672c34bf7669d1d56a` |

The source and output encoded video-stream SHA-256 values both equal
`9102a1a05c569ebef5881a14ac314b985901cddcf24f34eced53cf19ee4aa975`.
The final MP4 decodes without error and contains one H.264 video stream, one
48 kHz stereo AAC audio stream, and one English `mov_text` subtitle stream.
Measured audio is `-16.16 LUFS` integrated with `-1.49 dBTP` true peak.

## Public verification

- Watch HTTP: `200`
- Embed HTTP: `200`
- oEmbed HTTP: `200`, correct title and channel
- Player status: `OK`
- `playableInEmbed`: `true`
- Highest observed quality: `1080p`, 1920x1080, 30 fps
- Audio: two-channel adaptive audio present
- Captions: manual `English` track present; auto-generated English remains
  separately labeled
- YouTube checks: copyright and Community Guidelines reported no issues
- Upload settings: Public, not made for kids, AI use disclosed, standard
  YouTube license, embedding enabled, Shorts remix disabled, Science &
  Technology

All public verification output was sanitized before recording. No cookie,
account data, credential, caption-track signed URL, or media signed query string
was retained.
