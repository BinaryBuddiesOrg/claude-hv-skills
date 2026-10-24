---
name: audiogram
description: >-
  Audio into a shareable video: a podcast clip, an interview quote, a voice note, a song
  snippet — rendered with cover art or a colour background, a live waveform or spectrum
  that moves with the sound, a title, speaker name and burned captions of what is said,
  exported for Reels, LinkedIn, X or YouTube. Use whenever the input is audio-only or
  the user says "audiogram", "podcast clip", "make a video for this audio", "waveform
  video", "quote from the episode", or a Director's plan picks audiogram.
license: MIT
compatibility: ffmpeg >= 6.0 (showwaves, showcqt/showspectrum, drawtext, ass); optional local whisper for captions
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.style.audiogram]
  tools: [ffmpeg, whisper-cli?]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# audiogram

## What this skill does and does not decide

It gives audio a picture: a background (cover art, a photo, or a colour), a waveform or
spectrum that reacts to the sound, a title and speaker line, and room for captions —
then captions and export follow through the shared skills. The clip to use is chosen
first (`clips-to-short`'s `scenes.py --transcript` works on audio too).

It does not decide which 30 s of a 60-minute episode is the clip (the agent reads the
transcript and proposes two or three; the user picks), and it does not design the cover
art — it places what the user has.

## Workflow (in this order)

1. **Pick the clip** when the audio is long: transcribe (`video:captions` → `transcribe.py`),
   `scenes.py AUDIO --target 45 --transcript …` for candidates by speech energy, read
   the words, propose 2–3 with timestamps, and cut the chosen one
   (`cut.py` works on audio-only with `--audio-only`, or `ffmpeg -ss/-to -c copy`).
2. **Render the picture**: `python3 ${CLAUDE_SKILL_DIR}/scripts/audiogram.py CLIP.mp3 -o work/audiogram.mp4 --width 1080 --height 1920 --cover art.jpg --style wave --title "Why we quit SaaS" --speaker "Jane Doe · Episode 42" --accent '#FFD400'`
   — the cover sits in a rounded card over a blurred copy of itself (or `--bg #RRGGBB`),
   the waveform band lives between the card and the caption zone, title and speaker at
   the top.
3. **Captions** (`video:captions`): `social` style, `--safe <dest>`; the words are the
   point of an audiogram, so this step is not optional on social.
4. **Export** (`video:platform-export`) per destination; `look`: waveform visibly
   moving (two frames differ), captions above the zone, title not clipped.

## Decide or ask

Decide: 9:16 for Reels/Shorts, 1:1 for LinkedIn/X (both from the brief), `wave` style
(`bars` for music, `spectrum` for electronic), cover from the audio file's embedded art
when present, accent from the cover's dominant colour when no brand colour exists
(estimated by the agent from a look), clip length 30–60 s. Ask only which clip, when
the audio is long — bundled with the Director's round.

## Request → action

| Request looks like | Do |
|---|---|
| "podcast clip for Instagram" | pick clip → audiogram 9:16 `wave` → captions social → export reels |
| "quote from the episode for LinkedIn" | 1:1, title = the quote's first line, `--style bars`, captions `clean` |
| "visualiser for my track" | `--style spectrum --no-captions`, cover art, 16:9 for YouTube |
| "voice note into a video" | `audio:cleanup` first; `--bg` colour, no cover; captions social |
| "make it move more / less" | `--gain 1.6` / `0.7` on the waveform scale |

## Tools and installation

`ffmpeg` with `showwaves` (every build), `showcqt`/`showspectrum` (most builds;
`--style spectrum` reports if missing and falls back to `wave`). Captions from speech
need a local whisper.

## Report format

```
Done: out/ep42-clip/reels.mp4 — 44.6 s, 1080x1920, wave on cover art, title + speaker, 19 captions
Steps: transcript -> 3 candidates -> clip 12:04–12:49 -> audiogram (cover, wave, accent #F2A33A) -> captions social -> export reels -> look
Check: 13/13 reels; waveform moving (frames at 5 s and 6 s differ); captions above the zone
Look: out/ep42-clip/look/reels_sheet.png (cover card centred, wave band mid-frame, title readable)
Notes: accent taken from the cover's orange. Say "bars", "no title", or another clip time to re-render.
```

## Things that look right but are wrong

- A static cover with no motion: platforms treat it as an image post and viewers scroll. The wave must move.
- Captions skipped "because the audio is clear": most playback is muted. Burn them.
- The waveform under the caption band: both unreadable. The layout keeps the band above the zone.
- A 3-minute audiogram: nobody watches a waveform for 3 minutes. 30–60 s, one idea.
- Embedded cover art at 300 px blown up to 1080: soft. Ask for the original, or use a colour background.
- `showwaves` with `mode=line` on speech: a thin line. `cline` or `p2p` with `--gain` reads better.

## References

- `scripts/audiogram.py --help`.
- `video:clips-to-short` § selection (works on audio with a transcript).
