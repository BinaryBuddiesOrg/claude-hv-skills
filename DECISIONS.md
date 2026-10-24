# Decisions

Architecture decisions, newest last. Each entry says what was decided, why, and what it
costs, so a future reader (human or newadder) can tell whether the reason still holds
before changing it. Changing a decision means editing its entry in the same commit.

## ADR-001 — The repo is a plugin marketplace with one plugin per domain (2026-10-24)

**Decision.** Root `.claude-plugin/marketplace.json`; `plugins/<domain>/` each a plugin.
**Why.** Users install only the domains they want; skills are namespaced
(`/video:director`) so they never clash with a user's own; each plugin is versioned and
evaluated on its own; domain agents and commands have a natural home.
**Costs.** One manifest per domain; plugins must be self-contained (installing copies
only the plugin folder), so shared code is vendored, not imported.

## ADR-002 — Studio is a driver, not a toolchain (2026-10-24)

**Decision.** No external AI APIs. The repo supplies knowledge (tools, recipes,
interview strategy, decision tables, pitfalls, prompts, links); Claude does the thinking
and the work with local tools it installs on request.
**Why.** The user's words: Claude is already the AI in the session; what it lacks is the
specialist's knowledge, not another model. Keeps the repo free, offline-capable, and
usable by anyone with Claude Code.
**Costs.** Generative steps (images, music, synthetic video) depend on local tools and
the user's hardware; on weak hardware those capabilities are offered as heavy options or
not at all, honestly.

## ADR-003 — ffmpeg-skill is a reference, not a dependency (2026-10-24)

**Decision.** Study kajisho5/ffmpeg-skill (MIT); write Studio's own video skills in
Studio's structure; attribute borrowed patterns (report format, probe-first workflow).
**Why.** Studio's video skills are knowledge-first with few scripts (ADR-002); a 42-tool
dependency would dominate the plugin and fix its design. Speed comes from reading its
hard-won gotchas, not from vendoring its code.
**Costs.** Re-deriving some verification helpers; must keep attribution honest.

## ADR-004 — newadder commits autonomously, behind automated gates (2026-10-24)

**Decision.** newadder commits to `main` without a human review step, and only after
`lint_skills.py`, `claude plugin validate --strict`, `build_registry.py --check` and the
affected evals pass; its vetting rubric (licence, pinned install, no `curl | bash`, no
telemetry, offline) is mandatory before any tool enters the repo.
**Why.** The user chose speed of growth over review latency.
**Costs and mitigations.** A bad pick ships to every user on the next update. Mitigated
by the gates, by `draft` status (Auto never selects a draft capability), by recording
rejected candidates so they are not retried, and by a human reading the hand-back report.
Revisit if an incident occurs: the fallback is "auto-merge docs and evals, PR for tools".

## ADR-005 — Evals live at plugin level: `plugins/<domain>/evals/<skill>/<case>/` (2026-10-24)

**Decision.** Not inside the skill folder.
**Why.** `claude plugin eval` globs `<plugin>/evals/**/case.yaml` recursively, so this
layout runs natively, groups cases by skill, and keeps one `results/` folder. The
skill-creator loop can point at any case folder, so nothing is lost.
**Costs.** A skill copied out of the repo on its own leaves its evals behind; the
scaffolder can copy them when exporting.

## ADR-006 — Scripts are Python 3.10+ standard library; Node only in web skills (2026-10-24)

**Why.** The end user's machine has Python and not our dependencies; the ffmpeg-skill's
zero-dependency rule proved this works at scale. Web app/game skills already assume Node.
**Costs.** No PyYAML (use JSON/TOML), no requests (use urllib), more code for some tasks.

## ADR-007 — Frontmatter restricted to the portable set; tracking data in `metadata` (2026-10-24)

**Decision.** `name, description, license, compatibility, metadata, allowed-tools` only
(claude.ai rejects anything else). `metadata.{domain, role, status, version,
capabilities, tools}` drives REGISTRY.md.
**Costs.** `forge` skills that need Claude-Code-only keys (`context: fork`) are the
exception and never leave Claude Code.

## ADR-008 — Nothing installs implicitly (2026-10-24)

**Decision.** Skills declare tools; `core:doctor` detects; the Director offers a pinned
recipe with size and purpose and asks; model weights go to `${CLAUDE_PLUGIN_DATA}`.
**Why.** Users install Studio into their own projects; silent installs would be a breach
of trust and a support nightmare. Also keeps cloning the repo side-effect free.

## ADR-009 — Names: marketplace `studio`, plugins one word (2026-10-24)

**Decision.** Marketplace `studio` (placeholder; a one-line rename), plugins `core,
video, audio, graphics, game, apps, forge`. Never `claude-*` (validation rejects it).
**Why.** `claude plugin install video@studio` reads well; the repo folder can stay
`claude-skills`.

## ADR-010 — The brief is the state; outputs under `out/<slug>/` (2026-10-24)

**Decision.** `brief.json` written before work, `plan.json` next, deliverables and
`report.md` beside them; every change is a brief edit plus re-run.
**Why.** Iteration without re-interviewing; reproducibility; the Producer reads the
brief, not the chat, so a forked agent has everything it needs.
**Costs.** `out/` may collide with an existing folder; the Director asks when it does.

## ADR-011 — Five-label report (2026-10-24)

**Decision.** `Done/Failed, Steps, Check, Look, Notes`, numbers from measurements.
**Why.** Users can scan it; Claude cannot claim success without a probe; adopted from
ffmpeg-skill where it is proven across hundreds of eval runs.

## ADR-013 — Plugin versions are stamped from git history before every commit (2026-10-25)

**Decision.** `tooling/stamp_versions.py` sets each `plugin.json` `version` to
`0.<N>.0`, N = commits that touched that plugin (plus the one being made). It runs in
the gate before `git add`; `--check` is part of lint.
**Why.** With a fixed version an installed user stays pinned until the number changes,
and it was not being bumped. Removing `version` would let installs track commits, but
`claude plugin validate --strict` (the gate) treats a missing version as an error. A
stamped version keeps the validator strict and still bumps on every change, so
`claude plugin update video@studio` always brings the latest.
**Costs.** Versions are not hand-chosen semver (a breaking change is not visible as a
major); if that is wanted later, a `MAJOR` override per plugin can be added to the stamp.

## ADR-012 — Licence MIT (proposed, 2026-10-24)

**Decision.** Pending the owner's confirmation; MIT matches the public, reuse-friendly
intent and the references Studio draws on. Add `LICENSE` with the owner's name when
confirmed.
