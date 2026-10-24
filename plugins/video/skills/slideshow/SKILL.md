---
name: slideshow
description: >-
  Photos (or slides) into a video that holds attention: ordered images with Ken Burns
  motion anchored on the subject, dissolves, chapter titles and captions, a music bed,
  voice-over optional, exported for the destination. Use whenever the user has pictures
  and wants a video — "make a video from these photos", "slideshow", "recap of the trip /
  event / year", "memorial video", "product photos into a reel", "turn my slides into a
  video", "before and after" — or a Director's plan picks the slideshow style.
license: MIT
compatibility: ffmpeg >= 6.0 (zoompan, xfade); PDF/PPTX slides need a converter the Director offers (pdftoppm or LibreOffice headless)
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.style.slideshow]
  tools: [ffmpeg, pdftoppm?]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# slideshow

## What this skill does and does not decide

It turns a set of images into beats — one per image or per small group — and renders
them with motion and dissolves so stills read as a video, then hands the beats to the
shared pipeline (text, music, assemble, export). It decides per-image duration from the
target length, the order from file names or dates, and the motion direction so that
consecutive images do not all move the same way.

It does not decide which photos are good (the user does, or the agent proposes a cull
from a contact sheet and asks), does not retouch, and does not caption what it cannot
know — chapter titles come from the user's words or the folder names.

## Workflow (in this order)

1. **Collect and order**: `python3 ${CLAUDE_SKILL_DIR}/scripts/slideshow.py plan "photos/*.jpg" --target 60 -o out/<slug>/beats.json --order date|name|list --title "Lisbon 2026"`
   probes every image (size, orientation, EXIF date when present), fixes the order,
   computes per-image seconds (3 s default, 4 s with a caption, 2 s for > 40 images at a
   60 s target), writes `beats.json` with `image:` visuals, alternating `ken-burns`
   directions and a centre focus, plus a title beat and a closing card.
2. **Cull or caption** (optional): `slideshow.py sheet "photos/*.jpg" -o work/photos.png`
   for a contact sheet; drop or reorder by editing the beats file. Add `on_screen`
   chapter titles ("Day 1 — Alfama") on the first beat of each group.
3. **Faces and subjects**: when a photo's subject is off-centre, set `visual.focus`
   (e.g. `[0.3, 0.4]`) so Ken Burns tightens on it, not on the sky.
4. **Render**: `video:motion` `motion.py beats --frame none --bg #000000` → one clip per
   image with its move; `ass_text.py beats` for titles; `audio:music fit` for the bed;
   `audio:voice` if narrated; `timeline.py from-beats` with `transition: dissolve` on
   every beat (the plan sets it); `video:assemble`; `video:platform-export`.
5. **Look**: the sheet of the final export; every image fully visible or deliberately
   cropped on its subject; titles readable over the photo (text has an outline).

## Decide or ask

Decide: 3 s per image, dissolve 0.5 s, Ken Burns 1.12×, order by date, 16:9 for YouTube
/ WhatsApp recap or 9:16 for Reels (from the brief), music per mood, title from the
folder name. Ask — bundled with the Director's round — only for the music file (licence)
and, when there are > 60 photos for a ≤ 60 s video, whether to cull or lengthen.

## Request → action

| Request looks like | Do |
|---|---|
| "make a video from these photos" | `plan` → motion → music → assemble → export |
| "trip recap with chapters" | `plan --group-by folder` → chapter titles from folder names |
| "product photos into a reel" | 9:16, `--per-image 2`, `--fit cover` on the product focus, upbeat bed, CTA end card |
| "memorial / wedding" | 16:9, `--per-image 4`, dissolve 0.8 s, calm bed, no kinetic text — `--style gentle` |
| "turn my slides (PDF) into a video" | `slideshow.py slides deck.pdf --out-dir work/slides` (pdftoppm) → `plan` with `--per-image 6 --motion hold` and the speaker notes as voice |
| "before and after" | pairs: `--pairs` renders each pair side by side as one image first |
| "add my voice" | `audio:voice` from a script whose beats are the photo groups |

## Tools and installation

`ffmpeg`. Slides: `pdftoppm` (poppler) renders PDF pages; PPTX needs `soffice --headless
--convert-to pdf` first — both are recipes in `core:doctor`. HEIC photos need ffmpeg
with libheif or a prior conversion; the script reports unreadable files by name.
EXIF orientation is applied from the probe's rotation tag; a photo that still shows
sideways is reported with its name.

## Report format

```
Done: out/lisbon-recap/youtube.mp4 — 62.4 s, 1920x1080, 24 photos (3 s each, 0.5 s dissolves), title + 3 chapters, music "Morning Light" (CC BY)
Steps: plan (24 images by date, 3 groups) -> motion (ken-burns, alternating) -> titles ASS -> music fit -> assemble -> export youtube -> look
Check: every image rendered (24/24); duration 62.4 vs 60 target (+4 %); loudness -14.1 LUFS
Look: out/lisbon-recap/look/youtube_sheet.png (faces centred in the moves; titles clear over the photos)
Notes: 2 portrait photos were padded with black bars (say "crop them" to tighten). Credit line: "Morning Light by X — CC BY 4.0".
```

## Things that look right but are wrong

- Every image pushing in from the centre: hypnotic in the wrong way. Alternate push/pull
  and drift direction (`plan` does). -> [references/pacing.md](references/pacing.md)
- 2 s per image with a caption: unreadable. 4 s when there is text.
- A 4:3 photo stretched to 16:9. Never stretch: pad with black or blur, or crop on the subject.
- EXIF orientation ignored: sideways phone photos. The probe's rotation is applied.
- Dissolves of 1 s on a 2 s image: the image is never fully visible. Dissolve ≤ 25 % of the hold.
- 80 photos in 60 s: a flicker. Cull or lengthen; say which.
- Music that ends before the last photo: `fit` loops/trims to the exact total.

## References

- `references/pacing.md` — seconds per image by count and intent, motion alternation, chapter rules, slides.
- `scripts/slideshow.py --help` — `plan`, `sheet`, `slides`, `pairs`.
