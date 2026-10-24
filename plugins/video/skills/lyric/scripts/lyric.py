#!/usr/bin/env python3
"""lyric: lyric lines → timed beats (LRC, aligned words, or section spread); align; shift.

Usage:
  lyric.py plan --lyrics lyrics.txt --audio song.mp3 -o beats.json [--lrc timings.lrc | --words song.words.json | --sections "0:12 verse, 0:48 chorus"]
           [--aspect 16:9] [--visual footage:PATH|image:PATH|gradient|ai] [--language en] [--section chorus]
  lyric.py align --lyrics lyrics.txt --words song.words.json -o aligned.lrc
  lyric.py shift BEATS.json --by SECONDS [-o out.json]

Pure Python except the audio probe. Shared flags go after the subcommand.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, common_flags, ffprobe, finish, main_guard  # noqa: E402

LRC_LINE = re.compile(r"^\[(\d+):(\d{2}(?:\.\d{1,3})?)\](.*)$")
LRC_WORD = re.compile(r"<(\d+):(\d{2}(?:\.\d{1,3})?)>")


def norm(w: str) -> str:
    return re.sub(r"[^\w']", "", w.lower())


def lev(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def read_lyrics(path: str) -> list[str]:
    return [ln.rstrip() for ln in Path(path).read_text(encoding="utf-8").splitlines()]


def parse_lrc(path: str) -> list[dict]:
    out = []
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        m = LRC_LINE.match(ln.strip())
        if not m:
            continue
        start = int(m.group(1)) * 60 + float(m.group(2))
        text = m.group(3).strip()
        words = []
        if LRC_WORD.search(text):
            parts = LRC_WORD.split(text)
            # parts: [pre, mm, ss, word, mm, ss, word, ...]
            i = 1
            while i + 2 < len(parts) + 1 and i + 2 <= len(parts):
                t = int(parts[i]) * 60 + float(parts[i + 1])
                w = parts[i + 2].strip() if i + 2 < len(parts) else ""
                if w:
                    words.append({"start": t, "word": w})
                i += 3
            text = re.sub(LRC_WORD, "", text).strip()
            for k, w in enumerate(words):
                w["end"] = words[k + 1]["start"] - 0.05 if k + 1 < len(words) else w["start"] + 0.6
        if text:
            out.append({"start": start, "text": text, "words": words, "timing": "lrc"})
    for k, c in enumerate(out):
        c["end"] = min(out[k + 1]["start"] - 0.2, c["start"] + 6.0) if k + 1 < len(out) else c["start"] + 4.0
    return out


def align(lines: list[str], words: list[dict]) -> tuple[list[dict], float]:
    wi, out, matched_total, words_total = 0, [], 0, 0
    for ln in lines:
        if not ln.strip():
            continue
        toks = [norm(w) for w in ln.split() if norm(w)]
        words_total += len(toks)
        first = last = None
        matched = 0
        j = wi
        for tok in toks:
            # look ahead a little for the token
            for k in range(j, min(j + 6, len(words))):
                if lev(norm(words[k]["word"]), tok) <= (2 if len(tok) > 4 else 1):
                    first = words[k]["start"] if first is None else first
                    last = words[k]["end"]
                    matched += 1
                    j = k + 1
                    break
        matched_total += matched
        if first is not None and matched >= max(1, int(0.6 * len(toks))):
            out.append({"start": first, "end": last, "text": ln.strip(), "timing": "aligned", "matched": matched, "of": len(toks)})
            wi = j
        else:
            out.append({"start": None, "end": None, "text": ln.strip(), "timing": "interpolated", "matched": matched, "of": len(toks)})
    # interpolate the unmatched between neighbours
    for i, c in enumerate(out):
        if c["start"] is None:
            prev = next((x for x in reversed(out[:i]) if x["start"] is not None), None)
            nxt = next((x for x in out[i + 1:] if x["start"] is not None), None)
            if prev and nxt:
                gap_lines = [x for x in out[out.index(prev) + 1:out.index(nxt)]]
                span = (nxt["start"] - prev["end"]) / (len(gap_lines) + 1)
                idx = gap_lines.index(c) + 1
                c["start"], c["end"] = prev["end"] + span * (idx - 1) + 0.1, prev["end"] + span * idx - 0.1
            elif prev:
                c["start"], c["end"] = prev["end"] + 0.3, prev["end"] + 3.5
            elif nxt:
                c["start"], c["end"] = max(0.0, nxt["start"] - 3.5), nxt["start"] - 0.3
            else:
                c["start"], c["end"] = 0.0, 3.0
    rate = matched_total / words_total if words_total else 0.0
    return out, rate


def parse_sections(spec: str) -> list[tuple[float, str]]:
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        ts, _, name = part.partition(" ")
        m, s = ts.split(":")
        out.append((int(m) * 60 + float(s), name.strip() or "section"))
    return sorted(out)


def cmd_plan(a) -> int:
    lines = read_lyrics(a.lyrics)
    p = ffprobe(a.audio, a.timeout)
    duration = p["duration"]
    if a.lrc:
        cues = parse_lrc(a.lrc)
        source = "lrc"
    elif a.words:
        words = json.loads(Path(a.words).read_text(encoding="utf-8")).get("words", [])
        cues, rate = align(lines, words)
        source = f"aligned ({rate:.0%} words matched)"
        for c in cues:
            c["words"] = []
    elif a.sections:
        secs = parse_sections(a.sections)
        blocks = [b for b in re.split(r"\n\s*\n", "\n".join(lines).strip()) if b.strip()]
        if len(blocks) != len(secs):
            raise Failure("input", f"{len(blocks)} lyric blocks (separated by blank lines) but {len(secs)} sections")
        cues = []
        for i, (block, (start, name)) in enumerate(zip(blocks, secs)):
            end = secs[i + 1][0] if i + 1 < len(secs) else duration
            bl = [ln for ln in block.splitlines() if ln.strip()]
            span = (end - start) / max(1, len(bl))
            for k, ln in enumerate(bl):
                cues.append({"start": start + k * span, "end": start + (k + 1) * span - 0.2, "text": ln.strip(), "timing": "spread", "section": name, "words": []})
        source = "spread (approximate)"
    else:
        raise Failure("input", "a timing source is needed: --lrc, --words (aligned) or --sections")
    if a.section:
        cues = [c for c in cues if (c.get("section") or "").lower() == a.section.lower()] or cues
    # visuals
    if a.visual.startswith("footage:"):
        visual = {"source": a.visual[8:], "in_s": 0, "focus": [0.5, 0.5], "zoom": 1.08, "motion": "push-in", "fit": "cover", "darken": 0.25}
    elif a.visual.startswith("image:"):
        visual = {"source": a.visual, "focus": [0.5, 0.5], "zoom": 1.06, "motion": "ken-burns", "fit": "cover", "darken": 0.25}
    elif a.visual == "ai":
        visual = {"source": "ai:section", "fit": "cover", "darken": 0.2}
    else:
        visual = {"source": "color:#141821", "gradient": True}
    beats, t = [], 0.0
    if cues and cues[0]["start"] > 0.1:
        # the intro before the first sung line is a visual-only beat so the timeline starts at 0
        beats.append({"id": "intro", "purpose": "title", "start_s": 0.0, "duration_s": round(cues[0]["start"], 3), "voice": "", "on_screen": "",
                      "visual": dict(visual), "caption": False, "transition": "cut", "timing": "gap"})
        t = cues[0]["start"]
    for i, c in enumerate(cues):
        if c["start"] - t > 4.0:
            beats.append({"id": f"gap{i}", "purpose": "transition", "start_s": round(t, 3), "duration_s": round(c["start"] - t, 3), "voice": "", "on_screen": "",
                          "visual": dict(visual), "caption": False, "transition": "cut", "timing": "gap"})
            t = c["start"]
        elif c["start"] > t:
            # tiny gap: extend the previous beat
            if beats:
                beats[-1]["duration_s"] = round(beats[-1]["duration_s"] + (c["start"] - t), 3)
            t = c["start"]
        dur = max(1.0, c["end"] - c["start"])
        v = dict(visual)
        if a.visual == "ai":
            v["source"] = f"ai:{c.get('section') or 'song'}"
        b = {"id": f"l{i + 1}", "purpose": "chapter", "start_s": round(t, 3), "duration_s": round(dur, 3), "voice": "", "on_screen": c["text"],
             "visual": v, "caption": False, "transition": "cut", "timing": c.get("timing"), "lyric_words": c.get("words") or []}
        beats.append(b)
        t += dur
    if duration - t > 0.5:
        beats.append({"id": "outro", "purpose": "closer", "start_s": round(t, 3), "duration_s": round(duration - t, 3), "voice": "", "on_screen": "", "visual": dict(visual), "caption": False, "transition": "dissolve"})
    doc = {"studio_beats": "0.1", "title": Path(a.lyrics).stem, "language": a.language, "wpm": 150, "target_duration_s": round(duration, 1), "aspect": a.aspect,
           "voice": {"mode": "none", "voice": "", "rate": 1.0}, "music": {"mood": "song", "duck_db": 0, "file": a.audio}, "beats": beats,
           "cta": {"text": "", "url_on_screen": ""}, "lyric": {"timing_source": source, "karaoke_possible": all(b.get("lyric_words") for b in beats if b["purpose"] == "chapter")}}
    if not a.dry_run:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_lines = sum(1 for b in beats if b["purpose"] == "chapter")
    return finish({"status": "ok", "output": a.output, "lines": n_lines, "beats": len(beats), "timing_source": source, "karaoke_possible": doc["lyric"]["karaoke_possible"], "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {n_lines} lyric lines over {duration} s, timing {source}" + (", karaoke possible" if doc["lyric"]["karaoke_possible"] else ", line reveal only"))


def cmd_align(a) -> int:
    lines = read_lyrics(a.lyrics)
    words = json.loads(Path(a.words).read_text(encoding="utf-8")).get("words", [])
    cues, rate = align(lines, words)
    out = []
    for c in cues:
        m, s = divmod(c["start"], 60)
        out.append(f"[{int(m):02d}:{s:05.2f}]{c['text']}")
    if not a.dry_run:
        Path(a.output).write_text("\n".join(out) + "\n", encoding="utf-8")
    interp = sum(1 for c in cues if c["timing"] == "interpolated")
    return finish({"status": "ok", "output": a.output, "lines": len(cues), "match_rate": round(rate, 3), "interpolated": interp, "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(cues)} lines, {rate:.0%} words matched, {interp} interpolated" + ("\nmatch rate under 70 %: timing is rough — offer the typed-timing route" if rate < 0.7 else ""))


def cmd_shift(a) -> int:
    doc = json.loads(Path(a.beats).read_text(encoding="utf-8"))
    for b in doc["beats"]:
        b["start_s"] = round(max(0.0, b["start_s"] + a.by), 3)
        for w in b.get("lyric_words") or []:
            w["start"] = max(0.0, w["start"] + a.by); w["end"] = max(0.0, w["end"] + a.by)
    out = a.output or a.beats
    if not a.dry_run:
        Path(out).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return finish({"status": "ok", "output": out, "by": a.by, "dry_run": a.dry_run}, a.json, summary=f"shifted {len(doc['beats'])} beats by {a.by:+} s -> {out}")


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Lyric timing → beats. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    pl = sub.add_parser("plan", parents=cf); pl.add_argument("--lyrics", required=True); pl.add_argument("--audio", required=True); pl.add_argument("-o", "--output", required=True)
    pl.add_argument("--lrc"); pl.add_argument("--words"); pl.add_argument("--sections"); pl.add_argument("--aspect", default="16:9"); pl.add_argument("--visual", default="gradient")
    pl.add_argument("--language", default="en"); pl.add_argument("--section"); pl.set_defaults(fn=cmd_plan)
    al = sub.add_parser("align", parents=cf); al.add_argument("--lyrics", required=True); al.add_argument("--words", required=True); al.add_argument("-o", "--output", required=True); al.set_defaults(fn=cmd_align)
    sh = sub.add_parser("shift", parents=cf); sh.add_argument("beats"); sh.add_argument("--by", type=float, required=True); sh.add_argument("-o", "--output"); sh.set_defaults(fn=cmd_shift)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
