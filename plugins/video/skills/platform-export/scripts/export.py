#!/usr/bin/env python3
"""export: encode a video for a destination — frame, fit (blur-pad or crop), fps, HDR→SDR, loudness, codec.

Usage:  export.py INPUT -o OUTPUT --destination instagram-reels
                  [--fit auto|pad|crop|none] [--crop-x 0..1] [--crop-y 0..1]
                  [--over-length fail|trim|allow] [--no-loudness] [--codec h264|hevc] [--quality CRF]
                  [--fast] [--hw] [--dry-run] [--json] [--timeout S] [--overwrite]

Destinations and their specs come from ../assets/destinations.json (see references/destinations.md).
Writes only OUTPUT (refused if it exists, unless --overwrite). --dry-run prints the plan and runs nothing.
Exit 0 ok, 1 failed (ffmpeg error, over-length with --over-length fail), 124 timeout, 127 ffmpeg missing.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, check_output_path, ffprobe, finish, main_guard, require, run, run_or_fail  # noqa: E402

DESTINATIONS = Path(__file__).resolve().parent.parent / "assets" / "destinations.json"
HDR_TO_SDR = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
              "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def load_destination(name: str) -> dict:
    data = json.loads(DESTINATIONS.read_text(encoding="utf-8"))
    specs = {k: v for k, v in data.items() if not k.startswith("$")}
    if name not in specs:
        raise Failure("input", f"unknown destination '{name}'", "one of: " + ", ".join(sorted(specs)))
    return specs[name]


def display_size(p: dict) -> tuple[int, int]:
    w, h = int(p["width"]), int(p["height"])
    return (h, w) if abs(int(p.get("rotation") or 0)) in (90, 270) else (w, h)


def decide_fit(fit: str, src: tuple[int, int], dst: tuple[int, int]) -> str:
    sar, tar = src[0] / src[1], dst[0] / dst[1]
    if abs(sar - tar) < 0.01:
        return "none"
    if fit != "auto":
        return fit
    ratio = max(sar / tar, tar / sar)
    return "crop" if ratio <= 1.15 else "pad"


def video_filter(fit: str, W: int, H: int, fps, hdr: bool, cx: float, cy: float) -> str:
    pre = (HDR_TO_SDR + ",") if hdr else ""
    post = (f",fps={fps}" if fps else "") + ",format=yuv420p"
    if fit == "pad":
        return (f"[0:v]{pre}split[bg][fg];"
                f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2[bgb];"
                f"[fg]scale={W}:{H}:force_original_aspect_ratio=decrease:force_divisible_by=2[fgs];"
                f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2{post}[v]")
    if fit == "crop":
        return (f"[0:v]{pre}scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H}:x=(iw-{W})*{cx}:y=(ih-{H})*{cy}{post}[v]")
    return f"[0:v]{pre}scale={W}:{H}{post}[v]"


def measure_loudness(inp: str, I: float, TP: float, timeout: float) -> dict:
    # -vn: only the audio is measured, so a long clip is not decoded twice for nothing.
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", inp, "-vn", "-af",
             f"loudnorm=I={I}:TP={TP}:LRA=11:print_format=json", "-f", "null", "-"], timeout)
    # ffmpeg prints its own summary lines after the JSON block, so take the last {...} anywhere.
    blocks = re.findall(r"\{[^{}]*\}", r["stderr"], re.S)
    if r["code"] != 0 or not blocks:
        raise Failure("tool_error", "loudness measurement failed: " + (r["stderr"].strip().splitlines() or ["?"])[-1])
    return json.loads(blocks[-1])


def encoder_args(codec: str, quality: int | None, fast: bool, hw: bool) -> list[str]:
    crf = quality if quality is not None else (23 if fast else 18)
    if hw:
        enc = "hevc_nvenc" if codec == "hevc" else "h264_nvenc"
        args = ["-c:v", enc, "-preset", "p4" if fast else "p6", "-rc", "vbr", "-cq", str(crf), "-b:v", "0"]
    elif codec == "hevc":
        args = ["-c:v", "libx265", "-preset", "veryfast" if fast else "medium", "-crf", str(crf), "-tag:v", "hvc1"]
    else:
        args = ["-c:v", "libx264", "-preset", "veryfast" if fast else "medium", "-crf", str(crf), "-profile:v", "high"]
    return args + ["-pix_fmt", "yuv420p", "-movflags", "+faststart"]


@main_guard
def main() -> int:
    ap = base_parser("Encode a video for a destination: frame, fit, fps, HDR→SDR, loudness, codec.")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--destination", required=True, help="id from assets/destinations.json")
    ap.add_argument("--fit", default="auto", choices=["auto", "pad", "crop", "none"],
                    help="how to change aspect: pad = blurred background (default when the change is large), crop (default when small)")
    ap.add_argument("--crop-x", type=float, default=0.5, help="crop anchor 0=left … 1=right (default centre)")
    ap.add_argument("--crop-y", type=float, default=0.5, help="crop anchor 0=top … 1=bottom (default centre)")
    ap.add_argument("--over-length", default="fail", choices=["fail", "trim", "allow"],
                    help="input longer than the destination cap: fail (default), trim at the cap, or allow")
    ap.add_argument("--no-loudness", action="store_true", help="skip loudness normalisation")
    ap.add_argument("--codec", default="h264", choices=["h264", "hevc"])
    ap.add_argument("--quality", type=int, help="CRF (default 18; 23 with --fast)")
    ap.add_argument("--fast", action="store_true", help="preview quality, faster")
    ap.add_argument("--hw", action="store_true", help="NVENC hardware encoder (needs an NVIDIA GPU build)")
    a = ap.parse_args()

    dest = load_destination(a.destination)
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    src = ffprobe(a.input, a.timeout)
    if not src["has_video"]:
        raise Failure("input", f"{a.input} has no video stream")
    notes: list[str] = []

    W, H = int(dest["width"]), int(dest["height"])
    sw, sh = display_size(src)
    fit = decide_fit(a.fit, (sw, sh), (W, H))
    if fit == "crop" and a.fit == "auto":
        notes.append(f"aspect change is small ({sw}x{sh} → {W}x{H}); cropped at centre — pass --fit pad to keep everything")
    if fit == "pad":
        notes.append(f"{sw}x{sh} → {W}x{H} by blur-pad: the whole frame is kept over a blurred copy")
    if src.get("hdr"):
        notes.append("source is HDR/BT.2020: tone-mapped to SDR BT.709 (hable)")
    if src.get("vfr_suspected"):
        notes.append("source looks variable-frame-rate: output is constant frame rate")

    duration_args: list[str] = []
    cap = dest.get("max_duration_s")
    if cap and src["duration"] > cap + 0.05:
        if a.over_length == "fail":
            raise Failure("input", f"{src['duration']} s exceeds the {a.destination} cap of {cap} s",
                          "cut or select first; --over-length trim cuts at the cap (loses the end); --over-length allow exports anyway")
        if a.over_length == "trim":
            duration_args = ["-t", str(cap)]
            notes.append(f"trimmed at the {cap} s cap (source {src['duration']} s)")
        else:
            notes.append(f"exceeds the {cap} s cap ({src['duration']} s); exported anyway")

    fps = dest.get("fps")
    vf = video_filter(fit, W, H, fps, bool(src.get("hdr")), a.crop_x, a.crop_y)

    audio_args: list[str]
    loudness: dict = {"target_lufs": dest.get("lufs"), "target_tp": dest.get("true_peak_dbtp"), "applied": False}
    if not dest.get("audio", True):
        audio_args = ["-an"]
        notes.append("destination has no audio track")
    elif not src["has_audio"]:
        audio_args = ["-an"]
        notes.append("source has no audio; exported silent")
    else:
        af = "aresample=48000"
        if not a.no_loudness and dest.get("lufs") is not None:
            if a.dry_run:
                af = f"loudnorm=I={dest['lufs']}:TP={dest['true_peak_dbtp']}:LRA=11:linear=true,aresample=48000"
                loudness["applied"] = "planned (two-pass; measurement skipped under --dry-run)"
            else:
                m = measure_loudness(a.input, dest["lufs"], dest["true_peak_dbtp"], a.timeout)
                af = (f"loudnorm=I={dest['lufs']}:TP={dest['true_peak_dbtp']}:LRA=11:"
                      f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
                      f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
                loudness.update(applied=True, measured_input_lufs=float(m["input_i"]), measured_input_tp=float(m["input_tp"]))
        audio_args = ["-af", af, "-c:a", "aac", "-b:a", "192k", "-ac", "2"]

    cmd = (["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.input, "-filter_complex", vf, "-map", "[v]"]
           + (["-map", "0:a:0"] if audio_args != ["-an"] else [])
           + audio_args + encoder_args(a.codec, a.quality, a.fast, a.hw)
           + (["-fps_mode", "cfr"] if not fps else []) + duration_args + [a.output])
    r = run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg export")

    out = None if a.dry_run else ffprobe(a.output, a.timeout)
    if out and dest.get("max_size_mb") and out["size_bytes"] > dest["max_size_mb"] * 1_048_576:
        notes.append(f"output is {out['size_bytes'] / 1_048_576:.1f} MB, over the {dest['max_size_mb']} MB cap — re-run with --quality {(a.quality or 18) + 5}")
    result = {
        "status": "ok", "output": a.output, "destination": a.destination, "fit": fit, "filter": vf,
        "loudness": loudness, "duration_policy": a.over_length, "commands": [cmd], "notes": notes,
        "input_probe": src, "output_probe": out, "dry_run": a.dry_run,
    }
    if a.dry_run:
        summary = f"would write {a.output} for {a.destination}: {W}x{H}, fit {fit}" + ("; " + "; ".join(notes) if notes else "")
    else:
        summary = (f"{a.output}: {out['duration']} s, {out['width']}x{out['height']}, {out['fps']} fps, {out['vcodec']}"
                   f"/{out.get('acodec') or 'no audio'} (fit {fit})" + ("; " + "; ".join(notes) if notes else ""))
    return finish(result, a.json, summary=summary)


if __name__ == "__main__":
    main()
