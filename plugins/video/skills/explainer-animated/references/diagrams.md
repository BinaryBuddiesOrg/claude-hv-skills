# Diagram kinds (`beat.visual.diagram`)

| Kind | Fields | Shows | Limits |
|---|---|---|---|
| `steps` | `items: [{label, icon?}]` (2–4) | a horizontal (16:9) or vertical (9:16) row of numbered boxes, revealed one per 0.4 s | label ≤ 4 words |
| `icon-label` | `items: [{label, icon?}]` (1–3) | big icon(s) with a label under each | label ≤ 4 words |
| `number` | `value, unit?, label` | a large number counting up over 0.8 s, label below | label ≤ 6 words |
| `before-after` | `before: {label, icon?}, after: {label, icon?}` | two halves with an arrow | labels ≤ 3 words |
| `arrow` | `from, to, label?` | cause → effect with a label on the arrow | each ≤ 3 words |
| `chart` | `type: bar\|line, series: [{label, value}]` (≤ 5) | a minimal chart with the accent colour | values readable at 9:16 only up to 3 bars |
| `quote` | `text, by` | large quote marks, text, attribution | text ≤ 20 words |

## Layouts

16:9: content in the middle 70 % of the width; `steps` horizontal; captions band free at
the bottom. 9:16: content in the middle 80 % of the height; `steps` vertical; title at
the top 12 %.

## Timing

Reveal starts 0.2 s before the voice says the noun (from the beat's start when the
line opens with it); each item 0.4 s apart; numbers count 0.8 s. The beat holds the
finished diagram for at least 1.2 s after the last reveal.

## Icons

`items[].icon` names a file in `brand/icons/` (PNG with alpha, or SVG rasterised by
`rsvg-convert`). Missing icon → the label in a rounded box, never a placeholder image.

## ffmpeg route rendering

Each diagram becomes one PNG (`cards.py`-style drawtext + drawbox composition) at the
canvas size; the timeline shows it as an `image:` segment with `ken-burns` 1.04 for
life; item-by-item reveals are approximated by rendering 2–4 PNGs per beat (progressive
states) as consecutive sub-segments. Good enough for most explainers; Remotion is the
upgrade when easing and continuous motion matter.
