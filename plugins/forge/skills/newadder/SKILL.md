---
name: newadder
description: Entry point for growing the Studio repo. Use whenever the user addresses "newadder", asks to work on or improve a domain's skills (video, audio, graphics, game, apps), find new tools or techniques, discover what the repo is missing, add a skill, or refresh the toolbox. Parses the focus and delegates to the newadder agent with a precise brief.
metadata:
  domain: forge
  role: meta
  status: draft
  version: 0.1.0
---

# newadder (invocation)

This skill turns "hey newadder, work on video skills — anime styles are missing" into a
brief for the `newadder` agent and relays its report. It exists so the agent always
starts with the same, complete context, whatever words the user used.

## Workflow

1. **Parse the request** into: `domain` (one of video, audio, graphics, game, apps; ask
   only if none is named and none is implied), `focus` (free text, may be empty),
   `mode` (`add` new capabilities, `improve` an existing skill, `research-only`,
   `toolbox-refresh`; default `add`), and `budget` (default: two additions).
2. **Check preconditions** without fixing them: the repo root has `ARCHITECTURE.md` and
   `plugins/<domain>/`; `git status` is clean or the user has said uncommitted changes
   are fine. A dirty tree is reported, not committed over.
3. **Delegate** to the `newadder` agent (Agent tool) with this brief, filled in:

   ```
   Repo root: <absolute path>
   Domain: <domain>      Mode: <mode>      Budget: <n additions>
   Focus: <the user's words, or "top gaps">
   Read first: ARCHITECTURE.md §1 §6, CONVENTIONS.md, taxonomy/<domain>.md,
               plugins/<domain>/capabilities.json, research/INDEX.md, proposals/
   Rules: vet before adding; gates before commit; write research notes as you go;
          hand back the five-line report.
   Pushing: <allowed | not allowed>   Root installs: <ask first>
   ```

4. **Relay the report** verbatim, then add one line on what you would run next.

## Decide or ask

Do not ask about budget, sources or style; the agent's defaults are the conventions.
Ask only when the domain is genuinely ambiguous ("work on captions" → video) or when
the user names a tool that fails vetting on its face (paid, closed, needs an account) —
then say why before spending a run on it.

## Report format

The agent's report is the report. If delegation itself failed, use the five labels with
`Failed:` naming the precondition.
