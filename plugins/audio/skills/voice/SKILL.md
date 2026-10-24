---
name: voice
description: >-
  Voice-over without the cloud: synthesise narration from a script or beats.json with a
  local engine (piper neural voices; macOS `say`; espeak-ng as last resort), one file per
  beat plus a timeline-aligned track, measured durations written back so the video's
  timing is real, normalised to -16 LUFS. Also prepares a user's own recording for the
  same role. Use whenever a video needs a narrator, voice-over, TTS, "read this out",
  "add a voice", a dubbed or translated voice, or an audiobook-style narration — and
  whenever a Director's plan has a voice step.
license: MIT
compatibility: ffmpeg >= 6.0; one of piper (piper-tts), macOS say, espeak-ng. piper voices are .onnx + .json pairs under ${CLAUDE_PLUGIN_DATA}/piper/voices/
metadata:
  domain: audio
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [audio.stage.voice]
  tools: [ffmpeg, piper?, say?, espeak-ng?]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# voice

## What this skill does and does not decide

It makes the narration exist as audio with known timing: picks the best engine present,
synthesises each line, measures how long each really took, writes those durations back
into `beats.json` (so `script.py time --measured` reflows the video to the real voice),
builds one voice track aligned to beat starts, and levels it to −16 LUFS so music
ducking and platform loudness behave.

It does not write the words (`video:script`), does not choose whether the video has a
voice (the brief), and does not judge a voice's character — it offers the two or three
voices available for the language and lets the user hear one line before the whole script.

## Workflow (in this order)

1. **Engine**: `core:doctor` → `usable.tts_voiceover`. Order of preference: piper
   (neural, many languages, CPU-fast) → macOS `say` (good English and many system
   voices, no install) → espeak-ng (intelligible, robotic; say so). None → offer the
   piper recipe once, or fall back to text-on-screen (the Director decides).
2. **Voice**: `python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py voices [--language en]` lists
   what is installed for the language. Default per language in `references/voices.md`.
   For a job the user will publish, synthesise the first beat only and let them hear it:
   `tts.py say --text "<line>" --voice <v> -o out/<slug>/work/voice-sample.wav`.
3. **Synthesise the beats**: `tts.py beats out/<slug>/beats.json --voice <v> --out-dir out/<slug>/work/voice`
   writes `b1.wav …`, measures each, writes `measured_voice_s` into the beats file, and
   builds `work/voice/track.wav` with each line at its beat's `start_s`.
4. **Re-time the video**: `script.py time beats.json --measured --write` (video:script)
   — now every beat is as long as its spoken line really is, plus breath. Then
   `tts.py beats … --track-only` rebuilds the track at the new starts (fast, no synthesis).
5. **Level**: done inside `tts.py` (loudnorm −16 LUFS, −1.5 dBTP) — the track is ready
   for `video:assemble` as a `voice` role.
6. **User recording instead of TTS**: `audio:cleanup` → `tts.py recording REC.wav --beats beats.json`
   splits on the silences between lines to align (reports if the count differs).

## Decide or ask

Decide: engine by availability; voice by language default; rate 1.0 (never above 1.15
to "fit" — cut words instead); a 0.35 s breath between lines; −16 LUFS. Ask (bundled
into the Director's round) only which of two or three voices the user prefers when the
video is for publication and more than one good voice exists; for drafts, pick the
default and say which.

## Request → action

| Request looks like | Do |
|---|---|
| plan step "voice" with beats.json | `tts.py beats` → `script.py time --measured --write` → `tts.py beats --track-only` |
| "read this text" / one-off narration | `tts.py say --file text.txt -o narration.wav` |
| "which voices do I have" | `tts.py voices` |
| "a female / male / British voice" | pick from `voices` by name; piper voice names carry locale and speaker |
| "in Hindi / Spanish / Japanese" | a piper voice for that locale (`references/voices.md`); the script must already be in that language |
| "use my recording" | `audio:cleanup` first, then `tts.py recording` to align lines to beats |
| "it sounds robotic" | espeak-ng was used: offer the piper recipe (~100 MB + 60 MB voice) |
| "slower / faster" | `--rate 0.9 / 1.1`; beyond ±15 % change the script instead |

## Tools and installation

piper: `uv tool install piper-tts` (MIT engine; each voice has its own licence — check
before commercial use). Voices: two files (`<name>.onnx`, `<name>.onnx.json`) placed in
`${CLAUDE_PLUGIN_DATA}/piper/voices/` (or `$STUDIO_PIPER_VOICES`); `tts.py voices` lists
them; `references/voices.md` names good defaults per language and where to download.
macOS `say`: built in; `say -v ?` lists voices. espeak-ng: `apt install espeak-ng` /
`brew install espeak-ng`. All recipes live in `core:doctor` and are offered, never run
unasked.

## Report format

```
Done: out/coffee-promo/work/voice/track.wav — 29.4 s, 7 lines, piper en_US-amy-medium, -16.0 LUFS
Steps: doctor (piper) -> sample line b1 -> synthesise 7 beats -> measured durations into beats.json -> retime -> track at new starts -> loudnorm
Check: every beat has measured_voice_s; longest line b4 6.8 s; no clipping (true peak -1.5 dBTP)
Look: not needed
Notes: "Brü" read as "Brew" via the voice spelling; say "slower" or name another voice from `tts.py voices` to redo
```

## Things that look right but are wrong

- Timing the video to the *estimated* voice length and letting TTS overrun: always
  write measured durations back and retime. -> [references/voices.md#timing](references/voices.md#timing)
- Speeding the voice up to fit: audible above 1.15×. Cut words.
- Numbers, units and abbreviations read literally ("24/7" → "twenty-four slash seven"):
  fix in the script (`video:script` § Writing for TTS).
- A voice at −23 LUFS under music at −18: the music wins. Level the voice (this skill
  does) and duck the music (assemble does).
- One long WAV for all beats: timing drifts and one bad line means regenerating all.
  One file per beat.
- Voice licence ≠ engine licence: a piper voice trained on a dataset with a
  non-commercial licence cannot go in a product video. Check the voice's card.
- espeak-ng for a published promo: it is a fallback for drafts and accessibility, say so.
- `say` output is AIFF; the script converts to 48 kHz WAV — do not feed AIFF to assemble.

## References

- `references/voices.md` — default voices per language, where piper voices come from, timing rules, what a good sample line is.
- `scripts/tts.py --help` — `voices`, `say`, `beats`, `recording`.
