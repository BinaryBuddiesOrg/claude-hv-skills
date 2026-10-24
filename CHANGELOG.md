# Changelog

All notable changes. Versions follow semver per plugin; this file tracks the repo.

## Unreleased

- `video:platform-export`: `probe.py`, `export.py` (destination specs, blur-pad/crop fit, fps conform, HDR→SDR tone-map, two-pass loudnorm, over-length fail/trim/allow, H.264/HEVC, NVENC), `check.py` (13 spec rows, ebur128 loudness, verified flag), `look.py` (contact sheet / frame, platform safe zones); `assets/destinations.json` for 10 destinations
- `core:doctor`, `core:brief`, `core:deliver` skills; `video:director` skill with shipped decision tables; `video:producer` agent
- eval cases for platform-export, director and doctor in the `claude plugin eval` layout
- tooling: `lint_skills.py` (CONVENTIONS enforcement), `build_registry.py` (generated REGISTRY.md, `--check` gate), `gaps.py` (taxonomy − capabilities), `new_skill.py` (scaffolder), shared `_lib.py`
- `templates/skill/scripts/_common.py`: the runtime every skill script vendors — shared flags, JSON shape, exit codes, `ffprobe`, tool detection
- empty `capabilities.json` for audio, graphics, game, apps
- REGISTRY.md is now generated

## 0.1.0 — 2026-10-24 — skeleton

- Design: ARCHITECTURE, CONVENTIONS, DECISIONS (ADR-001 … 012), ROADMAP, TOOLBOX
- Marketplace `studio` with plugins `core, video, audio, graphics, game, apps, forge` (manifests only)
- `taxonomy/video.md` first draft; stubs for audio, graphics, game, apps
- `plugins/video/capabilities.json` schema with planned entries
- newadder agent draft; `research/` and `proposals/` memory layout
- Nothing installable yet; no skills beyond stubs
