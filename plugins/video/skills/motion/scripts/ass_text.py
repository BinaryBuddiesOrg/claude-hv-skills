#!/usr/bin/env python3
"""ass_text: animated on-screen text as ASS — beat lines, titles, lower thirds, end cards; merge ASS files.

Usage:
  ass_text.py beats BEATS.json -o text.ass --width W --height H [--style kinetic|clean] [--reveal word|line]
              [--position center|lower|upper] [--safe instagram-reels] [--font NAME] [--accent '#FFD400'] [--size PX]
  ass_text.py title --text "…" [--subtitle "…"] --start S --end E -o title.ass --width W --height H [--font] [--accent]
  ass_text.py lower-third --name "…" [--role "…"] --start S --end E -o lt.ass --width W --height H [--font] [--accent]
  ass_text.py end-card --text "…" [--url "…"] --start S --end E -o end.ass --width W --height H [--font] [--accent]
  ass_text.py merge A.ass B.ass [...] -o merged.ass

Pure Python. Shared flags (--json, --dry-run) go after the subcommand.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, common_flags, finish, main_guard  # noqa: E402

DESTINATIONS = Path(__file__).resolve().parent.parent.parent / "platform-export" / "assets" / "destinations.json"
FMT = ("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
       "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
EVFMT = "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"


def colour(hex_rgb: str, alpha: int = 0) -> str:
    h = hex_rgb.lstrip("#")
    if len(h) != 6:
        raise Failure("input", f"colour must be #RRGGBB, got {hex_rgb!r}")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def t(s: float) -> str:
    cs = int(round(max(0.0, s) * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    sec, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def header(W: int, H: int, styles: list[str]) -> str:
    return "\n".join(["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
                      "[V4+ Styles]", FMT] + styles + ["", "[Events]", EVFMT])


def style(name: str, font: str, size: int, bold: int, outline: float, align: int, primary: str = "#FFFFFF") -> str:
    return (f"Style: {name},{font},{size},{colour(primary)},{colour('#FFFFFF')},{colour('#000000')},{colour('#000000', 0x80)},{bold},0,0,0,"
            f"100,100,0,0,1,{outline},0,{align},40,40,40,1")


def wrap(text: str, max_chars: int) -> str:
    lines, line = [], ""
    for w in text.replace("\\N", " ").split():
        if line and len(line) + 1 + len(w) > max_chars:
            lines.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        lines.append(line)
    if len(lines) > 2:
        lines = [lines[0], " ".join(lines[1:])]
    return "\\N".join(lines)


def emphasis(text: str, accent: str) -> str:
    return re.sub(r"\*(.+?)\*", lambda m: "{\\b1\\c" + colour(accent) + "}" + m.group(1) + "{\\b0\\c&HFFFFFF&}", text)


def word_reveal(text: str, accent: str, start_ms: int = 300, step_ms: int = 110, dur_ms: int = 90) -> str:
    out, i = [], 0
    for line in text.split("\\N"):
        words = []
        for w in line.split():
            t1, t2 = start_ms + i * step_ms, start_ms + i * step_ms + dur_ms
            words.append("{\\alpha&HFF&\\t(" + str(t1) + "," + str(t2) + ",\\alpha&H00&)}" + emphasis(w, accent))
            i += 1
        out.append(" ".join(words))
    return "\\N".join(out)


def safe_bottom(dest: str | None) -> float:
    if not dest or not DESTINATIONS.is_file():
        return 0.0
    spec = json.loads(DESTINATIONS.read_text(encoding="utf-8")).get(dest) or {}
    return float((spec.get("safe_zones") or {}).get("bottom_pct", 0)) / 100


def write(path: str, content: str, dry_run: bool) -> None:
    if not dry_run:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")


def cmd_beats(a) -> int:
    beats = json.loads(Path(a.beats).read_text(encoding="utf-8"))
    W, H = a.width, a.height
    m = min(W, H)
    size = a.size or round(m * 0.09)
    font = a.font or "DejaVu Sans"
    max_chars = 14 if H > W else 24
    bottom = safe_bottom(a.safe)
    pos = {"center": (W / 2, H * 0.46), "lower": (W / 2, H * (1 - bottom) - 1.4 * size - (H * 0.06 if not bottom else 0)), "upper": (W / 2, H * 0.22)}[a.position]
    outline = round(3 * H / 1080, 1)
    styles = [style("Kinetic", font, size, -1 if a.style == "kinetic" else 0, outline, 5)]
    events = []
    for b in beats.get("beats") or []:
        text = (b.get("on_screen") or "").strip()
        if not text:
            continue
        start, end = float(b["start_s"]), float(b["start_s"]) + float(b["duration_s"]) - 0.1
        body = wrap(esc(text), max_chars)
        if a.reveal == "word":
            body = word_reveal(body, a.accent)
            tags = f"{{\\an5\\pos({pos[0]:.0f},{pos[1]:.0f})\\fad(0,160)}}"
        else:
            body = emphasis(body, a.accent)
            tags = f"{{\\an5\\pos({pos[0]:.0f},{pos[1]:.0f})\\fad(120,160)\\fscx80\\fscy80\\t(0,140,\\fscx100\\fscy100)}}"
        events.append(f"Dialogue: 1,{t(start + 0.3)},{t(end)},Kinetic,,0,0,0,,{tags}{body}")
    content = header(W, H, styles) + "\n" + "\n".join(events) + "\n"
    write(a.output, content, a.dry_run)
    return finish({"status": "ok", "output": a.output, "events": len(events), "size": size, "position": a.position, "reveal": a.reveal, "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(events)} on-screen lines, {a.reveal} reveal, {font} {size}px at {a.position}")


def cmd_title(a) -> int:
    W, H = a.width, a.height
    m = min(W, H)
    size, sub_size = round(m * 0.11), round(m * 0.045)
    font = a.font or "DejaVu Sans"
    styles = [style("Title", font, size, -1, round(3 * H / 1080, 1), 5), style("Sub", font, sub_size, 0, round(2 * H / 1080, 1), 5, a.accent)]
    events = [f"Dialogue: 1,{t(a.start)},{t(a.end)},Title,,0,0,0,,{{\\an5\\pos({W / 2:.0f},{H * 0.47:.0f})\\fad(200,200)\\fscx85\\fscy85\\t(0,220,\\fscx100\\fscy100)}}{wrap(esc(a.text), 14 if H > W else 26)}"]
    if a.subtitle:
        events.append(f"Dialogue: 1,{t(a.start + 0.35)},{t(a.end)},Sub,,0,0,0,,{{\\an5\\pos({W / 2:.0f},{H * 0.47 + size * 1.1:.0f})\\fad(250,200)}}{esc(a.subtitle)}")
    write(a.output, header(W, H, styles) + "\n" + "\n".join(events) + "\n", a.dry_run)
    return finish({"status": "ok", "output": a.output, "events": len(events), "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: title {a.start}–{a.end} s")


def cmd_lower_third(a) -> int:
    W, H = a.width, a.height
    m = min(W, H)
    size, role_size = round(m * 0.05), round(m * 0.035)
    font = a.font or "DejaVu Sans"
    x, y = W * 0.06, H * 0.80
    styles = [style("LTName", font, size, -1, round(3 * H / 1080, 1), 1), style("LTRole", font, role_size, 0, round(2 * H / 1080, 1), 1, a.accent)]
    events = [f"Dialogue: 1,{t(a.start)},{t(a.end)},LTName,,0,0,0,,{{\\an1\\move({x - 80:.0f},{y:.0f},{x:.0f},{y:.0f},0,220)\\fad(150,150)}}{esc(a.name)}"]
    if a.role:
        events.append(f"Dialogue: 1,{t(a.start + 0.12)},{t(a.end)},LTRole,,0,0,0,,{{\\an1\\move({x - 80:.0f},{y + role_size * 1.3:.0f},{x:.0f},{y + role_size * 1.3:.0f},0,220)\\fad(150,150)}}{esc(a.role)}")
    write(a.output, header(W, H, styles) + "\n" + "\n".join(events) + "\n", a.dry_run)
    return finish({"status": "ok", "output": a.output, "events": len(events), "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: lower third {a.start}–{a.end} s")


def cmd_end_card(a) -> int:
    W, H = a.width, a.height
    m = min(W, H)
    size, url_size = round(m * 0.08), round(m * 0.05)
    font = a.font or "DejaVu Sans"
    styles = [style("End", font, size, -1, round(3 * H / 1080, 1), 5), style("Url", font, url_size, -1, round(2 * H / 1080, 1), 5, a.accent)]
    events = [f"Dialogue: 1,{t(a.start)},{t(a.end)},End,,0,0,0,,{{\\an5\\pos({W / 2:.0f},{H * 0.46:.0f})\\fad(200,0)}}{wrap(esc(a.text), 14 if H > W else 26)}"]
    if a.url:
        events.append(f"Dialogue: 1,{t(a.start + 0.4)},{t(a.end)},Url,,0,0,0,,{{\\an5\\pos({W / 2:.0f},{H * 0.46 + size * 1.6:.0f})\\fad(500,0)}}{esc(a.url)}")
    write(a.output, header(W, H, styles) + "\n" + "\n".join(events) + "\n", a.dry_run)
    return finish({"status": "ok", "output": a.output, "events": len(events), "dry_run": a.dry_run}, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: end card {a.start}–{a.end} s")


def cmd_merge(a) -> int:
    styles, events, res = [], [], None
    for i, f in enumerate(a.inputs):
        text = Path(f).read_text(encoding="utf-8") if Path(f).is_file() else None
        if text is None:
            raise Failure("input", f"{f} does not exist")
        px = re.search(r"PlayResX:\s*(\d+)", text)
        py = re.search(r"PlayResY:\s*(\d+)", text)
        r = (int(px.group(1)), int(py.group(1))) if px and py else None
        if res is None:
            res = r
        elif r and r != res:
            raise Failure("input", f"{f} has PlayRes {r}, first file has {res}; render all text at the same canvas")
        renames = {}
        for line in text.splitlines():
            if line.startswith("Style:"):
                name = line[6:].split(",", 1)[0].strip()
                new = f"{name}_{i}"
                renames[name] = new
                styles.append("Style: " + new + "," + line[6:].split(",", 1)[1])
            elif line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    parts[3] = renames.get(parts[3].strip(), parts[3].strip())
                    events.append(",".join(parts))
    if res is None:
        raise Failure("input", "no PlayRes found in the inputs")
    # layer order: captions (layer 0) under motion text (layer 1); keep as authored; sort by start for readability
    events.sort(key=lambda e: e.split(",", 2)[1])
    write(a.output, header(res[0], res[1], styles) + "\n" + "\n".join(events) + "\n", a.dry_run)
    return finish({"status": "ok", "output": a.output, "styles": len(styles), "events": len(events), "dry_run": a.dry_run}, a.json,
                  summary=f"{'would write' if a.dry_run else 'wrote'} {a.output}: {len(events)} events from {len(a.inputs)} files")


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Animated on-screen text as ASS. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    geo = argparse.ArgumentParser(add_help=False)
    geo.add_argument("-o", "--output", required=True); geo.add_argument("--width", type=int, required=True); geo.add_argument("--height", type=int, required=True)
    geo.add_argument("--font"); geo.add_argument("--accent", default="#FFD400")
    b = sub.add_parser("beats", parents=cf + [geo]); b.add_argument("beats"); b.add_argument("--style", default="kinetic", choices=["kinetic", "clean"])
    b.add_argument("--reveal", default="word", choices=["word", "line"]); b.add_argument("--position", default="lower", choices=["center", "lower", "upper"])
    b.add_argument("--safe"); b.add_argument("--size", type=int); b.set_defaults(fn=cmd_beats)
    ti = sub.add_parser("title", parents=cf + [geo]); ti.add_argument("--text", required=True); ti.add_argument("--subtitle"); ti.add_argument("--start", type=float, required=True); ti.add_argument("--end", type=float, required=True); ti.set_defaults(fn=cmd_title)
    lt = sub.add_parser("lower-third", parents=cf + [geo]); lt.add_argument("--name", required=True); lt.add_argument("--role"); lt.add_argument("--start", type=float, required=True); lt.add_argument("--end", type=float, required=True); lt.set_defaults(fn=cmd_lower_third)
    ec = sub.add_parser("end-card", parents=cf + [geo]); ec.add_argument("--text", required=True); ec.add_argument("--url"); ec.add_argument("--start", type=float, required=True); ec.add_argument("--end", type=float, required=True); ec.set_defaults(fn=cmd_end_card)
    mg = sub.add_parser("merge", parents=cf); mg.add_argument("inputs", nargs="+"); mg.add_argument("-o", "--output", required=True); mg.set_defaults(fn=cmd_merge)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
