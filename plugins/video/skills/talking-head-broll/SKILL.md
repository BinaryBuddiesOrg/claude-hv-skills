---
name: talking-head-broll
description: >-
  Edit a person talking to camera into a watchable video: silence-aware jump cuts that
  remove pauses and false starts, filler-word removal from a transcript ("um", "uh",
  repeats), b-roll inserts over the speaker at the moments they mention, a name/role
  lower third, captions, music under, export. Use whenever the input is a speaker —
  vlog, testimonial, interview answer, course lesson, founder update, "tighten this up",
  "cut the ums", "add b-roll", "put my name on it" — or a Director's plan picks
  talking-head-broll.
license: MIT
compatibility: ffmpeg >= 6.0; optional local whisper for filler removal and content-based cuts
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.style.talking-head-broll]
  tools: [ffmpeg, whisper-cli?]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# talking-head-broll

## What this skill does and does not decide

It makes a speaker's footage tight and covered: finds the pauses and cuts them with
near-invisible joins, removes fillers when a word-level transcript exists, lays b-roll
over the speaker where the content asks for it, adds the lower third and captions, and
hands a clean edit to music and export.

It does not change what the speaker says (no reordering of answers, no sentence
surgery beyond fillers) and it does not pick *which* b-roll means what — the agent
reads the transcript, proposes the inserts with timestamps and the reason, and the user
approves or supplies clips. A wrong b-roll is worse than none.

## Workflow (in this order)

1. **Probe and clean audio**: probe the footage; if the audio is rough, extract and run
   `audio:cleanup`, then use the cleaned track in the final mix (`keep_source_audio`
   off, cleaned voice as the `voice` track).
2. **Transcript** (`video:captions` → `transcribe.py --words`) when a local engine
   exists; without one, jump cuts work from silence alone and fillers stay.
3. **Jump cuts**: `python3 ${CLAUDE_SKILL_DIR}/scripts/jumpcut.py INPUT -o work/tight.mp4 --min-silence 0.6 --keep 0.25 [--words work/transcript.words.json --fillers]`
   — speech regions ± 0.25 s are kept, pauses longer than 0.6 s go, fillers (and
   immediate word repeats) are cut on their word timings; joins get a 0.08 s crossfade
   so the audio never pops. The SRT is remapped to the new timeline (`--srt`).
4. **B-roll plan**: read the transcript; for each concrete noun or action the speaker
   names that the user has footage/images for, propose `start-end: clip (why)`. Write
   `work/broll.json`; show the list; wait for a yes or edits (bundled with the
   Director's round when the job is new).
5. **Inserts**: `broll.py work/tight.mp4 --plan work/broll.json -o work/covered.mp4 [--pip]`
   — full-frame replacement keeping the speaker's audio, 0.3 s dissolves in/out
   (`--pip` keeps the speaker and shows the b-roll in a rounded corner box instead).
6. **Lower third** (`ass_text.py lower-third`, 3–8 s), **captions**
   (`clean` on 16:9, `social` on 9:16), **music** (quiet bed, `duck -15`), **assemble**,
   **export**, **look**: cuts land in pauses, no half-word at a join, b-roll matches
   the words under it.

## Decide or ask

Decide: silence threshold −35 dBFS, 0.6 s minimum pause, 0.25 s keep, fillers list per
language (`references/fillers.md`), lower third at 3 s for 5 s, captions by
destination. Ask only to approve the b-roll plan and when the speaker's pauses are part
of the delivery (a slow, deliberate talk): "tighten lightly (pauses > 1.2 s) or fully
(> 0.6 s)?" — one question.

## Request → action

| Request looks like | Do |
|---|---|
| "tighten this up / cut the dead air" | jumpcut with defaults |
| "cut the ums and uhs" | transcript `--words` → `jumpcut --fillers` |
| "add b-roll" with a folder of clips | transcript → plan → approve → `broll.py` |
| "put my name and title on it" | `ass_text.py lower-third --name … --role …` |
| "make a reel from this testimonial" | jumpcut → `clips-to-short` selection for the best 30 s → reframe 9:16 with `--crop-x` on the face → captions social |
| "course lesson, keep it natural" | `--min-silence 1.2 --keep 0.35`, no music, `clean` captions, chapter titles |
| "picture-in-picture product shots" | `broll.py --pip --pip-corner top-right` |

## Tools and installation

`ffmpeg` (`silencedetect`, `xfade`/`acrossfade`, `overlay`, `ass`). Fillers and
content-based inserts need a local whisper with word timestamps (`core:doctor` →
`usable.transcription`); without it the report says cuts were by silence only.

## Report format

```
Done: out/founder-update/youtube.mp4 — 2:48 (from 4:31), 1920x1080, 37 cuts, 6 b-roll inserts, lower third, captions clean
Steps: probe -> cleanup (-16 LUFS, floor -58) -> transcript (words) -> jumpcut (41 pauses, 23 fillers) -> b-roll plan approved -> inserts -> lower third -> captions -> music -15 -> assemble -> export -> look
Check: 11/11 youtube; no join inside a word (all cuts in silences ≥ 0.6 s); b-roll 6/6 at approved times
Look: out/founder-update/look/youtube_sheet.png (speaker framed, lower third 3–8 s, b-roll over "our warehouse")
Notes: 3 pauses kept on purpose (> 2 s, deliberate). Say "lighter cut", "no music", or move an insert ("warehouse at 1:12") to re-render.
```

## Things that look right but are wrong

- Cutting every pause: the speaker sounds breathless and the thinking is gone. Keep
  pauses that follow a question or precede a point (> 2 s are kept by default). -> [references/fillers.md#what-to-keep](references/fillers.md#what-to-keep)
- Hard audio cuts at joins: a tick on every cut. 0.08 s crossfade, always.
- Filler removal on the segment transcript (no word timings): it cuts the wrong span.
  Words timings or no filler removal.
- B-roll over the one sentence the viewer needs to see the face for (the ask, the
  emotion): keep the speaker on the key line.
- A lower third that appears on frame one: 3 s in, after the viewer has seen the face.
- Reframing a two-shot to 9:16 by centre crop: crop on the speaker (`--crop-x`), or pad.
- Captions from the original transcript after cutting: they drift. `jumpcut --srt` remaps.

## References

- `references/fillers.md` — filler lists per language, what to keep, join rules, b-roll planning rules.
- `scripts/jumpcut.py --help`, `scripts/broll.py --help`.
