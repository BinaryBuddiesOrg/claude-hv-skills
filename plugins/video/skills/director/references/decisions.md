# Video decisions (shipped with the plugin)

The operational half of the video taxonomy: what the Director may ask, what Auto decides
and why, the defaults, the brief keys, and the plan per style. The repo's
`taxonomy/video.md` holds the full universe for maintainers; this file is the copy the
Director reads at run time. Edit both.

## Contents

1. Intents · 2. Question dimensions · 3. Auto decision table · 4. Defaults ·
5. Brief keys · 6. Style → capability → plan · 7. The audio plugin

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
| talking head / vlog / testimonial | from content | YouTube 16:9 (+ 9:16 cut) | the speaker |
| podcast clip / audiogram | 15–90 s (Auto 45) | Reels + LinkedIn | original audio |
| slideshow / recap | from photo count × 3 s | WhatsApp / Facebook / YouTube | none (music) |
| kinetic quote / typography | 10–30 s (Auto 20) | Reels + LinkedIn | TTS or music only |
| screencast / walkthrough | 1–10 min (from content) | YouTube 16:9 | user's audio, else TTS |
| lyric video | the song | YouTube 16:9 (+ chorus 9:16) | the song |
| story / cinematic / anime (AI shots) | 30 s – 3 min | YouTube 16:9 or 9:16 | TTS narration or none |

## 2. Question dimensions (ask at most these four, Auto first)

| Dimension | Ask when | Options, Auto first |
|---|---|---|
| destination | not named and not implied by intent words | Auto (by intent) · Reels/TikTok/Shorts 9:16 · YouTube 16:9 · LinkedIn/X 1:1 · website loop 16:9 · several (one export each) |
| length | not said; intent band is wide | Auto (band default) · 15 s · 30 s · 60 s · 1–3 min · 3–10 min |
| style | no style word; inputs do not force one | Auto (by inputs + intent) · one option per style family in `capabilities.json` at ≥ draft (bootstrap) — mark "needs <tool>" when `usable` says missing, "new" when draft |
| voice | intent normally has voice and nothing was said | Auto (local TTS if usable, else text-on-screen + music) · no voice, music only · my recording (path) · keep original audio |

Conditional, never counted in the four: **language**, **brand** (`brand.json`),
**AI tool** (only for ai-shots: which tool/account the user has), **music file**
(licensed source; `audio:music` § sources).

Each option's description states the trade-off in one clause ("crops 70 % of the width",
"needs piper — not installed, ~100 MB", "you generate the clips in Runway").

## 3. Auto decision table

