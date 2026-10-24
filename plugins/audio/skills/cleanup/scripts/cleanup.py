#!/usr/bin/env python3
"""cleanup: make a voice recording sit like narration — denoise, de-ess, compress, trim, level.

Usage:  cleanup.py INPUT -o OUT.wav [--denoise off|light|medium|strong|auto] [--highpass 80] [--no-deess]
                   [--deess-strength 0.5] [--no-compress] [--compress-ratio 3] [--no-trim] [--target-lufs -16]
                   [--ab AB.wav] [--dry-run] [--json] [--timeout S] [--overwrite]

Measures before and after (loudness, true peak, noise floor); --dry-run measures and prints the chain only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, check_output_path, ffprobe, finish, main_guard, require, run, run_or_fail  # noqa: E402

NR_DB = {"light": 12, "medium": 20, "strong": 30}


def measure(path: str, timeout: float) -> dict:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af", "ebur128=peak=true,astats=measure_overall=RMS_level+Peak_level+Noise_floor:measure_perchannel=none", "-f", "null", "-"], timeout)
    text = r["stderr"]
    tail = text[text.rfind("Summary:"):] if "Summary:" in text else text
    out = {}
    for key, pat in (("integrated_lufs", r"\bI:\s*(-?[\d.]+)\s*LUFS"), ("lra_lu", r"LRA:\s*(-?[\d.]+)\s*LU"), ("true_peak_dbtp", r"Peak:\s*(-?[\d.]+)\s*dBFS")):
        m = re.search(pat, tail)
        if m:
            out[key] = float(m.group(1))
    for key, pat in (("noise_floor_dbfs", r"Noise floor dB:\s*(-?[\d.]+)"), ("rms_dbfs", r"RMS level dB:\s*(-?[\d.]+)"), ("peak_dbfs", r"Peak level dB:\s*(-?[\d.]+)")):
        m = re.search(pat, text)
        if m:
            out[key] = float(m.group(1))
    return out


@main_guard
def main() -> int:
    ap = base_parser("Clean a voice recording: denoise, de-ess, compress, trim, level.")
    ap.add_argument("input"); ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--denoise", default="auto", choices=["off", "light", "medium", "strong", "auto"])
    ap.add_argument("--highpass", type=float, default=80)
    ap.add_argument("--no-deess", action="store_true"); ap.add_argument("--deess-strength", type=float, default=0.5)
    ap.add_argument("--no-compress", action="store_true"); ap.add_argument("--compress-ratio", type=float, default=3.0)
    ap.add_argument("--no-trim", action="store_true")
    ap.add_argument("--target-lufs", type=float, default=-16.0)
    ap.add_argument("--ab", help="also write a before/after A-B file of the loudest 10 s")
    a = ap.parse_args()
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    p = ffprobe(a.input, a.timeout)
    if not p["has_audio"]:
        raise Failure("input", f"{a.input} has no audio stream")
    before = measure(a.input, a.timeout)
    floor = before.get("noise_floor_dbfs")
    notes, warnings = [], []
    denoise = a.denoise
    if denoise == "auto":
        denoise = "off" if floor is None else ("strong" if floor > -40 else "medium" if floor > -50 else "light" if floor > -60 else "off")
        notes.append(f"noise floor {floor} dBFS -> denoise {denoise}")
    if before.get("peak_dbfs", -99) > -0.3:
        warnings.append("peaks at 0 dBFS: the recording is clipped; distortion cannot be removed")
    if floor is not None and floor > -35:
        warnings.append("noise floor above -35 dBFS: speech and noise overlap; expect artefacts, consider re-recording")
    chain = [f"highpass=f={a.highpass:g}"]
    if denoise != "off":
        chain.append(f"afftdn=nr={NR_DB[denoise]}:nf=-30:tn=1")
    if not a.no_deess:
        chain.append(f"deesser=i={a.deess_strength:.2f}:m=0.5:f=0.5")
    if not a.no_compress:
        chain.append(f"acompressor=threshold=-20dB:ratio={a.compress_ratio:g}:attack=5:release=60:makeup=2")
    if not a.no_trim:
        chain.append("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25:stop_periods=1:stop_threshold=-45dB:stop_silence=0.6:detection=peak")
    chain.append(f"loudnorm=I={a.target_lufs:g}:TP=-1.5:LRA=7")
    chain.append("aresample=48000")
    af = ",".join(chain)
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.input, "-vn", "-ac", "1", "-af", af, "-c:a", "pcm_s16le", a.output]
    if (p.get("channels") or 1) > 1:
        notes.append("folded to mono (narration is mono)")
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg cleanup")
    after = {} if a.dry_run else measure(a.output, a.timeout)
    out = None if a.dry_run else ffprobe(a.output, a.timeout)
    if a.ab and not a.dry_run:
        # loudest 10 s window: approximate with the middle of the file
        mid = max(0.0, p["duration"] / 2 - 5)
        fc = f"[0:a]atrim=start={mid:.2f}:duration=10,asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=mono[b];[1:a]atrim=start={mid:.2f}:duration=10,asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=mono[c];[b][c]concat=n=2:v=0:a=1[a]"
        run_or_fail(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.input, "-i", a.output, "-filter_complex", fc, "-map", "[a]", "-c:a", "pcm_s16le", a.ab], a.timeout, False, what="ffmpeg ab")
    ok = a.dry_run or (after.get("integrated_lufs") is not None and abs(after["integrated_lufs"] - a.target_lufs) <= 1.0)
    result = {"status": "ok" if ok else "failed", "output": a.output, "chain": af, "denoise": denoise, "before": before, "after": after,
              "duration_s": out and out["duration"], "ab": a.ab, "notes": notes, "warnings": warnings, "commands": [cmd], "dry_run": a.dry_run}
    if not ok:
        result["error"] = {"kind": "verify", "message": f"loudness after is {after.get('integrated_lufs')} LUFS, target {a.target_lufs}"}
    if a.dry_run:
        summary = f"would write {a.output}: before {before.get('integrated_lufs')} LUFS, floor {floor} dBFS; chain: {af}" + ("\n" + "\n".join(warnings) if warnings else "")
    else:
        summary = (f"{a.output}: {out['duration']} s, {after.get('integrated_lufs')} LUFS (was {before.get('integrated_lufs')}), peak {after.get('true_peak_dbtp')} dBTP, "
                   f"floor {after.get('noise_floor_dbfs')} dBFS (was {floor}); {denoise} denoise" + ("; " + "; ".join(notes) if notes else "") + ("\n" + "\n".join(warnings) if warnings else ""))
    return finish(result, a.json, summary=summary)


if __name__ == "__main__":
    main()
