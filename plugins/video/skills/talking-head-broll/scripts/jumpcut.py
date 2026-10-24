#!/usr/bin/env python3
"""jumpcut: silence-aware jump cuts with optional filler removal from word timings.

Usage:  jumpcut.py INPUT -o tight.mp4 [--noise -35] [--min-silence 0.6] [--keep 0.25] [--max-keep-pause 2.0]
                   [--words words.json --fillers [--fillers-aggressive] [--language en]] [--srt in.srt --srt-out out.srt]
                   [--punch-in] [--xfade 0.08] [--fast] [--dry-run] [--json] [--timeout S] [--overwrite]

Keeps speech regions ± keep seconds; removes pauses ≥ min-silence (pauses ≥ max-keep-pause are kept as
deliberate unless --max-keep-pause 0); cuts fillers and immediate repeats on word timings; joins with a
short crossfade. Writes a segment list (JSON) beside the output and remaps an SRT when asked.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, check_output_path, ffprobe, finish, main_guard, require, run, run_or_fail  # noqa: E402

FILLERS = {
    "en": (["um", "uh", "erm", "er", "hmm", "mm"], ["like", "sort of", "kind of", "you know"]),
    "es": (["eh", "este", "em"], ["o sea", "pues"]),
    "fr": (["euh", "ben", "bah", "hum"], ["tu vois"]),
    "de": (["äh", "ähm", "hm"], ["halt"]),
    "pt": (["é", "hum", "ahn"], ["tipo"]),
    "hi": (["अं", "हम्म"], ["अरे", "मतलब"]),
}


def silences(path: str, noise: float, min_s: float, timeout: float) -> list[tuple[float, float]]:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af", f"silencedetect=noise={noise}dB:d={min_s}", "-f", "null", "-"], timeout)
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", r["stderr"])]
    ends = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", r["stderr"])]
    return list(zip(starts, ends))


def speech_segments(duration: float, sil: list[tuple[float, float]], keep: float, max_keep: float) -> list[tuple[float, float]]:
    segs, t = [], 0.0
    for s, e in sil:
        if max_keep and (e - s) >= max_keep:
            continue  # deliberate pause: not a cut point
        if s - t > 0.2:
            segs.append((max(0.0, t - keep if segs else t), min(duration, s + keep)))
        t = e
    if duration - t > 0.2:
        segs.append((max(0.0, t - keep), duration))
    # merge overlaps
    merged: list[list[float]] = []
    for s, e in segs:
        if merged and s <= merged[-1][1] + 0.05:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(round(s, 3), round(e, 3)) for s, e in merged]


def filler_windows(words: list[dict], language: str, aggressive: bool) -> list[tuple[float, float, str]]:
    soft, hard = FILLERS.get(language, FILLERS["en"])
    targets = set(soft) | (set(hard) if aggressive else set())
    out = []
    prev = None
    for w in words:
        token = re.sub(r"[^\w']", "", w["word"].strip().lower())
        if not token:
            continue
        if token in targets:
            out.append((w["start"], w["end"], token))
        elif prev and prev[0] == token and w["start"] - prev[1] < 0.6 and len(token) > 1:
            out.append((prev[2], prev[1], f"repeat:{token}"))
        prev = (token, w["end"], w["start"])
    return out


def subtract(segs: list[tuple[float, float]], cuts: list[tuple[float, float, str]], pad: float = 0.03) -> list[tuple[float, float]]:
    out = []
    for s, e in segs:
        cur = s
        for cs, ce, _ in sorted(cuts):
            if ce <= cur or cs >= e:
                continue
            if cs - pad > cur + 0.15:
                out.append((cur, cs - pad))
            cur = max(cur, ce + pad)
        if e - cur > 0.15:
            out.append((cur, e))
    return [(round(s, 3), round(e, 3)) for s, e in out]


@main_guard
def main() -> int:
    ap = base_parser("Silence-aware jump cuts with optional filler removal.")
    ap.add_argument("input"); ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--noise", type=float, default=-35); ap.add_argument("--min-silence", type=float, default=0.6); ap.add_argument("--keep", type=float, default=0.25)
    ap.add_argument("--max-keep-pause", type=float, default=2.0, help="pauses at least this long are kept as deliberate (0 = cut all)")
    ap.add_argument("--words", help="word timings JSON (transcribe.py --words)"); ap.add_argument("--fillers", action="store_true"); ap.add_argument("--fillers-aggressive", action="store_true")
    ap.add_argument("--language", default="en"); ap.add_argument("--srt"); ap.add_argument("--srt-out"); ap.add_argument("--punch-in", action="store_true")
    ap.add_argument("--xfade", type=float, default=0.08); ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    p = ffprobe(a.input, a.timeout)
    if not p["has_video"] or not p["has_audio"]:
        raise Failure("input", f"{a.input} needs both video and audio")
    sil = silences(a.input, a.noise, a.min_silence, a.timeout)
    segs = speech_segments(p["duration"], sil, a.keep, a.max_keep_pause)
    cuts: list[tuple[float, float, str]] = []
    if a.fillers:
        if not a.words:
            raise Failure("input", "--fillers needs --words (word timings from transcribe.py --words)")
        words = json.loads(Path(a.words).read_text(encoding="utf-8")).get("words", [])
        cuts = filler_windows(words, a.language, a.fillers_aggressive)
        segs = subtract(segs, cuts)
    if not segs:
        raise Failure("input", "nothing left to keep — lower --noise or raise --min-silence")
    removed = round(p["duration"] - sum(e - s for s, e in segs), 2)
    here = Path(__file__).resolve().parent
    seg_spec = ",".join(f"{s}-{e}" for s, e in segs)
    # reuse clips-to-short's cutter for exact joins when it is installed beside us; otherwise inline
    cutter = here.parent.parent / "clips-to-short" / "scripts" / "cut.py"
    W, H = int(p["width"]), int(p["height"])
    if a.punch_in:
        # alternate 1.1x punch-ins: render odd segments slightly zoomed via a second pass is costly; do it inline below
        pass
    fps = p["fps"] or 30
    fc = []
    for i, (s, e) in enumerate(segs):
        zoom = ",scale=iw*1.1:ih*1.1,crop=iw/1.1:ih/1.1" if (a.punch_in and i % 2 == 1) else ""
        fc.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS{zoom},scale={W}:{H},fps={fps:g},format=yuv420p[v{i}]")
        fc.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS,aresample=48000[a{i}]")
    xf = max(0.0, min(a.xfade, min(e - s for s, e in segs) / 2 - 0.01))
    vcur, acur, cur_len = "v0", "a0", segs[0][1] - segs[0][0]
    for i in range(1, len(segs)):
        d = segs[i][1] - segs[i][0]
        if xf > 0:
            fc.append(f"[{vcur}][v{i}]xfade=transition=fade:duration={xf:.3f}:offset={cur_len - xf:.3f}[vx{i}]")
            fc.append(f"[{acur}][a{i}]acrossfade=d={xf:.3f}:c1=tri:c2=tri[ax{i}]")
            cur_len += d - xf
        else:
            fc.append(f"[{vcur}][v{i}]concat=n=2:v=1:a=0[vx{i}]"); fc.append(f"[{acur}][a{i}]concat=n=2:v=0:a=1[ax{i}]")
            cur_len += d
        vcur, acur = f"vx{i}", f"ax{i}"
    cmd = (["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.input, "-filter_complex", ";".join(fc), "-map", f"[{vcur}]", "-map", f"[{acur}]",
            "-c:v", "libx264", "-preset", "veryfast" if a.fast else "medium", "-crf", "23" if a.fast else "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.output])
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg jumpcut")
    seg_file = str(Path(a.output).with_suffix(".segments.json"))
    if not a.dry_run:
        Path(seg_file).write_text(json.dumps({"source": a.input, "segments": segs, "xfade_s": xf, "fillers_cut": [{"start": s, "end": e, "what": w} for s, e, w in cuts]}, indent=1), encoding="utf-8")
    remapped = None
    if a.srt:
        sys.path.insert(0, str(cutter.parent))
        try:
            from cut import remap_srt  # type: ignore
            remapped = remap_srt(a.srt, segs, xf, a.srt_out or str(Path(a.output).with_suffix(".srt")), a.dry_run)
        except ImportError:
            remapped = None
    out = None if a.dry_run else ffprobe(a.output, a.timeout)
    result = {"status": "ok", "output": a.output, "segments": len(segs), "segments_file": seg_file, "removed_s": removed, "pauses_found": len(sil),
              "fillers_cut": len(cuts), "kept_pauses": sum(1 for s, e in sil if a.max_keep_pause and e - s >= a.max_keep_pause), "planned_s": round(cur_len, 3),
              "remapped_cues": remapped, "output_probe": out, "commands": [cmd], "dry_run": a.dry_run}
    summary = (f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(segs)} segments, removed {removed} s of {p['duration']} s"
               + (f", {len(cuts)} fillers/repeats cut" if a.fillers else "") + f", {result['kept_pauses']} deliberate pauses kept" + (f", {out['duration']} s" if out else ""))
    return finish(result, a.json, summary=summary)


if __name__ == "__main__":
    main()
