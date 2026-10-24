#!/usr/bin/env python3
"""Scaffold a Studio skill that passes lint as soon as its {{placeholders}} are filled.

Usage:  python3 tooling/new_skill.py <domain> <skill> [--role capability|director|producer-support|meta]
                                     [--capability <id>] [--with-scripts]

Creates:
  plugins/<domain>/skills/<skill>/SKILL.md            from tooling/templates/skill/SKILL.md
  plugins/<domain>/skills/<skill>/references/         (empty, with .gitkeep)
  plugins/<domain>/skills/<skill>/scripts/_common.py  only with --with-scripts (vendored runtime)
  plugins/<domain>/evals/<skill>/<skill>-basic/       one eval case with a placeholder grader
  a capability entry in plugins/<domain>/capabilities.json when --capability is given and the id is new

The scaffold deliberately fails lint until the placeholders are replaced: a skill that is
half-written must not look finished to newadder or to the registry.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402

PROMPT_MD = """---
tags: [{domain}, {skill}]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

{{{{A realistic prompt a user would type: paths, a little backstory, casual phrasing.}}}}
"""

CASE_YAML = """schema_version: "1.1"
name: {case}
expected_outcome: |
  {{{{What a good result looks like, in two or three sentences.}}}}
"""

GRADER_MD = """---
type: llm
focus: trace
weight: 1
---

The response completes the task the prompt asks for.
"""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("domain")
    ap.add_argument("skill")
    ap.add_argument("--role", default="capability", choices=sorted(L.ROLES))
    ap.add_argument("--capability", help="capability id to register, e.g. video.style.slideshow")
    ap.add_argument("--with-scripts", action="store_true", help="vendor scripts/_common.py")
    a = ap.parse_args(argv)

    plugin = L.PLUGINS / a.domain
    if not (plugin / ".claude-plugin" / "plugin.json").is_file():
        L.die(f"no plugin at {L.rel(plugin)}; create its manifest first")
    if not L.CASE_NAME.match(a.skill):
        L.die("skill name must be lowercase-with-hyphens, starting with a letter")
    skill = plugin / "skills" / a.skill
    if skill.exists():
        L.die(f"{L.rel(skill)} already exists")

    template = (L.TEMPLATE_DIR / "SKILL.md").read_text(encoding="utf-8")
    text = (template.replace("{{skill}}", a.skill).replace("{{domain}}", a.domain)
            .replace("{{kind}}", "style").replace("{{slug}}", a.skill)
            .replace("  role: capability", f"  role: {a.role}"))
    if a.capability:
        text = text.replace(f"[{a.domain}.style.{a.skill}]", f"[{a.capability}]")
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(text, encoding="utf-8")
    (skill / "references").mkdir()
    (skill / "references" / ".gitkeep").write_text("", encoding="utf-8")
    created = [skill / "SKILL.md", skill / "references"]

    if a.with_scripts:
        (skill / "scripts").mkdir()
        shutil.copyfile(L.TEMPLATE_DIR / "scripts" / "_common.py", skill / "scripts" / "_common.py")
        created.append(skill / "scripts" / "_common.py")

    case_name = f"{a.skill}-basic"
    case = plugin / "evals" / a.skill / case_name
    (case / "graders").mkdir(parents=True)
    (case / "prompt.md").write_text(PROMPT_MD.format(domain=a.domain, skill=a.skill), encoding="utf-8")
    (case / "case.yaml").write_text(CASE_YAML.format(case=case_name), encoding="utf-8")
    (case / "graders" / "01-expected-output.md").write_text(GRADER_MD, encoding="utf-8")
    created.append(case)

    if a.capability:
        cap_file = plugin / "capabilities.json"
        data = L.load_capabilities(plugin) or {"domain": a.domain, "capabilities": []}
        if not any(c.get("id") == a.capability for c in data["capabilities"]):
            data["capabilities"].append({
                "id": a.capability, "intents": [], "style": a.skill if ".style." in a.capability else None,
                "summary": "{{one line}}", "pipeline": [f"{a.domain}:{a.skill}"], "tools": [],
                "hardware": {"gpu_vram_gb_min": 0, "cpu_ok": True}, "cost": {"time": "minutes", "quality": "good"},
                "status": "draft", "skill": f"{a.domain}:{a.skill}", "evals": [],
            })
            data["updated"] = dt.date.today().isoformat()
            cap_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            created.append(cap_file)
        else:
            print(f"capability {a.capability} already exists; not changed")

    print("created:")
    for p in created:
        print(f"  {L.rel(p)}")
    print("\nnext: replace every {{placeholder}} in SKILL.md and the eval case, then\n"
          "  python3 tooling/lint_skills.py plugins/" + a.domain + "\n"
          "  python3 tooling/build_registry.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
