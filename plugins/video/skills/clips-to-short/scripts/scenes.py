#!/usr/bin/env python3
"""scenes: scene cuts, loudness timeline, silences, candidate moments, and a first selection for a target length.

Usage:  scenes.py INPUT [--target 30] [--threshold 10] [--min-window 4] [--max-window 8] [--transcript cues.srt]
                 [--silences] [--sheet candidates.png] [--json] [--timeout S]

Measurement only (ffmpeg scdet + ebur128 + silencedetect); --dry-run is accepted and skips nothing except the sheet.
The selection is a starting point ranked by energy — the agent chooses by content (references/selection.md).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, ffprobe, finish, main_guard, require, run, run_or_fail  # noqa: E402


def detect_scenes(path: str, threshold: float, timeout: float) -> list[float]:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-an", "-vf", f"scdet=threshold={threshold}:sc_pass=0", "-f", "null", "-"], timeout)
    times = [float(x) for x in re.findall(r"lavfi\.scd\.time:\s*([\d.]+)", r["stderr"])]
    if not times:
        r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-an", "-vf", f"select='gt(scene,{threshold / 100:.3f})',showinfo", "-f", "null", "-"], timeout)
        times = [float(x) for x in re.findall(r"pts_time:\s*([\d.]+)", r["stderr"])]
    return sorted(set(round(t, 2) for t in times))


def loudness_timeline(path: str, timeout: float) -> tuple[list[tuple[float, float]], float | None]:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-filter_complex", "ebur128", "-f", "null", "-"], timeout)
    tl = [(float(t), float(m)) for t, m in re.findall(r"t:\s*([\d.]+)\s+TARGET:[^\n]*?M:\s*(-?[\d.]+)", r["stderr"])]
    if not tl:
        tl = [(float(t), float(m)) for t, m in re.findall(r"t:\s*([\d.]+)\s+M:\s*(-?[\d.]+)", r["stderr"])]
    tail = r["stderr"][r["stderr"].rfind("Summary:"):] if "Summary:" in r["stderr"] else ""
    mi = re.search(r"\bI:\s*(-?[\d.]+)\s*LUFS", tail)
    return [(t, m) for t, m in tl if m > -120], (float(mi.group(1)) if mi else None)


def detect_silences(path: str, timeout: float, noise_db: float = -35, min_s: float = 0.6) -> list[tuple[float, float]]:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af", f"silencedetect=noise={noise_db}dB:d={min_s}", "-f", "null", "-"], timeout)
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", r["stderr"])]
    ends = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", r["stderr"])]
    return [(round(s, 2), round(e, 2)) for s, e in zip(starts, ends)]


def read_srt(path: str) -> list[dict]:
    cues = []
    text = Path(path).read_text(encoding="utf-8-sig")
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue
        def tt(s: str) -> float:
            h, m, rest = s.strip().split(":")
            sec, ms = re.split(r"[,.]", rest)
            return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms.ljust(3, "0")) / 1000
        a, b = lines[idx].split("-->")
        cues.append({"start": tt(a), "end": tt(b), "text": " ".join(lines[idx + 1:])})
    return cues


def candidates(duration: float, scenes: list[float], tl: list[tuple[float, float]], integ: float | None, min_w: float, max_w: float) -> list[dict]:
    bounds = [0.0] + [s for s in scenes if 0 < s < duration] + [duration]
    out = []
    integ = integ if integ is not None else (sum(m for _, m in tl) / len(tl) if tl else -23.0)
    speech_thr = integ - 6
    def stats(a: float, b: float) -> tuple[float, float, float]:
        vals = [m for t, m in tl if a <= t < b]
        if not vals:
            return 0.0, 0.0, 0.0
        mean = sum(vals) / len(vals)
        energy = max(0.0, min(1.0, (mean - (integ - 15)) / 20))
        variation = max(0.0, min(1.0, (max(vals) - min(vals)) / 25))
        density = sum(1 for v in vals if v > speech_thr) / len(vals)
        return energy, variation, density
    i = 0
    while i < len(bounds) - 1:
        a = bounds[i]
        j = i + 1
        while j < len(bounds) and bounds[j] - a < min_w:
            j += 1
        if j >= len(bounds):
            b = duration
        else:
            b = bounds[j]
        if b - a > max_w:
            # slide fixed windows inside a long shot
            t = a
            while t + min_w <= b:
                w = min(max_w, b - t)
                e, v, d = stats(t, t + w)
                out.append({"start": round(t, 2), "end": round(t + w, 2), "score": round(0.5 * e + 0.2 * v + 0.3 * d, 3), "energy": round(e, 2), "variation": round(v, 2), "speech": round(d, 2), "on_cut": t == a})
                t += w / 2
        elif b - a >= 1.0:
            e, v, d = stats(a, b)
            out.append({"start": round(a, 2), "end": round(b, 2), "score": round(0.5 * e + 0.2 * v + 0.3 * d, 3), "energy": round(e, 2), "variation": round(v, 2), "speech": round(d, 2), "on_cut": True})
        i = max(j, i + 1)
    out.sort(key=lambda c: -c["score"])
    return out


def select(cands: list[dict], target: float) -> list[dict]:
    chosen: list[dict] = []
    total = 0.0
    for c in cands:
        if any(not (c["end"] <= x["start"] or c["start"] >= x["end"]) for x in chosen):
            continue
        d = c["end"] - c["start"]
        if total + d > target + 1.0:
            continue
        chosen.append(c)
        total += d
        if total >= target - 1.5:
            break
    return sorted(chosen, key=lambda c: c["start"])


@main_guard
def main() -> int:
    ap = base_parser("Scene cuts, loudness, silences, candidate moments and a first selection.")
    ap.add_argument("input"); ap.add_argument("--target", type=float, default=30.0); ap.add_argument("--threshold", type=float, default=10.0)
    ap.add_argument("--min-window", type=float, default=4.0); ap.add_argument("--max-window", type=float, default=8.0)
    ap.add_argument("--transcript", help="SRT: attach the words spoken inside each candidate"); ap.add_argument("--silences", action="store_true")
    ap.add_argument("--sheet", help="write a contact sheet with one frame per top candidate")
    a = ap.parse_args()
    require("ffmpeg")
    p = ffprobe(a.input, a.timeout)
    if not p["has_video"]:
        raise Failure("input", f"{a.input} has no video stream")
    scenes = detect_scenes(a.input, a.threshold, a.timeout)
    tl, integ = loudness_timeline(a.input, a.timeout) if p["has_audio"] else ([], None)
    cands = candidates(p["duration"], scenes, tl, integ, a.min_window, a.max_window)[:12]
    if a.transcript:
        cues = read_srt(a.transcript)
        for c in cands:
            c["words"] = " ".join(q["text"] for q in cues if q["end"] > c["start"] and q["start"] < c["end"])
    sil = detect_silences(a.input, a.timeout) if (a.silences and p["has_audio"]) else []
    sel = select(cands, a.target)
    sheet = None
    if a.sheet and cands and not a.dry_run:
        n = min(len(cands), 12)
        cols = 4 if n > 6 else 3
        rows = (n + cols - 1) // cols
        inputs, fc = [], []
        for i, c in enumerate(cands[:n]):
            inputs += ["-ss", f"{(c['start'] + c['end']) / 2:.3f}", "-i", a.input]
            fc.append(f"[{i}:v]scale=400:-2,drawtext=text='{i + 1}\\: {c['start']:.1f}-{c['end']:.1f}s':fontsize=24:fontcolor=white:borderw=2:x=8:y=8,trim=end_frame=1[f{i}]")
        fc.append("".join(f"[f{i}]" for i in range(n)) + f"xstack=inputs={n}:layout=" + "|".join(f"{(i % cols) * 404}_{(i // cols) * 232}" for i in range(n)) + ":fill=0x202020[v]")
        run_or_fail(["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[v]", "-frames:v", "1", a.sheet], a.timeout, False, what="ffmpeg sheet")
        sheet = a.sheet
    result = {"status": "ok", "file": a.input, "duration_s": p["duration"], "integrated_lufs": integ, "scenes": scenes, "scene_count": len(scenes),
              "candidates": cands, "selection": sel, "selection_total_s": round(sum(c["end"] - c["start"] for c in sel), 2), "target_s": a.target,
              "silences": sil, "sheet": sheet, "notes": ["scores rank energy, not meaning — choose by content or by the sheet"]}
    lines = [f"{p['duration']} s, {len(scenes)} scene cuts" + (f", {integ} LUFS" if integ is not None else ", no audio"), "candidates (top):"]
    for i, c in enumerate(cands[:8], start=1):
        lines.append(f"  {i:2}. {c['start']:7.2f}–{c['end']:7.2f}  score {c['score']:.2f}  (energy {c['energy']}, speech {c['speech']})" + (f"  \"{c['words'][:70]}\"" if c.get('words') else ""))
    lines.append(f"first selection for {a.target:g} s: " + ", ".join(f"{c['start']:.1f}-{c['end']:.1f}" for c in sel) + f"  ({result['selection_total_s']} s)")
    if sheet:
        lines.append(f"sheet: {sheet} — view it")
    return finish(result, a.json, summary="\n".join(lines))


if __name__ == "__main__":
    main()
