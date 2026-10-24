---
name: assemble
description: >-
  The render engine: turn a timeline (video segments or stills in order, voice-over,
  music ducked under speech, sound effects, captions file, logo or end-card overlays)
  into one edit.mp4 in a single ffmpeg pass, with cuts or dissolves, exact durations and
  a measured result. Use whenever beats or clips must become a finished video, when a
  Director's plan says "assemble", "mix", "put it together", "add music under the voice",
  "overlay the logo", or when several outputs (voice, visuals, captions) exist and need
  to be combined before platform export.
license: MIT
compatibility: ffmpeg >= 6.0 (xfade, amix, sidechaincompress, ass, overlay)
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.stage.assemble]
  tools: [ffmpeg]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# assemble

## What this skill does and does not decide

It renders exactly what `timeline.json` says — segment order, in/out points, stills
held for a duration, transitions, audio tracks with offsets and gains, ducking, captions,
overlays — into one intermediate edit at CRF 18, and reports its measured duration and
loudness. Other skills (script, motion, voice, music, captions) produce the pieces;
assemble is where they meet.

It does not pick what goes where. A timeline is derived from `beats.json` by the skill
that owns the style (`clips-to-short`, `slideshow`, `screencast-motion`, …) or written by
the Producer from the plan. It does not export for a platform either: `video:platform-export`
takes the edit from here.

## Workflow (in this order)

1. **Write `out/<slug>/work/timeline.json`** (format in `references/timeline.md`):
   `width/height/fps` from the brief's aspect, `video[]` segments in order (footage
   with `in_s`/`duration_s`, `image:` stills, `color:` cards, or pre-rendered beat clips
   from `video:motion`), `audio[]` tracks (`voice`, `music`, `sfx` roles with
   `start_s`), `subtitles` (an ASS from `video:captions`, optional), `overlays[]`.
2. **Dry-run**: `python3 ${CLAUDE_SKILL_DIR}/scripts/assemble.py work/timeline.json -o work/edit.mp4 --dry-run --json`
   prints the total duration, the filter graph and every input it will open; a missing
   file or a segment longer than its source fails here, not twenty minutes in.
3. **Render**: same without `--dry-run`. Music is fitted to the total length (looped or
   trimmed, faded out), ducked under `voice` tracks by `duck_db`, and the mix is
   measured. Video segments are scaled and padded to the frame, never stretched.
4. **Verify**: the result's `output_probe` must match the planned `total_s` within
   0.1 s; the voice must be audible (the script reports the mix's integrated loudness).
   A dissolve shortens the total by its length per transition — the dry-run total
   already accounts for it.
5. **Hand on**: `work/edit.mp4` → `video:captions` (if captions were not in the
   timeline) → `video:platform-export` per destination.

## Decide or ask

Decide: `cut` between segments unless the timeline says `dissolve`; music at −18 LUFS
under −16 LUFS voice, ducked −12 dB with 300 ms release; 1.5 s music fade-out; stills
held exactly their `duration_s`; overlay logos at 90 % opacity top-right with a 4 %
margin. Everything is a field in the timeline, so changing it is editing one value and
re-rendering. Ask nothing: if a piece is missing, fail with the path.

## Request → action

| Request looks like | Do |
|---|---|
| beats + per-beat clips from motion + voice + music | timeline with one `video` segment per beat clip, `voice` track at 0, `music` with `loop: true` |
| "add music under it" | add a `music` track to the timeline, keep `duck_under: voice`, re-render |
| "put my logo in the corner" | `overlays[]` entry with `src`, `x: "W-w-margin"`, `y: "margin"`, `opacity` |
| "dissolve between the photos" | `transition: "dissolve"`, `transition_s: 0.5` on the segments |
| "end card with the URL" | last segment `color:#111111` 3 s + an overlay PNG from `video:motion` (`cards.py`) |
| "the voice is too quiet / music too loud" | adjust `gain_db` on the track or `duck_db`; re-render |
| "same edit, different music" | swap the `music.src`, re-render; nothing else changes |

## Tools and installation

`ffmpeg` with `xfade`, `amix`, `sidechaincompress`, `ass`, `overlay`, `loudnorm` —
present in every normal build (`core:doctor` → `usable.video_edit`). No other
dependency. Long timelines (> 40 segments) are rendered in chunks automatically to stay
under ffmpeg's filter-graph limits.

## Report format

```
Done: out/coffee-promo/work/edit.mp4 — 29.97 s, 1080x1920, 30 fps, h264/aac, mix -15.8 LUFS (voice over music, ducked -12 dB)
Steps: timeline (7 segments, 3 tracks, 1 overlay) -> dry-run (29.97 s planned) -> render -> probe
Check: duration 29.97 s vs planned 29.97 s; all 7 inputs opened; captions ASS applied
Look: deferred to platform-export (sheet after export)
Notes: music looped once (bed was 18 s); b4 dissolve 0.5 s. Edit timeline.json and re-run for any change.
```

## Things that look right but are wrong

- A segment `duration_s` longer than what remains of its source after `in_s`: ffmpeg pads
  with the last frame silently; the dry-run refuses it. -> [references/timeline.md#segments](references/timeline.md#segments)
- Stretching a 16:9 clip into a 9:16 frame. Segments are fit (scale + pad); use
  `video:motion` to crop/zoom with intent first.
- Music at the same level as the voice: speech loses. Keep the gains; change `duck_db`
  only if the user asks for "more/less music".
- Dissolves on every cut in a 30 s promo feel like a wedding video. Cuts by default.
- `amix` with `normalize=1` (ffmpeg's default) halves everything when a track is added;
  assemble uses `normalize=0` and sets gains explicitly.
- Overlay PNG without alpha ends up a white box; `video:motion` writes RGBA.
- Different sample rates across audio tracks drift; every track is resampled to 48 kHz.
- Re-encoding the edit twice before export: assemble writes CRF 18 once; export is the
  second and last encode.

## References

- `references/timeline.md` — the timeline.json format, every field, the fitting and mixing rules. Open before writing a timeline.
- `scripts/assemble.py --help`.
