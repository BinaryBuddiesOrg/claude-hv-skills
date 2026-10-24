#!/usr/bin/env python3
"""captions: burn styled captions into a video (SRT → ASS at the video's resolution → libass), or write a sidecar.

Usage:
  captions.py INPUT -o OUTPUT --srt CUES.srt [--style social|clean|minimal|karaoke|top] [--safe instagram-reels]
              [--font NAME] [--size PX] [--accent '#FFD400'] [--words words.json] [--rtl] [--max-chars N]
              [--sidecar] [--fast] [--dry-run] [--json] [--timeout S] [--overwrite]

Writes OUTPUT and OUTPUT.caption-check.png (the frame at the first cue, safe zones shaded with --safe).
--sidecar copies the (reflowed) SRT to OUTPUT.srt and does not re-encode (stream copy).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, check_output_path, ffprobe, finish, main_guard, require, run_or_fail  # noqa: E402

HERE = Path(__file__).resolve().parent
DESTINATIONS = HERE.parent.parent / "platform-export" / "assets" / "destinations.json"


def safe_zones(dest: str | None) -> dict:
    if not dest:
        return {}
    data = json.loads(DESTINATIONS.read_text(encoding="utf-8")) if DESTINATIONS.is_file() else {}
    spec = data.get(dest)
    if not spec:
        raise Failure("input", f"unknown destination '{dest}'")
    return spec.get("safe_zones") or {}


def filter_path(path: str) -> str:
    """Escape a path for use inside an ffmpeg filter option value."""
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")


def drawbox_zones(z: dict) -> str:
    boxes = []
    if z.get("top_pct"):
        boxes.append(f"drawbox=x=0:y=0:w=iw:h=ih*{z['top_pct'] / 100}:color=red@0.35:t=fill")
    if z.get("bottom_pct"):
        boxes.append(f"drawbox=x=0:y=ih*{1 - z['bottom_pct'] / 100}:w=iw:h=ih*{z['bottom_pct'] / 100}:color=red@0.35:t=fill")
    if z.get("right_pct"):
        boxes.append(f"drawbox=x=iw*{1 - z['right_pct'] / 100}:y=0:w=iw*{z['right_pct'] / 100}:h=ih:color=red@0.35:t=fill")
    if z.get("left_pct"):
        boxes.append(f"drawbox=x=0:y=0:w=iw*{z['left_pct'] / 100}:h=ih:color=red@0.35:t=fill")
    return ",".join(boxes)


@main_guard
def main() -> int:
    ap = base_parser("Burn styled captions into a video, or write a sidecar SRT.")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--srt", required=True, help="cues (SRT)")
    ap.add_argument("--style", default="social", choices=["social", "clean", "minimal", "karaoke", "top"])
    ap.add_argument("--safe", help="destination id: keep text out of its UI zones and shade them in the check frame")
    ap.add_argument("--font"); ap.add_argument("--size", type=int); ap.add_argument("--accent", default="#FFD400")
    ap.add_argument("--words", help="word timings JSON for karaoke"); ap.add_argument("--rtl", action="store_true")
    ap.add_argument("--max-chars", type=int, help="reflow lines to this many characters first (default by aspect)")
    ap.add_argument("--sidecar", action="store_true", help="write OUTPUT.srt beside a stream-copied video instead of burning")
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()

    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    src = ffprobe(a.input, a.timeout)
    if not src["has_video"]:
        raise Failure("input", f"{a.input} has no video stream (an audiogram makes the picture first)")
    W, H = int(src["width"]), int(src["height"])
    if abs(int(src.get("rotation") or 0)) in (90, 270):
        W, H = H, W
    max_chars = a.max_chars or (42 if W > H else 32)
    out_dir = Path(a.output).parent
    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    stem = Path(a.output).stem

    # 1. reflow cues to the aspect's line length
    cues_srt = str(work / f"{stem}.cues.srt")
    run_or_fail([sys.executable, str(HERE / "srt.py"), "split", a.srt, "-o", cues_srt, "--max-chars", str(max_chars)], a.timeout, a.dry_run, what="srt split")
    info = {}
    if not a.dry_run:
        r = subprocess.run([sys.executable, str(HERE / "srt.py"), "info", cues_srt, "--json"], capture_output=True, text=True)
        info = json.loads(r.stdout or "{}")

    if a.sidecar:
        sidecar = str(Path(a.output).with_suffix(Path(a.output).suffix + ".srt")) if not a.output.endswith(".srt") else a.output
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.input, "-c", "copy", "-movflags", "+faststart", a.output]
        run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg copy")
        if not a.dry_run:
            shutil.copyfile(cues_srt, sidecar)
        return finish({"status": "ok", "output": a.output, "sidecar": sidecar, "cues": info.get("cues"), "dry_run": a.dry_run}, a.json,
                      summary=f"{'would write' if a.dry_run else 'wrote'} {a.output} + sidecar {sidecar} ({info.get('cues', '?')} cues)")

    # 2. ASS at the video's resolution, margins from the safe zones
    zones = safe_zones(a.safe)
    margin_bottom = round(H * ((zones.get("bottom_pct", 0) / 100) + 0.02)) if zones else round(H * 0.06)
    margin_side = round(W * (max(zones.get("left_pct", 0), zones.get("right_pct", 0)) / 100 + 0.03)) if zones else round(W * 0.05)
    if a.style == "top":
        margin_bottom = round(H * ((zones.get("top_pct", 0) / 100) + 0.02)) if zones else round(H * 0.06)
    ass_path = str(work / f"{stem}.ass")
    cmd = [sys.executable, str(HERE / "srt.py"), "to-ass", cues_srt, "-o", ass_path, "--width", str(W), "--height", str(H),
           "--style", a.style, "--accent", a.accent, "--margin-bottom", str(margin_bottom), "--margin-side", str(margin_side)]
    if a.font:
        cmd += ["--font", a.font]
    if a.size:
        cmd += ["--size", str(a.size)]
    if a.words:
        cmd += ["--words", a.words]
    if a.rtl:
        cmd.append("--rtl")
    run_or_fail(cmd, a.timeout, a.dry_run, what="srt to-ass")

    # 3. burn
    vf = f"ass={filter_path(ass_path)}"
    enc = ["-c:v", "libx264", "-preset", "veryfast" if a.fast else "medium", "-crf", "23" if a.fast else "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    audio = ["-c:a", "copy"] if src["has_audio"] else ["-an"]
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.input, "-vf", vf] + enc + audio + [a.output]
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg burn")

    # 4. check frame at the first cue
    check_png = str(Path(a.output).with_suffix("")) + ".caption-check.png"
    first = (info.get("first_s") or 0) + 0.3
    pre = (drawbox_zones(zones) + ",") if zones else ""
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", f"{first:.3f}", "-i", a.output, "-vf", f"{pre}scale=min(1280\\,iw):-2", "-frames:v", "1", check_png]
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg check frame")

    out = None if a.dry_run else ffprobe(a.output, a.timeout)
    result = {"status": "ok", "output": a.output, "check_frame": check_png, "ass": ass_path, "cues": info.get("cues"),
              "longest_line_chars": info.get("longest_line_chars"), "style": a.style, "safe": a.safe, "margin_bottom": margin_bottom,
              "font": a.font or "DejaVu Sans", "output_probe": out, "dry_run": a.dry_run}
    summary = (f"{'would write' if a.dry_run else 'wrote'} {a.output}: {info.get('cues', '?')} cues burned ({a.style}, bottom margin {margin_bottom}px"
               + (f", {a.safe} zones" if a.safe else "") + f") — view {check_png}")
    return finish(result, a.json, summary=summary)


if __name__ == "__main__":
    main()
