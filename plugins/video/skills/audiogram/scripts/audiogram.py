#!/usr/bin/env python3
"""audiogram: audio → video with cover/colour background, a moving waveform or spectrum, title and speaker.

Usage:  audiogram.py AUDIO -o out.mp4 --width 1080 --height 1920 [--cover art.jpg] [--bg '#101418'] [--style wave|bars|spectrum]
                     [--accent '#FFD400'] [--title "…"] [--speaker "…"] [--font NAME] [--gain 1.0] [--safe instagram-reels]
                     [--fast] [--dry-run] [--json] [--timeout S] [--overwrite]

Captions are added afterwards by video:captions (the layout leaves the bottom band free). Output is 30 fps H.264 + AAC.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, check_output_path, ffprobe, finish, main_guard, require, run, run_or_fail  # noqa: E402

DESTINATIONS = Path(__file__).resolve().parent.parent.parent / "platform-export" / "assets" / "destinations.json"


def dt_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\\\\\'").replace("%", "\\%")


def has_filter(name: str, timeout: float) -> bool:
    r = run(["ffmpeg", "-hide_banner", "-filters"], timeout)
    return any(line.split()[1] == name for line in r["stdout"].splitlines() if len(line.split()) > 1 and line.strip().startswith(("T", ".", "C", "S")))


@main_guard
def main() -> int:
    ap = base_parser("Audio → video with a moving waveform, cover and titles.")
    ap.add_argument("audio"); ap.add_argument("-o", "--output", required=True); ap.add_argument("--width", type=int, required=True); ap.add_argument("--height", type=int, required=True)
    ap.add_argument("--cover"); ap.add_argument("--bg", default="#101418"); ap.add_argument("--style", default="wave", choices=["wave", "bars", "spectrum"])
    ap.add_argument("--accent", default="#FFD400"); ap.add_argument("--title"); ap.add_argument("--speaker"); ap.add_argument("--font"); ap.add_argument("--gain", type=float, default=1.0)
    ap.add_argument("--safe"); ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    p = ffprobe(a.audio, a.timeout)
    if not p["has_audio"]:
        raise Failure("input", f"{a.audio} has no audio stream")
    W, H = a.width, a.height
    dur = p["duration"]
    bottom = 0.0
    if a.safe and DESTINATIONS.is_file():
        spec = json.loads(DESTINATIONS.read_text(encoding="utf-8")).get(a.safe) or {}
        bottom = float((spec.get("safe_zones") or {}).get("bottom_pct", 0)) / 100
    caption_band = H * (bottom + 0.14)
    accent = a.accent.lstrip("#")
    inputs = ["-i", a.audio]
    fc = []
    # background
    cover = a.cover
    if cover and not os.path.isfile(cover):
        raise Failure("input", f"{cover} does not exist")
    if cover:
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{dur:.3f}", "-i", cover]
        fc.append(f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:4,colorlevels=rimax=0.6:gimax=0.6:bimax=0.6,format=yuv420p[bg]")
        card = int(min(W * 0.72, (H - caption_band) * 0.42)) // 2 * 2
        fc.append(f"[1:v]scale={card}:{card}:force_original_aspect_ratio=increase,crop={card}:{card},format=yuv420p[cardv]")
        card_y = int(H * 0.16)
        fc.append(f"[bg][cardv]overlay=(W-w)/2:{card_y}[b1]")
        cur = "b1"
        wave_top = card_y + card + int(H * 0.04)
    else:
        inputs += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"color=c=0x{a.bg.lstrip('#')}:s={W}x{H}:r=30"]
        fc.append("[1:v]format=yuv420p[b1]")
        cur = "b1"
        wave_top = int(H * 0.36)
    wave_h = int(max(80, min(H * 0.18, (H - caption_band) - wave_top - H * 0.02))) // 2 * 2
    wave_w = int(W * 0.86) // 2 * 2
    style = a.style
    if style == "spectrum" and not has_filter("showcqt", a.timeout):
        style = "wave"
    if style == "wave":
        viz = f"[0:a]aformat=channel_layouts=mono,volume={a.gain:.2f},showwaves=s={wave_w}x{wave_h}:mode=cline:colors=0x{accent}:rate=30:scale=sqrt,format=rgba[viz]"
    elif style == "bars":
        viz = f"[0:a]aformat=channel_layouts=mono,volume={a.gain:.2f},showfreqs=s={wave_w}x{wave_h}:mode=bar:colors=0x{accent}:fscale=log:ascale=sqrt:rate=30,format=rgba[viz]"
    else:
        viz = f"[0:a]aformat=channel_layouts=mono,volume={a.gain:.2f},showcqt=s={wave_w}x{wave_h}:rate=30:axis=0:bar_g=2,format=rgba[viz]"
    fc.append(viz)
    fc.append(f"[{cur}][viz]overlay=(W-w)/2:{wave_top}:shortest=1[b2]")
    cur = "b2"
    draw = []
    m = min(W, H)
    if a.title:
        draw.append(f"drawtext=text='{dt_escape(a.title)}':fontsize={round(m * 0.055)}:fontcolor=white:borderw=2:bordercolor=black@0.6:x=(w-text_w)/2:y={int(H * 0.06)}" + (f":font='{a.font}'" if a.font else ""))
    if a.speaker:
        draw.append(f"drawtext=text='{dt_escape(a.speaker)}':fontsize={round(m * 0.034)}:fontcolor=0x{accent}:borderw=2:bordercolor=black@0.6:x=(w-text_w)/2:y={int(H * 0.06) + round(m * 0.075)}" + (f":font='{a.font}'" if a.font else ""))
    if draw:
        fc.append(f"[{cur}]" + ",".join(draw) + "[b3]")
        cur = "b3"
    fc.append(f"[{cur}]format=yuv420p[v]")
    cmd = (["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "0:a", "-c:v", "libx264",
            "-preset", "veryfast" if a.fast else "medium", "-crf", "23" if a.fast else "18", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-t", f"{dur:.3f}", "-movflags", "+faststart", a.output])
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg audiogram")
    out = None if a.dry_run else ffprobe(a.output, a.timeout)
    result = {"status": "ok", "output": a.output, "style": style, "cover": cover, "wave_band": [wave_top, wave_top + wave_h], "caption_band_from": round(H - caption_band),
              "output_probe": out, "commands": [cmd], "dry_run": a.dry_run}
    return finish(result, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {dur} s, {W}x{H}, {style}" + (" on cover" if cover else " on colour") + " — next: video:captions with --safe, then export")


if __name__ == "__main__":
    main()
