#!/usr/bin/env python3
"""broll: lay b-roll over a speaker at planned times — full-frame with dissolves, or picture-in-picture.

Usage:  broll.py EDIT.mp4 --plan broll.json -o covered.mp4 [--pip] [--pip-corner top-right|top-left|bottom-right|bottom-left]
                [--pip-width 0.38] [--dissolve 0.3] [--fast] [--dry-run] [--json] [--timeout S] [--overwrite]

broll.json: {"inserts":[{"start":71.2,"end":75.0,"src":"broll/warehouse.mp4","in_s":3.0,"why":"…"}]}  (images allowed as src)
The speaker's audio is kept untouched; b-roll audio is never used.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, check_output_path, ffprobe, finish, main_guard, require, run_or_fail  # noqa: E402

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@main_guard
def main() -> int:
    ap = base_parser("Overlay b-roll on a speaker edit.")
    ap.add_argument("edit"); ap.add_argument("--plan", required=True); ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--pip", action="store_true"); ap.add_argument("--pip-corner", default="top-right", choices=["top-right", "top-left", "bottom-right", "bottom-left"])
    ap.add_argument("--pip-width", type=float, default=0.38); ap.add_argument("--dissolve", type=float, default=0.3); ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    p = ffprobe(a.edit, a.timeout)
    W, H, fps = int(p["width"]), int(p["height"]), p["fps"] or 30
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    inserts = sorted(plan.get("inserts") or [], key=lambda i: i["start"])
    if not inserts:
        raise Failure("input", "plan has no inserts")
    inputs = ["-i", a.edit]
    fc = ["[0:v]format=yuv420p[base0]"]
    cur = "base0"
    notes = []
    for k, ins in enumerate(inserts):
        src, s, e = ins["src"], float(ins["start"]), float(ins["end"])
        if not os.path.isfile(src):
            raise Failure("input", f"insert {k + 1}: {src} does not exist")
        if e <= s or e > p["duration"] + 0.05:
            raise Failure("input", f"insert {k + 1}: window {s}-{e} is invalid for a {p['duration']} s edit")
        if k and s < float(inserts[k - 1]["end"]):
            raise Failure("input", f"insert {k + 1} overlaps insert {k}")
        dur = e - s
        is_img = Path(src).suffix.lower() in IMAGE_EXT
        in_s = float(ins.get("in_s", 0) or 0)
        if is_img:
            inputs += ["-loop", "1", "-framerate", f"{fps:g}", "-t", f"{dur + 0.2:.3f}", "-i", src]
        else:
            bp = ffprobe(src, a.timeout)
            if in_s + dur > bp["duration"] + 0.05:
                in_s = max(0.0, bp["duration"] - dur)
                notes.append(f"insert {k + 1}: {src} too short from {ins.get('in_s', 0)} s; starting at {in_s:.2f} s instead")
            inputs += ["-ss", f"{in_s:.3f}", "-t", f"{dur + 0.5:.3f}", "-i", src]
        idx = k + 1
        if a.pip:
            pw = int(W * a.pip_width) // 2 * 2
            prep = f"[{idx}:v]fps={fps:g},scale={pw}:-2,trim=duration={dur:.3f},setpts=PTS-STARTPTS+{s:.3f}/TB,format=yuv420p[b{k}]"
            m = int(W * 0.04)
            x = f"W-w-{m}" if "right" in a.pip_corner else f"{m}"
            y = f"{m}" if "top" in a.pip_corner else f"H-h-{m}"
            fc.append(prep)
            fc.append(f"[{cur}][b{k}]overlay=x={x}:y={y}:enable='between(t,{s:.3f},{e:.3f})'[o{k}]")
        else:
            d = min(a.dissolve, dur / 3)
            prep = (f"[{idx}:v]fps={fps:g},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},trim=duration={dur:.3f},setpts=PTS-STARTPTS,"
                    f"format=yuva420p,fade=t=in:st=0:d={d:.3f}:alpha=1,fade=t=out:st={dur - d:.3f}:d={d:.3f}:alpha=1,setpts=PTS+{s:.3f}/TB[b{k}]")
            fc.append(prep)
            fc.append(f"[{cur}][b{k}]overlay=x=0:y=0:enable='between(t,{s:.3f},{e:.3f})':eof_action=pass[o{k}]")
        cur = f"o{k}"
    fc.append(f"[{cur}]format=yuv420p[v]")
    cmd = (["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "0:a?", "-c:a", "copy",
            "-c:v", "libx264", "-preset", "veryfast" if a.fast else "medium", "-crf", "23" if a.fast else "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.output])
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg broll")
    out = None if a.dry_run else ffprobe(a.output, a.timeout)
    result = {"status": "ok", "output": a.output, "inserts": len(inserts), "mode": "pip" if a.pip else "full", "notes": notes, "output_probe": out, "commands": [cmd], "dry_run": a.dry_run}
    return finish(result, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(inserts)} b-roll inserts ({'pip' if a.pip else 'full-frame with dissolves'})" + ("; " + "; ".join(notes) if notes else ""))


if __name__ == "__main__":
    main()
