# beats.json

The one file every video skill reads. Written by `video:script`, enriched by
`audio:voice` (measured durations), consumed by `video:motion`, `video:captions`,
`video:slideshow`, `video:assemble`. Lives at `out/<slug>/beats.json`.

```json
{
  "studio_beats": "0.1",
  "title": "Coffee app promo",
  "language": "en",
  "wpm": 150,
  "target_duration_s": 30,
  "aspect": "9:16",
  "voice": { "mode": "tts", "voice": "en_US-amy-medium", "rate": 1.0 },
  "music": { "mood": "upbeat", "duck_db": -12, "file": null },
  "beats": [
    {
      "id": "b1",
      "purpose": "hook",
      "start_s": 0.0,
      "duration_s": 2.4,
      "voice": "Tired of waiting in line for coffee?",
      "on_screen": "Skip the line.",
      "visual": { "source": "rec/queue.mp4", "in_s": 4.0, "focus": [0.5, 0.35], "zoom": 1.3, "motion": "push-in" },
      "caption": true,
      "sfx": null,
      "transition": "cut"
    }
  ],
  "cta": { "text": "Download Brew today", "url_on_screen": "brew.app" }
}
```

## Fields

| Field | Required | Meaning |
|---|---|---|
| `studio_beats` | yes | format version, `"0.1"` |
| `language` | yes | BCP-47-ish (`en`, `hi`, `ja`); drives TTS voice, caption font, pace |
| `wpm` | yes | speaking pace used by `script.py time`; 150 TTS English, 130 human, see structures.md for other languages |
| `target_duration_s` | yes | from the brief |
| `aspect` | yes | from the brief; on-screen line length limits depend on it |
| `voice.mode` | yes | `tts` · `recording` (path in `voice.file`) · `original` (use the footage audio) · `none` |
| `music` | yes | `mood` (`upbeat`, `calm`, `cinematic`, `none`), `duck_db` under speech, `file` when the user supplied one |
| `beats[]` | yes | ordered; `start_s` contiguous; `duration_s` ≥ 1.2 |
| `beat.purpose` | yes | `hook`, `problem`, `solution`, `feature`, `proof`, `step`, `recap`, `cta`, `title`, `transition`, `free` |
| `beat.voice` | yes (may be `""`) | the spoken line; TTS-safe spelling (numbers and units in words) |
| `beat.on_screen` | yes (may be `""`) | ≤ 7 words for 16:9, ≤ 5 for 9:16 and 1:1; a takeaway, not a transcript |
| `beat.visual.source` | yes | input path, `image:<path>`, `color:#111111`, `text` (the on-screen text *is* the visual), or `ai:<shot id>` from ai-shots |
| `beat.visual.in_s` | for footage | where in the source the beat starts |
| `beat.visual.focus` | optional | `[x, y]` in 0–1 of the frame: where the viewer should look (zoom/crop anchor) |
| `beat.visual.zoom` | optional | 1.0–2.0; `video:motion` applies it |
| `beat.visual.motion` | optional | `push-in`, `pull-out`, `pan-left`, `pan-right`, `hold`, `ken-burns` |
| `beat.caption` | yes | burn this beat's voice line as a caption |
| `beat.sfx` | optional | `whoosh`, `click`, `pop`, or a path |
| `beat.transition` | optional | `cut` (default), `dissolve`, `wipe`; the transition *into* this beat |
| `beat.measured_voice_s` | set by audio:voice | the real TTS duration; `script.py time --measured` reflows to it |
| `cta` | optional | the ask; also used for the end card |

## Rules the validator enforces

- ids unique; beats contiguous (`start_s[i+1] == start_s[i] + duration_s[i]` ± 0.01);
  total within 10 % of `target_duration_s` (warning, not error);
- every beat has a `visual.source`; a `voice` line has `caption` set;
- `on_screen` word limit by aspect; no beat under 1.2 s;
- `voice.mode == "none"` → every `voice` is `""`; `tts` → `voice.voice` names a voice.

## Timing rule (`script.py time`)

`duration_s = max(1.2, words(voice) / (wpm / 60) + 0.35)` when there is a voice line
(the 0.35 s is the breath between lines); otherwise reading time of `on_screen`:
`max(1.5, 0.4 × words + 0.8)`; a beat with neither keeps its stated duration (visual
beat). Durations are then reflowed into contiguous `start_s`. With `--measured`, beats
that carry `measured_voice_s` use `measured + 0.3` instead of the estimate.
