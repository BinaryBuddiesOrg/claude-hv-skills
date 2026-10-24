#!/usr/bin/env python3
"""cut: exact segment cuts joined with short crossfades, original audio kept.

Usage:  cut.py INPUT --segments "12.4-18.0,41.2-47.5,88.0-95.0" -o edit.mp4 [--xfade 0.25] [--pad 0.15]
               [--width W --height H --fit cover|pad] [--remap-srt in.srt --srt-out out.srt] [--fast]
               [--dry-run] [--json] [--timeout S] [--overwrite]

Segments are "start-end" in seconds (or m:ss). --pad moves each in-point earlier (never before 0) so the first
syllable survives. --xfade crossfades video and audio at each join (0 = hard cut). --remap-srt shifts an SRT of the
source into the edit's timeline (cues outside the kept segments are dropped).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, check_output_path, ffprobe, finish, main_guard, require, run_or_fail  # noqa: E402


def parse_t(s: str) -> float:
    s = s.strip()
    if ":" in s:
        parts = [float(x) for x in s.split(":")]
        return sum(v * 60 ** i for i, v in enumerate(reversed(parts)))
    return float(s)


def parse_segments(spec: str, duration: float, pad: float) -> list[tuple[float, float]]:
    segs = []
    for part in [x for x in re.split(r"[,\s]+", spec.strip()) if x]:
        if "-" not in part:
            raise Failure("input", f"segment {part!r} must be start-end")
        a, b = part.rsplit("-", 1)
        s, e = max(0.0, parse_t(a) - pad), parse_t(b)
        if e <= s:
            raise Failure("input", f"segment {part!r}: end must be after start")
        if e > duration + 0.05:
            raise Failure("input", f"segment {part!r}: end {e} s exceeds the file ({duration} s)")
        segs.append((round(s, 3), round(min(e, duration), 3)))
    if not segs:
        raise Failure("input", "no segments")
    return segs


def remap_srt(src_srt: str, segs: list[tuple[float, float]], xfade: float, out_srt: str, dry_run: bool) -> int:
    text = Path(src_srt).read_text(encoding="utf-8-sig")
    def tt(s: str) -> float:
        h, m, rest = s.strip().split(":")
        sec, ms = re.split(r"[,.]", rest)
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms.ljust(3, "0")) / 1000
    def ft(t: float) -> str:
        ms = int(round(max(0.0, t) * 1000)); h, ms = divmod(ms, 3_600_000); m, ms = divmod(ms, 60_000); s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    offsets, t = [], 0.0
    for i, (s, e) in enumerate(segs):
        offsets.append(t - s)
        t += (e - s) - (xfade if i < len(segs) - 1 else 0)
    out, n = [], 0
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue
        a, b = lines[idx].split("-->")
        cs, ce = tt(a), tt(b)
        for (s, e), off in zip(segs, offsets):
            if ce > s and cs < e:
                n += 1
                out.append(f"{n}\n{ft(max(cs, s) + off)} --> {ft(min(ce, e) + off)}\n" + "\n".join(lines[idx + 1:]) + "\n")
                break
    if not dry_run:
        Path(out_srt).write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
    return n


@main_guard
def main() -> int:
    ap = base_parser("Exact segment cuts with crossfaded joins.")
    ap.add_argument("input"); ap.add_argument("--segments", required=True); ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--xfade", type=float, default=0.25); ap.add_argument("--pad", type=float, default=0.15)
    ap.add_argument("--width", type=int); ap.add_argument("--height", type=int); ap.add_argument("--fit", default="cover", choices=["cover", "pad"])
    ap.add_argument("--remap-srt"); ap.add_argument("--srt-out"); ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    p = ffprobe(a.input, a.timeout)
    if not p["has_video"]:
        raise Failure("input", f"{a.input} has no video stream")
    segs = parse_segments(a.segments, p["duration"], a.pad)
    xf = max(0.0, min(a.xfade, min(e - s for s, e in segs) / 2 - 0.01))
    fps = p["fps"] or 30
    W = a.width or int(p["width"]); H = a.height or int(p["height"])
    if abs(int(p.get("rotation") or 0)) in (90, 270) and not a.width:
        W, H = H, W
    scale = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" if a.fit == "cover"
             else f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")
    fc = []
    for i, (s, e) in enumerate(segs):
        fc.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS,{scale},fps={fps:g},format=yuv420p[v{i}]")
        if p["has_audio"]:
            fc.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS,aresample=48000[a{i}]")
    vcur, acur = "v0", "a0"
    cur_len = segs[0][1] - segs[0][0]
    for i in range(1, len(segs)):
        d = segs[i][1] - segs[i][0]
        if xf > 0:
            fc.append(f"[{vcur}][v{i}]xfade=transition=fade:duration={xf:.3f}:offset={cur_len - xf:.3f}[vx{i}]")
            if p["has_audio"]:
                fc.append(f"[{acur}][a{i}]acrossfade=d={xf:.3f}:c1=tri:c2=tri[ax{i}]")
            cur_len += d - xf
        else:
            fc.append(f"[{vcur}][v{i}]concat=n=2:v=1:a=0[vx{i}]")
            if p["has_audio"]:
                fc.append(f"[{acur}][a{i}]concat=n=2:v=0:a=1[ax{i}]")
            cur_len += d
        vcur, acur = f"vx{i}", f"ax{i}"
    maps = ["-map", f"[{vcur}]"] + (["-map", f"[{acur}]", "-c:a", "aac", "-b:a", "192k"] if p["has_audio"] else ["-an"])
    cmd = (["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.input, "-filter_complex", ";".join(fc)] + maps
           + ["-c:v", "libx264", "-preset", "veryfast" if a.fast else "medium", "-crf", "23" if a.fast else "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.output])
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg cut")
    out = None if a.dry_run else ffprobe(a.output, a.timeout)
    remapped = None
    if a.remap_srt:
        remapped = remap_srt(a.remap_srt, segs, xf, a.srt_out or str(Path(a.output).with_suffix(".srt")), a.dry_run)
    planned = round(cur_len, 3)
    ok = out is None or abs(out["duration"] - planned) < 0.2
    result = {"status": "ok" if ok else "failed", "output": a.output, "segments": segs, "planned_s": planned, "xfade_s": xf, "pad_s": a.pad,
              "remapped_cues": remapped, "output_probe": out, "commands": [cmd], "dry_run": a.dry_run}
    if not ok:
        result["error"] = {"kind": "verify", "message": f"output {out['duration']} s vs planned {planned} s"}
    summary = (f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(segs)} segments, {planned} s planned" + (f", {out['duration']} s measured" if out else "")
               + f", xfade {xf:g} s" + (f", {remapped} cues remapped" if remapped is not None else ""))
    return finish(result, a.json, summary=summary)


if __name__ == "__main__":
    main()
