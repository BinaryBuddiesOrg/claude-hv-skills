---
name: {{skill}}
description: >-
  {{What this skill does, in one sentence.}} Use whenever the user {{mentions / asks
  for / has files of ...}}, even if they do not say "{{the obvious word}}". Covers
  {{the main cases}}.
license: MIT
compatibility: {{tool >= version; optional tool for what}}
metadata:
  domain: {{domain}}
  role: capability
  status: draft
  version: 0.1.0
  capabilities: [{{domain}}.{{kind}}.{{slug}}]
  tools: [{{tool}}, {{optional-tool}}?]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
---

# {{skill}}

## What this skill does and does not decide

{{Two short paragraphs. What it executes. What belongs to the Director or the user:
taste, which cut, whether it ships.}}

## Workflow (in this order)

1. **Probe** {{what, with which script or command}}; plan from the numbers.
2. {{Act — the smallest sequence that does the job; prefer lossless/no-op where possible.}}
3. **Verify** {{the measurable facts that prove it worked}}.
4. **Look** — {{the image the agent views: contact sheet, screenshot}}; `Look: not needed` for audio-only.

## Decide or ask

Assume and say so: {{defaults}}. Ask, in one bundled question, only when
{{the answer changes the output materially}}. Never ask what a probe answers.

## Request → action

| Request looks like | Do |
|---|---|
| {{"..."}} | {{step / `python3 ${CLAUDE_SKILL_DIR}/scripts/x.py --flag`}} |

## Tools and installation

{{tool}}: detected by `core:doctor` as `{{command}}`. Missing → offer this recipe and ask:

```
tool: {{tool}}       licence: {{SPDX}}     needs: {{CPU ok | GPU ≥ N GB}}
linux: {{pinned command}}      macos: {{pinned command}}
proves: {{command}}
size: {{MB}}; models → ${CLAUDE_PLUGIN_DATA}/{{tool}}/
```

## Report format

```
Done: {{output}} — {{measured facts}}
Steps: {{step}} -> {{step}}
Check: {{spec}} — {{result}}
Look: {{image}} ({{what it shows}})
Notes: {{assumptions; what the user can change}}
```

## Things that look right but are wrong

- {{one line}} -> [references/{{file}}.md#{{anchor}}](references/{{file}}.md#{{anchor}})

## References

- `references/{{file}}.md` — open when {{the question}}.
