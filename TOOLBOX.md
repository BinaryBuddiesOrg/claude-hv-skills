# Toolbox

The curated catalogue of external tools Studio knows how to use. Skills declare tools
from this list; `core:doctor` detects them; Directors offer the recipe when one is
missing. newadder maintains this file with evidence links and re-checks each entry on
its freshness date.

Nothing here is installed by cloning the repo. Every entry is an offer.

This file is the maintainers' ledger: vetting status, evidence, rejections. The copy end
users receive — the recipes a Director may actually offer — is
`plugins/core/skills/doctor/references/recipes.md` (plugins are installed alone, so the
recipe text must live inside `core`). When a recipe changes, change both; newadder's
vetting updates the status line in both.

## Entry format

```
### <tool>                         vetted: <date> | by: <who> | re-check: <date>
what:     one line
why this: what it beats and why
licence:  SPDX
needs:    CPU ok | GPU ≥ N GB | network for first-run model download
linux:    <pinned command>        macos: <pinned command>        windows: <pinned command or "not supported">
proves:   <command that exits 0 when it works>
unlocks:  which capabilities
size:     binary and model sizes; where models go (${CLAUDE_PLUGIN_DATA}/<tool>/)
traps:    one line each
links:    homepage, release page, the research note in research/
```

Vetting rubric (ADR-004): licence allows use; pinned version from a registry or tagged
release; no `curl | bash`; no telemetry or account requirement; runs offline.

## Machine snapshot (this development machine, 2026-10-24)

Linux, 8 cores, 15 GB RAM, NVIDIA T500 4 GB. Present: ffmpeg/ffprobe 8.1.3, Godot,
Node 22, Python 3.12, uv, Docker, Java, gcc/cmake/make, git. Absent: Blender,
ImageMagick, Inkscape, GIMP, sox, Rust, Go, gh, yt-dlp, whisper, aseprite, tiled.
`core:doctor` produces this per machine; this snapshot only anchors the first decisions.

## Video

| Tool | What | Status |
|---|---|---|
| ffmpeg / ffprobe | the engine for every cut, encode, probe, caption burn, export | **present**; the reference implementation of its use is ffmpeg-skill (MIT) |
| whisper.cpp or faster-whisper | local speech-to-text for captions and silence-aware cuts | candidate; needs vetting of model sizes vs CPU time |
| Remotion / Motion Canvas | programmatic motion graphics in TypeScript (kinetic type, device frames) | candidate; Node present; weigh against pure-ffmpeg drawtext/zoompan |
| Manim | mathematical/explainer animation | candidate; Python; heavy LaTeX dependency is the trap |
| yt-dlp | download reference footage/audio | candidate; legal note required in the skill: only content the user may use |
| ImageMagick | thumbnails, contact sheets, image prep | candidate; absent here |
| Blender (headless) | 3D titles, product shots, camera moves | candidate; large install; CPU render works, slow |

| poppler (`pdftoppm`) | PDF pages → images for slideshows | candidate; recipe in core:doctor |
| LibreOffice (`soffice`) | PPTX → PDF headless | candidate; heavy install, offered with the size |
| Remotion | React compositions rendered headless (explainer route B) | candidate; `plugins/video/skills/explainer-animated/assets/remotion/` ships a composition; pin a version when vetted |

AI video generation (Veo, Runway, Kling, Pika, Seedance, PixVerse) is **not a tool
Studio runs**: `video:ai-shots` writes the shots and prompts, the user generates in
their own account, Studio verifies and assembles (ADR-002). The per-tool table lives in
`plugins/video/skills/ai-shots/references/tools.md` and is re-vetted every 30 days by
newadder. Local generation (Wan 2.x, CogVideoX, AnimateDiff pipelines) needs ≥ 12–24 GB
VRAM and minutes per clip; it is recorded here as a heavy-hardware route, never a
default. newadder's first video research task is to vet the candidates above and run
every shipped script on real media.

## Audio

| Tool | What | Status |
|---|---|---|
| ffmpeg | loudness, mixing, ducking, format | **present** |
| Piper / Kokoro | local neural TTS for voice-over | candidates; CPU-capable; vet voice quality and licences; `audio:voice` drives piper, macOS `say`, espeak-ng |
| espeak-ng | fallback synthetic TTS | candidate; drafts and timing only |
| sox | quick audio transforms | candidate; absent here |
| Local music generation | background music | heavy; record options, no default |

## Graphics

Pillow (Python), ImageMagick, Inkscape CLI (SVG → PNG/PDF), rembg (background removal,
CPU ok), Blender headless, LibreSprite/Aseprite (pixel art; Aseprite is paid). All
candidates; none vetted yet.

## Game

Godot (**present**; headless `--export-release`, `--script` for automation), Phaser,
Three.js, Tiled (maps), LDtk (levels). Candidates for vetting.

## Apps

Node 22 (**present**), pnpm (**present**), Vite, Next.js, Expo, Tauri, Playwright,
Docker (**present**). Mostly mainstream; vetting focuses on scaffold versions and the
verify step (tests, screenshots) per stack.

## Rejected

Kept so they are not re-evaluated; see `proposals/` for the full reason.

| Tool | Date | Reason |
|---|---|---|
| — | — | — |
