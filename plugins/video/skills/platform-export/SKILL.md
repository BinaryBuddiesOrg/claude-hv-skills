---
name: platform-export
description: >-
  Export a finished edit for a destination and prove it meets the spec: Instagram Reels,
  TikTok, YouTube Shorts, YouTube, X, LinkedIn, Facebook, WhatsApp status, website loop,
  presentation. Fits the aspect (blur-pad or crop), conforms fps, tone-maps HDR to SDR,
  normalises loudness to the platform target, encodes H.264/AAC, then checks every row of
  the spec and renders a contact sheet with the platform's UI safe zones. Use whenever a
  video is to be posted, delivered, exported, "made for Reels/TikTok/YouTube", resized to
  9:16/1:1/16:9, or when someone asks "does this meet the spec", "is it too loud", "will
  it get cut off". Also the probe for any media file.
license: MIT
compatibility: ffmpeg >= 6.0 with libx264 (libx265 for --codec hevc; zscale for HDR sources; NVENC for --hw)
metadata:
  domain: video
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [video.stage.platform-export]
  tools: [ffmpeg]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# platform-export

## What this skill does and does not decide

It turns a finished edit into the file a platform wants and proves it: frame and aspect,
constant frame rate, SDR colour, loudness at the target, the right codecs, under the
length and size caps, text outside the UI zones. Every number it reports is measured from
the output.

It does not decide the content. Whether a clip that is too long should be trimmed at the
cap or re-selected, whether a 16:9 frame should be cropped (losing the sides) or padded
(keeping everything, smaller), whether a loudness FAIL means "fix it" or "the ambience was
meant to be quiet" — those change what the viewer sees and belong to the Director or the
user. The scripts take the decision as a flag and refuse to guess the dangerous ones.

## Workflow (in this order)

1. **Probe** the edit: `python3 ${CLAUDE_SKILL_DIR}/scripts/probe.py EDIT --json`. Note
   aspect, duration against the cap, HDR, VFR, audio presence.
2. **Plan with `--dry-run`** when anything is non-obvious (aspect change, over cap, HDR):
   `export.py EDIT -o out/<slug>/<dest>.mp4 --destination <id> --dry-run --json`. Read
   `fit` and `notes`. Decide (or ask the Director to decide) fit and the over-length
   policy before the real run.
3. **Export**: same command without `--dry-run`. Two passes of loudness happen inside
   (measure, then normalise with `linear=true`), so the output lands on the target rather
   than near it. Several destinations = several exports from the same edit; captions
   must already be burned at the final frame size, so caption *before* export when the
   aspect does not change, or export first and caption the export when it does.
4. **Check**: `check.py OUT --destination <id> --json`. `verified: true` or the FAIL rows
   are the report's `Check:` line. Fix format FAILs by re-exporting with the right flag;
   report judgement FAILs (duration, aspect, loudness) with the choice they imply.
5. **Look**: `look.py OUT -o out/<slug>/look/<dest>_sheet.png --tiles 3x2 --safe <id>`,
   then **view the PNG**. Captions or logos inside the red zones are a real problem;
   letterbox bars from blur-pad are the correct result of that mode, not a defect.
6. **Report** in the five labels (`core:deliver`) with the probe numbers and the check
   counts.

## Decide or ask

Assume and say so: `--fit auto` (crop when the aspect change is ≤ 15 %, blur-pad
otherwise), centre anchor for crops, loudness on, H.264, CRF 18. Ask — through the
Director, in one bundled question — only when:

- the input is **longer than the cap**: trim at the cap (loses the end) or go back and
  select; `export.py` fails by default rather than silently cutting a 90 s story at 60 s;
- the **subject is off-centre** and a crop is wanted: pass `--crop-x 0..1`
  (0 = keep the left edge, 1 = the right) rather than guessing centre;
- a **loudness FAIL** is on material that is meant to be quiet (ambience, ASMR): re-export
  with `--no-loudness` only when the user confirms.

Never ask about codecs, pixel formats, bitrates or sample rates: the spec fixes them.

## Request → action

