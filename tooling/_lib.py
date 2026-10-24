#!/usr/bin/env python3
"""Shared helpers for Studio's maintainer tooling. Not shipped to users.

Standard library only (DECISIONS.md ADR-006). The frontmatter parser handles exactly the
YAML subset CONVENTIONS.md allows in SKILL.md: scalar `key: value`, folded `>-` / `>` and
literal `|` blocks, one level of nested mapping (`metadata:`), and inline lists `[a, b]`.
Anything else is a lint error, not a parse attempt — a skill that needs more YAML than
this is doing something the conventions did not foresee.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"
TAXONOMY = ROOT / "taxonomy"
TEMPLATE_DIR = ROOT / "tooling" / "templates" / "skill"
REGISTRY = ROOT / "REGISTRY.md"

# Frontmatter keys claude.ai accepts; every non-forge skill stays inside this set (ADR-007).
PORTABLE_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
# forge skills never leave Claude Code, so they may also use its own keys.
CLAUDE_CODE_KEYS = PORTABLE_KEYS | {
    "when_to_use", "argument-hint", "arguments", "disable-model-invocation", "user-invocable",
    "disallowed-tools", "model", "effort", "context", "agent", "background", "hooks", "paths", "shell",
}
METADATA_KEYS = {"domain", "role", "status", "version", "capabilities", "tools"}
ROLES = {"director", "producer-support", "capability", "meta"}
SKILL_STATUSES = {"idea", "draft", "tested", "stable", "deprecated"}
# `planned` = scheduled on the roadmap with a skill name reserved but no files yet.
CAPABILITY_STATUSES = {"idea", "planned", "draft", "tested", "stable", "deprecated"}
EVAL_PROMPT_KEYS = {"name", "tags", "runs", "max_turns", "timeout_seconds", "allowed_tools", "model", "env"}
EVAL_RESERVED_NAMES = {"results", "mocks", "files", "node_modules", "true", "false", "null"}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
CASE_NAME = re.compile(r"^[a-z][a-z0-9-]*$")


class FrontmatterError(ValueError):
    pass


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter, body). The opening --- must be line 1 or Claude Code ignores it."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("frontmatter must open with '---' on line 1")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    raise FrontmatterError("frontmatter never closes")


def _scalar(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [] if not inner else [_scalar(x) for x in inner.split(",")]
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if raw in ("true", "false"):
        return raw == "true"
    return raw


def parse_frontmatter(fm: str) -> dict:
    out: dict = {}
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line.startswith((" ", "\t")):
            raise FrontmatterError(f"unexpected indentation at frontmatter line {i + 1}: {line.strip()!r}")
        if ":" not in line:
            raise FrontmatterError(f"expected 'key: value' at frontmatter line {i + 1}: {line.strip()!r}")
        key, _, rest = line.partition(":")
        key, rest = key.strip(), rest.strip()
        if rest in (">-", ">", "|", "|-"):
            block = []
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            joiner = "\n" if rest.startswith("|") else " "
            out[key] = joiner.join(b for b in block if b).strip()
            continue
        if rest == "":
            nested: dict = {}
            i += 1
            while i < len(lines) and lines[i].startswith((" ", "\t")):
                sub = lines[i].strip()
                if sub and not sub.startswith("#"):
                    if ":" not in sub:
                        raise FrontmatterError(f"expected 'key: value' under '{key}' at frontmatter line {i + 1}")
                    k, _, v = sub.partition(":")
                    nested[k.strip()] = _scalar(v)
                i += 1
            out[key] = nested
            continue
        out[key] = _scalar(rest)
        i += 1
    return out


def read_frontmatter(path: Path) -> tuple[dict, str]:
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    return parse_frontmatter(fm), body


def plugin_dirs() -> list[Path]:
    return sorted(p for p in PLUGINS.iterdir() if (p / ".claude-plugin" / "plugin.json").is_file())


def skill_dirs(plugin: Path) -> list[Path]:
    skills = plugin / "skills"
    if not skills.is_dir():
        return []
    return sorted(s for s in skills.iterdir() if s.is_dir())


def agent_files(plugin: Path) -> list[Path]:
    agents = plugin / "agents"
    return sorted(agents.glob("*.md")) if agents.is_dir() else []


def load_capabilities(plugin: Path) -> dict | None:
    f = plugin / "capabilities.json"
    if not f.is_file():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def eval_cases(plugin: Path) -> list[Path]:
    """Case folders: plugins/<p>/evals/<skill>/<case>/ holding prompt.md or case.yaml."""
    root = plugin / "evals"
    if not root.is_dir():
        return []
    cases = []
    for skill_dir in sorted(root.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name in ("results", "mocks"):
            continue
        for case in sorted(skill_dir.iterdir()):
            if case.is_dir() and ((case / "prompt.md").is_file() or (case / "case.yaml").is_file()):
                cases.append(case)
    return cases


def headings(body: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^##\s+(.+?)\s*$", body, re.M)]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)
