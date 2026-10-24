# Video decisions (shipped with the plugin)

The operational half of the video taxonomy: what the Director may ask, what Auto decides
and why, the defaults, and the brief keys. The repo's `taxonomy/video.md` holds the full
universe for maintainers; this file is the copy the Director reads at run time. Edit both.

## Contents

1. Intents and their bands · 2. Question dimensions · 3. Auto decision table ·
4. Defaults · 5. Brief keys · 6. Plan skeletons per style

## 1. Intents

| Intent | Length band | Default destination | Voice by default |
|---|---|---|---|
| promo / ad | 15–60 s (Auto 30) | Reels + Shorts (9:16) | TTS if usable, else text + music |
| product demo | 30 s – 3 min (Auto 60) | website 16:9 + Reels 9:16 | TTS |
| explainer | 1–3 min (Auto 90 s) | YouTube 16:9 | TTS |
| tutorial / how-to | 3–15 min (from content) | YouTube 16:9 | user's audio, else TTS |
| social short | 7–60 s (Auto 30) | Reels / TikTok / Shorts 9:16 | original audio |
| trailer / teaser | 15–90 s (Auto 45) | YouTube + X 16:9 | none (music) |
| highlight reel | 30 s – 3 min (Auto 60) | YouTube 16:9 + Reels 9:16 | original audio |
| talking head / vlog | from content | YouTube 16:9 | user's audio |
| podcast clip / audiogram | 15–90 s (Auto 45) | Reels + LinkedIn | original audio |
| slideshow / recap | 30 s – 3 min (from photo count × 3 s) | WhatsApp / Facebook / YouTube | none (music) |
| kinetic quote / typography | 10–30 s (Auto 20) | Reels + LinkedIn | TTS or music only |
| screencast / walkthrough | 1–10 min (from content) | YouTube 16:9 | user's audio, else TTS |
| testimonial | 30–90 s (Auto 60) | website + LinkedIn | user's audio |

## 2. Question dimensions (ask at most these four, Auto first)

| Dimension | Ask when | Options, Auto first |
|---|---|---|
| destination | not named and not implied by intent words | Auto (by intent) · Reels/TikTok/Shorts 9:16 · YouTube 16:9 · LinkedIn/X 1:1 · website loop 16:9 · several (one export each) |
| length | not said; intent band is wide | Auto (band default) · 15 s · 30 s · 60 s · 1–3 min · 3–10 min |
| style | no style word; inputs do not force one | Auto (by inputs + intent) · one option per style family in `capabilities.json` at ≥ tested, plus the user's explicit ask if draft ("new") · mark "needs <tool>" when `usable` says missing |
| voice | intent normally has voice and nothing was said | Auto (local TTS if usable, else text-on-screen + music) · no voice, music only · my recording (path) · keep original audio |

Conditional, never counted in the four: **language** (when inputs/request are not in one
obvious language), **brand** (when "brand", "logo", "our colours" are mentioned: ask for
or create `brand.json` once).

Each option's description states the trade-off in one clause ("crops 70 % of the width",
"needs piper — not installed, ~100 MB").

## 3. Auto decision table

| Condition | Decision | Reason to record |
|---|---|---|
| promo/ad, no destination | Reels + Shorts, 9:16, 30 s | "promo defaults to vertical social; 30 s holds attention and fits every short-form cap" |
| tutorial/explainer, no destination | YouTube 16:9; length from script | "long-form instruction lives on YouTube; length follows the content" |
| "social" said | 9:16 1080×1920, ≤ 60 s, one export for Reels/TikTok/Shorts | "all three accept the same file" |
| "website" said | 16:9, 10–20 s, muted loop, no captions | "hero videos autoplay muted and loop" |
| inputs are screen recordings | style `screencast-motion` | "raw screen is unreadable on a phone; framing and zoom make it readable" |
| inputs are photos only | style `slideshow` | "stills need motion to hold attention" |
| inputs are footage, short requested | style `clips-to-short` | "cut, reframe, caption is the proven short-form shape" |
| no inputs | style `kinetic-typography` (if ≥ tested) else ask | "text is the visual that needs no footage" |
| destination social | captions on | "most social playback is muted" |
| destination YouTube long-form | captions off; sidecar SRT written | "YouTube has its own captions; burned text competes with chapters" |
| voice wanted, TTS usable | TTS from script, voice by language | "voice-over doubles retention of explainers" |
| voice wanted, TTS missing | offer recipe once; else text-on-screen + music | "never block a job on a missing engine" |
| promo/trailer/slideshow | music bed, ducked −12 dB under speech | "music drives pace; speech must win" |
| tutorial/testimonial | no music | "music under instruction lowers comprehension" |
| 16:9 source → 9:16 | blur-pad; crop only if subject centred or asked | "crop loses 70 % of the frame" |
| 9:16 source → 16:9 | blur-pad sides | "same reason, other axis" |
| HDR source → any social | tone-map to SDR | "social players flatten HDR unpredictably" |
| VFR source | conform to 30 fps CFR | "VFR breaks caption timing and some players" |
| any social | −14 LUFS, −1 dBTP | "platform normalisation target" |
| podcast/presentation | −16 LUFS | "speech-first targets" |
| length > footage | select + speed ramp ≤ 1.25× before looping | "looping reads as a mistake; mild speed does not" |
| length < 60 % of footage | select moments, never uniform speed-up | "a 3× speed-up is unwatchable" |

## 4. Defaults

30 fps (source fps if 24/25/50/60 and no social destination) · H.264 High + AAC 48 kHz
stereo · CRF 18 intermediates, platform export last · captions: white, 4 px dark outline,
bottom-centre inside the safe zone, one line ≤ 32 characters, sans-serif with glyphs for
the language · music ducked −12 dB under speech, 1 s fade in/out · titles ≤ 2 s on screen
per 5 words · originals untouched · everything under `out/<slug>/`.

## 5. Brief keys (video)

```json
{
  "destination": ["instagram-reels", "youtube"],
  "aspect": ["9:16", "16:9"],
  "duration_s": 30,
  "style": ["screencast-motion"],
  "visual_source": "screen-recordings",
  "voice": "tts | none | recording:<path> | original",
  "music": "upbeat | cinematic | calm | none | file:<path>",
  "captions": true,
  "language": "en",
  "brand": "./brand.json",
  "color_look": "neutral",
  "pace": "fast | medium | slow"
}
```

Destination ids: `instagram-reels`, `tiktok`, `youtube-shorts`, `youtube`, `x`,
`linkedin`, `facebook`, `whatsapp-status`, `website-loop`, `presentation`.

## 6. Plan skeletons

Every plan ends with `video:platform-export` per destination and a Look step. Steps carry
measurable checks (see `core:brief`).

- **screencast-motion**: doctor → probe inputs → script (from subject + inputs) → voice
  (TTS or none) → frame + zoom/pan per beat → captions → music + duck → export × n → look
- **clips-to-short**: doctor → probe → select moments (by brief length; transcript if
  usable) → reframe (blur-pad/crop) → captions → music → export → look
- **slideshow**: doctor → probe images (count, orientation) → order + per-image duration
  → Ken Burns + crossfade → titles → music → export → look
- **captions only**: doctor → probe → captions (SRT given / transcribe) → export → look
