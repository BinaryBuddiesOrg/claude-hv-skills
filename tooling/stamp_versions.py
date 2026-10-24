#!/usr/bin/env python3
"""Stamp every plugin's manifest version from git history, so each commit that touches a plugin
bumps its version and installed users receive the update (ADR-013).

Usage:  python3 tooling/stamp_versions.py            # write versions
        python3 tooling/stamp_versions.py --check    # exit 1 if any manifest is stale

version = 0.<N>.0 where N = commits that touched plugins/<name>/ on HEAD, plus one when the
working tree has uncommitted changes under it (the commit about to be made). Run it right
before `git add` in the gate; `--check` is what lint calls.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=L.ROOT, capture_output=True, text=True).stdout.strip()


def expected_version(plugin: Path) -> str:
    rel = L.rel(plugin)
    n = int(git("rev-list", "--count", "HEAD", "--", rel) or 0)
    dirty = bool(git("status", "--porcelain", "--", rel))
    return f"0.{n + (1 if dirty else 0)}.0"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    stale = []
    for plugin in L.plugin_dirs():
        mf = plugin / ".claude-plugin" / "plugin.json"
        data = json.loads(mf.read_text(encoding="utf-8"))
        want = expected_version(plugin)
        if data.get("version") != want:
            stale.append((plugin.name, data.get("version"), want))
            if not check:
                # keep key order: name, displayName, version, …
                items = list(data.items())
                out = {}
                placed = False
                for k, v in items:
                    if k == "version":
                        continue
                    out[k] = v
                    if k in ("displayName", "name") and not placed and (k == "displayName" or "displayName" not in data):
                        out["version"] = want
                        placed = True
                if not placed:
                    out["version"] = want
                mf.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if check:
        for name, have, want in stale:
            print(f"stale: {name} has {have}, expected {want}")
        if stale:
            print("run python3 tooling/stamp_versions.py", file=sys.stderr)
            return 1
        print("plugin versions are up to date")
        return 0
    for name, have, want in stale:
        print(f"{name}: {have} -> {want}")
    if not stale:
        print("plugin versions already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
