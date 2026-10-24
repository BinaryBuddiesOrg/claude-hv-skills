#!/usr/bin/env python3
"""timeline: build timeline.json from beats.json and the pieces the other skills rendered.

Usage:
  timeline.py from-beats BEATS.json -o work/timeline.json --width W --height H [--fps 30] [--clips-dir work/beats]
              [--voice work/voice/track.wav] [--music work/music.wav] [--music-gain -2] [--duck -12] [--subtitles work/text.ass]
              [--sfx-cues work/sfx.json] [--overlay badge.png[@x,y]] [--keep-source-audio] [--background '#000000']
              [--end-card end.png] [--ai-dir work/ai]

Segment per beat: work/beats/<id>.mp4 when motion rendered it; else the beat's visual.source (footage with in_s,
image:, color:, or text → a background card); ai:<id> → <ai-dir>/<id>.mp4. Fails on any missing piece.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, common_flags, finish, main_guard  # noqa: E402


def cmd_from_beats(a) -> int:
    bpath = Path(a.beats)
    if not bpath.is_file():
        raise Failure("input", f"{a.beats} does not exist")
    beats = json.loads(bpath.read_text(encoding="utf-8"))
    base = bpath.resolve().parent  # out/<slug>/
    def rel(p: str) -> str:
        pp = Path(p)
        try:
            return str(pp.resolve().relative_to(base)) if pp.exists() else p
        except ValueError:
            return str(pp.resolve())
    clips_dir = Path(a.clips_dir) if a.clips_dir else None
    segments, missing, notes = [], [], []
    for b in beats.get("beats") or []:
        bid, dur = b.get("id"), float(b["duration_s"])
        vis = b.get("visual") or {}
        src = str(vis.get("source") or "")
        seg = {"duration_s": round(dur, 3)}
        clip = clips_dir / f"{bid}.mp4" if clips_dir else None
        if clip and clip.is_file():
            seg.update(src=rel(str(clip)), in_s=0, fit="pad")
        elif src.startswith("ai:"):
            ai = Path(a.ai_dir or "work/ai")
            ai = ai if ai.is_absolute() else base / ai
            cand = ai / f"{src[3:]}.mp4"
            if cand.is_file():
                seg.update(src=rel(str(cand)), in_s=0, fit="cover")
            else:
                missing.append(f"{bid}: AI shot {src[3:]} expected at {cand}")
                continue
        elif src.startswith("image:"):
            path = src[6:]
            full = path if os.path.isabs(path) else str(base / path) if (base / path).exists() else path
            if not os.path.isfile(full):
                missing.append(f"{bid}: image {path}")
                continue
            seg.update(src=f"image:{rel(full)}", fit=vis.get("fit", "cover"))
        elif src.startswith("color:"):
            seg.update(src=src)
        elif src in ("text", ""):
            seg.update(src=f"color:{a.background}")
            if not (b.get("on_screen") or "").strip():
                notes.append(f"{bid}: text beat with no on_screen text — a plain {a.background} card")
        else:
            full = src if os.path.isabs(src) else str(base / src) if (base / src).exists() else src
            if not os.path.isfile(full):
                missing.append(f"{bid}: {src}")
                continue
            seg.update(src=rel(full), in_s=float(vis.get("in_s", 0) or 0), fit=vis.get("fit", "cover"))
        if b.get("transition") == "dissolve":
            seg.update(transition="dissolve", transition_s=0.4)
        segments.append(seg)
    if missing:
        raise Failure("input", "missing pieces: " + "; ".join(missing), "render them (motion.py beats, ai shots) or fix beats.json")
    audio = []
    if a.voice:
        audio.append({"src": rel(a.voice), "role": "voice", "start_s": 0, "gain_db": 0})
    if a.music:
        audio.append({"src": rel(a.music), "role": "music", "start_s": 0, "gain_db": a.music_gain, "loop": True, "fade_in_s": 0.5, "fade_out_s": 1.5,
                      "duck_under": "voice" if a.voice or a.keep_source_audio else None, "duck_db": a.duck})
    if a.sfx_cues:
        cues = json.loads(Path(a.sfx_cues).read_text(encoding="utf-8")).get("tracks", [])
        for c in cues:
            audio.append({"src": rel(c["src"]), "role": "sfx", "start_s": c["start_s"], "gain_db": c.get("gain_db", -6)})
    overlays = []
    for ov in a.overlay or []:
        path, _, pos = ov.partition("@")
        x, y = (pos.split(",") + ["", ""])[:2] if pos else ("W-w-43", "43")
        overlays.append({"src": rel(path), "x": x or "W-w-43", "y": y or "43", "opacity": 0.9})
    if a.end_card and segments:
        start = sum(s["duration_s"] for s in segments[:-1]) - sum(s.get("transition_s", 0) for s in segments[1:])
        overlays.append({"src": rel(a.end_card), "x": "0", "y": "0", "start_s": round(start, 3), "end_s": None, "opacity": 1.0})
    tl = {"studio_timeline": "0.1", "width": a.width, "height": a.height, "fps": a.fps, "background": a.background, "video": segments,
          "audio": audio, "keep_source_audio": bool(a.keep_source_audio), "subtitles": rel(a.subtitles) if a.subtitles else None, "overlays": overlays}
    total = sum(s["duration_s"] for s in segments) - sum(s.get("transition_s", 0) for s in segments[1:])
    if not a.dry_run:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(tl, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return finish({"status": "ok", "output": a.output, "segments": len(segments), "tracks": len(audio), "overlays": len(overlays), "total_s": round(total, 3), "notes": notes, "dry_run": a.dry_run},
                  a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(segments)} segments, {len(audio)} tracks, {len(overlays)} overlays, {total:.2f} s" + ("\n" + "\n".join(notes) if notes else ""))


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Build timeline.json from beats.json. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("from-beats", parents=[common_flags()])
    f.add_argument("beats"); f.add_argument("-o", "--output", required=True); f.add_argument("--width", type=int, required=True); f.add_argument("--height", type=int, required=True)
    f.add_argument("--fps", type=float, default=30.0); f.add_argument("--clips-dir"); f.add_argument("--voice"); f.add_argument("--music"); f.add_argument("--music-gain", type=float, default=-2.0)
    f.add_argument("--duck", type=float, default=-12.0); f.add_argument("--subtitles"); f.add_argument("--sfx-cues"); f.add_argument("--overlay", action="append", help="PNG[@x,y]")
    f.add_argument("--keep-source-audio", action="store_true"); f.add_argument("--background", default="#000000"); f.add_argument("--end-card"); f.add_argument("--ai-dir")
    f.set_defaults(fn=cmd_from_beats)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
