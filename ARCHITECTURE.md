# Architecture

This document is the design of Studio. It is written for two readers: a maintainer
deciding where something goes, and Claude (including newadder) deciding how to behave.
When code and this document disagree, fix one of them in the same change.

## 1. Purpose and the driver principle

Studio exists so that any user, in any project, can say "make me a video / game / app"
and get a specialist's result from Claude, with a specialist's judgement about what to
ask and what to decide.

**Studio is a driver, not a toolchain.** Claude is the AI; there are no external AI
APIs in the loop. What the repo supplies is knowledge: curated tools with install
recipes, interview strategy, decision tables, workflows, pitfalls, prompts, links, ideas.
Claude reads, thinks, installs what is needed (asking the user), and does the work.

Consequences:

- Prose and tables carry most of the value. Scripts exist only where determinism beats
  reasoning: probing inputs, verifying outputs, exporting to a platform spec, repeating a
  multi-step command exactly. If three runs of a skill each wrote the same helper, that
  helper becomes a script; otherwise it stays prose.
- Everything a skill depends on is *declared* and *detected*, never assumed and never
  installed silently. The end user hears "this needs X; install it? (recipe)" once.
- Hardware is a fact to plan around, not to fight. A capability states what it needs; a
  Director never picks a path the machine cannot run.

## 2. Layers

| Layer | Lives in | Role |
|---|---|---|
| Knowledge | `taxonomy/`, `TOOLBOX.md`, each skill's `references/` | What the domain is; which tools; how; pitfalls |
| Skills | `plugins/<domain>/skills/<skill>/` | Units Claude loads on demand: router prose + optional scripts |
| Contract | `CONVENTIONS.md`, `tooling/lint_skills.py` | One shape for every skill, so skills compose |
| Orchestration | Director skills, Producer agents, `capabilities.json` | Request → brief → plan → execution |
| Growth | `plugins/forge/` (newadder), `research/`, `proposals/` | The repo studies the world and extends itself |
| Quality | `tooling/`, `plugins/<domain>/evals/`, CI | Nothing is `stable` without passing gates |

## 3. The request flow

```
request ──▶ Director ──▶ Brief ──▶ Plan ──▶ Producer ──▶ Report
```

### 3.1 Director (a skill per domain)

`plugins/<domain>/skills/director/SKILL.md`, namespaced `/video:director` etc. Its
description makes it trigger on any request in the domain, including ones that never
say the domain's name ("make something for Instagram from these clips").

The Director's contract, in order:

1. **Parse before asking.** Extract everything the request already fixes: intent,
   subject, inputs on disk, platform, length, style words, mood. Probe inputs that exist
   (duration, resolution, count). Never ask what the request or a probe answers.
2. **Decide what changes the plan.** Each domain's taxonomy lists its *question
   dimensions* — the handful of choices that select a different pipeline (for video:
   destination, length, style, voice). Only an open dimension that changes the plan
   earns a question. Everything else gets the domain default, recorded as an auto
   decision with its reason.
3. **One round, at most four questions, Auto first.** Use `AskUserQuestion`. The first
   option of every question is `Auto (recommended): <what Auto would pick>`. Options
   come from the taxonomy, filtered by `capabilities.json` and by what `doctor` found
   on this machine; an option that needs a missing tool says so in its description and
   stays selectable (choosing it triggers the install offer). Question descriptions
   state the trade-off, not a definition.
4. **Auto mode.** If the user says "auto", "you decide", "surprise me", or chose Auto
   everywhere, ask nothing further. Auto picks by the decision table in the taxonomy
   (destination → aspect, length band, loudness; intent → style family; inputs →
   visual source), within hardware and installed-tool limits.
5. **Write the brief, then the plan.** `out/<slug>/brief.json` first, then `plan.json`:
   ordered steps, each naming the skill, the tool, the expected output and the check that
   proves it. Show the plan in five lines or fewer. For long or destructive work, run the
   dry-run steps and show their numbers before executing.
