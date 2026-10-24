#!/usr/bin/env python3
"""music: fit a bed to a length, duck it under a voice, make or place sound effects.

Usage:
  music.py probe MUSIC [--json]
  music.py fit MUSIC -o bed.wav --duration S [--start-at S|auto] [--fade-in 0.5] [--fade-out 1.5] [--level -18] [--no-loop]
  music.py duck MUSIC --voice VOICE.wav -o out.wav [--duck-db -12]
  music.py sfx --synth whoosh|pop|click|riser|ding|thud -o out.wav
  music.py sfx --beats BEATS.json --out-dir DIR [--pack DIR] [--cues cues.json]

Loops are made with a 1 s crossfade between copies, so the seam is inaudible wherever it falls.
Shared flags (--json, --dry-run, --timeout, --overwrite) go after the subcommand.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, check_output_path, common_flags, ffprobe, finish, main_guard, require, run, run_or_fail  # noqa: E402

SYNTH = {
    "whoosh": "anoisesrc=d=0.5:c=pink:a=0.8:r=48000,highpass=f=300,lowpass=f=4000,afade=t=in:d=0.15,afade=t=out:st=0.2:d=0.3",
    "pop": "sine=f=900:d=0.08:r=48000,afade=t=out:st=0.02:d=0.06",
    "click": "anoisesrc=d=0.02:c=white:a=0.6:r=48000,highpass=f=2000",
    "riser": "anoisesrc=d=2:c=pink:a=0.8:r=48000,highpass=f=200,afade=t=in:d=1.8,afade=t=out:st=1.8:d=0.2",
    "ding": "aevalsrc='0.6*sin(2*PI*1320*t)*exp(-3*t)+0.3*sin(2*PI*2640*t)*exp(-5*t)':d=1.2:s=48000",
    "thud": "aevalsrc='sin(2*PI*(60-20*t/0.15)*t)*exp(-20*t)':d=0.15:s=48000",
}


def ebur128(path: str, timeout: float) -> dict:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-filter_complex", "ebur128=peak=true", "-f", "null", "-"], timeout)
    text = r["stderr"]
    tail = text[text.rfind("Summary:"):] if "Summary:" in text else text
    out = {}
    m = re.search(r"\bI:\s*(-?[\d.]+)\s*LUFS", tail)
    if m:
        out["integrated_lufs"] = float(m.group(1))
    m = re.search(r"Peak:\s*(-?[\d.]+)\s*dBFS", tail)
    if m:
        out["true_peak_dbtp"] = float(m.group(1))
    # momentary timeline for onset-ish detection
    timeline = [(float(t), float(mm)) for t, mm in re.findall(r"t:\s*([\d.]+)\s+TARGET:[^\n]*?M:\s*(-?[\d.]+)", text)]
    if not timeline:
        timeline = [(float(t), float(mm)) for t, mm in re.findall(r"t:\s*([\d.]+)\s+M:\s*(-?[\d.]+)", text)]
    out["momentary"] = timeline
    return out


def first_strong_onset(meas: dict) -> float:
    tl = meas.get("momentary") or []
    integ = meas.get("integrated_lufs")
    if not tl or integ is None:
        return 0.0
    for t, m in tl:
        if m >= integ + 2.0:
            return max(0.0, t - 0.1)
    return 0.0


def cmd_probe(a) -> int:
    p = ffprobe(a.music, a.timeout)
    m = ebur128(a.music, a.timeout)
    onset = first_strong_onset(m)
    result = {"status": "ok", "file": a.music, "duration_s": p["duration"], "integrated_lufs": m.get("integrated_lufs"),
              "true_peak_dbtp": m.get("true_peak_dbtp"), "first_strong_onset_s": onset, "channels": p.get("channels"), "sample_rate": p.get("sample_rate")}
    return finish(result, a.json, summary=f"{a.music}: {p['duration']} s, {m.get('integrated_lufs')} LUFS, peak {m.get('true_peak_dbtp')} dBTP, first strong onset ≈ {onset} s")


def cmd_fit(a) -> int:
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    p = ffprobe(a.music, a.timeout)
    if not p["has_audio"]:
        raise Failure("input", f"{a.music} has no audio stream")
    start = 0.0
    if a.start_at == "auto":
        start = first_strong_onset(ebur128(a.music, a.timeout)) if not a.dry_run else 0.0
    elif a.start_at:
        start = float(a.start_at)
    available = max(0.0, p["duration"] - start)
    if available < 1.0:
        raise Failure("input", f"only {available:.1f} s of music after start {start} s")
    S = float(a.duration)
    notes = []
    inputs: list[str] = []
    xf = 1.0
    if available >= S or a.no_loop:
        inputs = ["-ss", f"{start:.3f}", "-t", f"{min(S, available) + 0.5:.3f}", "-i", a.music]
        fc = "[0:a]aresample=48000,aformat=channel_layouts=stereo"
        if available < S:
            notes.append(f"bed is {available:.1f} s, shorter than {S:.1f} s and --no-loop was set: ends early")
    else:
        copies = int(math.ceil((S + xf) / max(available - xf, 0.5))) + 1
        for _ in range(copies):
            inputs += ["-ss", f"{start:.3f}", "-i", a.music]
        parts = [f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[c{i}]" for i in range(copies)]
        cur = "c0"
        for i in range(1, copies):
            parts.append(f"[{cur}][c{i}]acrossfade=d={xf}:c1=tri:c2=tri[x{i}]")
            cur = f"x{i}"
        fc = ";".join(parts) + f";[{cur}]anull"
        notes.append(f"bed {available:.1f} s looped ×{copies} with {xf:g} s crossfades")
    fc += f",atrim=duration={S:.3f},asetpts=PTS-STARTPTS"
    if a.fade_in:
        fc += f",afade=t=in:st=0:d={a.fade_in:.3f}"
    if a.fade_out:
        fc += f",afade=t=out:st={max(0.0, S - a.fade_out):.3f}:d={a.fade_out:.3f}"
    fc += f",loudnorm=I={a.level}:TP=-1.5:LRA=11[a]"
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs + ["-filter_complex", fc, "-map", "[a]", "-ar", "48000", "-c:a", "pcm_s16le", a.output]
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg fit")
    out = None if a.dry_run else ffprobe(a.output, a.timeout)
    meas = {} if a.dry_run else ebur128(a.output, a.timeout)
    result = {"status": "ok", "output": a.output, "target_s": S, "start_at_s": start, "measured_s": out and out["duration"],
              "integrated_lufs": meas.get("integrated_lufs"), "notes": notes, "commands": [cmd], "dry_run": a.dry_run}
    summary = (f"{'would write' if a.dry_run else 'wrote'} {a.output}: {S:g} s from {start:g} s" + (f", {meas.get('integrated_lufs')} LUFS" if meas else "")
               + ("; " + "; ".join(notes) if notes else ""))
    return finish(result, a.json, summary=summary)


def cmd_duck(a) -> int:
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    depth = abs(float(a.duck_db))
    ratio = max(2.0, min(20.0, depth / 1.5))
    fc = (f"[1:a]aresample=48000,aformat=channel_layouts=stereo[v];[0:a]aresample=48000,aformat=channel_layouts=stereo[m];"
          f"[m][v]sidechaincompress=threshold=0.02:ratio={ratio:.1f}:attack=15:release=300:makeup=1:level_sc=1[a]")
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.music, "-i", a.voice, "-filter_complex", fc, "-map", "[a]", "-ar", "48000", "-c:a", "pcm_s16le", a.output]
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg duck")
    return finish({"status": "ok", "output": a.output, "duck_db": -depth, "ratio": ratio, "commands": [cmd], "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: ducked ~-{depth:g} dB under {a.voice}")


def synth_one(name: str, out: str, timeout: float, dry_run: bool) -> list[str]:
    if name not in SYNTH:
        raise Failure("input", f"unknown built-in sfx '{name}'", "one of: " + ", ".join(sorted(SYNTH)))
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-f", "lavfi", "-i", SYNTH[name], "-af", "aformat=channel_layouts=mono,volume=0.5", "-ar", "48000", "-c:a", "pcm_s16le", out]
    run_or_fail(cmd, timeout, dry_run, what=f"ffmpeg synth {name}")
    return cmd


def cmd_sfx(a) -> int:
    require("ffmpeg")
    if a.synth:
        if not a.output:
            raise Failure("input", "--synth needs -o")
        check_output_path(a.output, a.overwrite)
        cmd = synth_one(a.synth, a.output, a.timeout, a.dry_run)
        return finish({"status": "ok", "output": a.output, "sfx": a.synth, "commands": [cmd], "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output} ({a.synth})")
    if not a.beats or not a.out_dir:
        raise Failure("input", "sfx needs --synth NAME -o FILE, or --beats BEATS --out-dir DIR")
    beats = json.loads(Path(a.beats).read_text(encoding="utf-8"))
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cues = []
    for b in beats.get("beats") or []:
        name = b.get("sfx")
        if not name:
            continue
        path = None
        if os.path.isfile(str(name)):
            path = str(name)
        elif a.pack:
            hits = sorted(glob.glob(os.path.join(a.pack, f"{name}*")))
            path = hits[0] if hits else None
        if path is None:
            if name in SYNTH:
                path = str(out_dir / f"{name}.wav")
                if not os.path.isfile(path):
                    synth_one(name, path, a.timeout, a.dry_run)
            else:
                raise Failure("input", f"beat {b.get('id')}: sfx '{name}' is neither a file, in the pack, nor a built-in ({', '.join(sorted(SYNTH))})")
        cues.append({"beat": b.get("id"), "start_s": float(b.get("start_s", 0)), "name": name, "src": path, "role": "sfx", "gain_db": -6})
    if a.cues and not a.dry_run:
        Path(a.cues).write_text(json.dumps({"tracks": cues}, indent=2), encoding="utf-8")
    return finish({"status": "ok", "cues": cues, "output": a.cues, "dry_run": a.dry_run}, a.json,
                  summary=f"{len(cues)} sfx cues" + (f" -> {a.cues}" if a.cues else "") + "\n" + "\n".join(f"  {c['start_s']:7.2f}s {c['name']:8} {c['src']}" for c in cues))


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Fit, duck and make sound for a video. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    pr = sub.add_parser("probe", parents=cf); pr.add_argument("music"); pr.set_defaults(fn=cmd_probe)
    f = sub.add_parser("fit", parents=cf); f.add_argument("music"); f.add_argument("-o", "--output", required=True); f.add_argument("--duration", type=float, required=True)
    f.add_argument("--start-at", help="seconds, or 'auto' for the first strong onset"); f.add_argument("--fade-in", type=float, default=0.5); f.add_argument("--fade-out", type=float, default=1.5)
    f.add_argument("--level", type=float, default=-18.0); f.add_argument("--no-loop", action="store_true"); f.set_defaults(fn=cmd_fit)
    d = sub.add_parser("duck", parents=cf); d.add_argument("music"); d.add_argument("--voice", required=True); d.add_argument("-o", "--output", required=True); d.add_argument("--duck-db", type=float, default=-12); d.set_defaults(fn=cmd_duck)
    s = sub.add_parser("sfx", parents=cf); s.add_argument("--synth", choices=sorted(SYNTH)); s.add_argument("-o", "--output"); s.add_argument("--beats"); s.add_argument("--out-dir"); s.add_argument("--pack"); s.add_argument("--cues"); s.set_defaults(fn=cmd_sfx)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