| Condition | Decision | Reason to record |
|---|---|---|
| promo/ad, no destination | Reels + Shorts, 9:16, 30 s | "promo defaults to vertical social; 30 s holds attention and fits every short-form cap" |
| tutorial/explainer, no destination | YouTube 16:9; length from script | "long-form instruction lives on YouTube; length follows the content" |
| "social" said | 9:16 1080×1920, ≤ 60 s, one export for Reels/TikTok/Shorts | "all three accept the same file" |
| "website" said | 16:9, 10–20 s, muted loop, no captions | "hero videos autoplay muted and loop" |
| inputs are screen recordings | `screencast-motion` | "raw screen is unreadable on a phone; framing and zoom make it readable" |
| inputs are photos only | `slideshow` | "stills need motion to hold attention" |
| inputs are footage, short requested | `clips-to-short` | "cut, reframe, caption is the proven short-form shape" |
| inputs are one person talking | `talking-head-broll` | "pauses and fillers out, b-roll and a lower third in" |
| input is audio only | `audiogram` | "audio needs a moving picture and captions to be watched" |
| a song plus lyrics text | `lyric` | "lines timed to the singing; karaoke when word times exist" |
| no inputs, a quote/statistic/message | `kinetic-typography` | "text is the visual that needs no footage" |
| no inputs, "explain how X works" | `explainer-animated` | "diagrams carry an explanation; stock footage would not" |
| no inputs, a story/cinematic/anime/trailer ask | `ai-shots` (user's generator) | "footage that was never filmed must be generated; Studio writes the shots, the user's tool renders them" |
| destination social | captions on | "most social playback is muted" |
| destination YouTube long-form | captions off; sidecar SRT written | "YouTube has its own captions; burned text competes with chapters" |
| voice wanted, TTS usable | TTS from script, voice by language | "voice-over doubles retention of explainers" |
| voice wanted, TTS missing | offer recipe once; else text-on-screen + music | "never block a job on a missing engine" |
| promo/trailer/slideshow/kinetic | music bed, ducked −12 dB under speech | "music drives pace; speech must win" |
| tutorial/testimonial/talking head | no music (or −15 dB bed on request) | "music under instruction lowers comprehension" |
| 16:9 source → 9:16 | blur-pad; crop on the subject only when it is clearly centred or asked | "crop loses 70 % of the frame" |
| 9:16 source → 16:9 | blur-pad sides | "same reason, other axis" |
| HDR source → any social | tone-map to SDR | "social players flatten HDR unpredictably" |
| VFR source | conform to 30 fps CFR | "VFR breaks caption timing and some players" |
| any social | −14 LUFS, −1 dBTP | "platform normalisation target" |
| podcast/presentation | −16 LUFS | "speech-first targets" |
| length > footage | select + mild speed (≤ 1.25×) before looping | "looping reads as a mistake; mild speed does not" |
| length < 60 % of footage | select moments, never uniform speed-up | "a 3× speed-up is unwatchable" |
| ai-shots and no tool named | ask once which tool/account; default prompts `generic` | "generation happens in the user's account" |
| no capability at `tested`+ yet (bootstrap) | Auto may pick `draft`, plan says "new, not yet eval-tested" | "a fresh install should produce a result, not a refusal" |

## 4. Defaults

30 fps (source fps if 24/25/50/60 and no social destination) · H.264 High + AAC 48 kHz
stereo · CRF 18 intermediates, platform export last · captions: white, outline, bottom
inside the safe zone, one line ≤ 32 characters, sans-serif with glyphs for the language ·
music −18 LUFS ducked −12 dB under −16 LUFS voice · titles ≤ 2 s per 5 words · originals
untouched · everything under `out/<slug>/`.

## 5. Brief keys (video)

```json
{
  "destination": ["instagram-reels", "youtube"],
  "aspect": ["9:16", "16:9"],
  "duration_s": 30,
  "style": ["screencast-motion"],
  "visual_source": "screen-recordings | footage | photos | audio | song | none",
  "voice": "tts | none | recording:<path> | original",
  "music": "upbeat | cinematic | calm | none | file:<path>",
  "captions": true,
  "language": "en",
  "brand": "./brand.json",
  "ai_tool": "runway | veo | kling | pika | seedance | pixverse | generic | null",
  "color_look": "neutral",
  "pace": "fast | medium | slow"
}
```

Destination ids: `instagram-reels`, `tiktok`, `youtube-shorts`, `youtube`, `x`,
`linkedin`, `facebook`, `whatsapp-status`, `website-loop`, `presentation`.

## 6. Style → capability → plan

Every plan starts with `core:doctor` and `core:brief`, ends with
`video:platform-export` per destination and a Look step; `video:captions` is in when
the destination says so. The middle:

| Style | Capability id | Plan middle |
|---|---|---|
| screencast-motion | `video.style.screencast-motion` | probe + inventory → `video:script` → `audio:voice` (retime) → `video:motion beats --frame phone\|browser` → `ass_text beats` + captions merge → `audio:music fit` → `timeline from-beats` → `video:assemble` |
| clips-to-short | `video.style.clips-to-short` | probe → (`transcribe`) → `scenes.py` → choose → `cut.py` → reframe (`export --fit pad`) → captions → (music, keep_source_audio) → assemble |
| slideshow | `video.style.slideshow` | `slideshow.py plan` → (cull/caption) → `motion beats --frame none` → titles → `music fit` (→ voice) → timeline (dissolves) → assemble |
| talking-head-broll | `video.style.talking-head-broll` | probe → `audio:cleanup` → `transcribe --words` → `jumpcut` → b-roll plan (approve) → `broll.py` → lower third → captions → quiet bed → assemble |
| audiogram | `video.style.audiogram` | (transcribe) → pick clip (`scenes.py --transcript`) → `audiogram.py` → captions social → export |
| lyric | `video.style.lyric` | timing source → `lyric.py plan` → visuals (`motion beats` / gradient / ai) → karaoke or reveal ASS → assemble (song at 0 dB) |
| kinetic-typography | `video.style.kinetic-typography` | `kinetic.py plan` → (voice + retime) → `ass_text beats --position center` → background → `music fit` → assemble |
| explainer-animated | `video.style.explainer-animated` | `video:script` with diagrams → voice → cards + labels (ffmpeg) or Remotion → music → assemble |
| ai-shots / anime-cartoon | `video.style.ai-shots` / `.anime-cartoon` | `video:script` (ai: beats) → anchors → `shots.py plan` → user generates → `shots.py check` (look) → voice → music → captions → `timeline --ai-dir` → assemble |
| captions only | `video.stage.captions` | probe → captions (SRT/transcribe) → export |
| export only | `video.stage.platform-export` | probe → export → check → look |

## 7. The audio plugin

Voice (`audio:voice`), music (`audio:music`) and recording clean-up (`audio:cleanup`)
live in the `audio` plugin. When a plan needs them and the plugin is not installed, the
Director says so once with the install line
(`/plugin install audio --marketplace BinaryBuddiesOrg/claude-hv-skills`) and offers
the no-voice / no-music route for this run.
