---
name: brief
description: >-
  The brief is Studio's state: everything a job decided, written to out/<slug>/brief.json
  before any work starts, plus plan.json listing the steps and their checks. Use whenever
  a Director has finished intake and must record decisions, whenever a user asks to
  change a finished deliverable ("make it 15 s", "swap the music", "same but for
  YouTube"), when a Producer needs to know what it is executing, or when anyone asks
  "what did we decide" about a job. Create, update, validate and slug briefs with the
  bundled script; never re-interview the user for what a brief already holds.
license: MIT
compatibility: Python 3.10+
metadata:
  domain: core
  role: producer-support
  status: draft
  version: 0.1.0
  capabilities: []
  tools: []
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# brief

## What this skill does and does not decide

It owns the shape of two files and the rules for changing them: `brief.json` (what was
decided, by whom — user or Auto — and why) and `plan.json` (the ordered steps, each with
the check that proves it). It makes iteration cheap: a change request is an edit to one
field and a re-run, not a new conversation.

It does not decide any value. Directors decide (from the request, the taxonomy and
`capabilities.json`); Producers execute what is written and change nothing — if a step
cannot be done as written, that is a report, not a silent edit.

## Workflow (in this order)

1. **Slug.** `python3 ${CLAUDE_SKILL_DIR}/scripts/brief.py slug "<request>"` or pick a
   two-to-four-word slug yourself (`coffee-promo`, `platformer-prototype`). The output
   folder is `out/<slug>/`; if it exists, the script appends `-2`, `-3` — never reuse a
   folder from a different job.
2. **Create** before work:
   `brief.py new --domain video --slug coffee-promo --mode auto --set intent=promo --set 'inputs=["./rec/*.mov"]' --set duration_s=30 …`
   Every value from the user goes in as given; every value Auto chose goes in **with its
   reason** under `auto_decisions` (`--auto duration_s="30 s: Reels retention sweet spot"`).
   Store doctor's `machine` summary (`--machine-json <file>`).
3. **Plan.** Write `out/<slug>/plan.json` (shape below), then
   `brief.py validate out/<slug>` — it checks both files and refuses a step without a
   check. Only a plan that validates is handed to a Producer.
4. **Change** on request: `brief.py set out/<slug>/brief.json duration_s=15` bumps
   `revision`, appends to `history`, and prints what else may need to change (a plan step
   that mentioned the old value). Then re-plan the affected steps and re-run them.
5. **Read, don't ask.** Before any question to the user, read the brief; if the field is
   there, it is answered.

## Decide or ask

The brief skill asks nothing. If a Director is unsure whether a change request touches
one field or several ("make it punchier" could be pace, music and cut length), it asks
the user one bundled question with its interpretation as the first option — then edits
the brief, never the deliverable directly.

## Request → action

| Request looks like | Do |
|---|---|
| Director finished intake | `brief.py new …` with every decision and reason; then write `plan.json`; then `validate` |
| "make it 15 s", "use 16:9 too", "no captions" | `brief.py set <brief> key=value`; re-plan the steps that depend on it; re-run those |
| "same video but for LinkedIn" | `brief.py new` with `--from <old brief>` (copies, resets slug/revision/history) and the new destination |
| "what did we decide?" | read `brief.json`; answer with the user's choices first, then `auto_decisions` with their reasons |
| Producer about to start | `brief.py validate out/<slug>` and refuse to start on a failure |

## Tools and installation

Python 3.10+ only. `brief.py --help` lists subcommands: `new`, `set`, `validate`, `slug`.
Every subcommand takes `--json` (print the document) and `--dry-run` (print, write nothing).

### brief.json — common keys (every domain)

| Key | Type | Meaning |
|---|---|---|
| `studio` | string | brief schema version, `"0.1"` |
| `domain` | string | `video`, `audio`, `graphics`, `game`, `apps` |
| `slug` | string | folder name under `out/` |
| `mode` | `auto` \| `guided` | whether the user answered questions |
| `intent` | string | from the domain taxonomy (`promo`, `tutorial`, `prototype` …) |
| `subject` | string | what it is about, in the user's words |
| `inputs` | list | paths or globs the user supplied; `[]` when none |
| `constraints` | object | `language`, `brand` (path), `deadline`, anything the user insisted on |
| `auto_decisions` | object | `field → reason` for every value Auto chose |
| `machine` | object | doctor's summary: `os`, `cpu_cores`, `ram_gb`, `gpu`, `usable` |
| `created`, `updated` | ISO 8601 | timestamps |
| `revision` | int | starts at 1; `set` increments |
| `history` | list | `{at, change}` entries written by `set` |

Domain keys are added beside these (video: `destination[]`, `aspect[]`, `duration_s`,
`style[]`, `voice`, `music`, `captions`, …) and documented in the domain Director's
references.

### plan.json

```json
{
  "brief": "brief.json",
  "revision": 1,
  "steps": [
    {"step": 1, "skill": "core:doctor", "action": "inventory; confirm ffmpeg ≥ 6", "inputs": [], "output": null,
     "check": "usable.video_edit is true"},
    {"step": 2, "skill": "video:clips-to-short", "action": "probe ./rec/*.mov", "inputs": ["./rec/*.mov"],
     "output": "work/probe.json", "check": "every input has has_video true; durations recorded"},
    {"step": 3, "skill": "video:platform-export", "action": "export reels", "inputs": ["work/edit.mp4"],
     "output": "reels.mp4", "check": "check.py reels.mp4 --destination instagram-reels passes"}
  ]
}
```

Rules the validator enforces: steps numbered 1..n without gaps; every step has `skill`
(`plugin:skill`), `action` and a non-empty `check`; `output` paths are relative to
`out/<slug>/`; `revision` matches the brief's.

## Report format

Brief operations are silent inside a job. When the user asks what was decided, answer in
this shape:

```
Done: out/coffee-promo/brief.json (revision 2)
Steps: you chose: promo, ./rec/*.mov, Reels + YouTube, local TTS · auto: 30 s (Reels sweet spot), captions on (muted autoplay), blur-pad for 9:16 (keeps the whole screen)
Check: validate — brief ok, plan ok (7 steps)
Look: not needed
Notes: revision 2 changed duration_s 30 → 15 ("make it shorter"); steps 3–7 re-run
```

## Things that look right but are wrong

- Editing the deliverable without editing the brief: the next re-run silently undoes the
  change. Every change goes through `brief.py set`.
- A plan step whose `check` is "it ran" is not a check. Name the measured fact.
- Reusing `out/<slug>/` for a new job because the name fits: history and reports get
  mixed. Let the script pick `-2`.
- Writing `auto_decisions` without reasons: the user cannot tell a default from a
  choice, and newadder cannot learn which defaults are wrong.
- Putting the user's whole message in `subject`: `subject` is the thing, `constraints`
  holds the demands, `inputs` the files.
- Storing absolute paths in `inputs` when the project moves: prefer paths relative to
  the project root; the script keeps what it is given, so give it relative ones.

## References

- `scripts/brief.py --help` — subcommands and flags; `brief.py validate` is the contract.
- The domain Director's `references/decisions.md` — the domain-specific brief keys.