6. **Hand off to the Producer** with the brief and plan. The Director stays in the
   conversation; it is the only part allowed to talk to the user.

### 3.2 Brief (the state)

```json
{
  "studio": "0.1.0",
  "domain": "video",
  "slug": "coffee-promo",
  "mode": "auto | guided",
  "intent": "promo",
  "subject": "coffee ordering app",
  "inputs": ["./rec/*.mov"],
  "destination": ["instagram-reels", "youtube"],
  "aspect": ["9:16", "16:9"],
  "duration_s": 30,
  "style": ["screencast-motion", "kinetic-captions"],
  "voice": "local-tts",
  "music": "upbeat",
  "captions": true,
  "constraints": {"brand": "./brand.json", "language": "en"},
  "auto_decisions": {
    "aspect": "9:16 and 16:9 because both destinations were chosen",
    "duration_s": "30 s: Reels retention sweet spot, under YouTube's short limit"
  },
  "machine": {"gpu_vram_gb": 4, "tools": {"ffmpeg": "8.1.3"}},
  "created": "2026-10-24T16:30:00Z"
}
```

Rules: the brief is written before work starts; every later change to the deliverable is
a change to the brief followed by a re-run; the Producer reads the brief, never the chat.
Common keys above are shared by all domains; each domain adds its own, documented in its
taxonomy under "Brief keys".

### 3.3 Plan

`out/<slug>/plan.json`: `[{step, skill, tool, action, inputs, output, check}]`. A step's
`check` is how the Producer proves the step worked (a probe field, a file existing with a
size, a test passing, a screenshot taken). A step without a check is not a step.

### 3.4 Producer (an agent per domain)

`plugins/<domain>/agents/producer.md`. Executes the plan, forked from the conversation
so long work does not block it. At every step: **probe → act → verify**. On a failed
check it stops, reports the measured failure, and proposes the fix; it never silently
retries with different parameters, because a parameter change is a brief change.

The Producer keeps the user's originals, writes only under `out/<slug>/`, and uses
`${CLAUDE_PLUGIN_DATA}` for caches (models, `node_modules`), never the plugin folder.

### 3.5 Report

Every job ends in five labelled lines, numbers from measurements:

```
Done: out/coffee-promo/reels.mp4 — 30.0 s, 1080x1920, 30 fps, H.264, AAC, -14.0 LUFS
Steps: probe 6 clips -> script (62 words) -> tts -> device frame + motion -> captions -> music ducked -> export reels + youtube
Check: reels — all platform checks pass; youtube — pass
Look: out/coffee-promo/reels_sheet.png (captions in safe area, no face covered)
Notes: clip 3 was VFR, conformed to 30 fps; say "make it 15 s" or "swap the music" to re-render
```

On failure `Done:` becomes `Failed:` with the tool's error quoted, not paraphrased.
`Look:` names an image Claude actually viewed, or says why not. This format is adopted
from ffmpeg-skill (MIT); see CONVENTIONS.md § Report format.

## 4. The knowledge model: taxonomy → capabilities → gaps

Three artefacts, one chain:

- **`taxonomy/<domain>.md`** — the universe: intents, formats, styles, pipeline
  stages, destinations, question dimensions, defaults and the Auto decision table.
  Hand-written, grown by newadder. Directors generate question options from it.
- **`plugins/<domain>/capabilities.json`** — what Studio can do today:

  ```json
  {
    "id": "video.style.screencast-motion",
    "intents": ["promo", "product-demo", "tutorial"],
    "style": "screencast-motion",
    "summary": "Screen recordings in a device frame with zoom/pan motion and kinetic captions",
    "pipeline": ["video:script", "audio:voice", "video:motion", "video:captions", "audio:music", "video:export"],
    "tools": [{"name": "ffmpeg", "min": "6.0", "required": true}, {"name": "piper", "required": false, "for": "voice-over"}],
    "hardware": {"gpu_vram_gb_min": 0, "cpu_ok": true},
    "cost": {"time": "minutes", "quality": "good"},
    "status": "planned",
    "evals": ["screencast-promo-30s"]
  }
  ```

  Directors plan from it; `REGISTRY.md` is generated from it and from skill frontmatter.
