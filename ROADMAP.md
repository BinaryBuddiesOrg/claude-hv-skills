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
- [ ] `tooling/`: `new_skill.py`, `lint_skills.py`, `build_registry.py`, `gaps.py`, `doctor.py`, skill template
- [ ] `claude plugin validate` passes on every plugin
- [ ] Dummy eval case proves `claude plugin eval` discovery of `evals/<skill>/<case>/`

## Phase 1 — Video, end to end — planned

Goal: one real request goes request → Director → brief → plan → Producer → verified
report on this machine, with ffmpeg only, then with optional local TTS and transcription.

- `core:doctor` — machine inventory, tool detection, install-recipe offers
- `core:brief`, `core:deliver` — brief schema, `out/<slug>/` layout, five-label report
- `video:director` — intake with Auto; question dimensions from `taxonomy/video.md`
- `video:producer` agent — probe → act → verify; hands back the report
- First capabilities: `screencast-motion` (recordings → framed, zoomed, captioned promo),
  `clips-to-short` (footage → 9:16 short with captions), `slideshow` (images → video with
  music), `platform-export` (Reels/TikTok/YouTube/X specs + checks), `captions`
  (SRT/burn-in; transcription when a local engine exists)
- Evals: three realistic prompts per capability, with and without skill
- Trigger-description optimisation for `video:director`

## Phase 2 — Audio — planned

Voice-over with local TTS (candidates in TOOLBOX.md), podcast clean-up, loudness, music
bed with ducking, SFX placement. Video depends on this for voice; build it right after.

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
