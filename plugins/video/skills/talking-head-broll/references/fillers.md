# Fillers, pauses, joins, b-roll

## Fillers by language (removed with `--fillers` when word timings exist)

| Language | Fillers |
|---|---|
| en | um, uh, erm, er, hmm, "you know" (when followed by a pause), "like" at a sentence start, "sort of", "kind of" (optional, `--fillers-aggressive`) |
| es | eh, este, o sea (aggressive), pues (aggressive) |
| fr | euh, ben, bah, "tu vois" (aggressive) |
| de | äh, ähm, halt (aggressive) |
| hi | अं, अरे (aggressive), "मतलब" (aggressive) |
| pt | é, hum, tipo (aggressive) |

Immediate repeats ("I, I think", "the the") are cut to one, always.

## What to keep

- Pauses > 2 s after a question or before a key point (default kept; `--max-keep-pause`
  to override).
- The breath before the first word of a sentence (0.25 s keep handles it).
- Laughter and reactions, even if "silent" in speech terms (they are not silent in dB).

## Joins

Cut points snap to the middle of the detected silence, never to its edge; video and
audio cross-fade 0.08 s. A jump cut shows a small position jump of the speaker — that
is the accepted look; to hide it, alternate with a 1.1× "punch-in" on every other cut
(`--punch-in`), which reads as a second camera.

## B-roll planning

For every concrete noun or action in the transcript that the user has material for:

`{"start": 71.2, "end": 75.0, "src": "broll/warehouse.mp4", "in_s": 3.0, "why": "speaker says 'our warehouse in Pune'"}`

Rules: insert 0.3 s *after* the word is spoken, never before; 3–6 s per insert; at most
one insert per 15 s; never over the first sentence, the ask, or an emotional line; a
b-roll longer than its window is trimmed from `in_s`.
