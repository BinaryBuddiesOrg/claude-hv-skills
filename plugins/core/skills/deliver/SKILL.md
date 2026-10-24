---
name: deliver
description: >-
  How every Studio job ends: the out/<slug>/ folder layout, what "verified" means for a
  video, image, audio file, app or game, the Look image Claude must actually view, and
  the five-label report (Done / Steps / Check / Look / Notes) with numbers from
  measurements. Use whenever a Producer finishes or fails a step, a Director relays a
  result, a user asks "is it done", "did it work", "show me", or any deliverable is about
  to be reported — including short jobs, failures and refusals, which use the same shape.
license: MIT
compatibility: none beyond the tools the job itself used
metadata:
  domain: core
  role: producer-support
  status: draft
  version: 0.1.0
  capabilities: []
  tools: []
---

# deliver

## What this skill does and does not decide

It fixes the end of a job: where files go, what proves each kind of output, and the
exact shape of the report. The point is trust — a user who reads `Done:` must be able to
rely on it, which is only possible if every number in it was measured and every image
named in `Look:` was viewed.

It does not judge whether the result is good. Taste ("is this cut right", "does the
thumbnail pop") belongs to the user; deliver reports what was made and what was checked,
and names what the user still has to judge.

## Workflow (in this order)

1. **Lay out `out/<slug>/`** before the first write:

   ```
   out/<slug>/
   ├── brief.json  plan.json        from core:brief
   ├── <deliverables>               final files at the top level: reels.mp4, youtube.mp4, cover.png, the app folder
   ├── work/                        intermediates; safe to delete after delivery
   ├── look/                        contact sheets, screenshots, frames Claude viewed
   ├── logs/                        one JSON per step: step-03-export.json (the script's --json output)
   └── report.md                    the five lines plus a details section
   ```

   Originals are never written to; a user file is read and left as found.
2. **Verify each deliverable** by its kind (table below), and record the measured facts
   in `logs/`. A step is done only when its script exited 0 *and* the output probes as the
   plan's `check` says.
3. **Look** when pixels changed: generate the image (contact sheet, screenshot, rendered
   frame), **view it**, and write one line about what it shows. No vision in this session
   → `Look: look/sheet.png (not inspected: no image view available)`, never a claim.
4. **Write `report.md`** and reply with the same five lines. One report per job, in the
   user's language, labels in English.
5. **Say what is next** in `Notes:`: the one or two changes the user is most likely to
   ask for, phrased as the brief edit that does it.

## Decide or ask

Deliver asks nothing. If the job is a partial success, it is `Done:` with the shortfall in
`Notes:`; if a step was refused or failed, it is `Failed:`. Never invent a third label.

## Request → action

| Output kind | Verified means | Look |
|---|---|---|
| video | probe: duration, width×height, fps, codecs, loudness match the brief and destination; platform check passes | contact sheet 3×2 (or 4×3 for long) and one frame at the riskiest moment (captions, overlay) |
| audio | probe: duration, sample rate, channels, integrated loudness and true peak at target | `Look: not needed` (waveform PNG optional) |
| image | dimensions and format match the destination; file size within limit | the image itself |
| app (web/mobile/desktop) | build succeeds; tests pass; the app starts; one screenshot per key screen | screenshots |
| game | project opens headless without errors; export succeeds; one run reaches the first playable state | screenshot or captured frame |
| document / data | opens; schema or spot-check assertions hold | rendered page or `not needed` |

## Tools and installation

None of its own. Contact sheets come from the domain skill that owns the deliverable
(video: `video:platform-export`'s `look.py`); screenshots from the apps/game skills.

## Report format

Five lines, this order, nothing before them. Numbers from `--json` output or a probe,
never from memory.

```
Done: out/coffee-promo/reels.mp4 — 30.0 s, 1080x1920, 30 fps, H.264, AAC stereo, -14.0 LUFS
Steps: probe 6 clips -> script 62 words -> tts (piper, en_US-amy) -> frame + motion -> captions -> music ducked -12 dB -> export reels + youtube
Check: instagram-reels — all 9 checks pass; youtube — pass
Look: out/coffee-promo/look/reels_sheet.png (captions inside the safe zone; no face covered; logo top-right)
Notes: clip 3 was VFR, conformed to 30 fps. Say "make it 15 s" or "swap the music" to re-render.
```

Failure keeps the shape and quotes the tool:

```
Failed: export.py exited 1 — ffmpeg: "Unknown encoder 'libx265'" (this ffmpeg has no HEVC encoder)
Steps: probe -> edit -> captions -> export (failed); reels.mp4 not written
Check: nothing to verify
Look: not needed
Notes: install an ffmpeg build with libx265 (recipe in core:doctor), or say "H.264 is fine" and I re-export.
```

A refusal is `Failed:` naming why ("input is HDR and the request forbids tone-mapping").
A partial result is `Done:` with the gap in `Notes:` ("YouTube export done; Reels skipped:
source is 4:3 and you asked for no padding").

`report.md` holds the same five lines, then `## Details` with the per-step facts from
`logs/` and the `auto_decisions` from the brief, so the file stands on its own.

## Things that look right but are wrong

- "Exported successfully" from a tool's stdout is not verification; the probe of the
  output is. Report the probe.
- A `Look:` line naming an image nobody viewed. If it was not viewed, say so.
- Rounding to the brief ("30 s") instead of the measurement ("29.97 s"): report the
  measurement, then note that it meets the brief.
- Reporting loudness from the target instead of a measurement — `-14 LUFS` only after a
  loudness measurement says so.
- Writing deliverables next to the user's inputs. Everything goes under `out/<slug>/`.
- Deleting `work/` before the user has seen the result; it is the only way to re-render
  one step without redoing all.
- A reply that starts with prose and buries the five lines. The five lines come first.

## References

- `core:brief` — where `auto_decisions` and the plan's checks come from.
- `video:platform-export` — destination checks and contact sheets for video deliverables.
