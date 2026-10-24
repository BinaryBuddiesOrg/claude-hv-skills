#!/usr/bin/env python3
"""probe: measured facts about media files — duration, frame, fps, codecs, audio, rotation, VFR, HDR.

Usage:  probe.py FILE [FILE ...] [--json] [--raw]

Measurement only; --dry-run is accepted and nothing is written. Exit 0 when every file
probed, 1 when any did not. Plan from these numbers, never from the file name.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, ffprobe, finish, main_guard  # noqa: E402


def line(p: dict) -> str:
    if not p["has_video"]:
        return f"{p['path']}: audio only, {p['duration']} s, {p.get('acodec')} {p.get('channels')}ch {p.get('sample_rate')} Hz"
    flags = []
    if p.get("rotation"):
        flags.append(f"rotation {p['rotation']}°")
    if p.get("vfr_suspected"):
        flags.append("VFR suspected")
    if p.get("hdr"):
        flags.append("HDR/BT.2020")
    audio = f"{p.get('acodec')} {p.get('channels')}ch" if p["has_audio"] else "no audio"
    return (f"{p['path']}: {p['duration']} s, {p['width']}x{p['height']}, {p['fps']} fps, "
            f"{p['vcodec']}/{audio}" + (f" [{', '.join(flags)}]" if flags else ""))


@main_guard
def main() -> int:
    ap = base_parser("Measured facts about media files.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--raw", action="store_true", help="include the raw ffprobe document under each file")
    a = ap.parse_args()
    files, failed, lines = [], [], []
    for f in a.files:
        try:
            p = ffprobe(f, a.timeout)
            if not a.raw:
                p.pop("raw", None)
            files.append(p)
            lines.append(line(p))
        except Failure as e:
            failed.append({"path": f, "error": e.as_dict()})
            lines.append(f"{f}: {e.kind} — {e.message}")
    result = {"status": "ok" if not failed else "failed", "files": files, "failed": failed}
    if failed:
        result["error"] = {"kind": "probe", "message": f"{len(failed)} of {len(a.files)} files could not be probed"}
    return finish(result, a.json, summary="\n".join(lines))


if __name__ == "__main__":
    main()
