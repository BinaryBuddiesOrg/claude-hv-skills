# timeline.json

```json
{
  "studio_timeline": "0.1",
  "width": 1080, "height": 1920, "fps": 30,
  "background": "#000000",
  "video": [
    { "src": "work/beats/b1.mp4", "in_s": 0, "duration_s": 2.4 },
    { "src": "rec/queue.mp4", "in_s": 4.0, "duration_s": 3.2, "transition": "dissolve", "transition_s": 0.4 },
    { "src": "image:photos/hero.jpg", "duration_s": 3.0 },
    { "src": "color:#111111", "duration_s": 3.0 }
  ],
  "audio": [
    { "src": "work/voice.wav", "role": "voice", "start_s": 0, "gain_db": 0 },
    { "src": "music/upbeat.mp3", "role": "music", "start_s": 0, "gain_db": -2, "loop": true, "fade_in_s": 0.5, "fade_out_s": 1.5, "duck_under": "voice", "duck_db": -12 },
    { "src": "sfx/whoosh.wav", "role": "sfx", "start_s": 2.3, "gain_db": -6 }
  ],
  "keep_source_audio": false,
  "subtitles": "work/captions.ass",
  "overlays": [
    { "src": "brand/logo.png", "x": "W-w-43", "y": "43", "start_s": 0, "end_s": null, "opacity": 0.9, "scale_w": 180 }
  ]
}
```

## Segments

| Field | Meaning |
|---|---|
| `src` | a video file; `image:<path>` (still, held); `color:#RRGGBB` (card) |
| `in_s` | start inside the source (video only); default 0 |
| `duration_s` | how long the segment plays; must fit the source (`in_s + duration_s ≤ source duration`) |
| `transition` | `cut` (default) or `dissolve` *into* this segment; `transition_s` 0.2–1.0 |
| `fit` | `pad` (default: scale to fit, pad to frame) or `cover` (scale to fill, centre crop) |

Every segment is scaled to the frame with its aspect preserved, padded with
`background` (or cropped with `fit: cover`), converted to `fps`, `yuv420p`. Total
duration = Σ `duration_s` − Σ `transition_s`.

## Audio tracks

| Field | Meaning |
|---|---|
| `role` | `voice`, `music`, `sfx` — decides levels and ducking |
| `start_s` | offset on the timeline |
| `gain_db` | applied before mixing (voice 0, music −2, sfx −6 are good defaults) |
| `loop` | music only: loop to the total length, then trim |
| `fade_in_s`, `fade_out_s` | music/sfx fades |
| `duck_under` | `voice`: this track is compressed by the voice tracks' envelope |
| `duck_db` | depth of the duck (−12 default); release 300 ms |
| `trim_s` | optional: cut the track to this length |

`keep_source_audio: true` adds the video segments' own audio as a `voice`-role track
(for footage with speech). Voice tracks are pre-normalised by `audio:voice`/`audio:cleanup`
to −16 LUFS; music beds by `audio:music fit` to −18 LUFS; assemble does not normalise
the final mix (platform-export does, per destination), but it measures and reports it.

## Subtitles and overlays

`subtitles` is an ASS file from `video:captions` (`srt.py to-ass`), applied after
overlays so text is never covered. Overlays are PNGs with alpha; `x`/`y` are ffmpeg
overlay expressions (`W`, `H` frame; `w`, `h` overlay); `scale_w` resizes the PNG
first; `start_s`/`end_s` bound its visibility.

## Chunking

More than 40 segments are rendered as consecutive chunks of 40, concatenated by stream
copy, then audio and overlays are applied in a final pass. The dry-run says when this
will happen.
