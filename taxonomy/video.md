# Video taxonomy

The universe of what the `video` domain covers. The Director generates its question
options from this file; `plugins/video/capabilities.json` says which of it Studio can do
today; the difference is newadder's worklist. Grow this file when the world grows, not
when a skill is added.

## 1. Intents — what the video is for

| Intent | Typical length | Typical destination | Notes |
|---|---|---|---|
| promo / ad | 15–60 s | Reels, TikTok, Shorts, X | hook in 2 s, one message, call to action |
| product demo | 30 s – 3 min | website, YouTube, LinkedIn | show the thing working; screencast or footage |
| explainer | 1–3 min | YouTube, website | concept → steps → takeaway; often animated |
| tutorial / how-to | 3–15 min | YouTube | chapters, on-screen steps, no music under speech |
| social short (entertainment) | 7–60 s | Reels, TikTok, Shorts | pace, captions always on, trend-aware |
| trailer / teaser | 15–90 s | YouTube, X, website | rhythm cut to music, title cards |
| highlight reel | 30 s – 3 min | YouTube, Reels | from long footage; candidates ranked, human picks |
| talking head / vlog | 1–15 min | YouTube | jump cuts, b-roll inserts, captions optional |
| podcast clip / audiogram | 15–90 s | Reels, X, LinkedIn | waveform or static art + captions |
| slideshow / recap | 30 s – 3 min | WhatsApp, Facebook, YouTube | photos, Ken Burns, music, titles |
| music / lyric video | full song | YouTube | lyrics timed, visuals loop or footage |
| story / animation | 30 s – 5 min | YouTube, Shorts | cartoon, anime, motion comics; tool-dependent |
| kinetic typography / quote | 10–30 s | Reels, LinkedIn | text is the visual; music drives timing |
| meme / reaction | 5–30 s | TikTok, X | template-driven; speed |
| screencast / walkthrough | 1–10 min | YouTube, docs, support | cursor, zooms, callouts, chapters |
| testimonial | 30–90 s | website, LinkedIn | one speaker, lower third, b-roll |
| event / documentary cut | 2–20 min | YouTube | multicam, sync, chapters |

## 2. Destinations — what the platform fixes

| Destination | Aspect | Max length | Loudness | Safe zones / traps |
|---|---|---|---|---|
| Instagram Reels | 9:16 (1080×1920) | 90 s | −14 LUFS | bottom ~20 % and right column covered by UI |
| TikTok | 9:16 | 10 min (60 s performs) | −14 LUFS | same UI overlays; captions high-centre |
| YouTube Shorts | 9:16 | 60 s (180 s allowed) | −14 LUFS | title overlay top |
| YouTube | 16:9 (1920×1080 / 4K) | any | −14 LUFS | end screens last 20 s; chapters from timestamps |
| X / Twitter | 16:9 or 1:1 | 140 s (longer for subscribers) | −14 LUFS | autoplay muted → captions |
| LinkedIn | 1:1 or 16:9 | 10 min | −14 LUFS | muted autoplay → captions; professional pace |
| Facebook | 1:1, 4:5, 16:9 | long | −14 LUFS | muted autoplay |
| WhatsApp status | 9:16 | 30 s per status | — | heavy compression; big text |
| Website hero / background | 16:9 or 21:9 | 10–30 s loop | muted | no audio, seamless loop, small file |
| App Store / Play preview | device-specific | 15–30 s | — | exact resolutions per device |
| Presentation / embed | 16:9 | any | −16 LUFS | plays in a room; no platform UI |
| Broadcast / TV | 16:9 | spec | −23 LUFS (EBU R128) | strict specs; out of scope until asked |

## 3. Formats

- **Aspect**: 16:9, 9:16, 1:1, 4:5, 21:9. Reframing 16:9 → 9:16 by crop loses ~70 % of
  the width; by pad keeps everything with bars; by "smart crop" follows a subject.
- **Resolution**: 1080p default; 4K when the source is 4K and the destination is YouTube;
  720p for WhatsApp.
