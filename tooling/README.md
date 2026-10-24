# tooling

Maintainer scripts. Python 3.10+, standard library only (ADR-006). None of these are
shipped to users; they keep the repo consistent and let newadder work unattended.

| Script | Purpose | Status |
|---|---|---|
| `new_skill.py <domain> <skill>` | scaffold `plugins/<domain>/skills/<skill>/` from `templates/skill/`, vendor `_common.py`, add an empty capability entry and an eval case folder | planned |
| `lint_skills.py [path]` | enforce CONVENTIONS.md: frontmatter set and lengths, description trigger-first, SKILL.md size, required sections in order, scripts flags, vendored `_common.py` identical, no hand edits to REGISTRY.md, eval case format | planned |
| `build_registry.py [--check]` | generate REGISTRY.md from `plugins/*/capabilities.json` and skill frontmatter; `--check` fails if the committed file differs | planned |
| `gaps.py <domain>` | taxonomy − capabilities: style families and stages without a capability, capabilities below `tested`, heavy-hardware-only routes; newadder's worklist | planned |
| `doctor.py [--json]` | the maintainer-side machine inventory (the user-side version lives in `core:doctor`); used to write the TOOLBOX snapshot | planned |
| `templates/skill/` | the SKILL.md template and `scripts/_common.py` that every skill vendors | SKILL.md drafted |

Run everything from the repo root. CI runs lint, validate and the registry check on
every push; evals run only on changed plugins (they are billed model calls).
