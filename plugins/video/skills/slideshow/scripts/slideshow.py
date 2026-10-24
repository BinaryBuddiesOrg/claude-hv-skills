#!/usr/bin/env python3
"""slideshow: plan beats from images, make contact sheets, render slides, pair images.

Usage:
  slideshow.py plan "photos/*.jpg" -o out/<slug>/beats.json [--target 60] [--per-image 3] [--order date|name|list] [--list files.txt]
               [--title "…"] [--closing "…"] [--group-by folder|gap] [--style default|product|gentle] [--aspect 16:9|9:16] [--language en]
  slideshow.py sheet "photos/*.jpg" -o sheet.png [--cols 5]
  slideshow.py slides DECK.pdf --out-dir DIR [--width 1920]
  slideshow.py pairs BEFORE.jpg AFTER.jpg -o pair.png [--label-left Before --label-right After]

Shared flags go after the subcommand.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, check_output_path, common_flags, ffprobe, finish, main_guard, require, run, run_or_fail, which  # noqa: E402

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic"}
STYLES = {"default": (3.0, 0.5, 1.12), "product": (2.0, 0.3, 1.18), "gentle": (4.5, 0.8, 1.08)}
MOTIONS = [("push-in", [0.5, 0.5]), ("pull-out", [0.5, 0.5]), ("push-in", [0.35, 0.5]), ("push-in", [0.65, 0.5])]


def expand(patterns: list[str]) -> list[str]:
    files = []
    for pat in patterns:
        hits = sorted(glob.glob(pat, recursive=True)) if any(ch in pat for ch in "*?[") else [pat]
        files += [h for h in hits if Path(h).suffix.lower() in IMAGE_EXT]
    seen, out = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    if not out:
        raise Failure("input", "no images matched")
    return out


def exif_date(path: str, timeout: float) -> datetime | None:
    try:
        p = ffprobe(path, timeout)
        tags = (p.get("raw") or {}).get("format", {}).get("tags", {}) or {}
        for key in ("creation_time", "DateTimeOriginal", "date"):
            if key in tags:
                s = tags[key].replace("T", " ").replace("Z", "")[:19]
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S"):
                    try:
                        return datetime.strptime(s, fmt)
                    except ValueError:
                        pass
    except Failure:
        return None
    return datetime.fromtimestamp(os.path.getmtime(path))


def cmd_plan(a) -> int:
    files = expand(a.images)
    if a.order == "list":
        if not a.list:
            raise Failure("input", "--order list needs --list FILE")
        order = [ln.strip() for ln in Path(a.list).read_text(encoding="utf-8").splitlines() if ln.strip()]
        files = [f for f in order if f in files] + [f for f in files if f not in order]
    elif a.order == "date":
        files.sort(key=lambda f: exif_date(f, a.timeout) or datetime.max)
    hold, dissolve, zoom = STYLES[a.style]
    if a.per_image:
        hold = a.per_image
    n = len(files)
    groups: list[list[str]] = []
    if a.group_by == "folder":
        cur_dir = None
        for f in files:
            d = str(Path(f).parent)
            if d != cur_dir:
                groups.append([])
                cur_dir = d
            groups[-1].append(f)
    elif a.group_by == "gap":
        last = None
        for f in files:
            d = exif_date(f, a.timeout)
            if last is None or (d and last and (d - last).total_seconds() > 6 * 3600):
                groups.append([])
            groups[-1].append(f)
            last = d or last
    else:
        groups = [files]
    titled = {g[0] for g in groups if len(groups) > 1}
    holds = [hold + 1.0 if f in titled else hold for f in files]
    extra = (2.5 if a.title else 0) + (3.0 if a.closing else 0)
    if a.target:
        body = a.target - extra + dissolve * (n - 1)
        factor = body / sum(holds) if sum(holds) else 1
        holds = [max(1.5, round(h * factor, 2)) for h in holds]
    beats, t, unreadable = [], 0.0, []
    if a.title:
        beats.append({"id": "title", "purpose": "title", "start_s": 0.0, "duration_s": 2.5, "voice": "", "on_screen": a.title,
                      "visual": {"source": f"image:{files[0]}", "focus": [0.5, 0.5], "zoom": 1.05, "motion": "hold", "fit": "cover"}, "caption": False, "transition": "cut"})
        t += 2.5
    for i, (f, h) in enumerate(zip(files, holds)):
        try:
            p = ffprobe(f, a.timeout)
            if not p["has_video"]:
                unreadable.append(f)
                continue
        except Failure:
            unreadable.append(f)
            continue
        motion, focus = MOTIONS[i % len(MOTIONS)]
        on_screen = ""
        if f in titled:
            on_screen = Path(f).parent.name.replace("_", " ").replace("-", " ").title() if a.group_by == "folder" else f"Part {sum(1 for g in groups[:next(k for k, g in enumerate(groups) if g[0] == f) + 1])}"
        beats.append({"id": f"p{i + 1}", "purpose": "chapter" if on_screen else "free", "start_s": round(t, 3), "duration_s": h, "voice": "", "on_screen": on_screen,
                      "visual": {"source": f"image:{f}", "focus": focus, "zoom": zoom, "motion": motion, "fit": a.fit}, "caption": False,
                      "transition": "dissolve" if (i > 0 or a.title) else "cut"})
        t += h - (dissolve if (i > 0 or a.title) else 0)
    if a.closing:
        beats.append({"id": "closing", "purpose": "closer", "start_s": round(t, 3), "duration_s": 3.0, "voice": "", "on_screen": a.closing,
                      "visual": {"source": "color:#000000"}, "caption": False, "transition": "dissolve"})
        t += 3.0 - dissolve
    # reflow starts exactly (timeline subtracts dissolves itself; beats stay contiguous)
    tt = 0.0
    for b in beats:
        b["start_s"] = round(tt, 3)
        tt += b["duration_s"]
    doc = {"studio_beats": "0.1", "title": a.title or "", "language": a.language, "wpm": 150, "target_duration_s": a.target or round(tt, 1),
           "aspect": a.aspect, "voice": {"mode": "none", "voice": "", "rate": 1.0}, "music": {"mood": "calm" if a.style == "gentle" else "upbeat", "duck_db": -12, "file": None},
           "beats": beats, "cta": {"text": a.closing or "", "url_on_screen": ""}, "slideshow": {"dissolve_s": dissolve, "images": n, "groups": len(groups), "unreadable": unreadable}}
    if not a.dry_run:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = round(sum(b["duration_s"] for b in beats) - dissolve * max(0, sum(1 for b in beats if b.get("transition") == "dissolve")), 2)
    result = {"status": "ok", "output": a.output, "images": n, "groups": len(groups), "beats": len(beats), "hold_s": holds[:3], "dissolve_s": dissolve, "total_s": total,
              "unreadable": unreadable, "dry_run": a.dry_run}
    return finish(result, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {n} images in {len(groups)} group(s), {len(beats)} beats, ≈{total} s"
                  + (f"; unreadable: {', '.join(unreadable)}" if unreadable else ""))


def cmd_sheet(a) -> int:
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    files = expand(a.images)[:60]
    cols = a.cols
    n = len(files)
    rows = (n + cols - 1) // cols
    inputs, fc = [], []
    for i, f in enumerate(files):
        inputs += ["-i", f]
        fc.append(f"[{i}:v]scale=320:320:force_original_aspect_ratio=decrease,pad=324:324:(ow-iw)/2:(oh-ih)/2:color=0x202020,drawtext=text='{i + 1}':fontsize=28:fontcolor=white:borderw=2:x=8:y=8[f{i}]")
    fc.append("".join(f"[f{i}]" for i in range(n)) + f"xstack=inputs={n}:layout=" + "|".join(f"{(i % cols) * 324}_{(i // cols) * 324}" for i in range(n)) + ":fill=0x202020[v]")
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[v]", "-frames:v", "1", a.output]
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg sheet")
    return finish({"status": "ok", "output": a.output, "images": n, "order": files, "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {n} images numbered in order — view it")


def cmd_slides(a) -> int:
    if not os.path.isfile(a.deck):
        raise Failure("input", f"{a.deck} does not exist")
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    deck = a.deck
    if deck.lower().endswith((".pptx", ".ppt", ".odp", ".key")):
        if not which("soffice"):
            raise Failure("missing_tool", "soffice (LibreOffice) is needed to convert slides to PDF", "recipe in core:doctor; or export the deck to PDF yourself", 127)
        run_or_fail(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), deck], a.timeout, a.dry_run, what="soffice")
        deck = str(out_dir / (Path(deck).stem + ".pdf"))
    if not which("pdftoppm"):
        raise Failure("missing_tool", "pdftoppm (poppler) is needed to render PDF pages", "recipe in core:doctor (poppler-utils)", 127)
    run_or_fail(["pdftoppm", "-png", "-scale-to", str(a.width), deck, str(out_dir / "slide")], a.timeout, a.dry_run, what="pdftoppm")
    pages = sorted(glob.glob(str(out_dir / "slide*.png")))
    return finish({"status": "ok", "out_dir": str(out_dir), "pages": pages, "dry_run": a.dry_run}, a.json, summary=f"{'would render' if a.dry_run else 'rendered'} {len(pages)} pages into {out_dir} (use: plan \"{out_dir}/slide*.png\" --per-image 6 --style default)")


def cmd_pairs(a) -> int:
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    fc = (f"[0:v]scale=960:1080:force_original_aspect_ratio=decrease,pad=960:1080:(ow-iw)/2:(oh-ih)/2:color=0x101010,"
          f"drawtext=text='{a.label_left}':fontsize=48:fontcolor=white:borderw=3:x=(w-text_w)/2:y=40[l];"
          f"[1:v]scale=960:1080:force_original_aspect_ratio=decrease,pad=960:1080:(ow-iw)/2:(oh-ih)/2:color=0x101010,"
          f"drawtext=text='{a.label_right}':fontsize=48:fontcolor=white:borderw=3:x=(w-text_w)/2:y=40[r];[l][r]hstack[v]")
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.before, "-i", a.after, "-filter_complex", fc, "-map", "[v]", "-frames:v", "1", a.output]
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg pair")
    return finish({"status": "ok", "output": a.output, "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output} (1920x1080 pair)")


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Plan and prepare slideshows. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    pl = sub.add_parser("plan", parents=cf); pl.add_argument("images", nargs="+"); pl.add_argument("-o", "--output", required=True); pl.add_argument("--target", type=float)
    pl.add_argument("--per-image", type=float); pl.add_argument("--order", default="date", choices=["date", "name", "list"]); pl.add_argument("--list"); pl.add_argument("--title"); pl.add_argument("--closing")
    pl.add_argument("--group-by", default="none", choices=["none", "folder", "gap"]); pl.add_argument("--style", default="default", choices=sorted(STYLES)); pl.add_argument("--aspect", default="16:9")
    pl.add_argument("--fit", default="pad", choices=["pad", "cover"]); pl.add_argument("--language", default="en"); pl.set_defaults(fn=cmd_plan)
    sh = sub.add_parser("sheet", parents=cf); sh.add_argument("images", nargs="+"); sh.add_argument("-o", "--output", required=True); sh.add_argument("--cols", type=int, default=5); sh.set_defaults(fn=cmd_sheet)
    sl = sub.add_parser("slides", parents=cf); sl.add_argument("deck"); sl.add_argument("--out-dir", required=True); sl.add_argument("--width", type=int, default=1920); sl.set_defaults(fn=cmd_slides)
    pr = sub.add_parser("pairs", parents=cf); pr.add_argument("before"); pr.add_argument("after"); pr.add_argument("-o", "--output", required=True)
    pr.add_argument("--label-left", default="Before"); pr.add_argument("--label-right", default="After"); pr.set_defaults(fn=cmd_pairs)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
