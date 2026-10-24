---
name: screencast-motion
description: >-
  The style for app and software videos: screen recordings become a promo, demo or
  walkthrough — framed in a phone or browser mockup over a blurred or branded background,
  zoomed on the UI element the voice is talking about, with a scripted voice-over,
  kinetic on-screen text, captions, music, and platform exports. Use whenever the inputs
  are screen captures or the user says "app promo", "product demo video", "show the
  feature", "walkthrough", "SaaS video", "mockup video", "zoom in on the button" — or a
  Director's plan picks screencast-motion.
license: MIT
compatibility: ffmpeg >= 6.0; optional piper/say/espeak-ng for voice (audio plugin); optional whisper for captions from a recorded voice
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.style.screencast-motion]
  tools: [ffmpeg, piper?]
---

# screencast-motion

## What this skill does and does not decide

It is the recipe that chains the other skills for screen recordings: script → voice →
per-beat framed and zoomed clips → on-screen text → captions → music → assemble →
export. It owns the choices that make a screencast watchable on a phone: which
recording moment shows which claim, where to zoom, how tight, when text appears.

It does not record the screen (the user's recordings are inputs), does not invent
features the recordings do not show (the script is checked against what is on screen),
and does not decide the brand (a `brand.json` or the user's words do).

## Workflow (in this order)

1. **Probe the recordings** (`platform-export`'s `probe.py`): portrait phone captures
   (1080×2340-ish) → phone frame on 9:16; desktop captures (1920×1080+) → browser frame
   on 16:9 (and a phone-less 9:16 crop-zoom version for social if both destinations are
   asked). Note total length and that they are usually VFR (the clips are conformed).
2. **Watch what is there**: `look.py` a 4×3 sheet of each recording; write a one-line
   inventory per recording ("00–06 s onboarding, 06–14 s menu, 14–20 s checkout") into
   `work/inventory.md`. The script can only claim what this shows.
3. **Script** (`video:script`): promo or demo structure; every beat's `visual.source`
   is a recording with `in_s` from the inventory, `focus` on the UI element named by the
   voice (estimate from the sheet: a button at the lower third → `[0.5, 0.78]`), `zoom`
   1.4–1.8 for a tap, 1.0–1.2 for a screen overview, `motion` `push-in` on reveals,
   `hold` while reading. Validate and time.
4. **Voice** (`audio:voice`): synthesise, write measured durations back, retime, rebuild
   the track. No engine → text-on-screen carries the message (the Director chose).
5. **Motion** (`video:motion`): `motion.py beats … --frame phone --bg blur` (or
   `--bg #RRGGBB` from the brand); `ass_text.py beats … --reveal word --position lower --safe <dest>`.
6. **Captions** (`video:captions`) from the beats (`script.py srt` → `srt.py to-ass`),
   merged with the motion text (`ass_text.py merge`), captions lowest.
7. **Music** (`audio:music fit`) at the edit length; sfx `click`/`pop` on tap beats if asked.
8. **Assemble** (`timeline.py from-beats` → `assemble.py`), **export** per destination,
   **look**: the sheet must show the phone frame intact, the zoomed UI readable, text
   above the UI zones.

## Decide or ask

Decide: frame by capture orientation; blur background; zoom per beat from the voice;
word-reveal text for social, line pop for 16:9; captions on for social; upbeat bed for
promo, none for a walkthrough. Everything else comes from the brief. Ask nothing here;
the Director's one round covered destination, length, voice.

## Request → action

| Request looks like | Do |
|---|---|
| "promo for my app from these recordings" | full workflow, promo structure, 30 s, 9:16 + 16:9 |
| "demo of the checkout feature" | demo structure; beats only on the checkout moments; `zoom` 1.5 on each tap |
| "walkthrough for support / docs" | 16:9 browser frame, tutorial structure, user's voice or TTS, captions `clean`, no music, chapter titles |
| "zoom in when I tap" | set `focus`+`zoom` on those beats; sfx `click` |
| "use our colours / logo" | `brand.json` (`accent`, `bg`, `font`, `logo`) → `--bg`, `--accent`, `cards.py badge` overlay |
| "no voice, just text" | `voice.mode: none`; on-screen lines carry the message; music bed |
| "make the 16:9 version too" | same beats, `--frame browser`, re-render motion + text at 1920×1080, export youtube |

## Tools and installation

`ffmpeg` for everything visual. Voice needs the `audio` plugin and a local engine
(`core:doctor` → `usable.tts_voiceover`; piper recipe offered once). Captions from the
script need nothing; from a recorded voice they need a local whisper.

## Report format

```
Done: out/coffee-promo/reels.mp4 — 29.9 s, 1080x1920, 30 fps, h264/aac, -14.0 LUFS; youtube.mp4 — 29.9 s, 1920x1080
Steps: probe 3 recordings (VFR, conformed) -> inventory -> script (7 beats) -> voice (piper amy, retimed) -> motion (phone frame, blur, zoom 1.4–1.6) -> text (word reveal) -> captions -> music -> assemble -> export ×2 -> look
Check: reels 13/13 pass; youtube 11/11 pass; every beat's clip = its duration; focus points on the named UI
Look: out/coffee-promo/look/reels_sheet.png (phone frame intact, "Order" button readable at 1.6×, text above the zone)
Notes: b5 claims "loyalty points" — shown at rec/c.mp4 12 s. Say "tighter on b4", "no frame", or "calmer music" to re-render only that.
```

## Things that look right but are wrong

- A claim in the voice that the screen never shows: viewers notice. The inventory
  gates the script. -> [references/inventory.md](references/inventory.md)
- Zooming on the whole screen (1.2×) for a tap: unreadable on a phone. 1.5× on the element.
- Raw screen with no frame on 9:16: looks like a bug report. Frame it, blur behind.
- Text and captions at the same height: merge keeps captions lowest, text above.
- Cursor-less desktop capture with a "click here" voice: add `sfx click` and a zoom, or
  the viewer cannot find the click.
- VFR recordings assembled unconformed: captions drift. Motion conforms every clip.
- Voice estimated, not measured: the last beat is cut off. Measured durations, always.

## References

- `references/inventory.md` — how to inventory recordings from a sheet and map claims to moments.
- `video:script` § structures (promo, demo, tutorial), `video:motion` § frames.
