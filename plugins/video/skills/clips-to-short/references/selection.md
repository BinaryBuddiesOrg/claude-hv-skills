# Selecting moments

## What `scenes.py` measures

- **Scene cuts**: frames where the picture changes abruptly (`scdet` score above the
  threshold, default 10 on a 0–100 scale; `select='gt(scene,0.3)'` fallback). These are
  the natural in/out points; a segment that starts or ends on one looks edited on
  purpose.
- **Loudness timeline**: momentary loudness every 100 ms (`ebur128`). Speech sits
  10–20 LU above room tone; laughter, applause and music peaks sit higher still.
- **Silences**: stretches below −35 dBFS for ≥ 0.6 s — dead air, breaths, the gaps
  between sentences (jump-cut points).

## Scores

A candidate window (default 4–8 s, bounded by scene cuts) scores:

`energy` (mean momentary loudness relative to the file's integrated loudness, 0–1) ×
0.5 + `variation` (loudness range inside the window, 0–1) × 0.2 + `speech_density`
(fraction of the window above the speech threshold) × 0.3.

High scores find *events*: a punchline landing, a product reveal with a sting, a demo
moment with a click and a reaction. They also find applause and a passing truck. The
score ranks where to look; it does not say what matters.

## With a transcript

Each candidate carries the words spoken inside it. Pick by content:

| Intent | Pick |
|---|---|
| promo / highlight | the clearest claim, the strongest reaction, the result |
| talk / interview | the question, its answer, one memorable line; never two answers to the same question |
| tutorial excerpt | the one step that stands alone with its outcome |
| funny | the setup *and* the punchline — a punchline alone is noise |
| testimonial | "before", "after", the recommendation sentence |

Rules: a moment must start on a sentence start (within 0.3 s) and end on a sentence
end; prefer sentences ≤ 14 words; keep names and numbers in.

## Without a transcript and without speech

Pick by the sheet: faces, the product, motion, light. Open on the strongest frame;
alternate wide and tight; end on a frame that could loop to the first.

## Order

Chronological by default — it is the order that stays true. Social hook rule: the
single strongest moment (≤ 3 s) may open the short, followed by chronological order,
when the first chronological moment is slow. Never reorder a question after its answer.

## Length

Social: 15–30 s performs best; ≤ 60 s is the cap for one-export-fits-all. Three to six
moments of 3–8 s with 0.25 s crossfades. One moment longer than 12 s needs a caption or
a cut inside it.
