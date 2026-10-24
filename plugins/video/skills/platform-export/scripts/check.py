#!/usr/bin/env python3
"""check: verify a finished video against a destination spec — frame, aspect, length, fps, codecs, audio, loudness, HDR, size.

Usage:  check.py FILE --destination instagram-reels [--json] [--no-loudness]

Measurement only (runs ffprobe and an ebur128 pass); --dry-run is accepted and skips nothing.
Rows are PASS / WARN / FAIL with the measured and expected values. `verified` is true when no row
FAILs. Exit 0 when verified, 1 otherwise. Format rows (codec, pixel format, frame) are safe to fix by
re-exporting; judgement rows (duration, aspect, loudness) change content — report them, let the
Director decide.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import EXIT_FAIL, Failure, base_parser, ffprobe, finish, main_guard, require, run  # noqa: E402

DESTINATIONS = Path(__file__).resolve().parent.parent / "assets" / "destinations.json"


def load_destination(name: str) -> dict:
    data = json.loads(DESTINATIONS.read_text(encoding="utf-8"))
    specs = {k: v for k, v in data.items() if not k.startswith("$")}
    if name not in specs:
        raise Failure("input", f"unknown destination '{name}'", "one of: " + ", ".join(sorted(specs)))
    return specs[name]


def measure_ebur128(path: str, timeout: float) -> dict:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-filter_complex", "ebur128=peak=true", "-f", "null", "-"], timeout)
    text = r["stderr"]
    tail = text[text.rfind("Summary:"):] if "Summary:" in text else text
    out: dict = {}
    m = re.search(r"\bI:\s*(-?[\d.]+)\s*LUFS", tail)
    if m:
        out["integrated_lufs"] = float(m.group(1))
    m = re.search(r"LRA:\s*(-?[\d.]+)\s*LU", tail)
    if m:
        out["lra_lu"] = float(m.group(1))
    m = re.search(r"Peak:\s*(-?[\d.]+)\s*dBFS", tail)
    if m:
        out["true_peak_dbtp"] = float(m.group(1))
    if "integrated_lufs" not in out:
        raise Failure("tool_error", "ebur128 produced no integrated loudness: " + (text.strip().splitlines() or ["?"])[-1])
    return out


def row(name: str, result: str, measured, expected, kind: str = "format") -> dict:
    return {"check": name, "result": result, "measured": measured, "expected": expected, "kind": kind}


@main_guard
def main() -> int:
    ap = base_parser("Verify a video against a destination spec.")
    ap.add_argument("file")
    ap.add_argument("--destination", required=True)
    ap.add_argument("--no-loudness", action="store_true", help="skip the ebur128 measurement")
    a = ap.parse_args()
    dest = load_destination(a.destination)
    require("ffmpeg")
    p = ffprobe(a.file, a.timeout)
    if not p["has_video"]:
        raise Failure("input", f"{a.file} has no video stream")
    rows: list[dict] = []

    W, H = int(dest["width"]), int(dest["height"])
    w, h = int(p["width"]), int(p["height"])
    if abs(int(p.get("rotation") or 0)) in (90, 270):
        w, h = h, w
    if (w, h) == (W, H):
        rows.append(row("frame", "PASS", f"{w}x{h}", f"{W}x{H}"))
    elif abs(w / h - W / H) < 0.01:
        rows.append(row("frame", "WARN", f"{w}x{h}", f"{W}x{H}", "format"))
    else:
        rows.append(row("frame", "FAIL", f"{w}x{h} ({w / h:.3f})", f"{W}x{H} ({dest['aspect']})", "judgement"))
    if p.get("rotation"):
        rows.append(row("rotation", "WARN", f"{p['rotation']}° metadata", "0 (bake the rotation in)", "format"))

    cap = dest.get("max_duration_s")
    if cap:
        rows.append(row("duration", "PASS" if p["duration"] <= cap + 0.05 else "FAIL", f"{p['duration']} s", f"<= {cap} s", "judgement"))
    else:
        rows.append(row("duration", "PASS", f"{p['duration']} s", "no cap", "judgement"))

    fps = dest.get("fps")
    if fps:
        rows.append(row("fps", "PASS" if p["fps"] and abs(p["fps"] - fps) < 0.05 else "FAIL", p["fps"], fps))
    else:
        rows.append(row("fps", "PASS", p["fps"], "source rate, constant"))
    rows.append(row("constant frame rate", "FAIL" if p.get("vfr_suspected") else "PASS", "VFR suspected" if p.get("vfr_suspected") else "constant", "constant"))
    rows.append(row("video codec", "PASS" if p["vcodec"] == dest["vcodec"] else "FAIL", p["vcodec"], dest["vcodec"]))
    rows.append(row("pixel format", "PASS" if p.get("pix_fmt") == dest["pix_fmt"] else "FAIL", p.get("pix_fmt"), dest["pix_fmt"]))
    rows.append(row("SDR", "FAIL" if p.get("hdr") else "PASS", "HDR/BT.2020" if p.get("hdr") else "SDR", "SDR BT.709"))

    if dest.get("audio", True):
        if not p["has_audio"]:
            # platforms accept silent uploads; silence is only wrong if the brief wanted sound
            rows.append(row("audio", "WARN", "no audio stream (fine if intentional)", f"{dest['acodec']} stereo 48 kHz", "judgement"))
        else:
            rows.append(row("audio codec", "PASS" if p.get("acodec") == dest["acodec"] else "FAIL", p.get("acodec"), dest["acodec"]))
            rows.append(row("audio rate", "PASS" if p.get("sample_rate") == 48000 else "WARN", p.get("sample_rate"), 48000))
            rows.append(row("audio channels", "PASS" if p.get("channels") == 2 else "WARN", p.get("channels"), 2))
            if dest.get("lufs") is not None and not a.no_loudness:
                m = measure_ebur128(a.file, a.timeout)
                diff = abs(m["integrated_lufs"] - dest["lufs"])
                rows.append(row("loudness", "PASS" if diff <= 1.0 else ("WARN" if diff <= 2.0 else "FAIL"),
                                f"{m['integrated_lufs']} LUFS", f"{dest['lufs']} ± 1 LUFS", "judgement"))
                if "true_peak_dbtp" in m and dest.get("true_peak_dbtp") is not None:
                    rows.append(row("true peak", "PASS" if m["true_peak_dbtp"] <= dest["true_peak_dbtp"] + 0.1 else "FAIL",
                                    f"{m['true_peak_dbtp']} dBTP", f"<= {dest['true_peak_dbtp']} dBTP"))
    elif p["has_audio"]:
        rows.append(row("audio", "WARN", "has an audio stream", "no audio for this destination"))

    cap_mb = dest.get("max_size_mb")
    size_mb = p["size_bytes"] / 1_048_576
    rows.append(row("file size", "PASS" if not cap_mb or size_mb <= cap_mb else "FAIL", f"{size_mb:.1f} MB", f"<= {cap_mb} MB" if cap_mb else "no cap"))

    counts = {k: sum(1 for r in rows if r["result"] == k) for k in ("PASS", "WARN", "FAIL")}
    verified = counts["FAIL"] == 0
    result = {"status": "ok" if verified else "failed", "file": a.file, "destination": a.destination,
              "verified": verified, "counts": counts, "rows": rows, "probe": {k: v for k, v in p.items() if k != "raw"}}
    if not verified:
        result["error"] = {"kind": "spec", "message": "; ".join(f"{r['check']}: {r['measured']} (expected {r['expected']})" for r in rows if r["result"] == "FAIL")}
    lines = [f"{r['result']:4} {r['check']:20} {str(r['measured']):28} expected {r['expected']}" for r in rows]
    lines.append(f"{a.destination} — {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail (verified: {str(verified).lower()})")
    code = finish(result, a.json, summary="\n".join(lines))
    return code if verified else EXIT_FAIL


if __name__ == "__main__":
    main()
