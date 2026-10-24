#!/usr/bin/env python3
"""script: validate, time and export beats.json (see references/beats.md).

Usage:
  script.py outline --intent promo --duration 30 [--json]          print a beat skeleton to write from
  script.py time BEATS [--wpm 150] [--target S] [--measured] [--write] [--json]
  script.py validate BEATS [--json]
  script.py srt BEATS -o voice.srt [--max-chars 38]               voice lines as SRT cues at beat timing

Standard library only. Exit 0 ok, 1 invalid, 2 usage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import EXIT_FAIL, Failure, common_flags, finish, main_guard  # noqa: E402

PURPOSES = {"hook", "problem", "solution", "feature", "proof", "step", "recap", "cta", "title", "transition", "free",
            "question", "answer", "context", "outcome", "example", "takeaway", "world", "tension", "reveal", "chapter", "closer"}
VOICE_MODES = {"tts", "recording", "original", "none"}
MIN_BEAT_S = 1.2
BREATH_S = 0.35

STRUCTURES = {
    "promo": ["hook", "problem", "solution", "feature", "feature", "proof", "cta"],
    "ad": ["hook", "problem", "solution", "feature", "proof", "cta"],
    "product-demo": ["hook", "context", "step", "step", "step", "outcome", "cta"],
    "explainer": ["question", "answer", "step", "step", "step", "example", "takeaway"],
    "tutorial": ["hook", "context", "step", "step", "step", "step", "recap"],
    "social-short": ["hook", "feature", "feature", "cta"],
    "trailer": ["title", "world", "world", "tension", "tension", "reveal", "title"],
    "highlight-reel": ["hook", "chapter", "chapter", "chapter", "closer"],
    "testimonial": ["hook", "context", "problem", "outcome", "cta"],
    "slideshow": ["title", "chapter", "chapter", "chapter", "closer"],
    "kinetic-quote": ["hook", "feature", "feature", "cta"],
}


def words(text: str) -> int:
    return len([w for w in re.split(r"\s+", (text or "").strip()) if w])


def load(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise Failure("input", f"{path} does not exist")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Failure("input", f"{path} is not valid JSON: {e}")


def estimate(beat: dict, wpm: float, measured: bool) -> float:
    if measured and isinstance(beat.get("measured_voice_s"), (int, float)):
        return max(MIN_BEAT_S, float(beat["measured_voice_s"]) + 0.3)
    v = words(beat.get("voice", ""))
    if v:
        return max(MIN_BEAT_S, v / (wpm / 60.0) + BREATH_S)
    o = words(beat.get("on_screen", ""))
    if o:
        return max(1.5, 0.4 * o + 0.8)
    return max(MIN_BEAT_S, float(beat.get("duration_s") or MIN_BEAT_S))


def reflow(beats: list[dict]) -> None:
    t = 0.0
    for b in beats:
        b["start_s"] = round(t, 3)
        t += float(b["duration_s"])


def validate(doc: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    for key in ("studio_beats", "language", "wpm", "target_duration_s", "aspect", "voice", "music", "beats"):
        if key not in doc:
            errors.append(f"missing '{key}'")
    beats = doc.get("beats") or []
    if not beats:
        errors.append("beats is empty")
        return errors, warnings
    mode = (doc.get("voice") or {}).get("mode")
    if mode not in VOICE_MODES:
        errors.append(f"voice.mode '{mode}' not in {sorted(VOICE_MODES)}")
    if mode == "tts" and not (doc.get("voice") or {}).get("voice"):
        warnings.append("voice.mode is tts but voice.voice names no voice; audio:voice will pick the engine default")
    aspect = str(doc.get("aspect", "16:9"))
    max_words = 7 if aspect == "16:9" else 5
    ids, t = set(), 0.0
    for i, b in enumerate(beats, start=1):
        bid = b.get("id", f"#{i}")
        if bid in ids:
            errors.append(f"beat {bid}: duplicate id")
        ids.add(bid)
        if b.get("purpose") not in PURPOSES:
            warnings.append(f"beat {bid}: purpose '{b.get('purpose')}' is not a known purpose")
        if not isinstance(b.get("duration_s"), (int, float)) or b["duration_s"] < MIN_BEAT_S - 1e-6:
            errors.append(f"beat {bid}: duration_s must be ≥ {MIN_BEAT_S} s (run `script.py time`)")
        if abs(float(b.get("start_s", -1)) - t) > 0.01:
            errors.append(f"beat {bid}: start_s {b.get('start_s')} is not contiguous (expected {t:.3f}); run `script.py time --write`")
        t += float(b.get("duration_s") or 0)
        vis = b.get("visual") or {}
        if not vis.get("source"):
            errors.append(f"beat {bid}: visual.source is empty — an empty visual becomes a black beat")
        if b.get("voice") and "caption" not in b:
            errors.append(f"beat {bid}: has a voice line but no caption flag")
        if mode == "none" and b.get("voice"):
            errors.append(f"beat {bid}: voice.mode is none but the beat has a voice line")
        o = words(b.get("on_screen", ""))
        if o > max_words:
            errors.append(f"beat {bid}: on_screen has {o} words; max {max_words} for {aspect}")
        if (b.get("on_screen") or "").count("\n") > 1:
            errors.append(f"beat {bid}: on_screen has more than two lines")
    target = float(doc.get("target_duration_s") or 0)
    if target and abs(t - target) > 0.10 * target:
        warnings.append(f"total {t:.1f} s is more than 10 % from target {target:.0f} s")
    return errors, warnings


def srt_time(s: float) -> str:
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def wrap_cue(text: str, max_chars: int) -> str:
    out, line = [], ""
    for w in text.split():
        if line and len(line) + 1 + len(w) > max_chars:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return "\n".join(out[:2]) if len(out) <= 2 else "\n".join([" ".join(out[:-1]), out[-1]])


def cmd_outline(a) -> int:
    key = a.intent.lower().replace("_", "-")
    if key not in STRUCTURES:
        raise Failure("input", f"unknown intent '{a.intent}'", "one of: " + ", ".join(sorted(STRUCTURES)))
    purposes = STRUCTURES[key]
    per = a.duration / len(purposes)
    beats = []
    t = 0.0
    for i, p in enumerate(purposes, start=1):
        d = round(max(MIN_BEAT_S, per * (0.7 if p in ("hook", "title", "transition") else 1.0)), 1)
        beats.append({"id": f"b{i}", "purpose": p, "start_s": round(t, 3), "duration_s": d, "voice": "",
                      "on_screen": "", "visual": {"source": "", "in_s": 0, "focus": [0.5, 0.5], "zoom": 1.0, "motion": "hold"},
                      "caption": True, "sfx": None, "transition": "cut"})
        t += d
    doc = {"studio_beats": "0.1", "title": "", "language": "en", "wpm": 150, "target_duration_s": a.duration,
           "aspect": a.aspect, "voice": {"mode": "tts", "voice": "", "rate": 1.0},
           "music": {"mood": "upbeat", "duck_db": -12, "file": None}, "beats": beats, "cta": {"text": "", "url_on_screen": ""}}
    summary = "\n".join(f"{b['id']:4} {b['purpose']:10} ~{b['duration_s']} s" for b in beats)
    return finish({"status": "ok", "outline": doc}, a.json, summary=f"{key}: {len(beats)} beats for {a.duration} s\n{summary}\n(use --json for the skeleton to fill)")


def cmd_time(a) -> int:
    doc = load(a.beats)
    wpm = float(a.wpm or doc.get("wpm") or 150)
    changed = []
    for b in doc.get("beats") or []:
        new = round(estimate(b, wpm, a.measured), 2)
        if abs(new - float(b.get("duration_s") or 0)) > 0.05:
            changed.append(f"{b.get('id')}: {b.get('duration_s')} -> {new}")
        b["duration_s"] = new
    reflow(doc["beats"])
    total = round(sum(float(b["duration_s"]) for b in doc["beats"]), 2)
    target = float(a.target or doc.get("target_duration_s") or 0)
    if a.target:
        doc["target_duration_s"] = a.target
    doc["wpm"] = wpm
    spoken = sum(words(b.get("voice", "")) for b in doc["beats"])
    delta = round(total - target, 2) if target else None
    advice = ""
    if target and abs(delta) > 0.1 * target:
        longest = sorted(doc["beats"], key=lambda b: -float(b["duration_s"]))[:2]
        advice = (f"over by {delta:+.1f} s: cut words in " if delta > 0 else f"under by {delta:+.1f} s: let visuals breathe in ") \
            + ", ".join(b["id"] for b in longest)
    if a.write and not a.dry_run:
        Path(a.beats).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result = {"status": "ok", "output": a.beats if a.write else None, "total_s": total, "target_s": target or None,
              "delta_s": delta, "spoken_words": spoken, "wpm": wpm, "changed": changed, "advice": advice, "written": bool(a.write and not a.dry_run)}
    summary = f"{len(doc['beats'])} beats, {total} s at {wpm:g} wpm" + (f" (target {target:g} s, {delta:+.1f} s)" if target else "") \
        + f", {spoken} spoken words" + (f"\n{advice}" if advice else "") + ("" if a.write else "\n(not written; add --write)")
    return finish(result, a.json, summary=summary)


def cmd_validate(a) -> int:
    doc = load(a.beats)
    errors, warnings = validate(doc)
    result = {"status": "ok" if not errors else "failed", "file": a.beats, "errors": errors, "warnings": warnings,
              "beats": len(doc.get("beats") or []), "total_s": round(sum(float(b.get("duration_s") or 0) for b in doc.get("beats") or []), 2)}
    if errors:
        result["error"] = {"kind": "invalid", "message": "; ".join(errors)}
    text = ("ok" if not errors else "INVALID:\n  " + "\n  ".join(errors)) + ("\nwarnings:\n  " + "\n  ".join(warnings) if warnings else "")
    code = finish(result, a.json, summary=text)
    return code if not errors else EXIT_FAIL


def cmd_srt(a) -> int:
    doc = load(a.beats)
    cues, n = [], 0
    for b in doc.get("beats") or []:
        if not b.get("voice") or not b.get("caption", True):
            continue
        n += 1
        start, end = float(b["start_s"]), float(b["start_s"]) + float(b["duration_s"]) - 0.15
        cues.append(f"{n}\n{srt_time(start)} --> {srt_time(max(start + 0.5, end))}\n{wrap_cue(b['voice'], a.max_chars)}\n")
    text = "\n".join(cues) + ("\n" if cues else "")
    if not a.dry_run:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(text, encoding="utf-8")
    return finish({"status": "ok", "output": a.output, "cues": n, "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {n} cues")


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Validate, time and export beats.json. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    o = sub.add_parser("outline", parents=cf, help="beat skeleton for an intent and length")
    o.add_argument("--intent", required=True); o.add_argument("--duration", type=float, required=True); o.add_argument("--aspect", default="9:16"); o.set_defaults(fn=cmd_outline)
    t = sub.add_parser("time", parents=cf, help="compute durations from the text and reflow")
    t.add_argument("beats"); t.add_argument("--wpm", type=float); t.add_argument("--target", type=float)
    t.add_argument("--measured", action="store_true", help="prefer measured_voice_s from audio:voice"); t.add_argument("--write", action="store_true"); t.set_defaults(fn=cmd_time)
    v = sub.add_parser("validate", parents=cf, help="check the file against references/beats.md"); v.add_argument("beats"); v.set_defaults(fn=cmd_validate)
    s = sub.add_parser("srt", parents=cf, help="voice lines as SRT cues"); s.add_argument("beats"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--max-chars", type=int, default=38); s.set_defaults(fn=cmd_srt)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
