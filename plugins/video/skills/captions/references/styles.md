# Caption styles

## Contents

Styles · Size by resolution · Margins by destination · Fonts by script · RTL · Order ·
ASS notes

## Styles (`captions.py --style`)

| Style | Look | Use |
|---|---|---|
| `social` | bold sans, white, 4 px black outline, no box, bottom-centre | Reels, TikTok, Shorts, X, LinkedIn, Facebook |
| `clean` | medium sans, white, 2 px outline, soft shadow, bottom-centre | YouTube burn-in, presentations, website |
| `minimal` | regular sans, white on a 50 % black rounded box, bottom-centre | documentary, interviews, anything with busy backgrounds |
| `karaoke` | `social` + word-by-word highlight (accent colour sweeps the words as spoken) | TikTok-style speech, lyrics, quotes |
| `top` | `social` placed at the top (under the top safe zone) | when the bottom holds UI or a lower third |

Colours: text `#FFFFFF`, outline `#000000`, karaoke highlight `#FFD400` (override with
`--accent`). Emphasis `*word*` in cue text renders bold + accent in `social`/`karaoke`.

## Size by resolution

Font size = `round(height × 0.042)` for `social`/`karaoke`, `× 0.036` for `clean`,
`× 0.032` for `minimal`: 1920 tall → 80 / 69 / 61 px; 1080 tall → 45 / 39 / 35 px.
`--size` overrides. Characters per line: 32 on 9:16 and 1:1, 42 on 16:9. Two lines
maximum; `srt.py split` reflows.

## Margins by destination (`--safe <id>`)

Bottom margin = destination `safe_zones.bottom_pct` × height + 2 % of height; right/left
margins = the side zones + 3 %. For Reels on 1080×1920: text bottom at 1920 × 0.78 ≈
1498 px. With no `--safe`: 6 % of height from the bottom.

## Fonts by script

| Script / language | Find with | Typical families |
|---|---|---|
| Latin | `fc-list :lang=en family` | DejaVu Sans, Liberation Sans, Inter, Arial |
| Japanese | `fc-list :lang=ja family` | Noto Sans CJK JP, IPAGothic |
| Korean | `fc-list :lang=ko family` | Noto Sans CJK KR, NanumGothic |
| Chinese | `fc-list :lang=zh family` | Noto Sans CJK SC/TC |
| Hindi / Devanagari | `fc-list :lang=hi family` | Noto Sans Devanagari, Lohit Devanagari |
| Thai | `fc-list :lang=th family` | Noto Sans Thai |
| Arabic | `fc-list :lang=ar family` | Noto Sans Arabic, Amiri |

Pass `--font "<family>"`. libass shapes Devanagari, Thai and Arabic correctly (HarfBuzz);
`drawtext` does not — never fall back to drawtext for these scripts.

## RTL

`--rtl` sets the ASS `Encoding` and wraps the text with the Unicode RLE/PDF marks so
punctuation sits on the correct side. Mixed Latin words inside Arabic cues are fine.

## Order

reframe → captions → export. Captions are drawn at the frame size they are burned on;
scaling a burned caption makes it soft (upscale) or illegible (downscale). When a job
exports to two aspects, burn twice, once per export.

## ASS notes

- `PlayResX/Y` = the video's width/height, so a margin in pixels is a margin in pixels.
- `ScaledBorderAndShadow: yes` keeps outlines proportional.
- Times are `h:mm:ss.cc` (centiseconds). Colours are `&HAABBGGRR` (alpha first, BGR).
- Karaoke: `{\k<cs>}word ` per word, centiseconds of the word's duration;
  `PrimaryColour` is the highlighted colour, `SecondaryColour` the not-yet-sung colour.
- `Alignment`: 2 bottom-centre, 8 top-centre, 5 middle-centre (numpad layout).
- A cue's `MarginV` overrides the style's; `captions.py` sets it per destination.
