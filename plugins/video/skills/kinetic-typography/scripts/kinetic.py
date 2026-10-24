#!/usr/bin/env python3
"""kinetic: split text into readable beats with emphasis, timing and a background → beats.json.

Usage:  kinetic.py plan --text "…" | --file text.txt -o beats.json [--target 20] [--words-per-beat 3] [--attribution "— Name"]
                   [--aspect 9:16] [--bg '#0b0f19'|gradient|image:PATH|footage:PATH] [--voice] [--language en] [--music calm|upbeat|none]

Pure Python; the beats go through script.py validate and, with --voice, audio:voice → script.py time --measured.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, common_flags, finish, main_guard  # noqa: E402

STOP = {"a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at", "for", "is", "are", "was", "were", "be", "it", "that", "this", "with", "as", "by", "from", "not", "so", "if", "than", "then"}


def phrases(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?<=[.!?;:,—–-])\s+|\s+[—–]\s+", text)
    return [p.strip() for p in parts if p and p.strip()]


def group(words: list[str], per: int) -> list[list[str]]:
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= per:
            out.append(cur)
            cur = []
    if cur:
        if out and len(cur) == 1 and len(out[-1]) < 5:
            out[-1] += cur
        else:
            out.append(cur)
    return out


def emphasise(words: list[str]) -> list[str]:
    cands = [(i, w) for i, w in enumerate(words) if re.sub(r"[^\w]", "", w).lower() not in STOP]
    if not cands:
        return words
    # a number wins; else the longest content word
    num = [(i, w) for i, w in cands if re.search(r"\d", w)]
    i, w = (num[0] if num else max(cands, key=lambda iw: len(re.sub(r"[^\w]", "", iw[1]))))
    core = re.match(r"^(\W*)(.*?)(\W*)$", w)
    out = list(words)
    out[i] = f"{core.group(1)}*{core.group(2)}*{core.group(3)}" if core and core.group(2) else f"*{w}*"
    return out


def hold_for(words: list[str], aspect: str) -> float:
    n = len(words)
    h = max(1.5, 0.4 * n + 0.8)
    if any(re.search(r"\d", w) for w in words):
        h *= 1.3
    if n == 1:
        h = max(h, 1.2)
    return round(h, 2)


def cmd_plan(a) -> int:
    text = Path(a.file).read_text(encoding="utf-8") if a.file else (a.text or "")
    if not text.strip():
        raise Failure("input", "no text (--text or --file)")
    max_chars = 14 if a.aspect != "16:9" else 24
    beats = []
    for ph in phrases(text):
        words = ph.split()
        per = a.words_per_beat
        groups = group(words, per)
        # keep each beat's line under the character limit by splitting long groups
        fixed = []
        for g in groups:
            if len(" ".join(g)) > max_chars * 2 and len(g) > 2:
                half = len(g) // 2
                fixed += [g[:half], g[half:]]
            else:
                fixed.append(g)
        beats += fixed
    if a.bg.startswith("image:"):
        visual = {"source": a.bg, "focus": [0.5, 0.5], "zoom": 1.08, "motion": "ken-burns", "fit": "cover", "darken": 0.25}
    elif a.bg.startswith("footage:"):
        visual = {"source": a.bg[8:], "in_s": 0, "focus": [0.5, 0.5], "zoom": 1.0, "motion": "hold", "fit": "cover", "darken": 0.25}
    elif a.bg == "gradient":
        visual = {"source": "color:#141821", "gradient": True}
    else:
        visual = {"source": f"color:{a.bg}"}
    doc_beats, t = [], 0.0
    for i, g in enumerate(beats, start=1):
        h = hold_for(g, a.aspect)
        line = " ".join(emphasise(g))
        doc_beats.append({"id": f"k{i}", "purpose": "hook" if i == 1 else "feature", "start_s": round(t, 3), "duration_s": h,
                          "voice": " ".join(g) if a.voice else "", "on_screen": line, "visual": dict(visual), "caption": bool(a.voice), "transition": "cut"})
        t += h
    if a.attribution:
        doc_beats.append({"id": "attr", "purpose": "cta", "start_s": round(t, 3), "duration_s": 2.5, "voice": "", "on_screen": a.attribution,
                          "visual": dict(visual), "caption": False, "transition": "dissolve"})
        t += 2.5
    if a.target:
        body = sum(b["duration_s"] for b in doc_beats)
        f = a.target / body
        if f < 1.0 or f > 1.6:
            for b in doc_beats:
                b["duration_s"] = round(max(1.2, b["duration_s"] * max(f, 0.75)), 2)
        tt = 0.0
        for b in doc_beats:
            b["start_s"] = round(tt, 3)
            tt += b["duration_s"]
        t = tt
    doc = {"studio_beats": "0.1", "title": text[:60], "language": a.language, "wpm": 150, "target_duration_s": a.target or round(t, 1), "aspect": a.aspect,
           "voice": {"mode": "tts" if a.voice else "none", "voice": "", "rate": 1.0}, "music": {"mood": a.music, "duck_db": -12, "file": None},
           "beats": doc_beats, "cta": {"text": a.attribution or "", "url_on_screen": ""}, "kinetic": {"bg": a.bg, "reveal": "word" if a.aspect != "16:9" else "line"}}
    if not a.dry_run:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [f"  {b['id']:5} {b['duration_s']:4.1f}s  {b['on_screen']}" for b in doc_beats]
    return finish({"status": "ok", "output": a.output, "beats": len(doc_beats), "total_s": round(t, 2), "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(doc_beats)} beats, {t:.1f} s\n" + "\n".join(lines))


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Text → kinetic beats. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan", parents=[common_flags()])
    pl.add_argument("--text"); pl.add_argument("--file"); pl.add_argument("-o", "--output", required=True); pl.add_argument("--target", type=float)
    pl.add_argument("--words-per-beat", type=int, default=3); pl.add_argument("--attribution"); pl.add_argument("--aspect", default="9:16")
    pl.add_argument("--bg", default="#0b0f19"); pl.add_argument("--voice", action="store_true"); pl.add_argument("--language", default="en")
    pl.add_argument("--music", default="calm", choices=["calm", "upbeat", "cinematic", "none"]); pl.set_defaults(fn=cmd_plan)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
