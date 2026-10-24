#!/usr/bin/env python3
"""cards: PNG cards and badges with alpha for timeline overlays (Latin text via drawtext).

Usage:
  cards.py end --text "…" [--url "…"] -o end.png --width W --height H [--bg '#111111'|transparent] [--accent '#FFD400'] [--logo logo.png] [--font NAME]
  cards.py title --text "…" [--subtitle "…"] -o title.png --width W --height H [--bg …] [--font NAME]
  cards.py badge --logo logo.png -o badge.png --size 180 [--plate]

Shared flags go after the subcommand. For non-Latin scripts use ass_text.py (libass shapes them; drawtext does not).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, check_output_path, common_flags, finish, main_guard, require, run_or_fail  # noqa: E402


def dt_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\\\\\'").replace("%", "\\%")


def font_opt(font: str | None) -> str:
    return f":font='{font}'" if font else ""


def bg_input(bg: str, W: int, H: int) -> list[str]:
    if bg == "transparent":
        return ["-f", "lavfi", "-i", f"color=c=black@0.0:s={W}x{H},format=rgba"]
    return ["-f", "lavfi", "-i", f"color=c=0x{bg.lstrip('#')}:s={W}x{H},format=rgba"]


def cmd_end(a) -> int:
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    W, H = a.width, a.height
    m = min(W, H)
    size, url_size = round(m * 0.08), round(m * 0.05)
    inputs = bg_input(a.bg, W, H)
    fc = []
    cur = "0:v"
    if a.logo:
        if not os.path.isfile(a.logo):
            raise Failure("input", f"{a.logo} does not exist")
        inputs += ["-i", a.logo]
        lw = round(m * 0.22)
        fc.append(f"[1:v]format=rgba,scale={lw}:-1[lg]")
        fc.append(f"[{cur}][lg]overlay=(W-w)/2:{H * 0.30:.0f}-h/2[b1]")
        cur = "b1"
    y_text = H * 0.52 if a.logo else H * 0.46
    draw = f"[{cur}]drawtext=text='{dt_escape(a.text)}':fontsize={size}:fontcolor=white:borderw={max(2, round(3 * H / 1080))}:bordercolor=black:x=(w-text_w)/2:y={y_text:.0f}-text_h/2{font_opt(a.font)}"
    if a.url:
        draw += f",drawtext=text='{dt_escape(a.url)}':fontsize={url_size}:fontcolor=0x{a.accent.lstrip('#')}:borderw=2:bordercolor=black:x=(w-text_w)/2:y={y_text + size * 1.6:.0f}-text_h/2{font_opt(a.font)}"
    fc.append(draw + "[v]")
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[v]", "-frames:v", "1", a.output]
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg end card")
    return finish({"status": "ok", "output": a.output, "commands": [cmd], "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output} ({W}x{H} end card)")


def cmd_title(a) -> int:
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    W, H = a.width, a.height
    m = min(W, H)
    size, sub_size = round(m * 0.11), round(m * 0.045)
    draw = f"[0:v]drawtext=text='{dt_escape(a.text)}':fontsize={size}:fontcolor=white:borderw={max(2, round(3 * H / 1080))}:bordercolor=black:x=(w-text_w)/2:y={H * 0.46:.0f}-text_h/2{font_opt(a.font)}"
    if a.subtitle:
        draw += f",drawtext=text='{dt_escape(a.subtitle)}':fontsize={sub_size}:fontcolor=0x{a.accent.lstrip('#')}:x=(w-text_w)/2:y={H * 0.46 + size * 1.1:.0f}-text_h/2{font_opt(a.font)}"
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y"] + bg_input(a.bg, W, H) + ["-filter_complex", draw + "[v]", "-map", "[v]", "-frames:v", "1", a.output]
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg title card")
    return finish({"status": "ok", "output": a.output, "commands": [cmd], "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output} ({W}x{H} title card)")


def cmd_badge(a) -> int:
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    if not os.path.isfile(a.logo):
        raise Failure("input", f"{a.logo} does not exist")
    pad = 8
    if a.plate:
        fc = (f"[0:v]format=rgba,scale={a.size - 2 * pad}:-1[lg];color=c=black@0.5:s={a.size}x{a.size},format=rgba[pl];"
              f"[pl][lg]overlay=(W-w)/2:(H-h)/2[v]")
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.logo, "-filter_complex", fc, "-map", "[v]", "-frames:v", "1", a.output]
    else:
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.logo, "-vf", f"format=rgba,scale={a.size}:-1", "-frames:v", "1", a.output]
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg badge")
    return finish({"status": "ok", "output": a.output, "commands": [cmd], "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output} ({a.size}px badge)")


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="PNG cards and badges for overlays. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    geo = argparse.ArgumentParser(add_help=False)
    geo.add_argument("-o", "--output", required=True); geo.add_argument("--width", type=int, required=True); geo.add_argument("--height", type=int, required=True)
    geo.add_argument("--bg", default="#111111", help="#RRGGBB or transparent"); geo.add_argument("--accent", default="#FFD400"); geo.add_argument("--font")
    e = sub.add_parser("end", parents=cf + [geo]); e.add_argument("--text", required=True); e.add_argument("--url"); e.add_argument("--logo"); e.set_defaults(fn=cmd_end)
    ti = sub.add_parser("title", parents=cf + [geo]); ti.add_argument("--text", required=True); ti.add_argument("--subtitle"); ti.set_defaults(fn=cmd_title)
    bd = sub.add_parser("badge", parents=cf); bd.add_argument("--logo", required=True); bd.add_argument("-o", "--output", required=True); bd.add_argument("--size", type=int, default=180); bd.add_argument("--plate", action="store_true"); bd.set_defaults(fn=cmd_badge)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
