# Rhythm for kinetic text

## Grouping

Split at punctuation first (commas, dashes, full stops), then at sense boundaries so
each beat is a phrase that stands alone: "Courage is not / the absence of fear / but
the judgement / that something else / matters more." Target 3 words per beat, range
2–5; a number or a single powerful word may stand alone.

## Reading time

`hold = max(1.5, 0.4 × words + 0.8)` s; +30 % for a beat with a number or a name;
a lone word 1.2 s minimum; the attribution beat 2.5 s. With a voice, the voice's
measured line length wins (`script.py time --measured`).

## Emphasis

One word per beat, in the accent colour and bold: the noun that carries the meaning,
the number, the contrast word ("not", "but" only when the sentence turns on them). Never
articles, prepositions, or two words in one beat.

## Backgrounds

| Background | When | Treatment |
|---|---|---|
| solid `#0b0f19` / brand dark | default, quotes | text white, outline 3 px |
| gradient | announcements, stats | `gradients` filter, dark to darker |
| image | one strong photo | slow Ken Burns 1.08, darkened 25 % |
| footage loop | mood, product | `hold`, darkened 25 %, no sound unless asked |

## Reveal

`word` for 9:16 social (110 ms per word), `line` pop for 16:9 and calm pieces. The
reveal starts 0.3 s into the beat; the last word is on screen for at least 0.8 s before
the cut.
