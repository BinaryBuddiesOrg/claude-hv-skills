# Slideshow pacing

## Seconds per image

| Situation | Hold | Dissolve |
|---|---|---|
| default | 3.0 s | 0.5 s |
| image with a chapter title or caption | 4.0 s | 0.5 s |
| product reel (9:16, fast) | 2.0 s | 0.3 s |
| gentle (memorial, wedding) | 4.5 s | 0.8 s |
| slides with narration | the voice line's length + 1 s, min 5 s | 0.3 s or cut |
| > 40 images for ≤ 60 s | 1.5–2 s; ask to cull | 0.3 s |

Total = Σ holds − Σ dissolves; `plan --target` scales holds proportionally (never
below 1.5 s) and reports the result.

## Motion

Alternate per image: push-in → pull-out → push-in with a left drift → push-in with a
right drift. Zoom 1.12 (gentle 1.08, product 1.18). Focus at the centre unless set;
faces: set `focus` on the face (the agent can estimate from the contact sheet).
Portrait photos on 16:9: pad (black or blur) by default; `--fit cover` crops on focus.

## Chapters

The first image of each group gets `on_screen` = the chapter title (≤ 5 words) and
`4 s`; a group is a folder, a date gap > 6 h, or the user's list. The title beat at the
start is 2.5 s of the first image with the title; the closing card is 3 s (`color:`
beat with the end text, or the last image with a fade).

## Slides

`slideshow.py slides deck.pdf --out-dir work/slides` renders pages at 1920 px wide with
`pdftoppm`; each page is a beat with `motion: hold` and `fit: pad`; speaker notes (if
the user provides them as text) become the voice lines; the hold is the voice length
+ 1 s. Keep the slide fully visible: no Ken Burns on text-heavy slides.
