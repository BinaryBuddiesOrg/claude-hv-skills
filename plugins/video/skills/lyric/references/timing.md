# Lyric timing

## LRC

```
[00:12.40]Walking down the empty street
[00:16.10]Nothing left for me to keep
```

`[mm:ss.xx]` is the line's start; the line ends at the next line's start (minus 0.2 s)
or after 6 s of silence. Enhanced LRC (`<mm:ss.xx>` before words) gives word timings for
karaoke; `lyric.py plan --lrc` reads both.

## Alignment (whisper words → user's lines)

`transcribe.py SONG --words` on the vocal (or the full mix; isolated vocals align
better). `lyric.py align` walks the recognised words and the user's lines together,
matching by normalised text with tolerance for recognition errors (Levenshtein ≤ 2 per
word, up to 40 % unmatched words per line) and assigns each line the start of its first
matched word and the end of its last. Lines with no match inherit a position between
their neighbours and are flagged `timing: "interpolated"`. Match rate < 70 % → tell the
user the timing is rough and offer the typed-timing route.

## Section spread

With `--sections "0:12 verse, 0:48 chorus, 1:20 verse, 1:56 chorus"` and the lyrics
split by blank lines into the same number of blocks, each block's lines are spread
evenly across its section. Approximate (±1–2 s); flagged `timing: "spread"` on every
beat so the report says so.

## Karaoke vs reveal

| Source | Karaoke (word highlight) | Line reveal |
|---|---|---|
| enhanced LRC / aligned words ≥ 85 % | yes | yes |
| plain LRC | no (no word times) | yes |
| spread | no | yes, flagged rough |

## Layout

Centre, 2 rows max, size 0.07 × min(W, H), outline 3 px, 25 % darken on footage.
Instrumental gaps longer than 4 s get a visual-only beat (no text) so the screen is not
frozen on the last line.