| Request looks like | Do |
|---|---|
| "export this for Reels / TikTok / Shorts" | one `export.py --destination instagram-reels` (same file serves all three), `check.py`, `look.py --safe tiktok` (the strictest zones) |
| "post on YouTube and Instagram" | two exports from the same edit (`youtube`, `instagram-reels`); captions burned per export frame; two checks; one sheet each |
| "make it vertical / 9:16" | `export.py --destination instagram-reels --fit pad` (default pad for 16:9→9:16); crop only if the subject is centred or asked |
| "make it square for LinkedIn" | `--destination linkedin --fit auto` (crop, 44 % of the width lost — say so) |
| "it's an iPhone HDR clip" | nothing extra: `export.py` tone-maps when the probe says HDR; `check.py` row `SDR` proves it |
| "is this ok for X?" / "too loud?" | `check.py FILE --destination x` and report the rows |
| "website background video" | `--destination website-loop` (no audio, ≤ 30 s, ≤ 8 MB); if over size, `--quality 23` |
| "what is this file?" | `probe.py FILE` |
| "fast preview first" | add `--fast` (CRF 23, veryfast); drop it for the deliverable |

## Tools and installation

`ffmpeg`/`ffprobe` ≥ 6.0 (`core:doctor` → `usable.video_edit`). Build options that
matter: `libx264` (always), `libx265` only for `--codec hevc`, `zscale` (libzimg) for HDR
sources — without it export fails on an HDR input with "No such filter: zscale"; then
re-export without tone-mapping is wrong (flat colours), so report it and offer the ffmpeg
recipe from `core:doctor`. `--hw` needs an NVENC-capable build and GPU; a failure there
is answered by dropping `--hw`, not by retrying.

Specs live in `assets/destinations.json` (read by the scripts) and are explained in
`references/destinations.md`. Adding a destination is one JSON object plus one table row.

## Report format

```
Done: out/coffee-promo/reels.mp4 — 29.97 s, 1080x1920, 30 fps, h264/aac stereo 48 kHz, -14.1 LUFS, -1.3 dBTP
Steps: probe -> export instagram-reels (blur-pad from 1920x1080, loudnorm -17.8 -> -14) -> check -> look
Check: instagram-reels — 12 pass, 0 warn, 0 fail (verified: true)
Look: out/coffee-promo/look/reels_sheet.png (captions above the bottom 20 %, blurred bars left/right as expected)
Notes: source was VFR, now constant 30 fps. For YouTube too, say so: same edit, 16:9 export, no burned captions.
```

A FAIL row changes `Done:` to `Failed:` only when the row is a format row that could not be
fixed; a judgement FAIL (too long, too loud on purpose) is `Done:` with the row quoted in
`Check:` and the decision it needs in `Notes:`.

## Things that look right but are wrong

- Burning captions *before* a 16:9 → 9:16 export puts them in the blurred side bars or
  off-frame. Frame first, captions second, export last. -> [references/destinations.md#captions-and-destinations](references/destinations.md#captions-and-destinations)
- A centre crop to 9:16 keeps 32 % of the width: a two-person shot loses one person.
  Default is blur-pad; crop needs a reason. -> [references/destinations.md#reframing-between-aspects](references/destinations.md#reframing-between-aspects)
- "Normalised" audio can still clip: `check.py` measures true peak after loudnorm;
  trust the row, not the filter.
- `-c copy` would be faster but cannot change frame, fps or loudness; this skill always
  re-encodes once, at the end, from the CRF 18 intermediate — do not export twice.
- HDR that "looks fine" on an HDR laptop is grey and flat for everyone else; the probe's
  `hdr: true` decides, not the eye.
- A 59.94 fps phone clip exported for Reels becomes 30 fps on purpose; "it dropped
  frames" is the expected conform, not a bug.
- `look.py`'s red zones show where *the platform* draws its UI; text there is unreadable
  for the viewer even though the file is perfect.
- The same 1080×1920 file serves Reels, TikTok and Shorts; exporting three times only
  costs time.

## References

- `references/destinations.md` — every destination, why its numbers are what they are, reframing and caption rules. Open when a destination is named or a row fails.
- `assets/destinations.json` — the machine-readable specs the scripts read.
- `scripts/*.py --help` — flags; `export.py --dry-run --json` is the plan.
