---
name: kinetic-typography
description: >-
  Videos where the words are the picture: a quote, a statistic, a manifesto, a hook line,
  a lyric-style message — split into 2–5-word beats, animated word by word with an
  emphasis colour, over a solid, gradient, image or looping-footage background, timed to
  a voice-over or to music, captioned for mute playback, exported per platform. Use when
  there is no footage and the message is text ("make a video from this quote", "text
  animation", "typography video", "motivational video", "announcement with big text"), or
  when a Director's plan picks kinetic-typography.
license: MIT
compatibility: ffmpeg >= 6.0 with libass; optional local TTS for a spoken line
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.style.kinetic-typography]
  tools: [ffmpeg, piper?]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# kinetic-typography

## What this skill does and does not decide

It turns text into beats that read well on screen — short groups, one emphasis word
each, a rhythm of 1.5–3 s per beat — and renders them with `video:motion`'s animated
text over a background, with optional voice and music, through the shared pipeline.

It does not write the message (the user's words, or `video:script` when the user gives
a topic) and does not pick the typeface beyond a bold sans default; a brand font or
colour comes from `brand.json` or the user.

## Workflow (in this order)

1. **Plan the beats**: `python3 ${CLAUDE_SKILL_DIR}/scripts/kinetic.py plan --text "…" -o out/<slug>/beats.json --target 20 [--attribution "— Maya Angelou"] [--aspect 9:16] [--bg "#0b0f19"|gradient|image:bg.jpg|footage:loop.mp4]`
   splits the text at punctuation and sense into 2–5-word beats, marks the strongest
   word per beat with `*emphasis*`, times each by the reading rule (longer for numbers
   and short lines), sets `visual.source` to the background, and writes a closing
   attribution beat. `--voice` adds the full text as one spoken line split across beats.
2. **Validate and time** with `video:script` (`script.py validate`; with a voice,
   `audio:voice` → `script.py time --measured --write`).
3. **Text**: `ass_text.py beats … --position center --reveal word --style kinetic`
   (`video:motion`); 16:9 announcements may use `--reveal line` for calm.
4. **Background**: solid/gradient → `color:` segments (timeline); image → `motion.py
   beats` renders a slow Ken Burns per beat; footage → `motion.py beats` with `hold`
   and a 25 % darken so text wins (`--bg` on the plan sets it).
5. **Music** (`audio:music fit`, the beat rhythm is more felt with a bed), **assemble**,
   **export**, **look**: every beat's words fully inside the frame, emphasis colour
   visible, nothing inside the UI zones.

## Decide or ask

Decide: 9:16 centre text for social, 16:9 for a website/announcement; 3 words per beat
average; emphasis on the noun or number; accent `#FFD400`; a dark background when the
user gives none; music `calm` for quotes, `upbeat` for announcements. Ask nothing here;
the Director's round covered destination and length, and "make it blue" is a re-render.

## Request → action

| Request looks like | Do |
|---|---|
| "video from this quote" | `kinetic.py plan --text … --attribution …` → text → bg → music → assemble → export |
| "announce our launch date with big text" | `--aspect 16:9 --reveal line`, brand colours, `--voice` optional, upbeat bed |
| "a stat video: 73 % of …" | numbers get their own beat and a 30 % longer hold (plan does); emphasis on the number |
| "over this clip / photo" | `--bg footage:clip.mp4` or `image:photo.jpg`; darkened so text reads |
| "with a voice reading it" | `--voice` → `audio:voice` → retime → text follows the voice |
| "in Hindi / Arabic" | `--font` for the script's font; `--rtl` for Arabic/Hebrew; `video:captions` § fonts |
| "slower / faster" | `--target` longer/shorter re-plans the holds; `--words-per-beat` changes the grouping |

## Tools and installation

`ffmpeg` with libass. A spoken line needs a TTS engine (`audio:voice`). Nothing else.

## Report format

```
Done: out/quote-reel/reels.mp4 — 19.8 s, 1080x1920, 9 beats, word reveal, gradient background, music "Still" (CC0)
Steps: plan (9 beats from 31 words, emphasis on 9 words) -> text ASS -> bg -> music fit -> assemble -> export reels -> look
Check: 13/13 reels checks; every beat ≥ 1.5 s; longest line 13 chars
Look: out/quote-reel/look/reels_sheet.png (text centred, accent on "courage", nothing in the zones)
Notes: say "white on black", "line by line" or "add a voice" to re-render.
```

## Things that look right but are wrong

- One word per beat for a whole paragraph: exhausting. 2–5 words, with rhythm changes.
- Emphasis on an article or verb: emphasise the noun or number. -> [references/rhythm.md](references/rhythm.md)
- Light text on a bright photo with no outline or darkening: unreadable; the plan darkens footage 25 % and keeps the outline.
- 14+ characters per line on 9:16: wraps to three lines; the plan's grouping avoids it.
- A quote with no attribution: viewers ask who said it; the last beat says.
- Beats shorter than reading time because the music is fast: the reading rule wins; cut words instead.

## References

- `references/rhythm.md` — grouping rules, reading times, emphasis choice, backgrounds.
- `scripts/kinetic.py --help`; `video:motion` § text; `video:script` § on-screen text.
