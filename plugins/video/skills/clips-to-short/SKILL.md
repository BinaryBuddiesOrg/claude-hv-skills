---
name: clips-to-short
description: >-
  Turn footage into a short: find the moments worth keeping (scene cuts, loudness
  energy, and — when a transcript exists — what is actually said), cut and order them to
  the target length, reframe to 9:16 (or any aspect) with blur-pad or a focus-anchored
  crop, add captions and music, export per platform. Use whenever the user says "cut
  this into a short/reel/TikTok", "make a 30-second version", "highlights from this",
  "best parts", "trim this down", "make it vertical", or hands over footage longer than
  the video they want.
license: MIT
compatibility: ffmpeg >= 6.0 (scdet or select scene, ebur128, xfade); optional local whisper for transcript-aware selection
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.style.clips-to-short]
  tools: [ffmpeg, whisper-cli?]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# clips-to-short

## What this skill does and does not decide

It measures where the cuts and the energy are, proposes candidate moments, and once the
moments are chosen it cuts them exactly, in order, with clean joins, into a short at the
target length — then captions, music and export follow through the other skills.

Choosing the moments is a judgement: the script's measurements (`scenes.py`) rank by
loudness and motion, which is a proxy, not meaning. When a transcript exists, the agent
reads it and picks by *what is said*; when it does not, the agent looks at the candidate
contact sheet and picks by what is *seen*. The user can always name the moments
("the part where she laughs"), and that wins. This skill never pretends the loudest
window is the best one.

## Workflow (in this order)

1. **Probe** every input (`platform-export`'s `probe.py`): durations, aspect, audio,
   VFR. Total footage vs. target length sets the strategy: ≤ 1.5× → trim ends and
   dead air; 1.5–5× → select 3–6 moments; > 5× → select by transcript or ask the user
   for the moments.
2. **Analyse**: `python3 ${CLAUDE_SKILL_DIR}/scripts/scenes.py INPUT --target 30 --json`
   → scene cuts, a loudness timeline, candidate windows with scores, and a first
   `selection` that fits the target. With speech, add a transcript first
   (`video:captions` → `transcribe.py`) and pass `--transcript work/transcript.srt`: the
   candidates then carry the words spoken in them.
3. **Choose** (the agent): read candidates (and their words), view
   `scenes.py --sheet work/candidates.png` (one frame per candidate), and write the
   final segment list — chronological unless the hook rule says otherwise (the single
   strongest moment first for social). Say in one line why these moments.
4. **Cut**: `cut.py INPUT --segments "12.4-18.0,41.2-47.5,88.0-95.0" -o work/edit_raw.mp4 [--xfade 0.25] [--pad 0.15]`
   — exact (re-encoded) cuts with a short crossfade on audio and video so joins do
   not pop; original audio kept.
5. **Reframe**: `video:platform-export export.py --destination instagram-reels --fit pad` (or
   `crop --crop-x …` when the subject is clearly off-centre); for a subject that moves,
   `video:motion` `motion.py clip --focus … --zoom 1.0 --fit cover` per segment first.
6. **Captions** (`video:captions`, from the transcript or typed lines), **music**
   (`audio:music fit` + timeline with `keep_source_audio: true` so speech ducks it),
   **assemble** if music was added, **export** and **look** — `video:platform-export`.

## Decide or ask

Decide: strategy from the footage/target ratio; chronological order; crossfade 0.25 s;
pad 0.15 s before each cut-in so words are not clipped; blur-pad for reframing; captions
on for social. Ask — one bundled question via the Director — only when the footage is
over 5× the target and there is no transcript ("which moments? or shall I pick by
energy and show you a sheet?"), or when the user's own description names moments the
analysis cannot locate.

## Request → action

| Request looks like | Do |
|---|---|
| "cut this into a 30 s reel" | probe → scenes `--target 30` → choose → cut → export reels → captions → look |
| "best bits of this 20-minute talk" | transcribe → scenes `--transcript` → choose by content → cut (3–6 moments) |
| "the part where …" | find it in the transcript or ask for a timestamp; cut that segment ± 1 s |
| "make it vertical" (no cut needed) | skip to reframe with `export.py --fit pad` |
| "faster / punchier" | shorter segments, hook first, `--xfade 0.15`, music bed, captions `social` |
| "remove the boring parts / dead air" | `scenes.py --silences` → cut around silences > 1.2 s (`talking-head-broll` does jump cuts properly) |
| "same but 15 s" | re-select from the same candidates with `--target 15`; re-cut |

## Tools and installation

`ffmpeg` (`scdet`/`select=scene`, `ebur128`, `xfade`, `acrossfade`). Transcript-aware
selection needs a local whisper (`core:doctor` → `usable.transcription`); without it,
selection is by energy and by looking at the sheet, and the report says so.

## Report format

```
Done: out/talk-short/work/edit_raw.mp4 — 29.6 s, 3 segments from 14:12 of footage (12.4–18.0, 41.2–47.5, 88.0–95.0), audio kept
Steps: probe -> scenes (41 cuts, 9 candidates) -> transcript -> chose 3 by content (the question, the answer, the laugh) -> cut (xfade 0.25) -> reframe pad -> captions -> export reels -> look
Check: 29.6 s ≤ 30 target; joins at scene cuts; captions 11 cues
Look: out/talk-short/look/reels_sheet.png (speaker centred in the padded frame; captions above the zone)
Notes: picked by transcript; the loudest window (applause at 6:40) was skipped on purpose. Say "use the applause" or "15 s" to re-cut.
```

## Things that look right but are wrong

- Trusting the loudness ranking: applause and laughter score highest and say nothing. -> [references/selection.md#scores](references/selection.md#scores)
- Cutting on a word: `--pad 0.15` and snapping to the nearest silence or scene cut avoid clipped syllables.
- `-c copy` cuts land on keyframes, up to 2 s off; `cut.py` re-encodes once for exact in/out.
- A 3× uniform speed-up to "fit": unwatchable. Select, never speed past 1.25×.
- Reframing by centre crop: two people become one. Blur-pad by default.
- A short that opens on the establishing shot: social opens on the strongest moment; the
  context can come second.
- Joining segments with a hard audio cut: a pop or a cut-off room tone. `cut.py`
  crossfades audio even when video cuts.
- Captions from the *original* transcript timing after cutting: they drift. Transcribe
  the cut, or `srt.py shift` per segment (`cut.py --remap-srt` does it).

## References

- `references/selection.md` — how candidates are scored, what the scores mean and miss, picking rules by intent.
- `scripts/scenes.py --help`, `scripts/cut.py --help`.
