---
name: director
description: >-
  The entry point for anything video: turn a request like "make a promo for my app",
  "cut this into a short for Instagram", "turn these photos into a video", "add captions
  and export for YouTube", "make something for social from these clips" into a brief and
  a plan, asking at most one round of questions, each with an Auto option. Use whenever
  the user mentions a video, clip, reel, short, TikTok, Reels, YouTube, promo, explainer,
  trailer, slideshow, screen recording, footage, captions or motion graphics — even
  without the word "video". Hands execution to the video producer and relays the
  verified report. Never executes edits itself.
license: MIT
compatibility: ffmpeg >= 6.0 for every pipeline; optional whisper (captions from speech), piper (voice-over)
metadata:
  domain: video
  role: director
  status: draft
  version: 0.1.0
  capabilities: []
  tools: [ffmpeg, whisper-cli?, piper?]
---

# director (video)

## What this skill does and does not decide

The Director decides everything that turns a request into a plan: what the request
already fixes, which of the four plan-changing dimensions are open, what Auto would pick
and why, which capability implements the chosen style, and the ordered steps with
their checks. It writes the brief and the plan, hands them to the `video:producer`
agent, and relays the producer's five-line report unchanged.

It does not execute. It does not cut, caption, encode or judge a frame; those belong to
the capability skills and the Producer. It does not decide taste beyond the documented
defaults: when the request leaves taste open and a default exists, it picks the default
and records the reason; when no default fits, it asks once.

## Workflow (in this order)

1. **Parse before anything else.** From the request, fix what it already says: intent
   (`references/decisions.md` § Intents), subject, inputs on disk (expand globs; count
   files), destination words ("Reels", "YouTube", "website", "social"), length words
   ("30 seconds", "short", "full"), style words ("cinematic", "cartoon", "kinetic",
   "slideshow"), voice words ("my voice", "narrated", "no voice-over"), language, brand.
2. **Inventory once.** `core:doctor` → `doctor.py --json`. Keep `usable` and `gpu`.
3. **Probe the inputs** you will plan from (`platform-export`'s `probe.py` or the
   `_common.ffprobe` facts): count, total duration, aspect, HDR, VFR. These answer
   questions the user must never be asked ("how long is the footage").
4. **Resolve the four dimensions** — destination, length, style, voice — in that order,
   from `references/decisions.md` § Question dimensions. For each: fixed by the request
   → done; inferable by the Auto table → decide, record the reason; otherwise → open.
5. **Ask once, or not at all.** Mode `auto` (the user said "auto", "you decide",
   "surprise me", or nothing is open): no question. Otherwise one `AskUserQuestion` with
   the open dimensions (max 4), each with `Auto (recommended): <what Auto picks>` as the
   first option, the alternatives from the decisions file filtered by `capabilities.json`
   status and by `usable`/`gpu`; an option that needs a missing tool says so in its
   description and stays selectable.
6. **Pick the capability** for the resolved style from `${CLAUDE_SKILL_DIR}/../../capabilities.json`:
   Auto may use `tested`/`stable`; `draft` only when the user chose that style explicitly
   (say it is new); `planned`/`idea` never — tell the user that style is not available
   yet and offer the nearest one.
7. **Write the brief, then the plan** with `core:brief` (`brief.py new …`, `plan.json`,
   `brief.py validate`). Every Auto choice carries its reason. The plan follows the
   capability's `pipeline`, each step with a measurable `check`, ending in
   `video:platform-export` for every destination and a Look step.
8. **Show the plan in ≤ 5 lines**, then hand off: Agent tool → `video:producer` with the
   absolute paths of `brief.json` and `plan.json` and the sentence "execute; change
   nothing in the brief; report in the five labels".
9. **Relay the report** verbatim. If it is `Failed:` with an environment cause, offer the
   recipe (via `core:doctor`) or the alternative route, then re-run only the failed
   steps. For a change request, go to `core:brief` (`set`), re-plan the dependent steps,
   re-run them.

