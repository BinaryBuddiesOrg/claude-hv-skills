# Conventions: the contract every skill follows

One shape for every skill is what lets a Director chain skills across domains without
reading their internals, lets `tooling/lint_skills.py` catch drift, and lets newadder add
a skill at 3 a.m. that looks like the ones a human wrote. Where a rule has a reason, the
reason is written next to it; follow the reason when the rule does not fit.

## Naming

- Plugins: one lowercase word (`video`, `game`), never prefixed `claude-`, `anthropic-`
  or `cc-plugin-` (those fail validation).
- Skills: lowercase-with-hyphens, a noun or verb phrase for what it produces or does
  (`director`, `captions`, `platform-export`). The folder name is the skill name.
- Eval cases: lowercase-with-hyphens, a few words on what is tested
  (`screencast-promo-30s`). Never `results`, `mocks`, `files`, `true`, `false`, `null`.
- Capability ids: `<domain>.<kind>.<slug>` (`video.style.screencast-motion`).

## Anatomy of a skill

```
<skill>/
├── SKILL.md         required; under 300 lines (hard limit 500)
├── scripts/         optional; deterministic helpers, Python 3.10+ stdlib only
│   └── _common.py   vendored runtime, byte-identical to tooling/templates/skill/scripts/_common.py
├── references/      optional; loaded only when a question needs them; a TOC if over 300 lines
└── assets/          optional; small templates, presets, fonts; never binaries over 1 MB, never model weights
```

Evals live at `plugins/<domain>/evals/<skill>/<case>/`, not inside the skill
(DECISIONS.md ADR-005).

## Frontmatter

Use only the portable set, so a skill can also be uploaded to claude.ai unchanged:

```yaml
---
name: captions
description: >-
  Add burned-in or sidecar captions to a video from a transcript, an SRT, or by
  transcribing locally. Use whenever the user mentions captions, subtitles, SRT, making
  a video "readable without sound", or any social-video delivery — even if they do not
  say "captions". Covers styling, safe zones, karaoke/word highlight and CJK fonts.
license: MIT
compatibility: ffmpeg >= 6.0; optional whisper.cpp or faster-whisper for transcription
metadata:
  domain: video
  role: capability        # director | producer-support | capability | meta
  status: draft           # idea | draft | tested | stable | deprecated
  version: 0.1.0
  capabilities: [video.stage.captions]
  tools: [ffmpeg, whisper.cpp?]      # ? marks optional
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)
---
```

- `description` is the trigger. Lead with what the skill does, then the "use whenever"
  phrases, then what it covers. Be a little pushy: Claude under-triggers skills. Keep it
  under ~1,000 characters; the listing truncates at 1,536.
- `compatibility` ≤ 500 characters, human-readable tool needs.
- `metadata` is ignored by Claude Code and read by `tooling/build_registry.py`; the keys
  above are the full set, and `status` is the one that gates the registry.
- Nothing else. `context`, `model`, `argument-hint` and other Claude-Code-only keys are
  allowed only in `forge` (maintainer) skills, which never leave Claude Code.

## SKILL.md body: sections, in this order

1. **What this skill does and does not decide** — two short paragraphs. Execution
   belongs here; taste and judgement are named as the Director's or the user's.
2. **Workflow (in this order)** — numbered; probe first, verify last; where a dry run
   fits; which step produces the `Look:` image.
3. **Decide or ask** — what to assume by default (and say so), what to ask (only when
   the answer changes the output materially), bundled into one question.
4. **Request → action** — a table from the kinds of request to the step, script or tool
   invocation. This is the routing heart; keep it scannable.
5. **Tools and installation** — what is needed, how `doctor` detects it, the install
   recipe (pinned, with the proving command), what to do when it is missing.
6. **Report format** — the five labels, with one example specific to this skill.
7. **Things that look right but are wrong** — one line each, linking to the
   `references/` section with the long form.
8. **References** — when to open which file.

Write in the imperative. Explain why, not just what; a reader that understands the
reason handles the case the rule did not foresee. ALL-CAPS MUSTs are a sign the reason
is missing.

