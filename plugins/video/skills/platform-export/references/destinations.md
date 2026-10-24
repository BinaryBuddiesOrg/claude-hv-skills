# Destinations

What each platform fixes, and why. The machine-readable copy that `export.py` and
`check.py` read is `../assets/destinations.json`; keep the two in step. The Director reads
this table for the destination question.

| Id | Aspect · frame | fps | Max length | Loudness | Captions default | Safe zones (UI) |
|---|---|---|---|---|---|---|
| `instagram-reels` | 9:16 · 1080×1920 | 30 | 90 s | −14 LUFS, −1 dBTP | on | bottom 20 %, right 12 %, top 8 % |
| `tiktok` | 9:16 · 1080×1920 | 30 | 10 min (60 s performs) | −14 / −1 | on | bottom 22 %, right 12 %, top 10 % |
| `youtube-shorts` | 9:16 · 1080×1920 | 30 | 180 s (60 s classic) | −14 / −1 | on | bottom 18 %, right 10 %, top 8 % |
| `youtube` | 16:9 · 1920×1080 (4K ok) | source | none | −14 / −1 | off (sidecar SRT) | none |
| `x` | 16:9 · 1920×1080 | 30 | 140 s | −14 / −1 | on | none |
| `linkedin` | 1:1 · 1080×1080 | 30 | 10 min | −14 / −1 | on | none |
| `facebook` | 4:5 · 1080×1350 | 30 | 4 h | −14 / −1 | on | none |
| `whatsapp-status` | 9:16 · 720×1280 | 30 | 30 s, ≤ 16 MB | −14 / −1 | on | bottom 15 %, top 10 % |
| `website-loop` | 16:9 · 1920×1080 | 30 | 30 s, ≤ 8 MB | no audio | off | none |
| `presentation` | 16:9 · 1920×1080 | source | none | −16 / −1 | off | none |

## Why these numbers

- **9:16 at 1080×1920** is accepted by Reels, TikTok and Shorts alike, so one export
  serves all three; only the safe zones differ, and the strictest (TikTok's) is safe for
  the others.
- **−14 LUFS integrated, −1 dBTP** is what the social platforms normalise to; delivering
  louder gets turned down (and clipped first), quieter gets left quiet. Speech-first
  destinations (podcast, presentation) sit at −16.
- **30 fps** for social: phones record 30/60 VFR, platforms re-encode to 30; conforming to
  constant 30 keeps captions in sync. YouTube keeps the source rate because 24 fps film
  or 60 fps gameplay should stay what it is.
- **Safe zones** are the parts of the frame the platform's own UI covers (caption row,
  action icons, title). Burned text there is unreadable; `look.py --safe <id>` draws them.
- **Max length** is the platform's hard cap; the "performs" note is the practical one.
- **Size caps** matter for WhatsApp (16 MB, heavy recompression) and website loops
  (every visitor downloads it); elsewhere quality wins.

## Reframing between aspects

- 16:9 → 9:16 by **crop** keeps 32 % of the width; only right when the subject is
  centred. By **blur-pad** (default) the whole frame is shown over a blurred, enlarged
  copy of itself — the look every short-form feed is used to.
- 9:16 → 16:9: blur-pad left and right; crop would lose the top and bottom thirds.
- 16:9 → 1:1 or 4:5: crop is usually acceptable (loses ~44 % / ~30 % of the width);
  `export.py --fit auto` crops when the aspect change is small and pads when it is large.

## Captions and destinations

Muted autoplay (Reels, TikTok, X, LinkedIn, Facebook) makes burned captions the default.
YouTube long-form gets a sidecar `.srt` instead: YouTube renders its own captions and
burned text competes with chapters and end screens.
