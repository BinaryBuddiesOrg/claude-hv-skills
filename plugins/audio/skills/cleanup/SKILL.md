---
name: cleanup
description: >-
  Make a recorded voice sound produced: remove room hum and hiss, cut rumble, tame
  sibilance, even out levels, trim leading and trailing silence, and land at -16 LUFS —
  for a phone recording, a podcast, a talking-head clip's audio, a testimonial or a
  voice memo. Use whenever the user says "clean up the audio", "remove background
  noise", "it sounds echoey/hissy/boomy", "normalise", "make it louder", "podcast
  audio", or a Director's plan takes the user's own recording as the voice.
license: MIT
compatibility: ffmpeg >= 6.0 (afftdn, deesser, acompressor, silenceremove, loudnorm)
metadata:
  domain: audio
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [audio.stage.cleanup]
  tools: [ffmpeg]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# cleanup

## What this skill does and does not decide

It takes a human recording and makes it sit in a mix like narration: high-pass for
rumble, spectral noise reduction for hiss and hum, a de-esser, gentle compression,
silence trimming at the ends, and loudness to −16 LUFS. It measures before and after and
reports both.

It does not fix what was not recorded: heavy reverb, clipping distortion, a second
speaker bleeding in, or wind. It says so, with the measurement that shows it, and
suggests re-recording or the text-on-screen route. It does not cut *content*
(`video:talking-head-broll` does jump cuts).

## Workflow (in this order)

1. **Probe**: `python3 ${CLAUDE_SKILL_DIR}/scripts/cleanup.py INPUT -o work/voice_clean.wav --dry-run --json`
   measures loudness, peak and the noise floor and prints the chain it would apply.
2. **Listen to the problem** (the measurement names it): noise floor above −50 dBFS →
   `--denoise medium`; above −40 → `strong` and a warning; peaks at 0 dBFS → clipped,
   warn; LRA > 15 LU → levels wander, compression helps.
3. **Clean**: same command without `--dry-run`. Defaults: high-pass 80 Hz, denoise
   `light`, de-ess on, compressor 3:1, trim ends, −16 LUFS.
4. **Verify**: after-measurement −16 ± 0.5 LUFS, true peak ≤ −1.5 dBTP, noise floor
   lowered by the amount the report states. Write `work/voice_clean.wav`; this is the
   `voice` role track for `video:assemble` or input to `audio:voice recording` alignment.
5. **Hand the user a 10 s A/B** when the change is big: `--ab work/ab.wav` writes
   before/after of the loudest 10 s back to back.

## Decide or ask

Decide every parameter from the measurement; say what was applied and why in one line.
Ask only when the recording is unusable (clipped throughout, noise floor above the
speech) — "re-record, or use TTS from the script?" — bundled with the Director's round.

## Request → action

| Request looks like | Do |
|---|---|
| "clean up my recording" | probe → `cleanup.py` with defaults chosen from the floor |
| "remove the hum / hiss / fan" | `--denoise medium` (strong if the floor is above −40 dBFS; warn about artefacts) |
| "it's boomy / muddy" | `--highpass 120` |
| "too much sss" | `--deess` (default on); `--deess-strength 0.7` |
| "levels jump around" | compression is on; `--compress-ratio 4` |
| "make it louder" | it already lands at −16 LUFS; for a standalone file for the web use `--target-lufs -14` |
| "podcast episode" | `--target-lufs -16 --trim` and hand to `audio:music` for intro/outro beds |
| "it echoes" | no reliable fix in ffmpeg; report it and suggest a closer mic or a blanket |

## Tools and installation

`ffmpeg` only; all filters are in standard builds. No models, no downloads.

## Report format

```
Done: out/testimonial/work/voice_clean.wav — 84.2 s, -16.0 LUFS (was -23.4), peak -1.5 dBTP, noise floor -58 dBFS (was -46)
Steps: probe -> highpass 80 -> afftdn light (-12 dB) -> deesser -> acompressor 3:1 -> trim ends (0.8 s / 1.4 s) -> loudnorm -16
Check: loudness within ±0.5 of target; no clipping; floor improved 12 dB
Look: not needed
Notes: slight room reverb remains (not fixable in post); say "stronger denoise" if the hiss still bothers you (artefacts increase)
```

## Things that look right but are wrong

- Strong denoise on a clean recording: underwater artefacts. Choose from the measured
  floor, not from habit.
- Normalising peaks instead of loudness: a −1 dBFS peak file can still be quiet. Loudness is the target.
- Compressing before denoising: raises the noise with the voice. Denoise first (the chain does).
- Trimming silence inside the recording "to tighten it": that is editing, and it moves
  every caption timing. Only the ends are trimmed here.
- A stereo phone recording with one dead channel: the script folds to mono and says so.
- Reverb "fixed" with heavy EQ: it is not fixed, it is duller. Report reverb; do not pretend.

## References

- `scripts/cleanup.py --help`.
- `audio:voice` § recording — aligning the cleaned recording to beats.
