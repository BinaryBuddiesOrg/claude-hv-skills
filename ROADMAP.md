# Roadmap

Every heading carries a state so "on the roadmap" is never mistaken for "works":

- **shipped + tested** — in the repo, evals pass, status `tested` or `stable` in REGISTRY.md
- **shipped, untested** — in the repo as `draft`; no eval has graded it
- **in progress** — being written now
- **planned** — nothing exists yet; the lines below are intent, not description

Current version: **0.1.0** (skeleton). Nothing is installed by cloning.

## Phase 0 — Design and skeleton — in progress

- [x] Architecture, conventions, decisions, toolbox format, taxonomy format
- [x] Marketplace and plugin manifests for all domains
- [x] Video taxonomy (first draft) and capabilities schema
- [x] newadder agent draft; research/ and proposals/ memory layout
- [x] `tooling/`: `new_skill.py`, `lint_skills.py`, `build_registry.py`, `gaps.py`, skill template and vendored `_common.py` runtime
- [x] `claude plugin validate --strict` passes on the marketplace and every plugin
- [ ] First `claude plugin eval` run (billed) on the three cases below — awaiting the owner's go

## Phase 1 — Video, end to end — in progress

Goal: one real request goes request → Director → brief → plan → Producer → verified
report on this machine, with ffmpeg only, then with optional local TTS and transcription.

- [x] `core:doctor` — inventory script (30 tools, GPU/VRAM, fonts by script, `usable` map), recipe catalogue — *shipped, untested*
- [x] `core:brief`, `core:deliver` — `brief.py` (slug/new/set/validate), `out/<slug>/` layout, five-label report — *shipped, untested*
- [x] `video:director` — intake contract + shipped decision tables — *shipped, untested*
- [x] `video:producer` agent — *shipped, untested*
- [x] `video:platform-export` — probe / export (blur-pad, crop, HDR→SDR, two-pass loudness, over-length policy) / check (13 rows) / look (sheet + safe zones); exercised on synthetic clips: every path verified — *shipped, untested by eval*
- [x] `script` (beats.json, structures, timing), `captions` (SRT→ASS, styles, safe zones, transcription), `assemble` (timeline render engine), `motion` (zoom/pan, frames, animated text, cards) — *shipped, untested*
- [x] Styles: `screencast-motion`, `clips-to-short`, `slideshow`, `talking-head-broll`, `audiogram`, `lyric`, `kinetic-typography`, `explainer-animated`, `ai-shots` (+ anime-cartoon) — *shipped, untested*
- [x] Eval cases written: `platform-export/reels-from-landscape-clip`, `director/promo-from-screen-recordings`, `doctor/what-can-this-machine-do`
- [ ] Evals run with/without skill; statuses promoted to `tested` on pass — **the next job: real media through every script**
- [ ] Trigger-description optimisation for `video:director`

## Phase 2 — Audio — in progress

- [x] `audio:voice` (piper / macOS say / espeak-ng, per-beat files, measured durations, aligned track, recording alignment) — *shipped, untested*
- [x] `audio:music` (fit with crossfade loop, duck, built-in sfx, licensed sources) — *shipped, untested*
- [x] `audio:cleanup` (denoise by measured floor, de-ess, compress, trim, level) — *shipped, untested*
- [ ] piper voices vetted per language; Kokoro compared — newadder

## Phase 3 — Game — planned

Godot (installed here): headless project scaffold, scenes, GDScript patterns, asset
pipeline, export presets. Web games (Phaser / Three.js). Game design brief → vertical
slice. Director dimensions: genre, 2D/3D, engine, scope, art style.

## Phase 4 — Graphics — planned

Image ops (Pillow / ImageMagick), vector and icons (SVG, Inkscape CLI), thumbnails and
covers, background removal, 3D renders and motion (Blender headless), sprite sheets.
Several of these need installs; the Director offers them.

## Phase 5 — Apps — planned

Web (Vite/Next), mobile (Expo), desktop (Tauri), backend/API, deploy, Playwright e2e,
store assets. Least differentiated domain; the value is the Director's brief and the
verify-every-step discipline.

## Phase 6 — newadder on a schedule — planned

Weekly run per domain: gaps → research → vet → implement → gates → commit → hand-back.
Start manual; schedule once two manual runs have produced clean commits.

## Cross-cutting — planned

- CI: lint + validate + registry check on every push; evals on changed plugins
- Second-machine test (macOS) before any `stable` status
- `LICENSE` (MIT, pending owner confirmation)
