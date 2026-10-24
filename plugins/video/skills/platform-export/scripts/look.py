#!/usr/bin/env python3
"""look: a contact sheet (or one frame) of a video so the agent can see what it made.

Usage:  look.py FILE -o SHEET.png [--tiles 3x2] [--at SECONDS] [--safe instagram-reels] [--width 1600]
                 [--dry-run] [--json] [--timeout S] [--overwrite]

--tiles CxR samples C×R frames evenly across the clip; --at T renders the single frame at T seconds.
--safe <destination> shades the zones that platform's UI covers (red), so burned text inside them is
visible as a problem. Writes only the PNG. The agent then views the PNG — a probe cannot see a
caption over a face.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, check_output_path, ffprobe, finish, main_guard, require, run_or_fail  # noqa: E402

DESTINATIONS = Path(__file__).resolve().parent.parent / "assets" / "destinations.json"


def safe_filter(destination: str) -> str:
    data = json.loads(DESTINATIONS.read_text(encoding="utf-8"))
    spec = data.get(destination)
    if not spec:
        raise Failure("input", f"unknown destination '{destination}'")
    z = spec.get("safe_zones") or {}
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
    ap = base_parser("Contact sheet or single frame of a video, optionally with platform safe zones shaded.")
    ap.add_argument("file")
    ap.add_argument("-o", "--output", required=True, help="PNG path")
    ap.add_argument("--tiles", default="3x2", help="columns x rows (default 3x2); use 4x3 for long clips")
    ap.add_argument("--at", type=float, help="render the single frame at this time instead of a sheet")
    ap.add_argument("--safe", help="destination id whose UI zones to shade")
    ap.add_argument("--width", type=int, default=1600, help="sheet width in pixels (default 1600)")
    a = ap.parse_args()
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    p = ffprobe(a.file, a.timeout)
    if not p["has_video"]:
        raise Failure("input", f"{a.file} has no video stream — Look: not needed for audio-only")
    pre = (safe_filter(a.safe) + ",") if a.safe else ""

    if a.at is not None:
        t = max(0.0, min(a.at, max(p["duration"] - 0.05, 0.0)))
        vf = f"{pre}scale={a.width}:-2"
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", f"{t:.3f}", "-i", a.file, "-vf", vf, "-frames:v", "1", a.output]
        timestamps = [round(t, 3)]
        layout = "single frame"
    else:
        try:
            cols, rows = (int(x) for x in a.tiles.lower().split("x"))
        except ValueError:
            raise Failure("input", f"--tiles must look like 3x2, got {a.tiles!r}")
        n = cols * rows
        interval = max(p["duration"] / n, 0.04)
        start = interval / 2
        tile_w = max(160, a.width // cols)
        vf = f"{pre}fps=1/{interval:.6f},scale={tile_w}:-2,tile={cols}x{rows}:padding=4:margin=4:color=0x202020"
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", f"{start:.3f}", "-i", a.file, "-vf", vf, "-frames:v", "1", a.output]
        timestamps = [round(start + i * interval, 3) for i in range(n)]
        layout = f"{cols}x{rows}"
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg look")
    result = {"status": "ok", "output": a.output, "layout": layout, "timestamps": timestamps,
              "safe": a.safe, "commands": [cmd], "dry_run": a.dry_run,
              "source": {k: p[k] for k in ("path", "duration", "width", "height")}}
    summary = (f"{'would write' if a.dry_run else 'wrote'} {a.output} ({layout}, frames at "
               + ", ".join(f"{t:g}s" for t in timestamps) + (f", safe zones for {a.safe}" if a.safe else "") + ") — now view it")
    return finish(result, a.json, summary=summary)


if __name__ == "__main__":
    main()
