#!/usr/bin/env python3
"""brief: create, update and validate Studio briefs and plans (out/<slug>/brief.json, plan.json).

Usage:
  brief.py slug "Make a promo for my coffee app"                         -> prints a slug
  brief.py new --domain video --slug coffee-promo [--mode auto|guided] [--out-dir out]
               [--set key=value ...] [--auto key="reason" ...] [--machine-json FILE] [--from BRIEF]
  brief.py set out/coffee-promo/brief.json key=value [key=value ...]      -> bumps revision, records history
  brief.py validate out/coffee-promo                                       -> brief.json, and plan.json if present

Values parse as JSON when they can (30, true, ["a","b"], {"k":1}); otherwise they are strings.
Dotted keys set nested fields (constraints.language=en). --json prints the document; --dry-run
prints without writing. Exit 0 ok, 1 invalid, 2 usage.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import argparse

from _common import EXIT_FAIL, EXIT_UNDECIDABLE, Failure, common_flags, finish, main_guard  # noqa: E402

SCHEMA = "0.1"
DOMAINS = {"video", "audio", "graphics", "game", "apps"}
MODES = {"auto", "guided"}
REQUIRED = ["studio", "domain", "slug", "mode", "intent", "subject", "inputs", "constraints",
            "auto_decisions", "machine", "created", "updated", "revision", "history"]
STOP = {"a", "an", "the", "for", "my", "me", "of", "to", "and", "with", "make", "create", "build", "please", "from", "in", "on"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(text: str, max_words: int = 4) -> str:
    words = [w for w in re.sub(r"[^a-z0-9]+", " ", text.lower()).split() if w not in STOP]
    slug = "-".join(words[:max_words]) or "job"
    return slug[:40].rstrip("-")


def unique_dir(out_dir: str, slug: str) -> str:
    candidate, n = slug, 1
    while os.path.exists(os.path.join(out_dir, candidate)):
        n += 1
        candidate = f"{slug}-{n}"
    return candidate


def parse_value(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def set_path(doc: dict, dotted: str, value) -> None:
    keys = dotted.split(".")
    cur = doc
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
        if not isinstance(cur, dict):
            raise Failure("input", f"cannot set {dotted}: {k} is not an object")
    cur[keys[-1]] = value


def kv(items: list[str]) -> list[tuple[str, object]]:
    out = []
    for item in items or []:
        if "=" not in item:
            raise Failure("input", f"expected key=value, got {item!r}", code=EXIT_UNDECIDABLE)
        k, _, v = item.partition("=")
        out.append((k.strip(), parse_value(v)))
    return out


def load(path: str) -> dict:
    if not os.path.isfile(path):
        raise Failure("input", f"{path} does not exist")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Failure("input", f"{path} is not valid JSON: {e}")


def write(path: str, doc: dict, dry_run: bool) -> None:
    if dry_run:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Path(path).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_brief(doc: dict) -> list[str]:
    problems = []
    for key in REQUIRED:
        if key not in doc:
            problems.append(f"brief: missing '{key}'")
    if doc.get("domain") not in DOMAINS:
        problems.append(f"brief: domain '{doc.get('domain')}' not in {sorted(DOMAINS)}")
    if doc.get("mode") not in MODES:
        problems.append(f"brief: mode '{doc.get('mode')}' not in {sorted(MODES)}")
    if not isinstance(doc.get("inputs"), list):
        problems.append("brief: inputs must be a list")
    for key in ("constraints", "auto_decisions", "machine"):
        if not isinstance(doc.get(key), dict):
            problems.append(f"brief: {key} must be an object")
    for k, v in (doc.get("auto_decisions") or {}).items():
        if not isinstance(v, str) or not v.strip():
            problems.append(f"brief: auto_decisions.{k} needs a reason (a non-empty string)")
    if not isinstance(doc.get("revision"), int) or doc.get("revision", 0) < 1:
        problems.append("brief: revision must be an integer ≥ 1")
    if not str(doc.get("intent", "")).strip():
        problems.append("brief: intent is empty")
    for pattern in doc.get("inputs") or []:
        if isinstance(pattern, str) and not glob.glob(pattern) and not os.path.exists(pattern):
            problems.append(f"brief: input '{pattern}' matches nothing (checked from {os.getcwd()})")
    return problems


def validate_plan(plan: dict, brief: dict | None) -> list[str]:
    problems = []
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["plan: steps must be a non-empty list"]
    if brief is not None and plan.get("revision") != brief.get("revision"):
        problems.append(f"plan: revision {plan.get('revision')} does not match brief revision {brief.get('revision')}")
    for i, s in enumerate(steps, start=1):
        if s.get("step") != i:
            problems.append(f"plan: step {i} is numbered {s.get('step')}")
        if not re.match(r"^[a-z][a-z0-9-]*:[a-z][a-z0-9-]*$", str(s.get("skill", ""))):
            problems.append(f"plan: step {i} skill '{s.get('skill')}' must be plugin:skill")
        if not str(s.get("action", "")).strip():
            problems.append(f"plan: step {i} has no action")
        if not str(s.get("check", "")).strip():
            problems.append(f"plan: step {i} has no check — a step without a check is not a step")
        out = s.get("output")
        if out is not None and os.path.isabs(str(out)):
            problems.append(f"plan: step {i} output must be relative to out/<slug>/")
    return problems


def cmd_slug(a) -> int:
    return finish({"status": "ok", "slug": slugify(a.text)}, a.json, summary=slugify(a.text))


def cmd_new(a) -> int:
    base: dict = {}
    if a.from_brief:
        base = load(a.from_brief)
        for key in ("slug", "revision", "history", "created", "updated"):
            base.pop(key, None)
    doc = {
        "studio": SCHEMA, "domain": a.domain, "slug": None, "mode": a.mode,
        "intent": base.get("intent", ""), "subject": base.get("subject", ""), "inputs": base.get("inputs", []),
        "constraints": base.get("constraints", {}), "auto_decisions": base.get("auto_decisions", {}),
        "machine": base.get("machine", {}), "created": now(), "updated": now(), "revision": 1, "history": [],
    }
    for k, v in base.items():
        doc.setdefault(k, v)
    for k, v in kv(a.set):
        set_path(doc, k, v)
    for k, v in kv(a.auto):
        doc["auto_decisions"][k] = str(v)
    if a.machine_json:
        m = load(a.machine_json)
        doc["machine"] = {k: m.get(k) for k in ("os", "cpu_cores", "ram_gb", "gpu", "usable", "disk_free_gb") if k in m}
    slug = unique_dir(a.out_dir, a.slug or slugify(doc.get("subject") or doc.get("intent") or "job"))
    doc["slug"] = slug
    problems = [p for p in validate_brief(doc) if "matches nothing" not in p or a.strict_inputs]
    if problems:
        raise Failure("invalid", "; ".join(problems))
    path = os.path.join(a.out_dir, slug, "brief.json")
    if os.path.exists(path) and not a.overwrite:
        raise Failure("input", f"{path} exists; pass --overwrite to replace it")
    write(path, doc, a.dry_run)
    return finish({"status": "ok", "output": path, "brief": doc, "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {path} (revision 1)")


def cmd_set(a) -> int:
    doc = load(a.brief)
    changes = []
    for k, v in kv(a.pairs):
        before = doc
        for part in k.split(".")[:-1]:
            before = before.get(part, {}) if isinstance(before, dict) else {}
        old = before.get(k.split(".")[-1]) if isinstance(before, dict) else None
        set_path(doc, k, v)
        changes.append(f"{k}: {json.dumps(old)} -> {json.dumps(v)}")
    doc["revision"] = int(doc.get("revision", 1)) + 1
    doc["updated"] = now()
    doc.setdefault("history", []).append({"at": doc["updated"], "revision": doc["revision"], "change": "; ".join(changes)})
    problems = [p for p in validate_brief(doc) if "matches nothing" not in p]
    if problems:
        raise Failure("invalid", "; ".join(problems))
    write(a.brief, doc, a.dry_run)
    plan_path = os.path.join(os.path.dirname(a.brief), "plan.json")
    notes = []
    if os.path.isfile(plan_path):
        notes.append(f"plan.json is at revision {load(plan_path).get('revision')}; re-plan the steps that depend on: "
                     + ", ".join(k for k, _ in kv(a.pairs)))
    return finish({"status": "ok", "output": a.brief, "revision": doc["revision"], "changes": changes, "notes": notes,
                   "dry_run": a.dry_run}, a.json,
                  summary=f"revision {doc['revision']}: " + "; ".join(changes) + (("\n" + "\n".join(notes)) if notes else ""))


def cmd_validate(a) -> int:
    folder = a.path if os.path.isdir(a.path) else os.path.dirname(a.path)
    brief_path, plan_path = os.path.join(folder, "brief.json"), os.path.join(folder, "plan.json")
    brief = load(brief_path)
    problems = validate_brief(brief)
    plan = None
    if os.path.isfile(plan_path):
        plan = load(plan_path)
        problems += validate_plan(plan, brief)
    result = {"status": "ok" if not problems else "failed", "brief": brief_path, "plan": plan_path if plan else None,
              "steps": len(plan["steps"]) if plan and isinstance(plan.get("steps"), list) else 0, "problems": problems}
    if problems:
        result["error"] = {"kind": "invalid", "message": "; ".join(problems)}
    code = finish(result, a.json, summary=("brief ok" + (f", plan ok ({result['steps']} steps)" if plan else ", no plan.json yet"))
                  if not problems else "INVALID:\n  " + "\n  ".join(problems))
    return code if not problems else EXIT_FAIL


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Create, update and validate Studio briefs and plans. Shared flags (--json, --dry-run, --overwrite, --timeout) go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    s = sub.add_parser("slug", parents=cf, help="derive a slug from a request"); s.add_argument("text"); s.set_defaults(fn=cmd_slug)
    n = sub.add_parser("new", parents=cf, help="create out/<slug>/brief.json")
    n.add_argument("--domain", required=True, choices=sorted(DOMAINS)); n.add_argument("--slug")
    n.add_argument("--mode", default="auto", choices=sorted(MODES)); n.add_argument("--out-dir", default="out")
    n.add_argument("--set", action="append", default=[], metavar="KEY=VALUE"); n.add_argument("--auto", action="append", default=[], metavar="KEY=REASON")
    n.add_argument("--machine-json", help="doctor.py --json output to store under machine")
    n.add_argument("--from", dest="from_brief", help="copy fields from an existing brief")
    n.add_argument("--strict-inputs", action="store_true", help="fail when an input matches no file")
    n.set_defaults(fn=cmd_new)
    st = sub.add_parser("set", parents=cf, help="change fields; bumps revision"); st.add_argument("brief"); st.add_argument("pairs", nargs="+", metavar="KEY=VALUE"); st.set_defaults(fn=cmd_set)
    v = sub.add_parser("validate", parents=cf, help="validate brief.json and plan.json"); v.add_argument("path"); v.set_defaults(fn=cmd_validate)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