- **Gaps** — every taxonomy entry with no capability, or a capability whose status is
  below `tested`, or whose only engine needs hardware most users lack. Computed by
  `tooling/gaps.py`; this is newadder's worklist, so the repo grows where it is weakest
  rather than where it is easiest.

## 5. Tools: declared, detected, installed on request

- **`TOOLBOX.md`** is the curated catalogue: per domain, the tools worth using, why
  this one, licence, hardware needs, the install recipe per OS, the command that proves
  it works, and known traps. newadder maintains it with evidence links.
- **`core:doctor`** inspects the machine (OS, CPU, RAM, GPU and VRAM, each tool's
  presence and version, fonts, Python/Node) and prints what is usable. Directors run it
  once per job and store the result in the brief; Producers run it only on failure.
- **Install recipes** are offered, never run unasked: the Director names the tool, the
  recipe, the download size and what it unlocks, then asks. Recipes pin versions, avoid
  `curl | bash`, and end with the proving command. Heavy assets (model weights) download
  to `${CLAUDE_PLUGIN_DATA}` on first use.
- **Hardware awareness**: a capability's `hardware` block is compared with `doctor`'s
  report. On a 4 GB GPU, local video-diffusion models are not an option, so Auto never
  proposes them and the Director shows them as "needs ≥12 GB VRAM" only when the user
  asks for that style explicitly.

## 6. newadder: the self-improving agent

`plugins/forge/agents/newadder.md`, plus `plugins/forge/skills/newadder/` so both work:
"hey newadder, work on video skills" in prose, or `/forge:newadder video "anime styles"`.
Users do not need `forge`; maintainers load it with `claude --plugin-dir ./plugins`.

The loop:

1. **Scope.** Read `ROADMAP.md`, the domain's taxonomy and `capabilities.json`, the
   gaps report, and `research/INDEX.md` so no source is re-researched inside its
   freshness window. Take the user's focus if given ("anime styles"), else the top gaps.
2. **Research.** Follow the per-domain source playbook in
   `plugins/forge/skills/newadder/references/sources.md`: GitHub (topics, trending,
   awesome-lists, release notes), Hugging Face (models, spaces), PyPI and npm, Hacker
   News, Reddit, Stack Overflow, project blogs and papers. X and LinkedIn are mostly
   walled; they are reached only through search-result snippets and are treated as weak
   signals. Each finding goes to `research/<domain>/<date>-<topic>.md` with links and a
   one-line verdict; `research/INDEX.md` gets the pointer.
3. **Score.** For each candidate capability or tool: demand (how often users would ask),
   feasibility (local, free, scriptable), maturity (recent commits, answered issues,
   releases), contract fit (can be probed and verified), hardware fit (CPU or ≤ 4 GB
   GPU; otherwise it is recorded as a heavy-hardware option, not a default).
4. **Vet.** Before any tool enters `TOOLBOX.md` or a skill: licence allows use and
   redistribution of recipes; installable from a package registry or a tagged release
   with a pinned version and a checksum where available; no `curl | bash`; no surprise
   telemetry or account requirement; runs offline. A tool that fails vetting is
   recorded in `proposals/` with the reason, so it is not re-evaluated next week.
5. **Implement.** Scaffold with `tooling/new_skill.py`; write SKILL.md, references and
   any scripts; add the capability entry; extend the taxonomy; write two or three eval
   cases; run them with and without the skill; iterate; optimise the description's
   trigger phrases. Improving an existing skill follows the same path from its eval
   results and from repeated helper code found in transcripts.
6. **Gate, then commit.** newadder is autonomous (DECISIONS.md ADR-004) and commits to
   `main` only after every automated gate passes: `tooling/lint_skills.py`,
   `claude plugin validate plugins/<domain> --strict`, `tooling/build_registry.py
   --check`, and the new or changed evals. Commits follow `feat(video): …` /
   `fix(video): …` / `docs: …`; ROADMAP, CHANGELOG and DECISIONS are updated in the
   same commit.
