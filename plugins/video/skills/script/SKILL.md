---
name: script
description: >-
  Write the script and beat sheet for any video before a single frame is made: hook,
  beats, voice-over lines, on-screen text, visual per beat, timing at a real speaking
  pace, call to action — as beats.json, the file every other video skill reads (voice,
  motion, captions, slideshow, assemble). Use whenever a video needs words or structure:
  promo, ad, explainer, tutorial, product demo, trailer, testimonial, story, lyric or
  kinetic-text video; when the user says "write the script", "what should it say",
  "storyboard this", "plan the shots", or gives a topic with no footage; and whenever a
  Director's plan has a script step. Also times an existing script to a target length.
license: MIT
compatibility: Python 3.10+
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.stage.script]
  tools: []
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# script

## What this skill does and does not decide

It decides what the video *says* and in what order: the hook, the beats, the words the
voice speaks, the words on screen, what is seen during each beat, and how long each beat
lasts at a real speaking pace. It writes `out/<slug>/beats.json` (format in
`references/beats.md`) and validates it with `script.py`, so downstream skills never
guess timing.

It does not decide the destination, length or style — the brief does — and it does not
make pictures. It writes the plan the pictures follow. Taste in copy belongs to the user:
offer one strong draft, say what it optimises for, and change it on request without
re-deriving everything.

## Workflow (in this order)

1. **Read the brief**: intent, subject, `duration_s`, `destination`, `voice`,
   `language`, `style`, `inputs`. Everything in the script must serve these.
2. **Pick the structure** for the intent from `references/structures.md` (promo:
   hook → problem → product → proof → CTA; tutorial: promise → steps → recap; …). Count
   the beats the duration allows: a beat is 2–6 s; 30 s ≈ 6–8 beats.
3. **Write the beats** in `beats.json`: for each beat `purpose`, `voice` (what is
   spoken; empty when the video has no voice), `on_screen` (3–7 words max, not a
   transcript of the voice), `visual` (which input, which moment, where to look, how
   tight), `caption` (true when the voice line should be captioned).
4. **Time it**: `python3 ${CLAUDE_SKILL_DIR}/scripts/script.py time out/<slug>/beats.json --target 30 --write`.
   It computes each beat's duration from its voice at the pace in the file (default
   150 wpm), reflows start times, and tells you how far the total is from the target.
   Over by > 10 %: cut words, never speed the voice past 1.15×. Under: let visuals
   breathe, do not pad with words.
5. **Validate**: `script.py validate out/<slug>/beats.json` — ids unique, times
   contiguous, every beat has a visual, on-screen text short enough for the aspect.
6. **Show the script** to the user as a table (beat · seconds · voice · on screen ·
   visual) in ≤ 12 rows, then hand to the plan's next step. Downstream:
   `audio:voice` reads `voice`, `video:motion` reads `on_screen` and `visual`,
   `video:captions` reads `voice` + timing (`script.py srt`), `video:assemble` reads it all.

## Decide or ask

Decide: tone from intent (promo: confident, second person, present tense; tutorial:
plain, imperative; testimonial: first person), reading pace (150 wpm English TTS, 130
for a human recording, language-specific defaults in `references/structures.md`),
hook in the first 2 s for social, CTA last. Ask, through the Director and bundled with
its one round, only when the subject is too thin to write from ("promo for my app" with
no idea what the app does → one question: what does it do and for whom).

Never ask about jokes, adjectives or "tone of voice" in the abstract: write it, show it,
and change it.

## Request → action

| Request looks like | Do |
|---|---|
| "promo for my app", "ad for X" | promo structure, 6–8 beats, hook ≤ 2 s, CTA; voice + on-screen; `time --target` from brief |
| "explain how X works" | explainer: question → one-sentence answer → 3 steps → takeaway; 10–14 beats for 90 s |
| "tutorial", "how to" | tutorial: promise → numbered steps (one beat each, on-screen step titles) → recap; length from steps |
| "trailer / teaser" | no voice or one line; music-driven beats of 1–3 s; on-screen titles; cliff-hanger |
| "turn this text/blog into a video" | condense to the structure that fits the length: 1 idea per beat, 12 words max per voice line |
| "kinetic quote", "typography video" | on-screen only, 2–5 words per beat, voice optional; timing from reading rule |
| "time my script to 60 s" | `script.py time FILE --target 60 --write`; report the delta and which beats to cut |
| "captions from the script" | `script.py srt FILE -o out/<slug>/work/voice.srt` |

## Tools and installation

Python only. `script.py --help`: `validate`, `time`, `srt`, `outline` (prints the
beat skeleton for an intent and duration so the draft starts from the right count).

## Report format

```
Done: out/coffee-promo/beats.json — 7 beats, 29.4 s at 150 wpm (target 30 s), 61 spoken words, 7 captions
Steps: brief -> promo structure -> draft -> time (reflowed 2 beats) -> validate
Check: validate — ok; longest on-screen line 6 words
Look: not needed
Notes: hook "Skip the line." is 2.1 s; say "shorter" or "funnier" and I rewrite only the beats you name
```

## Things that look right but are wrong

- Voice line and on-screen text saying the same words: on-screen is the 3-word
  takeaway, not a subtitle (captions do that). -> [references/structures.md#on-screen-text](references/structures.md#on-screen-text)
- Timing by feel. 150 wpm is 2.5 words/s: a 20-word line is 8 s, not "about 4".
- A hook that starts with the brand name. Start with the viewer's problem or a visual
  surprise; the name comes with the CTA.
- Twelve beats in 30 s. Under 2 s a beat is unreadable; merge.
- Writing for YouTube pacing on a Reel: 9:16 social wants a cut or text change every
  2–3 s and the point by second 3.
- TTS reads numerals and abbreviations badly: write "twenty-four seven", "a. m.",
  spell out units. -> [references/structures.md#writing-for-tts](references/structures.md#writing-for-tts)
- Leaving `visual` empty because "the editor will decide": the editor is a script; an
  empty visual becomes a black beat.

## References

- `references/beats.md` — the beats.json format and rules. Open before writing the file.
- `references/structures.md` — structures per intent, pacing per language, on-screen rules, writing for TTS, hooks and CTAs. Open at step 2.