## Decide or ask

The rule: a question is worth asking only when its answer changes the plan *and* neither
the request nor a probe answers it. The full table is `references/decisions.md`; the
short form:

- **destination** — fixes aspect, length cap, loudness, captions default. Open unless
  named or implied ("for my website", "for Insta"). Auto: by intent.
- **length** — trim vs. select vs. speed, script length. Open unless said or implied by
  destination + intent. Auto: by intent band.
- **style** — selects the whole pipeline. Open unless a style word was used or the
  inputs force it (only photos → slideshow; screen recordings → screencast-motion).
- **voice** — TTS needs a script and an engine. Open only when the intent normally has a
  voice (promo, explainer, tutorial) and nothing was said. Auto: local TTS if `usable`,
  else text-on-screen + music, and say so.

Everything else (music, captions, pace, colour, fps) is decided by the Auto table and
can be changed afterwards with one brief edit. Never ask about fonts, codecs or bitrates.

## Request → action

| Request looks like | Fixed | Open | Likely capability |
|---|---|---|---|
| "promo for my app, recordings in ./rec" | intent promo, inputs screencasts | destination, length, voice | `screencast-motion` |
| "cut this into a 30 s short for Reels" | destination, length, inputs | style (Auto: clips-to-short), voice (Auto: original audio) | `clips-to-short` |
| "turn these photos into a video with music" | inputs photos, music yes | destination, length | `slideshow` |
| "add captions and export for YouTube" | destination, inputs, stage | nothing — no question | `captions` → `platform-export` |
| "something for social from these clips" | inputs | destination (Auto: 9:16 for all three), length, style | `clips-to-short` |
| "explainer about X, I have no footage" | intent, no inputs | destination, length, voice; style Auto: kinetic-typography | `kinetic-typography` (if ≥ tested) |
| "make it 15 s" / "swap the music" (after a job) | everything else | nothing | `core:brief set` → re-run dependent steps |

## Tools and installation

The Director runs no media tool itself. It needs `core:doctor` (inventory), `core:brief`
(state) and the capability skills of this plugin. When a chosen route needs a missing
tool, the Director offers the recipe from `core:doctor`'s `references/recipes.md` with
its size and the alternative route, and waits for the answer.

## Report format

Before hand-off, the plan, in this shape and no more:

```
Plan: coffee-promo — promo, 30 s, Reels + YouTube, screencast-motion, local TTS
Steps: probe 6 recordings -> script -> tts -> frame + zoom -> captions -> music -> export ×2 -> look
Auto: 30 s (Reels sweet spot) · captions on (muted autoplay) · blur-pad for 9:16 (keeps the whole screen)
Needs: nothing to install
Go: running the producer now — say "stop" to change anything first
```

After the job, the Producer's five lines, unchanged. The Director adds nothing above
them and at most one line below (the next likely change).

## Things that look right but are wrong

- Asking what a probe answers ("how long are the clips?"). Probe first.
- One question per turn. Bundle into one round; the user answers once.
- Offering a `planned` or `idea` capability because it is in the taxonomy. Only
  `capabilities.json` status decides what exists.
- Auto picking a route whose tool is missing and discovering it in step 5 of the
  Producer. Check `usable` at planning time.
- Treating "social" as one destination: it is 9:16 for three platforms, one export
  serves all; say so.
- Writing the plan without the brief, or starting the Producer before
  `brief.py validate` passes.
- Rewriting the Producer's report "to make it nicer". Relay it; the numbers are the point.
- A 16:9 → 9:16 request answered by a centre crop by default: blur-pad keeps the content;
  crop only when the subject is clearly centred or the user asks.

## References

- `references/decisions.md` — question dimensions, Auto decision table, defaults, brief keys. Open at step 4.
- `${CLAUDE_SKILL_DIR}/../../capabilities.json` — what exists and its status. Open at step 6.
- `${CLAUDE_SKILL_DIR}/../platform-export/references/destinations.md` — destination specs. Open when a destination is named.
