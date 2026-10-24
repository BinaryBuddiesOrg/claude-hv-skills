# Structures, pacing and copy rules

## Contents

Structures per intent · Beat budgets by length · Pace per language · Hooks · CTAs ·
On-screen text · Writing for TTS · Visual direction per beat

## Structures per intent

| Intent | Beats in order | Notes |
|---|---|---|
| promo / ad | hook → problem → solution (product in action) → feature ×1–3 → proof (number, quote, logo row) → cta | hook ≤ 2 s; product visible by second 4; one benefit per feature beat |
| product demo | hook (the result) → context (who it is for) → walkthrough step ×3–6 → outcome → cta | walkthrough beats follow the recording order; on-screen = the step name |
| explainer | question → one-sentence answer → how it works ×3 (cause → effect) → example → takeaway | voice carries it; on-screen = the three nouns |
| tutorial / how-to | promise ("by the end you will…") → prerequisites (one beat) → step ×n (title on screen) → common mistake → recap | numbered step titles; no music under steps |
| social short | hook (visual or text surprise) → payoff ×2–3 → loop point or cta | every beat ≤ 3 s; the last frame should match the first for a loop |
| trailer / teaser | title card → world ×2 → tension ×2–3 → reveal → title + date | voice optional; cuts on the music; 1–3 s beats |
| highlight reel | best moment first → chronological highlights ×n → closer | no voice; captions name the moment |
| testimonial | the result in one line → who they are → before → after → recommendation | the speaker's words, trimmed, never rewritten |
| slideshow / recap | title → chapters (3–8 photos each, one caption per chapter) → closing card | 3 s per photo, 4 s for a photo with a caption |
| kinetic quote | the quote split into 2–5-word beats → attribution | voice optional; emphasis word per beat |
| lyric video | one lyric line per beat at the sung timing | timing comes from the audio, not from words-per-minute |
| audiogram | the clip's best 15–60 s; title beat → clip → cta | captions are the visual |

## Beat budgets by length

| Length | Beats | Words of voice (150 wpm) |
|---|---|---|
| 15 s | 4–5 | ≤ 35 |
| 30 s | 6–8 | ≤ 70 |
| 60 s | 10–14 | ≤ 140 |
| 90 s | 14–18 | ≤ 210 |
| 3 min | 25–35 | ≤ 420 |

Over budget by a beat or two: merge two feature beats, never shorten the hook or CTA.

## Pace per language (TTS, words per minute of that language's words)

English 150 · Spanish 160 · French 155 · German 140 · Portuguese 155 · Hindi 140 ·
Japanese ~300 characters/min (set `wpm` to 100 and count characters/3 as words) ·
Chinese ~250 characters/min (same trick) · a human recording: 85 % of the TTS figure.

## Hooks (first 2 s)

- A question the viewer has asked themselves ("Still waiting in line for coffee?").
- A visual contradiction (the product doing the impossible) with 2–3 words on screen.
- A number ("3 taps. 0 queues.").
- The result first, then how (demos, tutorials).
Never: "Hi, I'm…", the logo, "In this video…".

## CTAs (last beat)

One verb, one place: "Download Brew", "Try it free at brew.app", "Follow for part 2".
On screen for ≥ 2.5 s; the voice says it once; URL in `cta.url_on_screen` is drawn by
`video:motion` as an end card.

## On-screen text

- A takeaway, not a transcript. Voice: "Order from your phone and skip straight to
  pickup." On screen: "Skip the line."
- ≤ 5 words on 9:16 and 1:1, ≤ 7 on 16:9. Two lines maximum.
- One emphasis word per line, marked with `*asterisks*` — `video:motion` renders it
  bold or in the accent colour.
- Numerals are fine on screen ("24/7") even when the voice says "twenty-four seven".
- Nothing on screen during the first 0.4 s of a beat if the beat has a cut: the eye
  needs the cut before the text.

## Writing for TTS

- Numbers, units, symbols in words: "two thousand twenty-six", "ten percent", "per
  cent" vs "percent" by locale, "a. m." for AM.
- Abbreviations spelled as said: "A P I", "U X", "ASAP" → "as soon as possible" unless
  the brand says "A-sap".
- Sentences ≤ 14 words; one idea each; commas where you want a micro-pause; a full stop
  where you want a breath.
- Avoid homographs the engine gets wrong ("read", "live", "lead"): rephrase.
- Brand names with odd spelling: add a pronunciation beat note (`"voice": "Brü"` →
  write "Brew" for the engine and keep "Brü" on screen).
- Emoji never go to the voice.

## Visual direction per beat

`visual` tells the editor where to look, not what the shot "feels like":

- footage: `source`, `in_s`, and `focus` (`[0.5, 0.35]` = upper centre), `zoom` 1.2–1.5
  for emphasis, `motion` `push-in` for reveals, `hold` for reading-heavy beats;
- screen recordings: `focus` on the UI element the voice names; `zoom` 1.4–1.8;
- photos: `motion` `ken-burns` with `focus` on the face/subject;
- no footage: `source: "text"` — the on-screen text is the visual, give it the whole
  beat; or `source: "ai:<shot-id>"` when `video:ai-shots` will supply the clip.
