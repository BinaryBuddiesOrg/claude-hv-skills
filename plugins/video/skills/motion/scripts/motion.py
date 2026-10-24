#!/usr/bin/env python3
"""motion: per-beat clips with zoom/pan moves, optional device frame and background.

Usage:
  motion.py clip SRC -o out.mp4 --width W --height H [--in 0] [--duration D] [--focus 0.5,0.5] [--zoom 1.3]
            [--motion push-in|pull-out|hold|pan-left|pan-right|ken-burns] [--fit cover|pad] [--frame none|phone|browser]
            [--bg blur|gradient|#RRGGBB] [--fps 30] [--keep-audio] [--fast]
  motion.py beats BEATS.json --out-dir DIR --width W --height H [--frame …] [--bg …] [--fps 30] [--only b3,b4] [--fast]
  motion.py mask -o mask.png --width W --height H --radius R [--fill '#15181d']

Shared flags (--json, --dry-run, --timeout, --overwrite) go after the subcommand.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, check_output_path, common_flags, ffprobe, finish, main_guard, require, run_or_fail  # noqa: E402

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic"}
DEFAULT_ZOOM = {"push-in": 1.15, "pull-out": 1.15, "hold": 1.0, "pan-left": 1.2, "pan-right": 1.2, "ken-burns": 1.12}


def even(n: float) -> int:
    v = int(round(n))
    return v if v % 2 == 0 else v - 1


def rounded_alpha_expr(w: int, h: int, r: int) -> str:
    return (f"if(lt(X,{r})*lt(Y,{r})*gt(hypot({r}-X,{r}-Y),{r})+gt(X,{w - r})*lt(Y,{r})*gt(hypot(X-{w - r},{r}-Y),{r})"
            f"+lt(X,{r})*gt(Y,{h - r})*gt(hypot({r}-X,Y-{h - r}),{r})+gt(X,{w - r})*gt(Y,{h - r})*gt(hypot(X-{w - r},Y-{h - r}),{r}),0,255)")


def make_mask(path: str, w: int, h: int, r: int, fill: str, timeout: float, dry_run: bool) -> list[str]:
    c = fill.lstrip("#")
    rr, gg, bb = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    vf = f"format=rgba,geq=r='{rr}':g='{gg}':b='{bb}':a='{rounded_alpha_expr(w, h, max(0, min(r, w // 2 - 1, h // 2 - 1)))}'"
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-f", "lavfi", "-i", f"color=c=white:s={w}x{h}", "-frames:v", "1", "-vf", vf, path]
    run_or_fail(cmd, timeout, dry_run, what="ffmpeg mask")
    return cmd


def zoom_exprs(motion: str, zoom: float, fx: float, fy: float, n: int) -> tuple[str, str, str]:
    Z = max(1.0, zoom)
    N = max(1, n)
    if motion == "push-in":
        z = f"min(1+({Z}-1)*on/{N},{Z})"
    elif motion == "pull-out":
        z = f"max({Z}-({Z}-1)*on/{N},1)"
    elif motion == "ken-burns":
        z = f"min(1+({Z}-1)*on/{N},{Z})"
    else:
        z = f"{Z}"
    x = f"{fx}*(iw-iw/zoom)"
    y = f"{fy}*(ih-ih/zoom)"
    if motion == "pan-right":
        x = f"(iw-iw/zoom)*min(on/{N},1)"
    elif motion == "pan-left":
        x = f"(iw-iw/zoom)*(1-min(on/{N},1))"
    return z, x, y


def render_clip(src: str, out: str, W: int, H: int, in_s: float, dur: float | None, fx: float, fy: float, zoom: float | None, motion: str,
                fit: str, frame: str, bg: str, fps: float, keep_audio: bool, fast: bool, timeout: float, dry_run: bool, work: Path) -> dict:
    is_image = Path(src).suffix.lower() in IMAGE_EXT
    if not os.path.isfile(src):
        raise Failure("input", f"{src} does not exist")
    p = ffprobe(src, timeout)
    if not p["has_video"]:
        raise Failure("input", f"{src} has no picture")
    if dur is None:
        dur = 3.0 if is_image else max(0.1, p["duration"] - in_s)
    if not is_image and in_s + dur > p["duration"] + 0.05:
        raise Failure("input", f"{src}: in {in_s} + duration {dur} exceeds {p['duration']} s")
    if motion == "ken-burns" and not is_image:
        motion = "push-in"
    Z = zoom if zoom is not None else DEFAULT_ZOOM.get(motion, 1.0)
    if motion == "hold" and zoom is None:
        Z = 1.0
    n = int(round(dur * fps))
    z, x, y = zoom_exprs(motion, Z, fx, fy, n)

    # inner box
    if frame == "phone":
        box_w, box_h, radius_f, bezel_f = 0.84, 0.82, 0.05, 0.02
    elif frame == "browser":
        box_w, box_h, radius_f, bezel_f = 0.90, 0.80, 0.015, 0.01
    else:
        box_w, box_h, radius_f, bezel_f = 1.0, 1.0, 0.0, 0.0
    sw, sh = int(p["width"]), int(p["height"])
    if abs(int(p.get("rotation") or 0)) in (90, 270):
        sw, sh = sh, sw
    if frame == "none":
        IW, IH = W, H
    else:
        scale = min(W * box_w / sw, H * box_h / sh)
        IW, IH = even(sw * scale), even(sh * scale)
    inputs: list[str] = []
    if is_image:
        inputs += ["-loop", "1", "-framerate", f"{fps:g}", "-t", f"{dur + 0.2:.3f}", "-i", src]
    else:
        inputs += ["-ss", f"{in_s:.3f}", "-t", f"{dur + 0.5:.3f}", "-i", src]
    # conform to the inner aspect (cover on focus, or pad), upsample, zoompan
    if fit == "pad" and frame == "none":
        conform = f"scale={IW}:{IH}:force_original_aspect_ratio=decrease,pad={IW}:{IH}:(ow-iw)/2:(oh-ih)/2:color=black"
    else:
        conform = f"scale={IW}:{IH}:force_original_aspect_ratio=increase,crop={IW}:{IH}:x=(iw-{IW})*{fx}:y=(ih-{IH})*{fy}"
    up_w, up_h = even(IW * 1.5), even(IH * 1.5)
    zp = f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={IW}x{IH}:fps={fps:g}"
    if is_image:
        zp = f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={IW}x{IH}:fps={fps:g}"
        rec = f"[0:v]{conform},scale={up_w}:{up_h},{zp},trim=duration={dur:.3f},setpts=PTS-STARTPTS[rec]"
    else:
        rec = f"[0:v]fps={fps:g},{conform},scale={up_w}:{up_h},{zp},trim=duration={dur:.3f},setpts=PTS-STARTPTS[rec]"
    fc = [rec]
    vout = "rec"
    cmds: list[list[str]] = []
    if frame != "none":
        radius = max(2, int(IW * radius_f))
        bez = max(2, int(IW * bezel_f))
        mask = str(work / f"mask_{IW}x{IH}_{radius}.png")
        bezel = str(work / f"bezel_{IW + 2 * bez}x{IH + 2 * bez}_{radius + bez}.png")
        if not os.path.isfile(mask):
            cmds.append(make_mask(mask, IW, IH, radius, "#FFFFFF", timeout, dry_run))
        if not os.path.isfile(bezel):
            cmds.append(make_mask(bezel, IW + 2 * bez, IH + 2 * bez, radius + bez, "#15181d", timeout, dry_run))
        inputs += ["-loop", "1", "-i", mask, "-loop", "1", "-i", bezel]
        if bg == "blur":
            inputs += (["-loop", "1", "-t", f"{dur + 0.2:.3f}", "-i", src] if is_image else ["-ss", f"{in_s:.3f}", "-t", f"{dur + 0.5:.3f}", "-i", src])
            fc.append(f"[3:v]fps={fps:g},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3,colorlevels=rimax=0.75:gimax=0.75:bimax=0.75,trim=duration={dur:.3f},setpts=PTS-STARTPTS[bg]")
        elif bg == "gradient":
            inputs += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"gradients=s={W}x{H}:c0=#141821:c1=#2b3244:x0=0:y0=0:x1=0:y1={H}:r={fps:g}"]
            fc.append("[3:v]format=yuv420p[bg]")
        else:
            inputs += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"color=c=0x{bg.lstrip('#')}:s={W}x{H}:r={fps:g}"]
            fc.append("[3:v]format=yuv420p[bg]")
        fc.append("[rec]format=rgba[recrgba];[recrgba][1:v]alphamerge[recr]")
        fc.append("[2:v]format=rgba[bz]")
        if frame == "browser":
            bar = max(8, int(IH * 0.036))
            fc.append(f"[bz]drawbox=x=0:y=0:w=iw:h={bar + bez}:color=#2a2f36@1:t=fill[bz2]")
            fc.append(f"[bg][bz2]overlay=(W-w)/2:(H-h)/2[b1]")
        else:
            fc.append("[bg][bz]overlay=(W-w)/2:(H-h)/2[b1]")
        fc.append("[b1][recr]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
        vout = "v"
    else:
        fc.append("[rec]format=yuv420p[v]")
        vout = "v"
    enc = ["-c:v", "libx264", "-preset", "veryfast" if fast else "medium", "-crf", "23" if fast else "18", "-pix_fmt", "yuv420p", "-r", f"{fps:g}", "-movflags", "+faststart"]
    audio = ["-map", "0:a:0?", "-c:a", "aac", "-b:a", "192k"] if (keep_audio and not is_image and p["has_audio"]) else ["-an"]
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", f"[{vout}]"] + audio + enc + ["-t", f"{dur:.3f}", out]
    run_or_fail(cmd, timeout, dry_run, what="ffmpeg motion")
    cmds.append(cmd)
    thumb = str(Path(out).with_suffix(".jpg"))
    if not dry_run:
        run_or_fail(["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", f"{dur / 2:.3f}", "-i", out, "-frames:v", "1", "-q:v", "3", thumb], timeout, False, what="ffmpeg thumb")
    o = None if dry_run else ffprobe(out, timeout)
    return {"output": out, "thumb": thumb, "duration_s": o and o["duration"], "planned_s": round(dur, 3), "motion": motion, "zoom": Z,
            "focus": [fx, fy], "frame": frame, "bg": bg, "inner": [IW, IH], "commands": cmds}


def parse_focus(s: str) -> tuple[float, float]:
    try:
        fx, fy = (float(v) for v in s.split(","))
    except ValueError:
        raise Failure("input", f"--focus must be x,y in 0..1, got {s!r}")
    return min(1.0, max(0.0, fx)), min(1.0, max(0.0, fy))


def cmd_clip(a) -> int:
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    work = Path(a.output).parent
    work.mkdir(parents=True, exist_ok=True)
    fx, fy = parse_focus(a.focus)
    r = render_clip(a.src, a.output, a.width, a.height, a.in_s, a.duration, fx, fy, a.zoom, a.motion, a.fit, a.frame, a.bg, a.fps,
                    a.keep_audio, a.fast, a.timeout, a.dry_run, work)
    r.update(status="ok", dry_run=a.dry_run)
    return finish(r, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {r['planned_s']} s, {a.motion} ×{r['zoom']} on {fx},{fy}, frame {a.frame}, bg {a.bg}" + ("" if a.dry_run else f" — view {r['thumb']}"))


def cmd_beats(a) -> int:
    require("ffmpeg")
    beats = json.loads(Path(a.beats).read_text(encoding="utf-8"))
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    only = set(x.strip() for x in a.only.split(",")) if a.only else None
    base = Path(a.beats).resolve().parent
    results, skipped = [], []
    for b in beats.get("beats") or []:
        bid = b.get("id")
        if only and bid not in only:
            continue
        vis = b.get("visual") or {}
        src = str(vis.get("source") or "")
        if not src or src in ("text",) or src.startswith(("color:", "ai:")):
            skipped.append((bid, src or "(none)"))
            continue
        path = src[6:] if src.startswith("image:") else src
        path = path if os.path.isabs(path) else str((base / path) if (base / path).exists() else path)
        fx, fy = (vis.get("focus") or [0.5, 0.5])[:2]
        motion = vis.get("motion") or ("ken-burns" if src.startswith("image:") else ("hold" if a.frame != "none" and vis.get("zoom") is None else "push-in"))
        out = str(out_dir / f"{bid}.mp4")
        if os.path.isfile(out) and not a.overwrite:
            os.remove(out)
        r = render_clip(path, out, a.width, a.height, float(vis.get("in_s", 0) or 0), float(b["duration_s"]), float(fx), float(fy), vis.get("zoom"),
                        motion, vis.get("fit", "cover"), a.frame, a.bg, a.fps, False, a.fast, a.timeout, a.dry_run, out_dir)
        r["beat"] = bid
        results.append(r)
    bad = [r for r in results if r["duration_s"] is not None and abs(r["duration_s"] - r["planned_s"]) > 0.05]
    result = {"status": "ok" if not bad else "failed", "out_dir": str(out_dir), "clips": results, "skipped": skipped, "dry_run": a.dry_run}
    if bad:
        result["error"] = {"kind": "verify", "message": "; ".join(f"{r['beat']}: {r['duration_s']} s vs {r['planned_s']} s planned" for r in bad)}
    lines = [f"  {r['beat']:4} {r['planned_s']:5.2f}s {r['motion']:9} x{r['zoom']:<4} focus {r['focus']} -> {r['output']}" for r in results]
    if skipped:
        lines.append("  skipped (text/color/ai beats are drawn by ASS or supplied later): " + ", ".join(f"{b} ({s})" for b, s in skipped))
    return finish(result, a.json, summary=f"{'would render' if a.dry_run else 'rendered'} {len(results)} beat clips in {out_dir} ({a.frame} frame, {a.bg} bg)\n" + "\n".join(lines))


def cmd_mask(a) -> int:
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    cmd = make_mask(a.output, a.width, a.height, a.radius, a.fill, a.timeout, a.dry_run)
    return finish({"status": "ok", "output": a.output, "commands": [cmd], "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}")


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Per-beat clips with zoom/pan, device frames, backgrounds. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--width", type=int, required=True); common.add_argument("--height", type=int, required=True)
    common.add_argument("--frame", default="none", choices=["none", "phone", "browser"]); common.add_argument("--bg", default="blur", help="blur | gradient | #RRGGBB")
    common.add_argument("--fps", type=float, default=30.0); common.add_argument("--fast", action="store_true")
    c = sub.add_parser("clip", parents=cf + [common]); c.add_argument("src"); c.add_argument("-o", "--output", required=True)
    c.add_argument("--in", dest="in_s", type=float, default=0.0); c.add_argument("--duration", type=float); c.add_argument("--focus", default="0.5,0.5")
    c.add_argument("--zoom", type=float); c.add_argument("--motion", default="push-in", choices=sorted(DEFAULT_ZOOM)); c.add_argument("--fit", default="cover", choices=["cover", "pad"])
    c.add_argument("--keep-audio", action="store_true"); c.set_defaults(fn=cmd_clip)
    b = sub.add_parser("beats", parents=cf + [common]); b.add_argument("beats"); b.add_argument("--out-dir", required=True); b.add_argument("--only"); b.set_defaults(fn=cmd_beats)
    m = sub.add_parser("mask", parents=cf); m.add_argument("-o", "--output", required=True); m.add_argument("--width", type=int, required=True); m.add_argument("--height", type=int, required=True)
    m.add_argument("--radius", type=int, required=True); m.add_argument("--fill", default="#15181d"); m.set_defaults(fn=cmd_mask)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
