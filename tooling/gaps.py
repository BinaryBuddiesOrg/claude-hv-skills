#!/usr/bin/env python3
"""Gaps = taxonomy − capabilities, per domain. This is newadder's worklist.

Usage:  python3 tooling/gaps.py <domain> [--json]

Reads taxonomy/<domain>.md § 5 (style families, the backticked names) and § 11 (the
hand-written "look at first" list), compares with plugins/<domain>/capabilities.json,
and prints: families with no capability at all, capabilities below `tested`, routes that
only exist for heavy hardware, and the taxonomy's own suggestions. Nothing here is a
verdict; it is where to look, ranked by how empty the slot is.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402

HEAVY_GPU_GB = 8


def _section(text: str, number: str) -> str:
    m = re.search(rf"^##\s+{re.escape(number)}\.?\s.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def taxonomy_families(domain: str) -> list[str]:
    path = L.TAXONOMY / f"{domain}.md"
    if not path.is_file():
        L.die(f"no taxonomy for '{domain}' at {L.rel(path)}")
    body = _section(path.read_text(encoding="utf-8"), "5")
    seen: list[str] = []
    for name in re.findall(r"`([a-z0-9][a-z0-9-]*)`", body):
        if name not in seen:
            seen.append(name)
    return seen


def taxonomy_suggestions(domain: str) -> list[str]:
    body = _section((L.TAXONOMY / f"{domain}.md").read_text(encoding="utf-8"), "11")
    items = re.findall(r"^\s*[-*]\s+(.+?)\s*$", body, re.M)
    if not items:
        items = [ln.strip() for ln in body.strip().splitlines() if ln.strip()]
    return items


def gaps(domain: str) -> dict:
    plugin = L.PLUGINS / domain
    data = L.load_capabilities(plugin) or {"capabilities": []}
    caps = data["capabilities"]
    families = taxonomy_families(domain)
    covered = {c.get("style") for c in caps if c.get("style")}
    below = [{"id": c["id"], "status": c.get("status", "?"), "skill": c.get("skill")}
             for c in caps if c.get("status") not in ("tested", "stable", "deprecated")]
    heavy = [{"id": c["id"], "gpu_vram_gb_min": (c.get("hardware") or {}).get("gpu_vram_gb_min", 0)}
             for c in caps if ((c.get("hardware") or {}).get("gpu_vram_gb_min", 0) or 0) >= HEAVY_GPU_GB
             or (c.get("hardware") or {}).get("cpu_ok") is False]
    return {
        "domain": domain,
        "families_total": len(families),
        "families_uncovered": [f for f in families if f not in covered],
        "capabilities_below_tested": sorted(below, key=lambda x: (["idea", "planned", "draft"].index(x["status"]) if x["status"] in ("idea", "planned", "draft") else 9, x["id"])),
        "heavy_hardware_only": heavy,
        "taxonomy_suggestions": taxonomy_suggestions(domain),
    }


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    g = gaps(args[0])
    if "--json" in argv:
        print(json.dumps(g, indent=2, ensure_ascii=False))
        return 0
    print(f"Gaps for {g['domain']} — taxonomy/{g['domain']}.md vs plugins/{g['domain']}/capabilities.json\n")
    print(f"Style families with no capability ({len(g['families_uncovered'])} of {g['families_total']}):")
    for f in g["families_uncovered"] or ["(none)"]:
        print(f"  - {f}")
    print(f"\nCapabilities below tested ({len(g['capabilities_below_tested'])}):")
    for c in g["capabilities_below_tested"] or [{"id": "(none)", "status": "", "skill": ""}]:
        print(f"  - {c['id']}  [{c['status']}]  {c.get('skill') or ''}".rstrip())
    print(f"\nHeavy-hardware-only routes ({len(g['heavy_hardware_only'])}):")
    for c in g["heavy_hardware_only"] or [{"id": "(none)", "gpu_vram_gb_min": ""}]:
        print(f"  - {c['id']}  GPU ≥ {c['gpu_vram_gb_min']} GB".rstrip(" GPU ≥ B"))
    print("\nTaxonomy says look at first:")
    for s in g["taxonomy_suggestions"] or ["(nothing listed)"]:
        print(f"  - {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
