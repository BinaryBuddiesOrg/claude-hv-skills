#!/usr/bin/env python3
"""Lint Studio against CONVENTIONS.md: skills, agents, capabilities files, eval cases, REGISTRY.md.

Usage:  python3 tooling/lint_skills.py            # whole repo
        python3 tooling/lint_skills.py plugins/video
Exit 0 when there are no errors; 1 otherwise. Warnings are printed and never fail the run.

Every check names the convention it enforces, so a failure message tells you what to
read, not just what broke. Standard library only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402
import build_registry  # noqa: E402

SECTION_PREFIXES = [
    "What this skill does", "Workflow", "Decide or ask", "Request", "Tools and installation",
    "Report format", "Things that look right", "References",
]
REQUIRED_SECTIONS = {
    "capability": SECTION_PREFIXES,
    "director": SECTION_PREFIXES,
    "producer-support": SECTION_PREFIXES,
    "meta": ["Workflow", "Report format"],
}
SCRIPT_FLAGS = ("--dry-run", "--json", "--timeout")
MAX_ASSET_BYTES = 1_000_000


class Report:
    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []

    def error(self, path: Path, msg: str) -> None:
        self.errors.append((L.rel(path), msg))

    def warn(self, path: Path, msg: str) -> None:
        self.warnings.append((L.rel(path), msg))


def lint_skill(plugin: Path, skill: Path, rep: Report) -> None:
    md = skill / "SKILL.md"
    if not md.is_file():
        rep.error(skill, "no SKILL.md (CONVENTIONS § Anatomy)")
        return
    text = md.read_text(encoding="utf-8")
    try:
        fm, body = L.parse_frontmatter(L.split_frontmatter(text)[0]), L.split_frontmatter(text)[1]
    except L.FrontmatterError as e:
        rep.error(md, f"frontmatter: {e}")
        return

    allowed = L.CLAUDE_CODE_KEYS if plugin.name == "forge" else L.PORTABLE_KEYS
    for key in sorted(set(fm) - allowed):
        rep.error(md, f"frontmatter key '{key}' is not portable (CONVENTIONS § Frontmatter; ADR-007)")
    if fm.get("name") != skill.name:
        rep.error(md, f"name '{fm.get('name')}' must equal the folder name '{skill.name}'")

    desc = str(fm.get("description", "") or "")
    if not desc:
        rep.error(md, "description missing — it is the trigger (CONVENTIONS § Frontmatter)")
    elif len(desc) > 1536:
        rep.error(md, f"description is {len(desc)} chars; the listing truncates at 1536")
    elif len(desc) > 1000:
        rep.warn(md, f"description is {len(desc)} chars; keep under ~1000 so the trigger survives truncation")
    if len(str(fm.get("compatibility", "") or "")) > 500:
        rep.error(md, "compatibility over 500 chars")

    meta = fm.get("metadata")
    role = None
    if not isinstance(meta, dict):
        rep.error(md, "metadata block missing (CONVENTIONS § Frontmatter)")
    else:
        for key in sorted(set(meta) - L.METADATA_KEYS):
            rep.error(md, f"metadata key '{key}' unknown; allowed: {sorted(L.METADATA_KEYS)}")
        if meta.get("domain") != plugin.name:
            rep.error(md, f"metadata.domain '{meta.get('domain')}' must equal the plugin name '{plugin.name}'")
        role = meta.get("role")
        if role not in L.ROLES:
            rep.error(md, f"metadata.role '{role}' not in {sorted(L.ROLES)}")
        if meta.get("status") not in L.SKILL_STATUSES:
            rep.error(md, f"metadata.status '{meta.get('status')}' not in {sorted(L.SKILL_STATUSES)}")
        if not L.SEMVER.match(str(meta.get("version", ""))):
            rep.error(md, f"metadata.version '{meta.get('version')}' is not MAJOR.MINOR.PATCH")
        for key in ("capabilities", "tools"):
            if key in meta and not isinstance(meta[key], list):
                rep.error(md, f"metadata.{key} must be an inline list [a, b]")

    n_lines = text.count("\n") + 1
    if n_lines > 500:
        rep.error(md, f"{n_lines} lines; hard limit 500 (CONVENTIONS § Anatomy)")
    elif n_lines > 300:
        rep.warn(md, f"{n_lines} lines; aim under 300, move detail to references/")
    if "{{" in text:
        rep.error(md, "template placeholder '{{…}}' left in the file")

    if role in REQUIRED_SECTIONS:
        found = L.headings(body)
        positions = []
        for prefix in REQUIRED_SECTIONS[role]:
            idx = next((i for i, h in enumerate(found) if h.startswith(prefix)), None)
            if idx is None:
                rep.error(md, f"missing section '## {prefix}…' (CONVENTIONS § SKILL.md body)")
            else:
                positions.append(idx)
        if positions != sorted(positions):
            rep.error(md, "required sections are out of order (CONVENTIONS § SKILL.md body)")

    scripts = skill / "scripts"
    if scripts.is_dir():
        template_common = L.TEMPLATE_DIR / "scripts" / "_common.py"
        for py in sorted(scripts.glob("*.py")):
            if py.name == "_common.py":
                if template_common.is_file() and py.read_bytes() != template_common.read_bytes():
                    rep.error(py, "vendored _common.py differs from tooling/templates/skill/scripts/_common.py — re-copy it")
                continue
            if py.name.startswith("_"):
                continue
            src = py.read_text(encoding="utf-8")
            uses_runtime = "base_parser" in src or "common_flags" in src
            if not uses_runtime:
                # a script that builds its own parser must spell the shared flags out itself
                for flag in SCRIPT_FLAGS:
                    if flag not in src:
                        rep.error(py, f"script does not support {flag} (CONVENTIONS § Scripts contract; use _common.base_parser)")
                if "argparse" not in src:
                    rep.error(py, "script has no argparse/base_parser, so --help cannot work")
            if not (scripts / "_common.py").is_file():
                rep.error(py, "scripts/ has no vendored _common.py")

    refs = skill / "references"
    if refs.is_dir():
        for ref in sorted(refs.glob("*.md")):
            rtext = ref.read_text(encoding="utf-8")
            if rtext.count("\n") > 300 and "contents" not in rtext[:1500].lower():
                rep.warn(ref, "over 300 lines without a table of contents near the top")

    assets = skill / "assets"
    if assets.is_dir():
        for f in assets.rglob("*"):
            if f.is_file() and f.stat().st_size > MAX_ASSET_BYTES:
                rep.error(f, f"asset is {f.stat().st_size // 1024} KB; assets stay under 1 MB, weights go to ${{CLAUDE_PLUGIN_DATA}}")


def lint_agent(agent: Path, rep: Report) -> None:
    try:
        fm, _ = L.read_frontmatter(agent)
    except L.FrontmatterError as e:
        rep.error(agent, f"frontmatter: {e}")
        return
    for key in ("name", "description"):
        if not fm.get(key):
            rep.error(agent, f"agent frontmatter needs '{key}'")
    if fm.get("name") and fm["name"] != agent.stem:
        rep.warn(agent, f"agent name '{fm['name']}' differs from file name '{agent.stem}'")


def lint_capabilities(plugin: Path, rep: Report) -> None:
    f = plugin / "capabilities.json"
    if not f.is_file():
        if plugin.name not in ("core", "forge"):
            rep.warn(f, "no capabilities.json; Directors cannot plan for this domain")
        return
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        rep.error(f, f"invalid JSON: {e}")
        return
    if data.get("domain") != plugin.name:
        rep.error(f, f"domain '{data.get('domain')}' must equal the plugin name")
    seen: set[str] = set()
    skill_names = {s.name for s in L.skill_dirs(plugin)}
    cases = {f"{c.parent.name}/{c.name}" for c in L.eval_cases(plugin)}
    for cap in data.get("capabilities", []):
        cid = cap.get("id", "?")
        where = f"capability {cid}"
        for key in ("id", "intents", "summary", "pipeline", "tools", "hardware", "cost", "status"):
            if key not in cap:
                rep.error(f, f"{where}: missing '{key}'")
        if not cid.startswith(plugin.name + "."):
            rep.error(f, f"{where}: id must start with '{plugin.name}.'")
        if cid in seen:
            rep.error(f, f"{where}: duplicate id")
        seen.add(cid)
        status = cap.get("status")
        if status not in L.CAPABILITY_STATUSES:
            rep.error(f, f"{where}: status '{status}' not in {sorted(L.CAPABILITY_STATUSES)}")
        for t in cap.get("tools", []):
            if not isinstance(t, dict) or "name" not in t:
                rep.error(f, f"{where}: every tools[] entry is an object with 'name'")
        skill = cap.get("skill")
        if status in ("draft", "tested", "stable"):
            if not skill or not str(skill).startswith(plugin.name + ":"):
                rep.error(f, f"{where}: status {status} needs skill '{plugin.name}:<skill>'")
            elif skill.split(":", 1)[1] not in skill_names:
                rep.error(f, f"{where}: skill '{skill}' has no folder under plugins/{plugin.name}/skills/")
        if status in ("tested", "stable"):
            evals = cap.get("evals") or []
            if not evals:
                rep.error(f, f"{where}: status {status} needs at least two eval cases (CONVENTIONS § Status lifecycle)")
            for case in evals:
                key = f"{skill.split(':', 1)[1]}/{case}" if skill and ":" in skill else case
                if key not in cases:
                    rep.error(f, f"{where}: eval '{case}' not found under plugins/{plugin.name}/evals/")


def lint_evals(plugin: Path, rep: Report) -> None:
    skill_names = {s.name for s in L.skill_dirs(plugin)}
    for case in L.eval_cases(plugin):
        if case.parent.name not in skill_names:
            rep.error(case, f"eval folder '{case.parent.name}' names no skill under plugins/{plugin.name}/skills/")
        if not L.CASE_NAME.match(case.name) or case.name in L.EVAL_RESERVED_NAMES:
            rep.error(case, "case name must be lowercase-with-hyphens and not a reserved word (CONVENTIONS § Evals)")
        prompt = case / "prompt.md"
        if not prompt.is_file():
            rep.error(case, "no prompt.md")
        else:
            try:
                fm, body = L.read_frontmatter(prompt)
                for key in sorted(set(fm) - L.EVAL_PROMPT_KEYS):
                    rep.error(prompt, f"unknown settings key '{key}' makes the case fail to load")
                if not body.strip():
                    rep.error(prompt, "prompt body is empty")
            except L.FrontmatterError as e:
                rep.error(prompt, f"settings block: {e}")
        cy = case / "case.yaml"
        if not cy.is_file():
            rep.error(case, "no case.yaml")
        else:
            ytext = cy.read_text(encoding="utf-8")
            if 'schema_version: "1.1"' not in ytext:
                rep.error(cy, 'needs schema_version: "1.1" (quoted)')
            if f"name: {case.name}" not in ytext:
                rep.error(cy, f"name must be '{case.name}'")
        graders = sorted((case / "graders").glob("*.md")) if (case / "graders").is_dir() else []
        if not graders:
            rep.error(case, "graders/ needs at least one .md (a placeholder is fine)")
        for g in graders:
            try:
                gfm, gbody = L.read_frontmatter(g)
                if "type" not in gfm:
                    rep.error(g, "grader frontmatter needs 'type'")
                if not gbody.strip():
                    rep.error(g, "grader statement is empty")
            except L.FrontmatterError as e:
                rep.error(g, f"grader frontmatter: {e}")


def lint_registry(rep: Report) -> None:
    if not L.REGISTRY.is_file():
        rep.error(L.REGISTRY, "missing; run tooling/build_registry.py")
        return
    if build_registry.MARKER not in L.REGISTRY.read_text(encoding="utf-8"):
        rep.error(L.REGISTRY, "generated marker missing — was it edited by hand?")
    if not build_registry.check():
        rep.error(L.REGISTRY, "stale; run python3 tooling/build_registry.py (REGISTRY.md is generated, never edited)")


def main(argv: list[str]) -> int:
    rep = Report()
    targets = [Path(a).resolve() for a in argv] or [L.PLUGINS]
    plugins = [p for p in L.plugin_dirs() if any(t == p or t in p.parents or p in t.parents for t in targets)]
    for plugin in plugins:
        for skill in L.skill_dirs(plugin):
            lint_skill(plugin, skill, rep)
        for agent in L.agent_files(plugin):
            lint_agent(agent, rep)
        lint_capabilities(plugin, rep)
        lint_evals(plugin, rep)
    if not argv:
        lint_registry(rep)
    for path, msg in rep.errors:
        print(f"ERROR {path}: {msg}")
    for path, msg in rep.warnings:
        print(f"WARN  {path}: {msg}")
    n_skills = sum(len(L.skill_dirs(p)) for p in plugins)
    print(f"{len(rep.errors)} errors, {len(rep.warnings)} warnings — {len(plugins)} plugins, {n_skills} skills")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
