#!/usr/bin/env python3
"""assemble: render timeline.json (segments, audio tracks, captions, overlays) into one edit.mp4.

Usage:  assemble.py TIMELINE.json -o edit.mp4 [--fast] [--dry-run] [--json] [--timeout S] [--overwrite]

Paths inside the timeline are relative to the timeline file's folder's parent (out/<slug>/), or absolute.
--dry-run validates every input, prints the planned total and the filter graph, and writes nothing.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, check_output_path, ffprobe, finish, main_guard, require, run, run_or_fail  # noqa: E402

MAX_SEGMENTS = 40


def resolve(base: Path, src: str) -> str:
    p = Path(src)
    return str(p if p.is_absolute() else (base / p))


def esc(path: str) -> str:
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")


def colour(c: str) -> str:
    return c if re.match(r"^#?[0-9a-fA-F]{6}$", c) else "#000000"


def build(tl: dict, base: Path, timeout: float, dry_run: bool) -> tuple[list[str], dict]:
    W, H, fps = int(tl["width"]), int(tl["height"]), float(tl.get("fps", 30))
    bg = colour(tl.get("background", "#000000")).lstrip("#")
    segs, tracks, overlays = tl.get("video") or [], tl.get("audio") or [], tl.get("overlays") or []
    if not segs:
        raise Failure("input", "timeline has no video segments")
    if len(segs) > MAX_SEGMENTS:
        raise Failure("input", f"{len(segs)} segments; chunking above {MAX_SEGMENTS} is not implemented yet — render in two timelines and concatenate")
    inputs: list[str] = []
    fc: list[str] = []
    notes: list[str] = []
    probes: dict = {}

    # ---- video segments ----
    vlabels = []
    for i, s in enumerate(segs):
        src, dur = str(s["src"]), float(s["duration_s"])
        if dur <= 0:
            raise Failure("input", f"segment {i + 1}: duration_s must be > 0")
        if src.startswith("color:"):
            inputs += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"color=c=0x{colour(src[6:]).lstrip('#')}:s={W}x{H}:r={fps:g}"]
            chain = f"[{len(inputs) // 2 - 1}:v]trim=duration={dur:.3f},setpts=PTS-STARTPTS,format=yuv420p"
        elif src.startswith("image:"):
            path = resolve(base, src[6:])
            if not os.path.isfile(path):
                raise Failure("input", f"segment {i + 1}: {path} does not exist")
            inputs += ["-loop", "1", "-framerate", f"{fps:g}", "-t", f"{dur:.3f}", "-i", path]
            fit = s.get("fit", "pad")
            scale = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" if fit == "cover"
                     else f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x{bg}")
            chain = f"[{len(inputs) // 2 - 1}:v]{scale},fps={fps:g},trim=duration={dur:.3f},setpts=PTS-STARTPTS,format=yuv420p"
        else:
            path = resolve(base, src)
            if not os.path.isfile(path):
                raise Failure("input", f"segment {i + 1}: {path} does not exist")
            p = probes.get(path) or ffprobe(path, timeout)
            probes[path] = p
            if not p["has_video"]:
                raise Failure("input", f"segment {i + 1}: {path} has no video stream")
            in_s = float(s.get("in_s", 0))
            if in_s + dur > p["duration"] + 0.05:
                raise Failure("input", f"segment {i + 1}: in_s {in_s} + duration {dur} exceeds {path} ({p['duration']} s)")
            inputs += ["-ss", f"{in_s:.3f}", "-t", f"{dur + 0.5:.3f}", "-i", path]
            fit = s.get("fit", "pad")
            scale = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" if fit == "cover"
                     else f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x{bg}")
            chain = f"[{len(inputs) // 2 - 1}:v]{scale},fps={fps:g},trim=duration={dur:.3f},setpts=PTS-STARTPTS,format=yuv420p"
        # the index arithmetic above assumes each input adds exactly two tokens before "-i"; recompute robustly:
        idx = sum(1 for t in inputs if t == "-i") - 1
        chain = re.sub(r"^\[\d+:v\]", f"[{idx}:v]", chain)
        fc.append(chain + f"[v{i}]")
        vlabels.append((f"v{i}", dur, s.get("transition", "cut"), float(s.get("transition_s", 0.4) or 0.4)))

    # concat / xfade chain
    total = sum(d for _, d, _, _ in vlabels)
    cur, cur_len = vlabels[0][0], vlabels[0][1]
    for n, (lab, dur, trans, tdur) in enumerate(vlabels[1:], start=1):
        if trans == "dissolve" and tdur > 0:
            tdur = min(tdur, dur / 2, cur_len / 2)
            off = cur_len - tdur
            fc.append(f"[{cur}][{lab}]xfade=transition=fade:duration={tdur:.3f}:offset={off:.3f}[x{n}]")
            cur, cur_len = f"x{n}", cur_len + dur - tdur
            total -= tdur
        else:
            fc.append(f"[{cur}][{lab}]concat=n=2:v=1:a=0[x{n}]")
            cur, cur_len = f"x{n}", cur_len + dur
    vcur = cur

    # overlays
    for k, o in enumerate(overlays):
        path = resolve(base, o["src"])
        if not os.path.isfile(path):
            raise Failure("input", f"overlay {k + 1}: {path} does not exist")
        inputs += ["-i", path]
        idx = sum(1 for t in inputs if t == "-i") - 1
        prep = f"[{idx}:v]format=rgba"
        if o.get("scale_w"):
            prep += f",scale={int(o['scale_w'])}:-1"
        if o.get("opacity") is not None and float(o["opacity"]) < 1:
            prep += f",colorchannelmixer=aa={float(o['opacity']):.3f}"
        fc.append(prep + f"[ov{k}]")
        enable = ""
        if o.get("start_s") is not None or o.get("end_s") is not None:
            s0, s1 = float(o.get("start_s") or 0), float(o["end_s"]) if o.get("end_s") is not None else total + 1
            enable = f":enable='between(t,{s0:.3f},{s1:.3f})'"
        fc.append(f"[{vcur}][ov{k}]overlay=x={o.get('x', 'W-w-40')}:y={o.get('y', '40')}{enable}[vo{k}]")
        vcur = f"vo{k}"

    # subtitles
    if tl.get("subtitles"):
        ass = resolve(base, tl["subtitles"])
        if not os.path.isfile(ass):
            raise Failure("input", f"subtitles {ass} does not exist")
        fc.append(f"[{vcur}]ass={esc(ass)}[vs]")
        vcur = "vs"

    # ---- audio ----
    alabels, voice_labels = [], []
    if tl.get("keep_source_audio"):
        notes.append("keep_source_audio is applied per segment with its own trim; segment audio is treated as voice")
        t_acc = 0.0
        for i, s in enumerate(segs):
            src = str(s["src"])
            if not src.startswith(("color:", "image:")):
                path = resolve(base, src)
                if probes[path]["has_audio"]:
                    idx = [j for j, t in enumerate(inputs) if t == "-i"]
                    # the segment's input index equals its position among video inputs
                    vin = i
                    dur = float(s["duration_s"])
                    fc.append(f"[{vin}:a]atrim=duration={dur:.3f},asetpts=PTS-STARTPTS,aresample=48000,adelay={int(t_acc * 1000)}|{int(t_acc * 1000)}[sa{i}]")
                    alabels.append(f"sa{i}")
                    voice_labels.append(f"sa{i}")
            t_acc += float(s["duration_s"]) - (float(s.get("transition_s", 0.4) or 0.4) if s.get("transition") == "dissolve" and i > 0 else 0)
    music_labels = []
    for k, t in enumerate(tracks):
        path = resolve(base, t["src"])
        if not os.path.isfile(path):
            raise Failure("input", f"audio track {k + 1}: {path} does not exist")
        role = t.get("role", "sfx")
        loop = bool(t.get("loop")) and role == "music"
        inputs += (["-stream_loop", "-1"] if loop else []) + ["-i", path]
        idx = sum(1 for x in inputs if x == "-i") - 1
        start = float(t.get("start_s", 0))
        chain = f"[{idx}:a]aresample=48000"
        trim = float(t.get("trim_s") or 0) or (max(0.1, total - start) if loop else 0)
        if trim:
            chain += f",atrim=duration={trim:.3f},asetpts=PTS-STARTPTS"
        if t.get("fade_in_s"):
            chain += f",afade=t=in:st=0:d={float(t['fade_in_s']):.3f}"
        if t.get("fade_out_s") and trim:
            chain += f",afade=t=out:st={max(0.0, trim - float(t['fade_out_s'])):.3f}:d={float(t['fade_out_s']):.3f}"
        if t.get("gain_db"):
            chain += f",volume={float(t['gain_db']):.2f}dB"
        if start > 0:
            chain += f",adelay={int(start * 1000)}|{int(start * 1000)}"
        lab = f"a{k}"
        fc.append(chain + f"[{lab}]")
        if role == "voice":
            voice_labels.append(lab)
            alabels.append(lab)
        elif role == "music":
            music_labels.append((lab, t))
        else:
            alabels.append(lab)
    for m, (lab, t) in enumerate(music_labels):
        if t.get("duck_under") == "voice" and voice_labels:
            # one copy of the voice mix as the sidechain key
            if len(voice_labels) > 1:
                fc.append("".join(f"[{v}]" for v in voice_labels) + f"amix=inputs={len(voice_labels)}:normalize=0[vmix{m}]")
                vkey = f"vmix{m}"
            else:
                vkey = voice_labels[0]
            fc.append(f"[{vkey}]asplit=2[{vkey}_k{m}][{vkey}_p{m}]")
            # the split consumes vkey; re-point consumers
            voice_labels = [f"{vkey}_p{m}" if v == vkey else v for v in voice_labels]
            alabels = [f"{vkey}_p{m}" if v == vkey else v for v in alabels]
            depth = abs(float(t.get("duck_db", -12)))
            ratio = max(2.0, min(20.0, depth / 1.5))
            fc.append(f"[{lab}][{vkey}_k{m}]sidechaincompress=threshold=0.02:ratio={ratio:.1f}:attack=15:release=300:makeup=1:level_sc=1[md{m}]")
            alabels.append(f"md{m}")
            notes.append(f"music ducked under voice (~-{depth:.0f} dB, ratio {ratio:.1f})")
        else:
            alabels.append(lab)
    has_audio = bool(alabels)
    if has_audio:
        if len(alabels) == 1:
            fc.append(f"[{alabels[0]}]anull[aout]")
        else:
            fc.append("".join(f"[{l}]" for l in alabels) + f"amix=inputs={len(alabels)}:normalize=0:dropout_transition=0[aout]")
    plan = {"total_s": round(total, 3), "segments": len(segs), "tracks": len(tracks), "overlays": len(overlays), "has_audio": has_audio,
            "subtitles": bool(tl.get("subtitles")), "notes": notes, "filter_complex": ";".join(fc), "vout": vcur}
    return inputs, plan


def measure_lufs(path: str, timeout: float) -> float | None:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-filter_complex", "ebur128", "-f", "null", "-"], timeout)
    m = re.search(r"\bI:\s*(-?[\d.]+)\s*LUFS", r["stderr"][r["stderr"].rfind("Summary:"):] if "Summary:" in r["stderr"] else r["stderr"])
    return float(m.group(1)) if m else None


@main_guard
def main() -> int:
    ap = base_parser("Render a timeline.json into one edit.mp4.")
    ap.add_argument("timeline")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--fast", action="store_true", help="preview quality")
    a = ap.parse_args()
    require("ffmpeg")
    check_output_path(a.output, a.overwrite)
    tpath = Path(a.timeline)
    if not tpath.is_file():
        raise Failure("input", f"{a.timeline} does not exist")
    tl = json.loads(tpath.read_text(encoding="utf-8"))
    base = tpath.resolve().parent.parent if tpath.resolve().parent.name == "work" else tpath.resolve().parent
    inputs, plan = build(tl, base, a.timeout, a.dry_run)
    fps = float(tl.get("fps", 30))
    cmd = (["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs + ["-filter_complex", plan["filter_complex"], "-map", f"[{plan['vout']}]"]
           + (["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"] if plan["has_audio"] else ["-an"])
           + ["-c:v", "libx264", "-preset", "veryfast" if a.fast else "medium", "-crf", "23" if a.fast else "18", "-pix_fmt", "yuv420p",
              "-r", f"{fps:g}", "-t", f"{plan['total_s']:.3f}", "-movflags", "+faststart", a.output])
    run_or_fail(cmd, a.timeout, a.dry_run, what="ffmpeg assemble")
    out = None if a.dry_run else ffprobe(a.output, a.timeout)
    lufs = None if (a.dry_run or not plan["has_audio"]) else measure_lufs(a.output, a.timeout)
    ok_dur = out is None or abs(out["duration"] - plan["total_s"]) <= 0.15
    result = {"status": "ok" if ok_dur else "failed", "output": a.output, "planned_total_s": plan["total_s"], "segments": plan["segments"],
              "tracks": plan["tracks"], "overlays": plan["overlays"], "subtitles": plan["subtitles"], "mix_lufs": lufs, "notes": plan["notes"],
              "commands": [cmd], "output_probe": out, "dry_run": a.dry_run}
    if not ok_dur:
        result["error"] = {"kind": "verify", "message": f"output is {out['duration']} s, planned {plan['total_s']} s"}
    if a.dry_run:
        summary = f"would render {a.output}: {plan['segments']} segments, {plan['tracks']} tracks, {plan['overlays']} overlays, {plan['total_s']} s" + ("; " + "; ".join(plan["notes"]) if plan["notes"] else "")
    else:
        summary = (f"{a.output}: {out['duration']} s (planned {plan['total_s']}), {out['width']}x{out['height']}, {out['fps']} fps"
                   + (f", mix {lufs} LUFS" if lufs is not None else ", no audio") + ("; " + "; ".join(plan["notes"]) if plan["notes"] else ""))
    return finish(result, a.json, summary=summary)


if __name__ == "__main__":
    main()
