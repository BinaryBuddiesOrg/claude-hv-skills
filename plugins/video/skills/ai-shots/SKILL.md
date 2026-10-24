---
name: ai-shots
description: >-
  Videos that need footage nobody filmed: write the shot list and director-grade prompts
  per beat for AI video generators (Veo, Runway, Kling, Pika, Seedance, PixVerse, or a
  local model on a big GPU), with character and style consistency across shots, the
  right duration and aspect per tool, then receive the generated clips, verify them
  against the beats, and assemble them with voice, music and captions through the
  normal pipeline. Use whenever the user wants "AI video", "generate the visuals",
  "cinematic shots", "animated / anime / cartoon story", "b-roll I don't have", a
  "trailer for a story", or names Veo, Runway, Kling, Pika, Sora, Seedance — and when a
  Director's plan picks ai-shots or anime-cartoon.
license: MIT
compatibility: ffmpeg >= 6.0 for verification and assembly. Generation happens in the user's own tool/account (no API in Studio); local generation needs ≥ 12 GB VRAM and is a heavy option.
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.style.ai-shots, video.style.anime-cartoon]
  tools: [ffmpeg]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# ai-shots

## What this skill does and does not decide

It does the director's work around generation: turns beats into a shot list where every
shot has a purpose, a duration, an aspect, a five-element prompt (shot + subject +
environment/light + camera + style), consistency anchors (character sheet, palette,
lens, time of day) shared across shots, and the tool's own constraints (max clip length,
aspect options, reference-image support). It hands the user `shots.md` to paste into
their tool, and when the clips come back it checks each against its beat and routes
them into the timeline.

It does not call any generation service — Studio is a driver; the user generates in
the tool they have an account for — and it does not pretend a generated clip matches
the prompt: the agent looks at a frame of each and says what it sees. Local generation
(Wan, CogVideoX, AnimateDiff pipelines) is a heavy-hardware route recorded in
TOOLBOX, offered only when `core:doctor` reports ≥ 12 GB VRAM.

## Workflow (in this order)

1. **Beats first** (`video:script`): every beat that needs generated footage gets
   `visual.source: "ai:<shot-id>"` and a `visual.shot` note of what must be visible
   (the thing the voice names). Beats that can be text or stills stay that way —
   generation is expensive and slow; use it where it earns its place.
2. **Consistency anchors** once per job in `work/ai/anchors.json`: character(s)
   (`"a woman in her 30s, short black hair, red wool coat, no glasses"`), palette, lens
   (`35 mm, shallow depth of field`), time of day, film style (`24 fps, soft grain`),
   negative list (`no text, no logos, no extra people`). Every prompt repeats them
   verbatim — that is how consistency survives across clips.
3. **Shot list and prompts**: `python3 ${CLAUDE_SKILL_DIR}/scripts/shots.py plan out/<slug>/beats.json --anchors work/ai/anchors.json --tool veo -o work/ai/shots.json --md work/ai/shots.md`
   → per shot: id, beat, duration (rounded to the tool's clip lengths), aspect, the
   prompt, a reference-image slot, 2 variations to generate, what to check. The
   `references/tools.md` table sets lengths and quirks per tool; `--tool generic` for
   anything else.
4. **The user generates** (their tool, their account, 2–3 variations per shot; the
   `.md` tells them exactly what to name the files: `work/ai/<shot-id>.mp4`).
5. **Receive and verify**: `shots.py check --dir work/ai --beats beats.json` → every
   expected clip present, duration ≥ beat, aspect right, a frame extracted per clip;
   the agent views the frames and marks each shot `ok` or `redo: <reason>` (wrong
   subject, text artefacts, extra limbs, continuity break). Redo prompts get the
   reason appended as a negative.
6. **Assemble** (`timeline.py from-beats --ai-dir work/ai`, clips trimmed to the beat,
   `fit: cover`), voice, music, captions, export as usual. Native audio from the tool is
   dropped unless the beat says `keep_source_audio` (dialogue clips).

## Decide or ask

Decide: tool by what the user already has (ask once which); clip length by tool;
2 variations per shot; cinematic defaults from `references/prompting.md` by genre;
anime/cartoon style anchors when the brief says so. Ask — bundled with the Director's
round — which tool/account and whether a reference image (product, character) exists.
Never ask the user to describe shots: that is this skill's job; they approve.

## Request → action

| Request looks like | Do |
|---|---|
| "AI video about X" | script → anchors → `shots.py plan` → user generates → `check` → assemble |
| "anime / cartoon story" | anchors with the 2D style block (`references/prompting.md § anime`), character sheet first, 5–8 s shots, line-art consistency notes |
| "b-roll I don't have for my talk" | only the beats that need it get `ai:`; the rest stay the speaker |
| "product in different scenes" | reference image per shot; `--tool runway` or `kling` (reference support); `check` compares the product frame |
| "trailer for my novel" | trailer structure (`video:script`), 1–3 s beats cut from 5 s shots, music-driven |
| "I have a 24 GB GPU, do it locally" | the heavy route in TOOLBOX (user installs; newadder vets models); same shots.json drives it |
| "the clips don't match" | `check` marks redo with reasons; `shots.py plan --redo` re-emits only those with negatives |

## Tools and installation

`ffmpeg` only on Studio's side. Generation: the user's tool. `references/tools.md`
summarises clip lengths, aspects, reference-image support and typical cost per tool
(2026 snapshot, re-vetted by newadder). Local models are heavy-hardware entries in
TOOLBOX, never defaults.

## Report format

```
Done: out/story-trailer/youtube.mp4 — 58.0 s, 1920x1080, 9 AI shots (Veo), voice piper, music "Dawn" (CC BY)
Steps: script (11 beats, 9 ai) -> anchors -> shots.md (9 shots × 2 variations) -> user generated 18 clips -> check (8 ok, 1 redo → ok) -> assemble -> export -> look
Check: 9/9 shots present, durations ≥ beats, 16:9; continuity: coat colour consistent in 9/9 frames
Look: out/story-trailer/look/youtube_sheet.png (character consistent across shots 2, 5, 8; no text artefacts)
Notes: shot 6 was redone once (extra figure). Say "warmer light", "slower cuts" or "9:16 version" to re-plan; generation is on your side.
```

## Things that look right but are wrong

- A different prompt style per shot: a different film per shot. Anchors verbatim in
  every prompt. -> [references/prompting.md#consistency](references/prompting.md#consistency)
- Describing instead of directing ("a woman walks"): the 5-element formula or nothing.
- Asking for 30 s from a tool that makes 8 s: plan 4 shots. `shots.py` rounds to the tool's lengths.
- Text in the prompt ("a sign that says OPEN"): generators misspell; add text in `video:motion`.
- Trusting a clip without looking: six fingers ship. `check` extracts a frame; look at it.
- Using the tool's native audio under a voice-over: two voices. Drop it unless it is the dialogue.
- Generating every beat: slow, costly, and the stills/text beats were better as stills/text.
- Calling an API from Studio: there is none; the user's tool and account do the generating.

## References

- `references/prompting.md` — the five-element formula, shot/camera/lighting vocabulary, genre and anime/cartoon style blocks, consistency rules, negatives.
- `references/tools.md` — per-tool clip lengths, aspects, references, quirks (2026 snapshot).
- `scripts/shots.py --help` — `plan`, `check`.
