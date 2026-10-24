# Music and SFX sources, licences, levels

## Where a bed may legitimately come from

| Source | Licence | What it requires | Notes |
|---|---|---|---|
| The user's own purchased/licensed library | per licence | keep the receipt | the common case for brands |
| YouTube Audio Library (studio.youtube.com) | YouTube's licence | credit for some tracks | fine for YouTube; read the per-track terms for other platforms |
| Free Music Archive | CC BY / CC BY-SA / CC0 | credit line for BY; same licence for SA | check "commercial use allowed" |
| Pixabay Music / Mixkit | their own royalty-free licence | no credit | commercial OK; no reselling the track |
| Incompetech (Kevin MacLeod) | CC BY 4.0 | credit line | widely used |
| ccMixter | CC variants | per track | check each |
| Epidemic Sound / Artlist / Musicbed | subscription | active subscription at publish time | the user's account |

Record in the brief: `constraints.music_licence = {"title", "artist", "source", "licence", "credit_line"}`.
The credit line, when required, goes in the report's `Notes:` and in the video's
description; say so.

Never: tracks ripped from streaming services, "no copyright" YouTube uploads of
commercial songs, anything whose licence cannot be named.

## SFX

Freesound (CC0 / CC BY per sound), Mixkit, Pixabay, the user's packs. Built-in
synthesised set in `sfx.md` for drafts and when nothing else exists.

## Levels

| Element | Integrated loudness | Notes |
|---|---|---|
| voice track | −16 LUFS, −1.5 dBTP | `audio:voice` / `audio:cleanup` level it |
| music bed | −18 LUFS before ducking | `music.py fit` levels it |
| duck under speech | −12 dB (−15 for dense narration) | 15 ms attack, 300 ms release |
| sfx | −6 dB relative to the mix | short, never under speech |
| final export | per destination (−14 social, −16 podcast/presentation) | `video:platform-export` |

## Loop and trim

A bed shorter than the video loops at a bar boundary: `fit` detects onsets and picks
the loop point nearest to a multiple of the detected bar length; a 1-beat crossfade
hides the seam. Longer than the video: `--start-at` chooses the section (a drop at 42 s
is usually a better start than the intro), trim at the end with a fade.