## Scripts contract

Write a script when the same multi-step command recurs, when a number must be measured
(probe, loudness, dimensions), or when an output must be checked against a spec. Do not
write a script for what a sentence can tell Claude to do.

Every script:

- Python 3.10+, standard library only (the end user's machine has Python; it does not
  have your dependencies). Node is acceptable only inside `apps` and `game` web skills,
  where the user already has Node.
- `--help`, `--dry-run` (print what would run, run nothing that writes), `--json`
  (machine-readable result; a `status: ok|failed`, the output path, the measured facts,
  and on failure `error.kind` and `error.message`), `--timeout SECONDS` (default 1800).
- Exit codes: 0 success, 1 failure, 2 undecidable, 124 timeout, 127 missing tool.
- Never overwrites a file it did not create in this run unless `--overwrite` is passed.
- Uses `_common.py` for argument plumbing, JSON output, timeouts and tool detection, so
  the behaviour above is the same in every skill.

## Install recipes

Nothing installs implicitly. A recipe is a block in TOOLBOX.md and in the skill's
"Tools and installation" section:

```
tool: whisper.cpp          licence: MIT     needs: CPU ok; GPU optional
linux:  <package-manager or pinned release command>
macos:  brew install whisper-cpp
proves: whisper-cli --help
unlocks: local transcription for captions and silence-aware cuts
size: ~30 MB binary; models 75 MB (tiny) to 3 GB (large), downloaded to ${CLAUDE_PLUGIN_DATA}/models on first use
```

Pin versions; prefer package registries and tagged releases; never `curl | bash`; state
the download size; end with the proving command. The Director offers the recipe and asks
before running it.

## Report format

Adopted from ffmpeg-skill (MIT). Every job, long or short, successful or failed, ends
with these five labels, in the user's language, labels in English:

```
Done:  <output path> — <measured facts>            (or  Failed: <what> — "<tool's error, quoted>")
Steps: <step> -> <step> -> <step>
Check: <spec or test name> — <result>              (or  Check: nothing to verify)
Look:  <image Claude viewed> (<what it shows>)     (or  Look: not needed / not inspected because …)
Notes: <what was assumed, what the user can change next>
```

Numbers come from `--json` or a probe, never from memory. A partial result is `Done:`
with the shortfall in `Notes:`; a refusal is `Failed:` naming why.

## Evals

`plugins/<domain>/evals/<skill>/<case>/` in the `claude plugin eval` layout:

```
<case>/
├── prompt.md        frontmatter: tags, max_turns, timeout_seconds, allowed_tools; body: the prompt as a user would type it
├── case.yaml        schema_version: "1.1", name, expected_outcome: |
├── graders/         01-<few-words>.md … each: type: llm, focus: trace, weight: 1, body = one verifiable statement
└── files/           optional inputs, with place-files.sh and context.scaffold_script in case.yaml
```

Prompts are realistic: paths, a little backstory, casual phrasing, the odd typo. Graders
state facts about the result ("reels.mp4 is 1080x1920"), not about where it was saved.

## Status lifecycle

| Status | Meaning | Criteria |
|---|---|---|
| `idea` | listed in a taxonomy or proposal | nothing exists in `plugins/` |
| `draft` | skill exists | SKILL.md passes lint; capability entry present |
| `tested` | shown to work | ≥ 2 eval cases pass with the skill; description trigger-tested |
| `stable` | safe to depend on | tested on two machines/OSes; pitfalls section populated from real failures; no open correctness issue |
| `deprecated` | superseded | points to the replacement; removed after one minor release |

The Director's Auto mode may pick `tested` and `stable` capabilities; it offers `draft`
ones only when the user asks for that style explicitly, and says they are new.

## Attribution

Studio writes its own skills. Where a pattern, table or snippet is taken from another
project, name it in the skill's References section and keep its licence notice. The
report format and probe-first workflow come from ffmpeg-skill (MIT, kajisho5).
