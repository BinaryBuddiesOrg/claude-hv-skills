---
name: doctor
description: >-
  Inspect the machine before planning creative or software work: OS, CPU, RAM, GPU and
  VRAM, which tools are installed and their versions (ffmpeg, Blender, Godot, Node,
  ImageMagick, whisper, piper, …), fonts by script, free disk — and offer a pinned install
  recipe for anything missing, asking first. Use whenever a Director starts a job, a
  Producer hits "command not found" or a codec/filter error, the user asks "what can this
  machine do", "is X installed", "do I have a GPU", or before recommending any tool.
  Never installs anything on its own.
license: MIT
compatibility: Python 3.10+. Richer detail when nvidia-smi, lspci, fc-list or system_profiler exist; works without them.
metadata:
  domain: core
  role: producer-support
  status: draft
  version: 0.1.0
  capabilities: []
  tools: []
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# doctor

## What this skill does and does not decide

It measures: what hardware this is, which tools exist and in which versions, which
scripts the fonts can render, how much disk is free — and turns that into a short
"usable for" summary a Director can plan from. It also knows the install recipe for every
tool Studio relies on (`references/recipes.md`) and how to offer one.

It does not decide to install. Installing changes the user's machine; the user says yes
to a named recipe with a known size, or it does not happen. It also does not decide
which tool a job *should* use — the Director picks from `capabilities.json` within what
doctor found; doctor only says what is here.

## Workflow (in this order)

1. **Run the inventory once per job**, not once per step:
   `python3 ${CLAUDE_SKILL_DIR}/scripts/doctor.py --json`. It writes nothing. Save the
   result (or its `machine` summary) into the brief's `machine` field so Producers and
   re-runs see the same facts.
2. **Read `usable`** before `tools`: it maps capability groups (`video_edit`,
   `transcription`, `tts_voiceover`, `image_ops`, `vector_svg`, `render_3d`,
   `game_godot`, `web_apps`) to ok / missing. A Director's Auto mode may only pick routes
   whose group is ok.
3. **Read `gpu.vram_gb`** when a capability declares `hardware.gpu_vram_gb_min`. No GPU or
   less VRAM than declared means the route is shown as "needs ≥ N GB VRAM", never chosen
   by Auto.
4. **When something is missing and the job needs it**, offer the recipe (next section),
   then re-run `doctor.py --tools <name>` after the user installs, and only then proceed.
5. **On a Producer failure** that smells like the environment (`command not found`,
   `Unknown encoder`, `No such filter`, a font rendering as boxes), run doctor again with
   `--tools` for the suspect and quote the fact in the report's `Notes:`.

## Decide or ask

Assume the inventory is right for this session; do not re-run it per step. Ask exactly
one thing, and only when a needed tool is missing:

> This job needs **whisper.cpp** for transcription (MIT, ~30 MB plus a 75 MB model, CPU
> is fine). Install with `<recipe>`? Or I can use the text-on-screen route without it.

Always name the alternative route when one exists, so "no" is a real option. Never
install silently, never run a recipe the user has not seen, never pick a recipe that is
not in `references/recipes.md` (anything else has not been vetted).

## Request → action

| Request looks like | Do |
|---|---|
| a Director starting any job | `doctor.py --json`; store `machine`; plan within `usable` |
| "what can this machine do", "is ffmpeg installed", "do I have a GPU" | `doctor.py` (text), answer from it |
| "install X" / user accepted a recipe | run the recipe from `references/recipes.md` exactly as written, then `doctor.py --tools X --json` to prove it |
| Producer error naming a missing binary, encoder, filter or font | `doctor.py --tools <tool> --json`; quote the fact; offer the recipe or the alternative route |
| "which TTS / transcription can I use offline" | read `usable.tts_voiceover` / `usable.transcription`; if none, list the recipes with sizes and ask |

## Tools and installation

doctor itself needs only Python. Optional detail sources, used when present: `nvidia-smi`
(GPU name and VRAM), `lspci` (GPU name on Linux without NVIDIA), `system_profiler`
(macOS GPU), `fc-list` (fonts by script). Their absence is reported as `null`, not as an
error.

Install recipes for every Studio tool live in `references/recipes.md`, one block per tool
with licence, needs, per-OS pinned command, the proving command, what it unlocks, size
and traps. Read the block for the tool in question before offering it; quote the size.

## Report format

Doctor's own answer to "what can this machine do" is the text output of `doctor.py`:

```
Machine: Linux x86_64 · 8 cores · 15.6 GB RAM · GPU NVIDIA T500 4.0 GB · 118 GB free
Present: ffmpeg 8.1.3 · ffprobe 8.1.3 · python3 3.12.3 · node 22.22.2 · godot 4.3 · docker 28.0
Missing: blender · magick · inkscape · whisper-cli · piper · yt-dlp
Usable:  video_edit ✓ · web_apps ✓ · game_godot ✓ · transcription ✗ (whisper-cli or whisper-ctranslate2) · tts_voiceover ✗ (piper) · image_ops ✗ · vector_svg ✗ · render_3d ✗
Fonts:   412 families · latin ✓ ja ✓ ko ✗ zh ✓ hi ✓ th ✗ ar ✓
```

Inside a job, doctor has no report of its own: its facts go into the brief's `machine`
field and, after an install, into the final report's `Notes:` ("installed piper 1.2.0 at
the user's request").

## Things that look right but are wrong

- `ffmpeg` present does not mean every encoder is: `libx265`, `libaom` and `libass` are
  build options. On an encoder error, run `ffmpeg -hide_banner -encoders | grep <name>`
  and report that line. -> [references/recipes.md#ffmpeg](references/recipes.md#ffmpeg)
- A GPU name without VRAM (`lspci` route) is not "4 GB"; treat unknown VRAM as none for
  planning and say so.
- Apple Silicon reports unified memory as VRAM; a 16 GB Mac can run models a 4 GB card
  cannot, but a model that wants 24 GB still will not fit.
- Python tools installed in a virtual environment are invisible to `which`; if the user
  says it is installed, ask for the path or activate the environment before re-checking.
- `fc-list :lang=ja` finding a font does not mean ffmpeg's `drawtext` will pick it; the
  caption skill names the font file explicitly for non-Latin scripts.
- The inventory is a snapshot: a tool installed mid-job needs `doctor.py --tools <name>`
  before any step relies on it.

## References

- `references/recipes.md` — open when a tool is missing: the only recipes doctor may offer.
- `scripts/doctor.py --help` — the flags (`--json`, `--tools a,b`, `--timeout`).