7. **Hand back** one report: added, improved, rejected (with why), and anything that
   needs a human decision (licence doubts, paid tools, large downloads).

newadder's memory is the repo itself: `research/` (sources, dates, verdicts, freshness),
`proposals/` (ideas with status: `proposed | accepted | rejected | shipped`), and the
taxonomy/capabilities pair. It can later run on a schedule; it starts as a manual
invocation.

## 7. Distribution and namespaces

- The repo root is a **marketplace** (`.claude-plugin/marketplace.json`, name `studio`);
  each `plugins/<domain>/` is a plugin with its own `.claude-plugin/plugin.json`.
- Users: `claude plugin marketplace add BinaryBuddiesOrg/claude-hv-skills`, then
  `claude plugin install video@studio`. Skills appear as `/video:director`, agents as
  `video:producer`; nothing clashes with the user's own skills.
- Maintainers: `claude --plugin-dir ./plugins` loads every plugin from source;
  `/reload-plugins` after edits. No install step while developing.
- Installing copies **only the plugin folder** into a versioned cache, so a plugin never
  references `../`. Shared code is vendored by the scaffolder and kept identical by the
  linter. Cross-plugin knowledge is referenced by name (`core:doctor`), never by path.
- Inside a SKILL.md, bundled files are referenced as `${CLAUDE_SKILL_DIR}/…`, which
  resolves wherever the skill is loaded from.

## 8. Quality and the status lifecycle

`idea → draft → tested → stable → deprecated` (criteria in CONVENTIONS.md). Gates:

| Gate | Tool | Checks |
|---|---|---|
| Lint | `tooling/lint_skills.py` | frontmatter set, description length and trigger-first, SKILL.md size, required sections, scripts contract, vendored runtime identical |
| Validate | `claude plugin validate … --strict` | manifest and plugin structure |
| Registry | `tooling/build_registry.py --check` | REGISTRY.md matches capabilities and frontmatter |
| Evals | `claude plugin eval plugins/<domain> --case <skill>/*` | with/without-skill delta on realistic prompts (billed model runs; run on change, not on every commit) |

`REGISTRY.md` is generated; editing it by hand is a lint failure. `ROADMAP.md` is
hand-written and every heading carries a state, so "on the roadmap" is never mistaken
for "works".

## 9. Repository layout

```
claude-skills/
├── README.md ARCHITECTURE.md CONVENTIONS.md DECISIONS.md ROADMAP.md TOOLBOX.md CHANGELOG.md
├── REGISTRY.md                       generated
├── .claude-plugin/marketplace.json
├── taxonomy/   video.md audio.md graphics.md game.md apps.md
├── research/   INDEX.md  <domain>/<date>-<topic>.md
├── proposals/  README.md <id>-<slug>.md
├── plugins/
│   ├── core/     skills/doctor/ skills/brief/ skills/deliver/
│   ├── video/    capabilities.json skills/director/ skills/<capability>/ agents/producer.md evals/<skill>/<case>/
│   ├── audio/ graphics/ game/ apps/      same shape
│   └── forge/    agents/newadder.md skills/newadder/ skills/new-skill/
└── tooling/    new_skill.py lint_skills.py build_registry.py gaps.py doctor.py templates/skill/
```

## 10. To verify (cheap checks, not blockers)

- Whether `${CLAUDE_PLUGIN_ROOT}` is substituted inside `allowed-tools` (docs confirm only
  `${CLAUDE_SKILL_DIR}`); until then, skills use `${CLAUDE_SKILL_DIR}`.
- The exact `dependencies` format in `plugin.json` (video → core); until confirmed the
  README tells users to install `core` alongside a domain.
- Agent-definition frontmatter accepted by this CLI version (`name`, `description`,
  `tools`, `model`); confirm with `claude plugin validate`.