- **Frame rate**: keep the source; 30 fps default for screen recordings; 24 for cinematic;
  60 for gameplay.
- **Duration bands**: ≤ 15 s, 15–30 s, 30–60 s, 1–3 min, 3–10 min, 10 min +.
- **Codecs**: H.264 + AAC for every social destination; HEVC/ProRes only when asked;
  HDR sources are handled explicitly (tone-map to SDR or keep HDR), never by accident.

## 4. Visual sources — where the pixels come from

| Source | Needs | Notes |
|---|---|---|
| user footage (camera, phone) | ffmpeg | probe for HDR, VFR, rotation |
| screen recordings | ffmpeg | usually VFR; cursor and zoom matter |
| photos / images | ffmpeg (or Pillow) | Ken Burns, crossfades, aspect fitting |
| slides (PDF, PPTX) | converter → images | one slide per beat |
| user-provided stock / b-roll | ffmpeg | licence is the user's responsibility; say so once |
| generated graphics (text, shapes, charts) | ffmpeg drawtext/filters, or Remotion/Motion Canvas | kinetic type, lower thirds, device frames |
| 3D renders | Blender headless | slow on CPU; product shots, titles |
| whiteboard / hand-drawn | tool-dependent | candidate tools in TOOLBOX |
| anime / cartoon animation | heavy GPU or external tools | ≥ 12 GB VRAM for local diffusion; otherwise 2D rigging tools |
| avatar / talking head synthesis | heavy GPU | not a default anywhere |

## 5. Style families

A style family is the unit a Director offers as an option and a capability implements.

| Family | One line | Typical sources |
|---|---|---|
| `clips-to-short` | cut the best moments, reframe, captions, music | footage |
| `screencast-motion` | device frame, zoom/pan on the action, kinetic captions, cursor emphasis | screen recordings |
| `slideshow` | images with motion and transitions, titles, music | photos, slides |
| `kinetic-typography` | words are the picture, timed to voice or music | script only |
| `explainer-animated` | motion graphics: icons, shapes, diagrams, transitions | script + assets |
| `talking-head-broll` | speaker with jump cuts, inserts, lower thirds | footage + b-roll |
| `cinematic` | colour grade, speed ramps, music-driven cuts, letterbox | footage |
| `audiogram` | audio with waveform or art and captions | audio + image |
| `lyric` | timed lyrics over visuals | audio + lyrics |
| `whiteboard` | drawn-in illustrations with narration | script |
| `anime-cartoon` | 2D animated characters and scenes | script; tool-dependent |
| `3d-product` | rendered product or title sequences | model or text |
| `meme-format` | template with text and timing | template + text |

## 6. Pipeline stages

brief → script / storyboard → assets (gather, probe, fix VFR/HDR/rotation) → voice
(TTS, recording clean-up, or original audio) → edit (cut, order, reframe) → motion and
graphics (frames, zooms, titles, lower thirds) → captions → music and SFX (bed, ducking)
→ colour (grade, LUT, tone-map) → export (per destination) → QA (spec check + contact
sheet + one human look).

Frame changes before captions (text is sized for the final frame); captions before export
(never upscale burned text); loudness last before export.

> Sections 7–10 are mirrored in the shipped copy the Director reads at run time:
> `plugins/video/skills/director/references/decisions.md` (plugins are installed alone, so
> the plugin cannot read this file). Edit both; a lint check for drift is planned.

## 7. Question dimensions — what the Director may ask

Ordered by plan impact. The Director asks only the open ones, at most four, one round,
Auto first. A dimension already fixed by the request or a probe is never asked.

