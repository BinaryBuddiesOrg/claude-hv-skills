---
name: explainer-animated
description: >-
  Explainer videos with motion graphics instead of footage: a narrated concept broken
  into diagram-like beats — icons, labelled shapes, step counters, arrows, charts, big
  numbers — animated and composed with what Studio has (ASS text, PNG cards, ffmpeg
  shapes) or, when Node is present and the user wants richer motion, a Remotion
  composition generated from beats.json. Use whenever the user says "explainer",
  "explain how X works", "animated video about", "motion graphics", "whiteboard-style",
  "infographic video", "SaaS explainer", or a Director's plan picks explainer-animated.
license: MIT
compatibility: ffmpeg >= 6.0 with libass and drawtext; optional Node 18+ for the Remotion route (user installs; offered, never run unasked)
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.style.explainer-animated]
  tools: [ffmpeg, node?]
---

# explainer-animated

## What this skill does and does not decide

It gives an explainer a visual grammar when there is nothing to film: each beat is a
*diagram moment* — a labelled icon, a three-step row, a number that counts up, a
before/after, an arrow from cause to effect — rendered as cards and animated text over
a clean background, synced to the voice. Two routes: **ffmpeg-only** (cards + ASS text +
simple shape animation; works everywhere) and **Remotion** (React compositions rendered
headless; richer easing, charts, SVG icons; needs Node, offered when `usable.web_apps`).

It does not draw custom illustrations (icons come from the user's set or a licensed
icon pack named in TOOLBOX) and does not choose the route for the user when both exist:
it states the trade-off once (ffmpeg: ready now, simpler motion; Remotion: install +
minutes, better motion) and the Director's one question decides.

## Workflow (in this order)

1. **Script as diagrams** (`video:script`, explainer structure): every beat gets a
   `visual.diagram` block — `{"kind": "steps|icon-label|number|before-after|arrow|chart|quote", "items": […], "accent": "#…"}`.
   `references/diagrams.md` lists the kinds, what each needs, and the on-screen word
   limits. The voice explains; the diagram shows the nouns.
2. **Voice** (`audio:voice`) and retime — diagram timing follows the voice.
3. **Route A — ffmpeg**: `cards.py` (`video:motion`) renders one PNG per diagram beat
   from the `diagram` block (`cards.py diagram --beats beats.json --out-dir work/cards --width … --height …`
   — the `diagram` subcommand is part of this skill's assets, see step 5), `ass_text.py
   beats --reveal line` for labels, timeline with the cards as `image:` segments (Ken
   Burns 1.04 for life), `assemble`, `export`.
4. **Route B — Remotion**: `assets/remotion/` holds a composition that reads
   `beats.json` and renders the same diagram kinds with easing; the Director offers the
   install (`npm create video@latest`, pinned by the README there), the user runs it;
   `npx remotion render` writes `work/explainer.mp4`, then captions/music/export as usual.
5. **Look**: one card per diagram kind viewed; labels inside the frame; numbers
   readable; the voice names what the frame shows at that second.

## Decide or ask

Decide: ffmpeg route when Node is absent or the brief says "quick"; 16:9 for YouTube
explainers, 9:16 for a social cut of one diagram; icons from `brand/icons/` if present,
else text-only labels in rounded boxes; accent from the brand; calm bed under the
voice at −15 dB. Ask once (Director's round) when Node is present: "quick ffmpeg route
now, or Remotion for richer motion (installs Node packages, a few minutes)?"

## Request → action

| Request looks like | Do |
|---|---|
| "explain how our API works" | explainer script with `steps` and `arrow` diagrams, TTS, route by Node presence |
| "90-second SaaS explainer" | 14–18 beats, `icon-label` for features, `number` for proof, end card CTA |
| "whiteboard style" | white background, dark text, `#1a73e8` accent, line-reveal text; (true hand-drawn strokes are a TOOLBOX candidate, say so) |
| "infographic from these stats" | `number` and `chart` beats (bar/line from the beat's `items`), 9:16 for social |
| "add our icons" | `brand/icons/*.svg|png` mapped by `items[].icon` name |
| "richer animation" | Remotion route; `assets/remotion/README.md` |

## Tools and installation

ffmpeg route: nothing extra. Remotion route: Node 18+ and the project's packages
(installed by the user; recipe in `core:doctor` for Node, project README for the rest).
SVG icons need `rsvg-convert` or Inkscape to rasterise for the ffmpeg route (recipes in
`core:doctor`); PNG icons need nothing.

## Report format

```
Done: out/api-explainer/youtube.mp4 — 1:32, 1920x1080, 16 diagram beats (ffmpeg route), voice piper, calm bed
Steps: script (16 beats, 5 diagram kinds) -> voice -> cards (16 PNG) -> labels ASS -> timeline (image segments, ken-burns 1.04) -> assemble -> export youtube -> look
Check: 11/11 youtube; every diagram's labels ≤ 4 words; voice names the on-screen noun within 0.5 s (spot-checked 3)
Look: out/api-explainer/look/youtube_sheet.png (steps row readable, numbers large, nothing clipped)
Notes: Node is installed — say "Remotion" for richer motion (install on your side), or "9:16 cut of the steps" for social.
```

## Things that look right but are wrong

- A wall of text per diagram: 4 words per label, 3–4 items per frame, or split the beat. -> [references/diagrams.md#limits](references/diagrams.md#limits)
- Diagram appears before the voice names it: cards cut in 0.2 s before the noun, not 2 s before.
- Icons from the web with unknown licences: use the user's or a named pack.
- A chart with 12 bars on 9:16: three bars or a number.
- Remotion rendered at 60 fps for YouTube: 30 fps, and export through platform-export, not Remotion's encoder settings.
- Whiteboard "drawing" faked with a wipe: it reads as a wipe; call it a reveal, or wait for the TOOLBOX candidate.

## References

- `references/diagrams.md` — diagram kinds, their fields, limits, layouts per aspect.
- `assets/remotion/README.md` — the Remotion route: scaffold, where beats.json goes, render command, pitfalls.
- `video:motion` § cards, `video:script` § explainer structure.
