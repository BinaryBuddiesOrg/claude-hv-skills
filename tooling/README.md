# tooling

Maintainer scripts. Python 3.10+, standard library only (ADR-006). None of these are
shipped to users; they keep the repo consistent and let newadder work unattended. Run
them from anywhere — paths resolve from the repo root.

| Script | Purpose |
|---|---|
| `new_skill.py <domain> <skill> [--role R] [--capability ID] [--with-scripts]` | scaffold `plugins/<domain>/skills/<skill>/` from `templates/skill/`, an eval case, and (optionally) a capability entry; fails lint until its `{{placeholders}}` are filled |
| `lint_skills.py [path]` | enforce CONVENTIONS.md: frontmatter set and lengths, section order, SKILL.md size, scripts contract, vendored `_common.py` identical, capabilities.json shape and skill references, eval case format, REGISTRY.md freshness |
| `build_registry.py [--check]` | generate REGISTRY.md from `plugins/*/capabilities.json`, skill frontmatter and agents; `--check` exits 1 when stale (deterministic, no timestamps) |
| `gaps.py <domain> [--json]` | taxonomy − capabilities: uncovered style families, capabilities below `tested`, heavy-hardware-only routes, the taxonomy's own suggestions — newadder's worklist |
| `stamp_versions.py [--check]` | set each plugin's manifest `version` to `0.<commits touching it>.0` (+1 when dirty) so every change reaches installed users; `--check` is run by lint (ADR-013) |
| `_lib.py` | shared: repo paths, the frontmatter parser for the allowed YAML subset, plugin/skill/eval discovery |
| `templates/skill/SKILL.md` | the skill template, section for section as CONVENTIONS.md § SKILL.md body |
| `templates/skill/scripts/_common.py` | the runtime every skill with scripts vendors: shared flags, JSON shape, exit codes, `ffprobe`, tool detection |

The gate newadder runs before any commit (ARCHITECTURE.md § 6.6):

```
python3 tooling/stamp_versions.py            # bump the touched plugins' versions
python3 tooling/build_registry.py            # regenerate REGISTRY.md
python3 tooling/lint_skills.py               # includes registry and version checks
claude plugin validate plugins/<domain> --strict
claude plugin eval plugins/<domain> --case "<skill>/*" --allow-tools Bash,Write,Edit   # billed; only changed cases
```

The machine inventory for users lives in `plugins/core/skills/doctor/` (self-contained,
as every plugin must be); there is no separate maintainer copy.
