---
name: lyric
description: >-
  Lyric videos and sung-text visuals: lines timed to the song (from an LRC/SRT the user
  has, from a local whisper alignment of the vocal, or spread by the song's structure
  when nothing else exists), rendered as karaoke word highlight or line reveals over
  footage, images, a generated gradient or AI-made shots, with the song as the audio
  track and the lyrics burned — exported for YouTube or vertical. Use whenever the user
  says "lyric video", "lyrics on screen", "karaoke video", "bhajan/devotional video with
  lyrics", "visualiser with the words", or hands over a song and its text.
license: MIT
compatibility: ffmpeg >= 6.0 with libass; optional local whisper for alignment; the song file is the user's (licence is theirs)
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.style.lyric]
  tools: [ffmpeg, whisper-cli?]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# lyric

## What this skill does and does not decide

It turns a song plus its words into beats — one per lyric line, timed to when it is
sung — and renders the lines as karaoke or reveal text over visuals, with the song as
the only audio. Timing precision is the whole craft here, so the skill is explicit
about where each timing came from and how exact it is.

It does not source the song (the user's file and the user's rights), does not translate
lyrics unless asked, and does not decide the visual world beyond the brief's style —
footage, photos, gradient, or `ai:` shots from `video:ai-shots`.

## Workflow (in this order)

1. **Timing source**, in order of precision:
   - **LRC or SRT from the user** (`[mm:ss.xx]Line`) → exact;
   - **whisper alignment** of the vocal (`video:captions` → `transcribe.py SONG --words`),
     then `lyric.py align --lyrics lyrics.txt --words work/song.words.json` matches the
     user's lines to the recognised words (the lyrics text wins over recognition
     errors) → good for clear vocals, weak for heavy production — report the match rate;
   - **even spread** over the song's duration between verse/chorus marks the user
     gives (`--sections "0:12 verse, 0:48 chorus, …"`) → approximate, say so and offer
     the user a quick timing pass (listen and type `[mm:ss]` per line).
2. **Plan**: `python3 ${CLAUDE_SKILL_DIR}/scripts/lyric.py plan --lyrics lyrics.txt --audio song.mp3 -o out/<slug>/beats.json [--lrc timings.lrc | --words …] [--aspect 16:9] [--visual footage:clip.mp4|image:bg.jpg|gradient|ai]`
   → one beat per line at its sung time, `on_screen` = the line, karaoke word timings
   kept when available, instrumental gaps as visual-only beats.
3. **Visuals**: footage/photos → `video:motion beats` (slow moves, 25 % darken);
   `gradient` → colour segments; `ai` → `video:ai-shots` writes a shot per section
   (verse/chorus) and the user drops the clips in `work/ai/`.
4. **Text**: `ass_text.py beats --position center --reveal line` for reveals, or, for
   karaoke, `srt.py to-ass --style karaoke --words …` (`video:captions`) so the sung
   word lights up. Devanagari/Gurmukhi/Arabic lyrics need the script's font (`--font`).
5. **Assemble** with the song as a `music`-role track at `gain_db 0`, no ducking, no
   voice; **export** (`youtube` 16:9, or `instagram-reels` for a chorus cut); **look**:
   lines appear on the sung beat (check two frames at known lyric times).

## Decide or ask

Decide: reveal per line for calm songs, karaoke highlight for upbeat; centre position;
16:9 for a full song, 9:16 for a chorus cut (from the brief); the user's font if given,
else a bold sans with the language's glyphs. Ask — one question — only for the timing
source when none is exact: "LRC/SRT? let me align with whisper (±0.3 s)? or spread
evenly and you correct?"

## Request → action

| Request looks like | Do |
|---|---|
| song + LRC | `plan --lrc` → visuals → karaoke → assemble → export youtube |
| song + lyrics text only | transcribe `--words` → `align` → `plan --words`; report match rate |
| "chorus for a reel" | `plan --section chorus --aspect 9:16` → 9:16 export with the hook line first |
| "devotional / bhajan video" | gradient or the user's images with gentle Ken Burns, line reveals, Devanagari font, calm pacing |
| "with AI visuals" | `plan --visual ai` → `video:ai-shots` per section → drop clips → assemble |
| "the timing is off by a second" | `lyric.py shift --by -1.0` (or per-line edits in beats.json) → re-render text only |

## Tools and installation

`ffmpeg` with libass. Alignment needs a local whisper (`core:doctor`). Fonts for
non-Latin scripts: `fc-list :lang=hi family` etc. (`video:captions` § fonts).

## Report format

```
Done: out/song-lyric/youtube.mp4 — 3:42, 1920x1080, 48 lines (LRC exact), karaoke highlight, footage with 25 % darken
Steps: lrc (48 lines) -> plan -> motion (12 clips, slow push) -> karaoke ASS -> assemble (song at 0 dB) -> export youtube -> look
Check: 11/11 youtube; lines at sung times (spot-checked 0:32 and 2:10 within 0.1 s); every line ≤ 2 rows
Look: out/song-lyric/look/youtube_sheet.png (text centred, highlight on the sung word, footage darkened)
Notes: timing source LRC (exact). Say "reveal instead of karaoke", "white text", or give a corrected LRC to re-render text only.
```

## Things that look right but are wrong

- Timing lines by words-per-minute: a song is not speech; only sung timing works. -> [references/timing.md](references/timing.md)
- Whisper's lyrics instead of the user's: recognition errors become burned mistakes. Align the user's text to the timings.
- Karaoke highlight on fake word timings: wrong on every long note. No word timings → line reveal.
- Lyrics over bright footage without darkening: unreadable. 25 % darken + outline.
- Ducking the song under "voice": there is no voice; the song is the track at 0 dB.
- A 9:16 full-song lyric video: 3 minutes of vertical is unwatched; vertical gets the chorus.
- Publishing with a song the user does not have rights to: the report states the song's source and that rights are theirs.

## References

- `references/timing.md` — LRC format, alignment method and its limits, section spreading, karaoke vs reveal.
- `scripts/lyric.py --help` — `plan`, `align`, `shift`.
