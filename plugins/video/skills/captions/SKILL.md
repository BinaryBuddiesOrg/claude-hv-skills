---
name: captions
description: >-
  Put captions on a video the right way: from an SRT the user has, from a script's
  beats, from plain text timed to the clip, or by transcribing speech locally
  (whisper.cpp / whisper-ctranslate2 when installed). Styles for social (bold, outlined,
  inside the platform's safe zone), clean, minimal box, karaoke word-highlight; CJK and
  Indic fonts by script; sidecar SRT for YouTube. Use whenever the user mentions
  captions, subtitles, SRT, "readable on mute", "add the words", transcribe, karaoke,
  lyrics on screen, or any social delivery where burned text is the default — even if
  they do not say "captions".
license: MIT
compatibility: ffmpeg >= 6.0 built with libass (filter `ass`); optional whisper-cli (whisper.cpp) or whisper-ctranslate2 for transcription
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.stage.captions]
  tools: [ffmpeg, whisper-cli?, whisper-ctranslate2?]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# captions

## What this skill does and does not decide

It makes the words appear: it turns text or speech into timed cues, styles them for the
destination, keeps them out of the platform's UI zones, burns them in or writes a
sidecar, and proves the result with a frame the agent looks at. The cue *text* is never
rewritten — too long for the frame means a smaller size or more lines, never a
paraphrase.

It does not decide whether a video should have captions (the Director does, from the
destination), what the words are (the script or the speaker does), or whether a
transcript is accurate enough to publish — that is reported as a confidence and left to
the user.

## Workflow (in this order)

1. **Get cues** (pick one):
   - SRT supplied → use it (run `srt.py split FILE --max-chars 32` if lines are long);
   - script beats → `python3 <script skill>/scripts/script.py srt beats.json -o work/voice.srt`;
   - plain text + known duration → `srt.py from-text text.txt --duration 28 -o work/cues.srt`;
   - speech in the video → `transcribe.py INPUT -o work/transcript.srt --words` (needs
     a local engine; `core:doctor` → `usable.transcription`). Read the transcript before
     burning: fix names and brand words in the SRT, never in the video.
2. **Know the final frame.** Captions are sized and placed for the *final* width,
   height and destination. If the video will still be reframed (16:9 → 9:16), do the
   reframe first (`video:platform-export`), then caption the export.
3. **Burn or sidecar**:
   `captions.py INPUT -o OUTPUT --srt work/cues.srt --style social --safe instagram-reels`
   converts the SRT to ASS at the video's own resolution (so margins are exact), places
   the text above the destination's UI zone, and burns with libass. `--sidecar` writes
   `OUTPUT.srt` beside the video instead (YouTube long-form). `--words work/transcript.words.json --style karaoke`
   highlights word by word.
4. **Look**: `captions.py` writes `OUTPUT.caption-check.png` (the frame at the first cue,
   with safe zones shaded when `--safe` is given). View it: text inside a red zone, text
   over a face, tofu boxes (missing glyphs) are all failures.
5. **Report**: cue count, style, position, the frame viewed.

## Decide or ask

Decide: style `social` for Reels/TikTok/Shorts/X/LinkedIn, `clean` for YouTube 16:9
burn-ins, sidecar for YouTube long-form, 32 characters per line on 9:16 and 42 on 16:9,
two lines max, bottom-centre above the safe zone, font by language (Latin: a bold
sans; `ja/zh/ko/hi/th/ar`: the script's font found by `fc-list :lang=xx`). Say what you
picked in one line.

Ask only when there is no text source at all and no local transcription engine: "give
me the text or an SRT, or install whisper (recipe) — which?" Never invent dialogue.

## Request → action

| Request looks like | Do |
|---|---|
| "add captions" + SRT present | `captions.py IN -o OUT --srt FILE --style social --safe <dest>` |
| "add captions" + no text, speech in video, engine usable | `transcribe.py` → review → `captions.py` |
| "add captions" + no text, no engine | ask for text/SRT or offer the recipe; alternative: `srt.py from-text` if the user types the lines |
| "captions from my script" | `script.py srt` → `captions.py` |
| "karaoke / word by word / TikTok style" | `transcribe.py --words` (or `srt.py from-beats --words` for TTS beats) → `captions.py --style karaoke --words …` |
| "lyrics on screen" | timing from `video:lyric`; then `captions.py --style karaoke` or `social` |
| "for YouTube" | `--sidecar` (and `--style clean` only if the user wants burned text too) |
| "the captions are cut off / under the buttons" | re-run with `--safe <dest>` (margin from the zone) and `--size` smaller |
| "Japanese / Hindi / Arabic captions" | `--font` from `fc-list :lang=xx family`; `--rtl` for Arabic/Hebrew; check the frame for tofu |

## Tools and installation

`ffmpeg` with libass (`ffmpeg -hide_banner -filters | grep -w ass`). Transcription
engines are optional; `core:doctor` reports `usable.transcription`; recipes in
`core:doctor`'s `references/recipes.md` (whisper.cpp: MIT, CPU; whisper-ctranslate2:
MIT, `uv tool install`). Models download on first run to `${CLAUDE_PLUGIN_DATA}/whisper/`
— say the size before the first run. Fonts: `fc-list : family` lists what libass can
use; no font for the script = tofu = failed job.

## Report format

```
Done: out/coffee-promo/work/edit_captioned.mp4 — 29.97 s, 1080x1920, 14 cues burned (social, 80 px, bottom above 20 % zone)
Steps: beats -> srt (14 cues, ≤ 32 chars/line) -> ass (PlayRes 1080x1920) -> burn (libass) -> frame check
Check: cues 14/14 inside 0–29.5 s; longest line 31 chars; font "DejaVu Sans Bold" has every glyph
Look: out/coffee-promo/look/edit_captioned.caption-check.png (first cue above the Reels zone, no overlap with the UI)
Notes: say "bigger", "top", "yellow highlight" or "two lines" and I re-burn from the same SRT
```

## Things that look right but are wrong

- Burning before the reframe: captions land in the blurred side bars or off-frame. Frame first. -> [references/styles.md#order](references/styles.md#order)
- `subtitles=file.srt` straight from an SRT: libass picks a 384×288 play resolution and
  the size/margins drift by video. Always convert to ASS at the video's resolution (`captions.py` does).
- A line that fits on a 1920-wide frame overflows on 1080 — the character limit is per aspect.
- Default font for Japanese/Hindi/Arabic: boxes instead of glyphs. Check the frame.
- Whisper transcripts spell brand names phonetically; fix the SRT before burning.
- Cues that end exactly when the next starts flicker; `srt.py` leaves a 0.15 s gap.
- Karaoke highlight needs word timings; faking them from cue length looks wrong on every long word.
- White text on a bright sky without an outline. `social` has a 4 px outline for a reason.
- Burning *and* a sidecar on YouTube: the viewer sees doubled captions. One or the other.

## References

- `references/styles.md` — the four styles, sizes per resolution, margins per destination, fonts by script, RTL, order of operations. Open when picking or tweaking a style.
- `scripts/srt.py --help`, `scripts/captions.py --help`, `scripts/transcribe.py --help`.
