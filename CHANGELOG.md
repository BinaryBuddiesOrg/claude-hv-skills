# Changelog

All notable changes. Versions follow semver per plugin; this file tracks the repo.

## Unreleased

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
