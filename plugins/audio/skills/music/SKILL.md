---
name: music
description: >-
  Music and sound under a video: fit a bed to the exact length (loop, trim on a beat,
  fade), level it for speech (-18 LUFS), duck it under a voice track, place sound
  effects at beat times, and know where royalty-free music and SFX legitimately come
  from. Use whenever a video needs "music", "a track under it", "background music",
  "make it feel upbeat/cinematic/calm", "sound effects", "whoosh", "ducking", "the
  music is too loud", or a Director's plan has a music step. No generation service:
  the bed is the user's file or a licensed download they choose.
license: MIT
compatibility: ffmpeg >= 6.0
metadata:
  domain: audio
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [audio.stage.music]
  tools: [ffmpeg]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# music

## What this skill does and does not decide

It makes a music file fit the video — exact length, clean start and end, the right
level under speech, ducked when the voice speaks — and places sound effects where the
beats ask. It also tells the user where music that may legally be used comes from, and
records the licence in the brief.

It does not compose or generate music (no local generator is a default on ordinary
hardware; see TOOLBOX), does not pick a track's *mood* beyond the brief's word, and does
not decide that music belongs under a tutorial (it does not; the Director's table says
so).

## Workflow (in this order)

1. **Source**: the user's file (`music.file` in beats.json / `brief.music`) or ask them
   to pick one from a licensed library (`references/sources.md`) — one bundled question
   via the Director with the mood from the brief, two or three library suggestions, and
   "no music" as an option. Record title, source and licence in `brief.constraints.music_licence`.
2. **Probe** the file: duration, loudness; `fit` needs to know whether to loop.
3. **Fit**: `python3 ${CLAUDE_SKILL_DIR}/scripts/music.py fit MUSIC -o work/music.wav --duration 29.97 [--start-at 12.0] [--fade-out 1.5]`
   loops (1 s crossfades between copies) or trims to the length, starts at the first
   strong onset when `--start-at auto`, fades, levels to −18 LUFS.
4. **Duck**: done in `video:assemble` from the timeline (`duck_under: voice`, `duck_db`).
   For an audio-only deliverable: `music.py duck work/music.wav --voice work/voice/track.wav -o work/bed_ducked.wav`.
5. **SFX**: `music.py sfx --beats beats.json --out work/sfx.json` lists the cues; the
   timeline gets one `sfx` track per cue (`references/sfx.md` for a tiny built-in set
   synthesised with ffmpeg — whoosh, pop, click, riser — when the user has none).
6. **Verify**: the fitted bed's measured duration equals the target; loudness −18 ± 1.

## Decide or ask

Decide: −18 LUFS bed under −16 LUFS voice, duck −12 dB, 0.5 s fade in, 1.5 s fade out,
loop at a bar boundary when the file is shorter than the video, trim at the end
otherwise; no music under tutorials/testimonials unless asked. Ask only for the track
itself (source + licence), bundled with the Director's round — never ask about "BPM" or
"key".

## Request → action

| Request looks like | Do |
|---|---|
| plan step "music" with a file | `fit` to the edit's length → timeline `music` track |
| "add some upbeat music" (no file) | suggest 2–3 licensed sources for the mood, ask the user to drop the file, then `fit` |
| "start the music at the drop" | `fit --start-at 42.5` (or `auto` for the first strong onset) |
| "music too loud / can't hear the voice" | lower `gain_db` by 3 or deepen `duck_db` to −15 in the timeline; re-assemble |
| "fade the music out at the end" | `--fade-out 2.5` |
| "whoosh on the title / pop on each word" | `sfx` cues from beats → timeline sfx tracks; built-in synth SFX if none supplied |
| podcast intro/outro bed | `fit --duration 12 --fade-out 3` and `duck` under the voice |

## Tools and installation

`ffmpeg` only. Built-in SFX are synthesised with ffmpeg's `sine`/`anoisesrc` and filters
(`references/sfx.md`), so a job never blocks on a missing sound pack. Music generation
tools are recorded in TOOLBOX as heavy options, never defaults.

## Report format

```
Done: out/coffee-promo/work/music.wav — 29.97 s (bed 18.2 s looped ×2, trimmed), -18.0 LUFS, fade in 0.5 s / out 1.5 s
Steps: probe bed -> fit (loop at 18.2 s bar) -> level -> sfx cues (3) from beats
Check: duration 29.97 vs 29.97 target; loudness -18.0; licence recorded (Free Music Archive, CC BY 4.0, credit in Notes)
Look: not needed
Notes: credit line required by the licence: "Track Name by Artist — CC BY 4.0". Say "calmer" and pick another file; ducking happens in assemble.
```

## Things that look right but are wrong

- Music from a streaming service or "a YouTube rip": not licensed for the user's
  video; refuse and point to `references/sources.md`.
- A bed at −14 LUFS under a −16 voice: the music wins; bed −18, voice −16, duck −12. -> [references/sources.md#levels](references/sources.md#levels)
- Looping with a hard cut: an audible seam. `fit` overlaps copies with a 1 s crossfade so the seam disappears wherever it falls.
- A hard cut at the end of the video: 1.5 s fade minimum.
- Music under a tutorial or a testimonial lowers comprehension; the default is none.
- Ducking with a slow release (> 600 ms): the music pumps; 300 ms.
- Stereo bed, mono voice, no resample: assemble resamples everything to 48 kHz stereo.
- Forgetting the credit line a CC BY licence requires: it goes in the report's Notes and the description.

## References

- `references/sources.md` — licensed music and SFX sources, what each licence requires, levels.
- `references/sfx.md` — the built-in synthesised SFX and how to add the user's packs.
- `scripts/music.py --help` — `fit`, `duck`, `sfx`, `probe`.
