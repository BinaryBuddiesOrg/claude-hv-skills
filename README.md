# Studio

A Claude skill arsenal: one repo that turns Claude into a specialist for **video, audio,
graphics, games and apps**. Point Claude at it, say what you want, answer a few smart
questions (or say "auto"), and get a finished, verified deliverable.

Studio is a **driver, not a toolchain**. Claude is the intelligence. This repo gives it
what a specialist knows: which tools to use and how to install them, how to interview a
client without wasting their time, which decisions to make automatically, the pitfalls
that look right but are wrong, and workflows that end in a result that was checked, not
assumed.

> Status: pre-release skeleton (0.1.0). Cloning this repo installs nothing on your machine.

## Use it

One step, inside Claude Code (2.1.275+):

```
/plugin install core  --marketplace BinaryBuddiesOrg/claude-hv-skills    # shared runtime, needed by every domain
/plugin install video --marketplace BinaryBuddiesOrg/claude-hv-skills    # the video Director and every video style
/plugin install audio --marketplace BinaryBuddiesOrg/claude-hv-skills    # voice-over, music, recording clean-up (video uses it)
```

Later: `claude plugin update video@studio` (and `core`, `audio`) pulls new commits.

Or from a terminal:

```bash
claude plugin marketplace add BinaryBuddiesOrg/claude-hv-skills   # once
claude plugin install video@studio core@studio
```

Then, in any project:

> make a 30 s promo video for my coffee app from the screen recordings in ./rec

Claude's **Director** asks one round of questions, each with an **Auto (recommended)**
option, plans the work, offers to install anything missing, runs the pipeline, verifies
the output and reports. Say "auto" or "you decide" and it asks nothing.

You can also paste this repo's link and say what you want; Claude runs the two commands
above (asking permission first).

## How it works

```
request ──▶ Director ──▶ Brief ──▶ Plan ──▶ Producer ──▶ Report
             (skill)    (state)            (agent)      (verified)
```

| Piece | What it is | Why |
|---|---|---|
| **Director** | The entry skill of a domain (`/video:director`). Reads the request, fills a brief, asks only what changes the plan, max one round, every question has Auto. | Nobody wants a form. A good producer asks three sharp questions, then works. |
| **Brief** | `out/<slug>/brief.json`: everything decided, including `auto_decisions` with reasons. | The brief is the state. "Make it 15 s" edits one field and re-renders; no re-interview. |
| **Plan** | Ordered steps, each naming the skill, tool and check that proves it worked. | Dry-run before long work; the user sees what will happen. |
| **Producer** | The domain agent that executes: probe → act → verify at every step. | Long, heavy work runs forked; the conversation stays responsive. |
| **Report** | Five lines: `Done / Steps / Check / Look / Notes`, numbers from measurements, never memory. | Success is reported from the output probe, or it is not reported. |

Behind the Director sits one knowledge model, shared by every domain:

- **Taxonomy** (`taxonomy/<domain>.md`): the universe of what the domain covers. Question options come from here.
- **Capabilities** (`plugins/<domain>/capabilities.json`): what Studio can actually do today, with which tools, on which hardware. Plans come from here.
- **Gaps** = taxonomy − capabilities. That is newadder's worklist.

## Domains

| Plugin | Status | Covers |
|---|---|---|
| `core` | draft | `doctor` (what this machine can do, install recipes), briefs, delivery and report conventions |
| `video` | draft — complete, untested | 15 capabilities: screencast promos/demos, shorts from footage, slideshows, talking-head edits, audiograms, lyric videos, kinetic text, animated explainers, AI-shot stories; captions, motion, assembly, platform export |
| `audio` | draft | voice-over with local TTS (piper / macOS say / espeak-ng), music fit and ducking, recording clean-up |
| `graphics` | planned | image ops, vector/SVG, thumbnails, 3D renders, sprites, background removal |
| `game` | planned | Godot and web games: scaffold, scenes, assets pipeline, export |
| `apps` | planned | web, mobile, desktop, backend, deploy, end-to-end tests, store assets |
| `forge` | draft | maintainers only: **newadder**, the agent that researches and grows this repo |

Statuses are defined in [CONVENTIONS.md](CONVENTIONS.md#status-lifecycle); `planned` means nothing works yet.

## Grow it

The repo improves itself. In a session with the `forge` plugin loaded:

> hey newadder, work on video skills — anime and hand-drawn styles are missing

newadder reads the taxonomy and capabilities, researches GitHub, Hugging Face, package
registries and community sources, scores candidates against a vetting rubric, writes or
improves skills with evals, passes the automated gates (lint, validate, evals) and commits.
Its memory lives in `research/`; its proposals and verdicts in `proposals/`. See
[ARCHITECTURE.md § newadder](ARCHITECTURE.md#6-newadder-the-self-improving-agent).

## Repo map

```
README.md ARCHITECTURE.md CONVENTIONS.md DECISIONS.md ROADMAP.md TOOLBOX.md CHANGELOG.md
REGISTRY.md                     generated: every skill, status, tools, evals
.claude-plugin/marketplace.json the marketplace; lists plugins/
taxonomy/                       the universe per domain
research/                       newadder's memory (what was checked, when, verdict)
proposals/                      what newadder wants to add, with verdicts
plugins/<domain>/               one installable plugin per domain
  .claude-plugin/plugin.json
  capabilities.json
  skills/<skill>/SKILL.md       (+ scripts/ references/ assets/)
  agents/ evals/<skill>/<case>/
tooling/                        maintainer scripts: scaffold, lint, registry, doctor
```

## Read next

- [ARCHITECTURE.md](ARCHITECTURE.md) — the design, end to end
- [CONVENTIONS.md](CONVENTIONS.md) — the contract every skill follows
- [DECISIONS.md](DECISIONS.md) — why things are the way they are
- [ROADMAP.md](ROADMAP.md) — what exists, what is next, with honest states
- [TOOLBOX.md](TOOLBOX.md) — curated tools per domain and how they get installed

Studio stands on the shoulders of [ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill)
(MIT), whose probe-first / verify-last workflow and report format shaped our conventions.
