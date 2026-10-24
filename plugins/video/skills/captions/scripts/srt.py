#!/usr/bin/env python3
"""srt: make, reflow, shift and convert subtitle cues.

Usage:
  srt.py from-text TEXT.txt --duration S -o cues.srt [--max-chars 32] [--start 0]
  srt.py from-whisper transcript.json -o cues.srt [--max-chars 32] [--words-out words.json]
  srt.py split IN.srt -o OUT.srt [--max-chars 32]
  srt.py shift IN.srt --by SECONDS -o OUT.srt
  srt.py to-ass IN.srt -o OUT.ass --width W --height H [--style social|clean|minimal|karaoke|top]
         [--font NAME] [--size PX] [--accent '#FFD400'] [--margin-bottom PX] [--margin-side PX]
         [--words words.json] [--rtl]
  srt.py info IN.srt

Shared flags (--json, --dry-run, …) go after the subcommand. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, common_flags, finish, main_guard  # noqa: E402

TIME_RE = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")
GAP_S = 0.15


# ---------- SRT read / write ----------

def parse_time(s: str) -> float:
    m = TIME_RE.search(s)
    if not m:
        raise Failure("input", f"bad SRT timestamp: {s!r}")
    h, mi, se, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(se) + int(ms.ljust(3, "0")) / 1000


def fmt_time(t: float) -> str:
    ms = int(round(max(0.0, t) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def read_srt(path: str) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8-sig") if Path(path).is_file() else None
    if text is None:
        raise Failure("input", f"{path} does not exist")
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        idx = 1 if "-->" in lines[1] else 0
        if "-->" not in lines[idx]:
            continue
        a, b = lines[idx].split("-->")
        cues.append({"start": parse_time(a), "end": parse_time(b), "text": "\n".join(lines[idx + 1:]).strip()})
    return cues


def write_srt(cues: list[dict], path: str, dry_run: bool) -> None:
    out = []
    for i, c in enumerate(cues, start=1):
        out.append(f"{i}\n{fmt_time(c['start'])} --> {fmt_time(c['end'])}\n{c['text']}\n")
    if not dry_run:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")


# ---------- text helpers ----------

def wrap(text: str, max_chars: int, max_lines: int = 2) -> list[str]:
    """Greedy wrap; returns up to max_lines lines (the last one takes the overflow)."""
    lines, line = [], ""
    for w in text.replace("\n", " ").split():
        if line and len(line) + 1 + len(w) > max_chars:
            lines.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [" ".join(lines[max_lines - 1:])]
    return lines


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+", text.replace("\n", " ").strip())
    return [p.strip() for p in parts if p.strip()]


def chunk_words(sentence: str, max_chars: int) -> list[str]:
    """Split a sentence into cue-sized chunks (two lines of max_chars each)."""
    chunks, cur = [], ""
    for w in sentence.split():
        if cur and len(cur) + 1 + len(w) > max_chars * 2 - 4:
            chunks.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        chunks.append(cur)
    return chunks


# ---------- commands ----------

def cmd_from_text(a) -> int:
    text = Path(a.text).read_text(encoding="utf-8") if Path(a.text).is_file() else a.text
    chunks = [c for s in sentences(text) for c in chunk_words(s, a.max_chars)]
    if not chunks:
        raise Failure("input", "no text to time")
    total_words = sum(len(c.split()) for c in chunks)
    usable = max(a.duration - a.start, 1.0)
    t, cues = a.start, []
    for c in chunks:
        share = len(c.split()) / total_words * usable
        dur = max(0.8, share - GAP_S)
        cues.append({"start": round(t, 3), "end": round(t + dur, 3), "text": "\n".join(wrap(c, a.max_chars))})
        t += share
    write_srt(cues, a.output, a.dry_run)
    return finish({"status": "ok", "output": a.output, "cues": len(cues), "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(cues)} cues over {a.duration} s")


def cmd_from_whisper(a) -> int:
    doc = json.loads(Path(a.transcript).read_text(encoding="utf-8"))
    # whisper.cpp (-oj): {"transcription":[{"timestamps":{"from","to"},"offsets":{"from","to"} (ms),"text", "tokens"?}]}
    # faster-whisper / whisper-ctranslate2 json: {"segments":[{"start","end","text","words":[{"start","end","word"}]}]}
    segs, words = [], []
    if "segments" in doc:
        for s in doc["segments"]:
            segs.append({"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip()})
            for w in s.get("words") or []:
                words.append({"start": float(w["start"]), "end": float(w["end"]), "word": w["word"].strip()})
    elif "transcription" in doc:
        for s in doc["transcription"]:
            off = s.get("offsets") or {}
            segs.append({"start": off.get("from", 0) / 1000, "end": off.get("to", 0) / 1000, "text": s["text"].strip()})
            for tk in s.get("tokens") or []:
                o = tk.get("offsets") or {}
                if tk.get("text", "").startswith("[_"):
                    continue
                words.append({"start": o.get("from", 0) / 1000, "end": o.get("to", 0) / 1000, "word": tk["text"]})
    else:
        raise Failure("input", "unrecognised transcript JSON (expected 'segments' or 'transcription')")
    cues = []
    for s in segs:
        for c in chunk_words(s["text"], a.max_chars):
            share = len(c.split()) / max(1, len(s["text"].split())) * (s["end"] - s["start"])
            start = cues[-1]["end"] + GAP_S if cues and cues[-1]["end"] > s["start"] else s["start"]
            cues.append({"start": round(start, 3), "end": round(start + max(0.6, share - GAP_S), 3), "text": "\n".join(wrap(c, a.max_chars))})
            s["start"] = cues[-1]["end"] + GAP_S
    write_srt(cues, a.output, a.dry_run)
    if a.words_out and words and not a.dry_run:
        Path(a.words_out).write_text(json.dumps({"words": words}, indent=1, ensure_ascii=False), encoding="utf-8")
    return finish({"status": "ok", "output": a.output, "cues": len(cues), "words": len(words), "words_out": a.words_out if words else None,
                   "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(cues)} cues, {len(words)} word timings")


def cmd_split(a) -> int:
    cues, out = read_srt(a.input), []
    for c in cues:
        chunks = chunk_words(c["text"].replace("\n", " "), a.max_chars)
        n = max(1, len(chunks))
        span = (c["end"] - c["start"]) / n
        for i, ch in enumerate(chunks):
            out.append({"start": round(c["start"] + i * span, 3), "end": round(c["start"] + (i + 1) * span - (GAP_S if i < n - 1 else 0), 3),
                        "text": "\n".join(wrap(ch, a.max_chars))})
    write_srt(out, a.output, a.dry_run)
    return finish({"status": "ok", "output": a.output, "cues_in": len(cues), "cues_out": len(out), "dry_run": a.dry_run}, a.json,
                  summary=f"{len(cues)} -> {len(out)} cues, ≤ {a.max_chars} chars/line")


def cmd_shift(a) -> int:
    cues = read_srt(a.input)
    for c in cues:
        c["start"], c["end"] = max(0.0, c["start"] + a.by), max(0.0, c["end"] + a.by)
    write_srt(cues, a.output, a.dry_run)
    return finish({"status": "ok", "output": a.output, "cues": len(cues), "by": a.by, "dry_run": a.dry_run}, a.json,
                  summary=f"shifted {len(cues)} cues by {a.by:+} s -> {a.output}")


def cmd_info(a) -> int:
    cues = read_srt(a.input)
    longest = max((len(ln) for c in cues for ln in c["text"].splitlines()), default=0)
    lines = max((len(c["text"].splitlines()) for c in cues), default=0)
    overlaps = sum(1 for x, y in zip(cues, cues[1:]) if y["start"] < x["end"])
    result = {"status": "ok", "cues": len(cues), "first_s": cues[0]["start"] if cues else None, "last_end_s": cues[-1]["end"] if cues else None,
              "longest_line_chars": longest, "max_lines": lines, "overlapping": overlaps}
    return finish(result, a.json, summary=f"{len(cues)} cues, {result['first_s']}–{result['last_end_s']} s, longest line {longest} chars, max {lines} lines, {overlaps} overlaps")


# ---------- ASS ----------

STYLE_PRESETS = {
    # size factor of height, outline px at 1080p, shadow, border style (1 outline, 3 box), alignment, bold
    "social": {"size": 0.042, "outline": 4, "shadow": 0, "border": 1, "align": 2, "bold": -1},
    "clean": {"size": 0.036, "outline": 2, "shadow": 1, "border": 1, "align": 2, "bold": 0},
    "minimal": {"size": 0.032, "outline": 0, "shadow": 0, "border": 3, "align": 2, "bold": 0},
    "karaoke": {"size": 0.042, "outline": 4, "shadow": 0, "border": 1, "align": 2, "bold": -1},
    "top": {"size": 0.042, "outline": 4, "shadow": 0, "border": 1, "align": 8, "bold": -1},
}


def ass_colour(hex_rgb: str, alpha: int = 0) -> str:
    h = hex_rgb.lstrip("#")
    if len(h) != 6:
        raise Failure("input", f"colour must be #RRGGBB, got {hex_rgb!r}")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ass_time(t: float) -> str:
    cs = int(round(max(0.0, t) * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def emphasis(text: str, accent_tag: str) -> str:
    # *word* -> bold + accent colour, then back
    return re.sub(r"\*(.+?)\*", lambda m: "{\\b1" + accent_tag + "}" + m.group(1) + "{\\b0\\c}", text)


def karaoke_line(cue: dict, words: list[dict]) -> str:
    """Rebuild the cue text with \\k tags from word timings that fall inside the cue."""
    inside = [w for w in words if w["start"] >= cue["start"] - 0.05 and w["end"] <= cue["end"] + 0.05]
    if not inside:
        return ass_escape(cue["text"].replace("\n", "\\N"))
    parts, t = [], cue["start"]
    for w in inside:
        lead = max(0, int(round((w["start"] - t) * 100)))
        dur = max(1, int(round((w["end"] - w["start"]) * 100)))
        if lead:
            parts.append(f"{{\\k{lead}}}")
        parts.append(f"{{\\k{dur}}}{ass_escape(w['word'])} ")
        t = w["end"]
    return "".join(parts).strip()


def cmd_to_ass(a) -> int:
    preset = STYLE_PRESETS[a.style]
    W, H = a.width, a.height
    size = a.size or round(H * preset["size"])
    scale = H / 1080
    outline = round(preset["outline"] * scale, 1)
    margin_v = a.margin_bottom if a.margin_bottom is not None else round(H * 0.06)
    margin_side = a.margin_side if a.margin_side is not None else round(W * 0.05)
    primary = ass_colour(a.accent if a.style == "karaoke" else "#FFFFFF")
    secondary = ass_colour("#FFFFFF") if a.style == "karaoke" else ass_colour("#FFFF00")
    back = ass_colour("#000000", 0x80) if preset["border"] == 3 else ass_colour("#000000", 0x00)
    font = a.font or "DejaVu Sans"
    encoding = 1
    header = "\n".join([
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,{font},{size},{primary},{secondary},{ass_colour('#000000')},{back},{preset['bold']},0,0,0,100,100,0,0,"
        f"{preset['border']},{outline},{preset['shadow']},{preset['align']},{margin_side},{margin_side},{margin_v},{encoding}",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])
    words = json.loads(Path(a.words).read_text(encoding="utf-8")).get("words", []) if a.words else []
    accent_tag = "\\c" + ass_colour(a.accent)
    events = []
    for c in read_srt(a.input):
        if a.style == "karaoke" and words:
            text = karaoke_line(c, words)
        else:
            text = emphasis(ass_escape(c["text"]).replace("\n", "\\N"), accent_tag)
        if a.rtl:
            text = "‫" + text + "‬"
        events.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Cap,,0,0,0,,{text}")
    content = header + "\n" + "\n".join(events) + "\n"
    if not a.dry_run:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(content, encoding="utf-8")
    return finish({"status": "ok", "output": a.output, "events": len(events), "style": a.style, "font": font, "size": size,
                   "margin_v": margin_v, "margin_side": margin_side, "karaoke": bool(a.style == "karaoke" and words), "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(events)} events, {a.style}, {font} {size}px, bottom margin {margin_v}px")


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Make, reflow, shift and convert subtitle cues. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    ft = sub.add_parser("from-text", parents=cf); ft.add_argument("text", help="text file or literal text"); ft.add_argument("--duration", type=float, required=True)
    ft.add_argument("-o", "--output", required=True); ft.add_argument("--max-chars", type=int, default=32); ft.add_argument("--start", type=float, default=0.0); ft.set_defaults(fn=cmd_from_text)
    fw = sub.add_parser("from-whisper", parents=cf); fw.add_argument("transcript"); fw.add_argument("-o", "--output", required=True)
    fw.add_argument("--max-chars", type=int, default=32); fw.add_argument("--words-out"); fw.set_defaults(fn=cmd_from_whisper)
    sp = sub.add_parser("split", parents=cf); sp.add_argument("input"); sp.add_argument("-o", "--output", required=True); sp.add_argument("--max-chars", type=int, default=32); sp.set_defaults(fn=cmd_split)
    sh = sub.add_parser("shift", parents=cf); sh.add_argument("input"); sh.add_argument("--by", type=float, required=True); sh.add_argument("-o", "--output", required=True); sh.set_defaults(fn=cmd_shift)
    inf = sub.add_parser("info", parents=cf); inf.add_argument("input"); inf.set_defaults(fn=cmd_info)
    ta = sub.add_parser("to-ass", parents=cf); ta.add_argument("input"); ta.add_argument("-o", "--output", required=True)
    ta.add_argument("--width", type=int, required=True); ta.add_argument("--height", type=int, required=True)
    ta.add_argument("--style", default="social", choices=sorted(STYLE_PRESETS)); ta.add_argument("--font"); ta.add_argument("--size", type=int)
    ta.add_argument("--accent", default="#FFD400"); ta.add_argument("--margin-bottom", type=int); ta.add_argument("--margin-side", type=int)
    ta.add_argument("--words", help="word timings JSON (from from-whisper --words-out) for karaoke"); ta.add_argument("--rtl", action="store_true"); ta.set_defaults(fn=cmd_to_ass)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
