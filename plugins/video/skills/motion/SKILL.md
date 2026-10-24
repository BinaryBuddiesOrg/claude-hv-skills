---
name: motion
description: >-
  Motion and graphics for any video, with ffmpeg only: per-beat clips with push-in,
  pull-out, pan and Ken Burns moves anchored on a focus point; screen recordings inside a
  phone or browser frame with rounded corners on a solid, gradient or blurred background;
  animated on-screen text (pop-in, word-by-word reveal, emphasis colour), title cards,
  lower thirds, end cards with a URL, logo badges — all as ASS or PNG that assemble
  burns. Use whenever a video needs "zoom in on", "device frame", "mockup", "kinetic
  text", "title", "lower third", "name tag", "end screen", "logo in the corner", "make it
  move", or a Director's plan has a motion step.
license: MIT
compatibility: ffmpeg >= 6.0 (zoompan, geq, alphamerge, overlay, drawtext with fontconfig, ass)
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.stage.motion]
  tools: [ffmpeg]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# motion

## What this skill does and does not decide

It makes pictures move and words appear, deterministically, from `beats.json`: one clip
per beat with the move the beat asks for (`visual.focus`, `zoom`, `motion`), framed as
a device when the source is a screen recording, plus one ASS file with every on-screen
line animated at its beat time, and PNG cards for overlays. Everything it writes is an
intermediate that `video:assemble` composes.

It does not decide *where* to look or *what* to say — the script does (`focus`, `zoom`,
`on_screen`). It applies defaults when a beat is silent about motion (a gentle 1.15×
push-in on footage, Ken Burns on photos, hold on screen recordings unless `zoom` is
set) and reports them.

## Workflow (in this order)

1. **Read beats.json** (validated by `video:script`). Decide the frame: `--frame phone`
   for portrait screen recordings, `browser` for desktop captures, `none` for footage
   and photos. Decide the background: `blur` (the recording itself, blurred — the social
   look), a solid `#101418`, or `gradient`.
2. **Render the beat clips**:
   `python3 ${CLAUDE_SKILL_DIR}/scripts/motion.py beats out/<slug>/beats.json --out-dir out/<slug>/work/beats --width 1080 --height 1920 --frame phone --bg blur`
   → `work/beats/<id>.mp4`, one per beat whose visual is footage or an image, exact
   duration, no audio. Use `--fast` first for a preview pass.
3. **Render the text**:
   `ass_text.py beats out/<slug>/beats.json -o out/<slug>/work/text.ass --width 1080 --height 1920 --style kinetic --reveal word --safe instagram-reels`
   — every `on_screen` line pops in at its beat start above the platform's safe zone;
   `*emphasis*` words take the accent colour. Titles, lower thirds and end cards are
   separate commands and `ass_text.py merge` combines ASS files (captions from
   `video:captions` included) into the one file assemble burns.
4. **Cards and badges** for overlays: `cards.py end --text "Download Brew" --url brew.app -o work/endcard.png --width 1080 --height 1920`,
   `cards.py badge --logo brand/logo.png --size 180 -o work/badge.png`.
5. **Look**: `motion.py` writes `work/beats/<id>.jpg` (the middle frame of each clip);
   view two or three — the focus point must be in frame, text must not sit on a face,
   the device frame must not crop the UI the voice talks about.
6. **Hand on**: `timeline.py from-beats` (in `video:assemble`) picks the clips, the
   merged ASS, the voice and music tracks, and the cards as overlays.

## Decide or ask

Decide: frame by source type, blur background for social, solid for 16:9 explainers;
push-in 1.15× default; word reveal for social, line pop for 16:9; text size by frame
(`references/motion.md`); accent `#FFD400` unless `brand.json` has one. Ask nothing in
this skill: a wrong default is one brief edit and a re-render of the beats concerned.

## Request → action

| Request looks like | Do |
|---|---|
| plan step "motion" for a screencast | `motion.py beats --frame phone --bg blur` + `ass_text.py beats --reveal word` |
| "zoom in on the button when I say it" | set `visual.focus` and `zoom` 1.6 on that beat in beats.json; re-render that beat only (`--only b4`) |
| "put the recording in a phone / browser mockup" | `--frame phone` / `--frame browser` |
| "kinetic text video" | `ass_text.py beats --style kinetic --reveal word --position center` with `visual.source: "text"` beats |
| "title at the start" | `ass_text.py title --text … --start 0 --end 2.5` then `merge` |
| "name and role under the speaker" | `ass_text.py lower-third --name … --role … --start 3 --end 8` |
| "end screen with the link" | `cards.py end …` → timeline overlay on the last beat, or an `end-card` ASS event |
| "logo top right" | `cards.py badge` → timeline `overlays[]` |
| "the move is too fast / jittery" | lower `zoom`, use `hold`; jitter means the source is low-res — `motion.py` upsamples 1.5× before zooming |

## Tools and installation

`ffmpeg` with `zoompan`, `geq` (masks), `alphamerge`, `overlay`, `drawtext` (needs
fontconfig/freetype — every normal build), `ass`. Fonts: `fc-list : family`; pass
`--font` for a brand font. Nothing else.

## Report format

```
Done: out/coffee-promo/work/beats/ — 7 clips (1080x1920, phone frame, blur bg), work/text.ass (7 lines, word reveal), work/endcard.png
Steps: beats -> 7 zoompan renders (push-in 1.3–1.6 on focus) -> rounded-corner frame -> text ASS -> end card
Check: every clip's duration equals its beat ± 0.03 s; focus points inside the frame; text above the 20 % Reels zone
Look: work/beats/b3.jpg (zoomed on the "Order" button, phone frame intact), work/beats/b6.jpg
Notes: b2 had no zoom set → 1.15× push-in default. Say "tighter on b4" or "no frame" and I re-render those beats.
```

## Things that look right but are wrong

- Zooming with `crop` and time expressions: crop sizes are fixed at init; `zoompan` is
  the filter that animates, and it needs the 1.5× upsample first or it jitters. -> [references/motion.md#zoompan](references/motion.md#zoompan)
- `zoompan` with the output size in a different aspect than its input: it stretches.
  Conform to the target aspect (cover crop anchored on the focus) *before* zooming.
- Text drawn with `drawtext` for Devanagari/Arabic/Thai: wrong shaping. All text goes
  through ASS/libass; `drawtext` is only for Latin cards.
- Pop-in text that starts at the exact cut: the eye misses it. The reveal starts 0.3 s
  into the beat.
- On-screen text and captions in the same band: merge order puts text higher
  (`position lower` is above the caption band).
- A device frame that crops the UI the voice names: check the frame, lower `zoom`.
- Rounded corners from `geq` on every frame: minutes per clip. The mask is rendered
  once as a PNG and `alphamerge`d.
- A blur background from a static frame: the social look blurs the *moving* clip.

## References

- `references/motion.md` — moves and their expressions, frame geometry, text sizes and positions, ASS animation tags used.
- `scripts/motion.py --help`, `scripts/ass_text.py --help`, `scripts/cards.py --help`.
