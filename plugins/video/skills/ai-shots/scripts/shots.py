#!/usr/bin/env python3
"""shots: shot list + prompts per beat for AI video tools; verify received clips.

Usage:
  shots.py plan BEATS.json --anchors anchors.json --tool veo|runway|kling|seedance|pika|pixverse|generic -o shots.json [--md shots.md]
           [--style "cinematic drama"|"anime"|…] [--variations 2] [--redo]
  shots.py check --dir work/ai --beats BEATS.json [--shots shots.json] [--json]

anchors.json: {"characters": "…", "palette": "…", "lens": "…", "time_of_day": "…", "film_style": "…", "negatives": "…", "reference_images": {"hero": "refs/hero.png"}}
Beats whose visual.source is "ai:<shot-id>" become shots; visual.shot (free text) says what must be visible.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, common_flags, ffprobe, finish, main_guard, require, run_or_fail, which  # noqa: E402

TOOLS = {
    "veo": {"lengths": [8], "max": 8, "ref": True, "aspects": ["16:9", "9:16"], "note": "8 s native; extend in-tool for longer beats"},
    "runway": {"lengths": [5, 10], "max": 10, "ref": True, "aspects": ["16:9", "9:16", "1:1"], "note": "attach the character/product reference to every shot"},
    "kling": {"lengths": [5, 10, 15], "max": 15, "ref": True, "aspects": ["16:9", "9:16", "1:1"], "note": "multi-shot prompts allowed for one scene"},
    "seedance": {"lengths": [15, 20], "max": 20, "ref": True, "aspects": ["16:9", "9:16"], "note": "one generation can carry a whole scene"},
    "pika": {"lengths": [5, 10], "max": 10, "ref": True, "aspects": ["16:9", "9:16", "1:1"], "note": "effects presets; cheap tests"},
    "pixverse": {"lengths": [5, 8], "max": 8, "ref": True, "aspects": ["16:9", "9:16"], "note": "free tier for tests"},
    "generic": {"lengths": [5, 10], "max": 10, "ref": False, "aspects": ["16:9", "9:16", "1:1"], "note": "check the tool's limits"},
}
STYLE_BLOCKS = {
    "cinematic drama": "35 mm film grain, anamorphic, 24 fps, letterbox 2.39:1, muted palette",
    "commercial": "clean studio, three-point lighting, slow smooth orbit, premium, editorial",
    "documentary": "natural diffused light, locked-off or slow push, true colours",
    "action": "handheld, slight shake, motion blur on fast elements, 60 fps slow-motion burst on the key moment",
    "sci-fi": "volumetric neon, atmospheric haze, holographic elements, anamorphic flares",
    "anime": "2D anime style, clean line art, flat cel shading with two-tone shadows, limited animation feel, consistent character design, soft painterly background, no photorealism, no 3D render look",
    "cartoon": "bold outlines, flat colours, expressive faces, simple backgrounds, consistent character design, no photorealism",
}
NEGATIVES = "no text, no captions, no logos, no watermark, no extra people, no distorted hands, no morphing, no sudden cuts"


def shot_length(d: float, tool: dict) -> float:
    need = d + 0.5
    for L in tool["lengths"]:
        if L >= need:
            return float(L)
    return float(tool["max"])


def build_prompt(b: dict, anchors: dict, style: str, aspect: str, redo_reason: str | None) -> str:
    shot = (b.get("visual") or {}).get("shot") or b.get("on_screen") or b.get("voice") or b.get("purpose", "")
    purpose = b.get("purpose", "")
    shot_type = {"hook": "Medium close-up, eye level", "problem": "Medium shot", "solution": "Medium shot", "feature": "Close-up", "proof": "Wide shot",
                 "cta": "Medium close-up", "title": "Extreme wide shot, establishing", "world": "Extreme wide shot, establishing", "tension": "Close-up, low angle",
                 "reveal": "Medium shot, slow push-in", "chapter": "Wide shot", "step": "Close-up"}.get(purpose, "Medium shot")
    camera = {"hook": "slow steadicam push-in", "title": "slow crane descend", "world": "slow dolly forward", "tension": "handheld, slight shake",
              "reveal": "slow push-in then hold", "cta": "locked-off"}.get(purpose, "slow dolly in")
    def sentence(s: str) -> str:
        s = (s or "").strip().rstrip(".")
        return (s[0].upper() + s[1:] + ".") if s else ""
    chars = anchors.get("characters", "").strip()
    env = ", ".join(x for x in (anchors.get("environment", "").strip(), anchors.get("time_of_day", "").strip()) if x)
    parts = [
        f"{shot_type} — {chars}." if chars else f"{shot_type}.",
        sentence(shot),
        sentence(env),
        f"Lighting: {anchors.get('lighting', 'motivated, soft key, practical lights')}.",
        f"Camera: {camera}.",
        f"Style: {STYLE_BLOCKS.get(style, style)}; {anchors.get('lens', '35 mm, shallow depth of field')}; {anchors.get('film_style', '24 fps')}; palette {anchors.get('palette', 'natural')}.",
        f"Aspect {aspect}.",
        f"Negative: {anchors.get('negatives', NEGATIVES)}" + (f"; {redo_reason}" if redo_reason else "") + ".",
    ]
    return " ".join(p for p in parts if p)


def load_json(path: str, what: str) -> dict:
    if not Path(path).is_file():
        raise Failure("input", f"{what} {path} does not exist")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Failure("input", f"{what} {path} is not valid JSON: {e}")


def cmd_plan(a) -> int:
    beats = load_json(a.beats, "beats file")
    anchors = load_json(a.anchors, "anchors file") if a.anchors else {}
    tool = TOOLS[a.tool]
    aspect = beats.get("aspect", "16:9")
    if aspect not in tool["aspects"]:
        aspect = tool["aspects"][0]
    prev = {}
    if a.redo and Path(a.output).is_file():
        prev = {s["id"]: s for s in json.loads(Path(a.output).read_text(encoding="utf-8")).get("shots", [])}
    shots = []
    for b in beats.get("beats") or []:
        src = str((b.get("visual") or {}).get("source") or "")
        if not src.startswith("ai:"):
            continue
        sid = src[3:]
        old = prev.get(sid)
        if a.redo and old and old.get("status") != "redo":
            shots.append(old)
            continue
        redo_reason = old.get("redo_reason") if old else None
        L = shot_length(float(b["duration_s"]), tool)
        n_shots = max(1, math.ceil((float(b["duration_s"]) + 0.5) / tool["max"]))
        ref = None
        for name, path in (anchors.get("reference_images") or {}).items():
            if name.lower() in (b.get("on_screen", "") + " " + b.get("voice", "") + " " + str((b.get("visual") or {}).get("shot", ""))).lower():
                ref = path
        shots.append({"id": sid, "beat": b.get("id"), "beat_duration_s": b["duration_s"], "shot_length_s": L, "shots_needed": n_shots, "aspect": aspect,
                      "prompt": build_prompt(b, anchors, a.style, aspect, redo_reason), "reference_image": ref if tool["ref"] else None,
                      "variations": a.variations, "file": f"work/ai/{sid}.mp4", "must_show": (b.get("visual") or {}).get("shot") or b.get("on_screen") or "",
                      "status": "pending", "redo_reason": None})
    if not shots:
        raise Failure("input", "no beats with visual.source 'ai:<id>' in the beats file")
    doc = {"tool": a.tool, "tool_note": tool["note"], "style": a.style, "aspect": aspect, "anchors": anchors, "shots": shots}
    if not a.dry_run:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.md:
        lines = [f"# Shots for {a.tool} — {len(shots)} shots, {aspect}", "", f"Tool note: {tool['note']}", "",
                 "Generate the variations for each shot, pick the best, and save it as the file named. Keep the prompt text exactly; add your tool's own settings (seed, motion) as you like.", ""]
        for s in shots:
            lines += [f"## {s['id']}  ({s['shot_length_s']:g} s × {s['shots_needed']}, {s['variations']} variations) → save as `{s['file']}`", "",
                      f"Must show: {s['must_show']}", ""] + ([f"Reference image: `{s['reference_image']}`", ""] if s["reference_image"] else []) + ["```", s["prompt"], "```", ""]
        if not a.dry_run:
            Path(a.md).write_text("\n".join(lines), encoding="utf-8")
    pending = [s for s in shots if s["status"] == "pending"]
    return finish({"status": "ok", "output": a.output, "md": a.md, "shots": len(shots), "pending": len(pending), "tool": a.tool, "aspect": aspect, "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}" + (f" and {a.md}" if a.md else "") + f": {len(shots)} shots for {a.tool} ({aspect}), {len(pending)} to generate")


def cmd_check(a) -> int:
    require("ffmpeg")
    beats = load_json(a.beats, "beats file")
    shots_doc = load_json(a.shots, "shots file") if a.shots and Path(a.shots).is_file() else None
    d = Path(a.dir)
    frames_dir = d / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    rows, missing = [], []
    for b in beats.get("beats") or []:
        src = str((b.get("visual") or {}).get("source") or "")
        if not src.startswith("ai:"):
            continue
        sid = src[3:]
        f = d / f"{sid}.mp4"
        if not f.is_file():
            missing.append(sid)
            rows.append({"id": sid, "present": False})
            continue
        p = ffprobe(str(f), a.timeout)
        w, h = int(p["width"]), int(p["height"])
        want = beats.get("aspect", "16:9")
        got = "16:9" if w > h * 1.3 else "9:16" if h > w * 1.3 else "1:1"
        frame = str(frames_dir / f"{sid}.jpg")
        if not a.dry_run:
            run_or_fail(["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", f"{p['duration'] / 2:.3f}", "-i", str(f), "-frames:v", "1", "-q:v", "3", frame], a.timeout, False, what="ffmpeg frame")
        ok_len = p["duration"] + 0.05 >= float(b["duration_s"])
        rows.append({"id": sid, "present": True, "duration_s": p["duration"], "needed_s": b["duration_s"], "length_ok": ok_len, "aspect": got, "aspect_ok": got == want,
                     "frame": frame, "has_audio": p["has_audio"]})
    verified = not missing and all(r.get("length_ok") and r.get("aspect_ok") for r in rows if r["present"])
    lines = []
    for r in rows:
        if not r["present"]:
            lines.append(f"  MISSING {r['id']}")
        else:
            lines.append(f"  {'ok ' if r['length_ok'] and r['aspect_ok'] else 'BAD'} {r['id']:10} {r['duration_s']:5.1f}s (need {r['needed_s']}) {r['aspect']}{'' if r['aspect_ok'] else ' (wrong aspect)'} -> view {r['frame']}")
    result = {"status": "ok" if verified else "failed", "dir": str(d), "shots": rows, "missing": missing, "verified": verified}
    if not verified:
        result["error"] = {"kind": "verify", "message": f"{len(missing)} missing; " + "; ".join(f"{r['id']} {'short' if not r.get('length_ok') else ''} {'wrong aspect' if not r.get('aspect_ok') else ''}".strip() for r in rows if r['present'] and not (r['length_ok'] and r['aspect_ok']))}
    return finish(result, a.json, summary=f"{len(rows) - len(missing)}/{len(rows)} clips present in {d}\n" + "\n".join(lines) + "\nnow view the frames and mark each shot ok or redo (with the reason) in shots.json")


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Shot lists and prompts for AI video tools; clip verification. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    pl = sub.add_parser("plan", parents=cf); pl.add_argument("beats"); pl.add_argument("--anchors"); pl.add_argument("--tool", default="generic", choices=sorted(TOOLS))
    pl.add_argument("-o", "--output", required=True); pl.add_argument("--md"); pl.add_argument("--style", default="cinematic drama"); pl.add_argument("--variations", type=int, default=2)
    pl.add_argument("--redo", action="store_true", help="re-emit only shots marked redo in the existing shots.json, with their reasons as negatives"); pl.set_defaults(fn=cmd_plan)
    ck = sub.add_parser("check", parents=cf); ck.add_argument("--dir", required=True); ck.add_argument("--beats", required=True); ck.add_argument("--shots"); ck.set_defaults(fn=cmd_check)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
