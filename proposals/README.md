# Proposals

What newadder (or a human) wants to add to Studio, with the vetting result and the
decision. Rejected proposals stay here so the same tool is not re-evaluated every run.

Files: `P-<NNNN>-<slug>.md`, numbered in order of creation. Status lifecycle:
`proposed → accepted → shipped`, or `proposed → rejected`. A `rejected` proposal may
return to `proposed` only when its rejection reason no longer holds, and the proposal
says which sentence changed.

## Template

```markdown
# P-0001 — <title>

Status: proposed | accepted | rejected | shipped        Date: <YYYY-MM-DD>      Domain: <domain>
Gap: <taxonomy entry or capability id this fills>
Research: research/<domain>/<note>.md

## What
<the capability or tool, in two sentences>

## Scores
demand <1–5> · feasibility <1–5> · maturity <1–5> · contract fit <1–5> · hardware fit <1–5> → weighted <n>

## Vetting
- [ ] licence permits use and recipe publication: <licence>
- [ ] pinned install from registry or tagged release; checksum: <yes/no/n.a.>
- [ ] no account, no undisclosable telemetry, offline after first run
- [ ] maintained (last release <date>) or stable-and-done
- [ ] proving command ran in isolation: `<command>` → <result>

## Plan
<skill(s) to add or change; eval cases; TOOLBOX entry; taxonomy changes>

## Decision
<accepted/rejected and the one reason that decided it>
```

| ID | Title | Domain | Status | Date |
|---|---|---|---|---|
| — | — | — | — | — |