| Dimension | Why it changes the plan | Options (Auto first) |
|---|---|---|
| **destination** | fixes aspect, length cap, loudness, safe zones, captions default | Auto (from intent) · Reels/TikTok/Shorts 9:16 · YouTube 16:9 · LinkedIn/X 1:1 · website loop · several (export each) |
| **length** | trim vs. speed vs. select; script length; music edit | Auto (from intent band) · 15 s · 30 s · 60 s · 1–3 min · 3–10 min |
| **style family** | selects the whole pipeline and the tools | Auto (from sources + intent) · the families in § 5 that fit the sources, with "needs <tool>" when not installed |
| **voice** | TTS needs a script and an engine; recording needs clean-up; none needs on-screen text | Auto (local TTS if installed, else text-on-screen + music) · no voice, music only · my recording · keep original audio |
| language | fonts, TTS voice, caption script | asked only when the request or inputs are not in one obvious language |
| brand | colours, font, logo placement | asked only when the user mentions a brand, logo or "our style"; create `brand.json` once |
| pace / mood | music choice, cut rhythm | never asked; inferred from intent, overridable later |

## 8. Auto decision table

Each row: condition → decision, with the reason the Director records in
`auto_decisions`.

| Condition | Decision | Reason recorded |
|---|---|---|
| intent promo/ad, no destination | Reels + Shorts (9:16), 30 s | "promo defaults to vertical social; 30 s holds attention and fits every short-form cap" |
| intent tutorial/explainer, no destination | YouTube 16:9, length from script | "long-form instruction lives on YouTube; length follows the content" |
| "social" said, nothing else | 9:16 for Reels/TikTok/Shorts, one export fits all three | "all three accept 1080×1920 ≤ 60 s" |
| user says "website" | 16:9, muted loop 10–20 s, no captions | "hero videos autoplay muted and loop" |
| sources are screen recordings | `screencast-motion` | "recordings read best framed and zoomed; raw screen is unreadable on a phone" |
| sources are photos only | `slideshow` | "stills need motion to hold attention" |
| sources are footage, short requested | `clips-to-short` | "cut, reframe, caption is the proven short-form shape" |
| no sources at all | `kinetic-typography` (or `explainer-animated` when a tool is installed) | "text is the visual that needs no footage" |
| destination is social | captions on | "most social playback is muted" |
| destination YouTube long-form | captions off (sidecar SRT offered) | "YouTube has its own captions; burned text competes with chapters" |
| voice needed, local TTS installed | TTS from the script, voice by language | "voice-over doubles retention of explainers" |
| voice needed, no TTS installed | offer the install once; else text-on-screen + music | "never block a job on a missing engine" |
| music for promo/trailer/slideshow | upbeat/cinematic bed, ducked −12 dB under speech | "music drives pace; speech must win" |
| music for tutorial/testimonial | none | "music under instruction lowers comprehension" |
| 16:9 footage → 9:16 | pad with blurred background, unless the subject is clearly centred (then crop) | "crop loses 70 % of the frame; blur-pad keeps the content" |
| HDR source → social | tone-map to SDR | "social players flatten HDR unpredictably" |
| source is VFR (screen/phone) | conform to 30 fps constant | "VFR breaks captions timing and some players" |
| loudness, any social | −14 LUFS, true peak −1 dBTP | "platform normalisation target" |

## 9. Defaults (when nothing says otherwise)

30 fps, H.264 high profile, AAC 48 kHz stereo, CRF 18 intermediates and a platform
export last, captions white with dark outline inside the safe zone, one sans-serif that
has glyphs for the caption language, music ducked under speech, originals never touched,
everything written under `out/<slug>/`.

## 10. Brief keys (video adds to the common brief)

`destination[]`, `aspect[]`, `duration_s`, `style[]`, `visual_source`, `voice`,
`music`, `captions` (bool or style), `language`, `brand` (path), `color_look`, `pace`.

## 11. Gaps newadder should look at first

- anime / cartoon and hand-drawn styles: which 2D tools run on CPU or ≤ 4 GB GPU
- local TTS: voice quality and licences of Piper, Kokoro and newer engines
- local transcription: whisper.cpp vs faster-whisper speed on CPU for 10-minute inputs
- programmatic motion graphics: Remotion / Motion Canvas vs pure ffmpeg for device
  frames and kinetic captions — which is faster to install and more reliable headless
- smart reframing (subject-following crop) without a GPU
- slides (PDF/PPTX) → images without LibreOffice
