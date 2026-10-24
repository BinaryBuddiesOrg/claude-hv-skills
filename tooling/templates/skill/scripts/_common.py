"""Shared runtime for Studio skill scripts. Vendored, byte-identical, into every skill's
scripts/ folder (tooling/lint_skills.py checks the copy against
tooling/templates/skill/scripts/_common.py). Edit the template, then re-copy.

Why one runtime: a Director chains scripts from several skills without reading them,
so every script must speak the same language — the flags in CONVENTIONS.md § Scripts
contract, one JSON shape, one set of exit codes, one way to say "tool missing".

Standard library only. Python 3.10+.

Typical script:

    from _common import base_parser, run, require, ffprobe, finish, Failure, main_guard

    @main_guard
    def main() -> int:
        p = base_parser("Trim a clip without re-encoding where possible")
        p.add_argument("input"); p.add_argument("-o", "--output", required=True)
        a = p.parse_args()
        require("ffmpeg")
        check_output_path(a.output, a.overwrite)
        src = ffprobe(a.input, a.timeout)
        r = run(["ffmpeg", "-y", "-i", a.input, "-c", "copy", a.output], a.timeout, a.dry_run)
        out = None if a.dry_run else ffprobe(a.output, a.timeout)
        return finish({"status": "ok", "output": a.output, "input_probe": src, "output_probe": out,
                       "commands": [r["cmd"]]}, a.json, summary=f"{a.output}: {out and out['duration']}s")
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Any

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_UNDECIDABLE = 2
EXIT_TIMEOUT = 124
EXIT_MISSING_TOOL = 127


class Failure(Exception):
    """A failure the script reports as JSON (status failed, error.kind/message/hint) and exits with `code`."""

    def __init__(self, kind: str, message: str, hint: str | None = None, code: int = EXIT_FAIL):
        super().__init__(message)
        self.kind, self.message, self.hint, self.code = kind, message, hint, code

    def as_dict(self) -> dict:
        d = {"kind": self.kind, "message": self.message}
        if self.hint:
            d["hint"] = self.hint
        return d


def base_parser(description: str) -> argparse.ArgumentParser:
    """The flags every Studio script shares. Add the script's own on top."""
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--dry-run", action="store_true", help="print the commands that would run; write nothing")
    p.add_argument("--json", action="store_true", help="machine-readable result on stdout")
    p.add_argument("--timeout", type=float, default=1800.0, help="seconds per external command (default 1800; 0 = no limit)")
    p.add_argument("--overwrite", action="store_true", help="allow replacing an existing output file")
    return p


def which(tool: str) -> str | None:
    return shutil.which(tool)


def require(tool: str, hint: str | None = None) -> str:
    """Path of `tool`, or Failure(kind=missing_tool, exit 127). The hint names the install recipe."""
    path = which(tool)
    if not path:
        raise Failure("missing_tool", f"{tool} not found on PATH",
                      hint or f"see TOOLBOX.md for the {tool} install recipe", EXIT_MISSING_TOOL)
    return path


def check_output_path(path: str, overwrite: bool) -> None:
    """Refuse to replace a file this run did not create unless --overwrite was passed."""
    if os.path.exists(path) and not overwrite:
        raise Failure("input", f"{path} exists; pass --overwrite to replace it")
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)


def run(cmd: list[str], timeout: float, dry_run: bool = False, capture: bool = True) -> dict:
    """Run `cmd`. Returns {cmd, code, stdout, stderr, seconds[, dry_run]}.
    Timeout → Failure(timeout, 124). Missing binary → Failure(missing_tool, 127).
    A non-zero exit is returned, not raised: the caller knows what the tool's exit means."""
    if dry_run:
        return {"cmd": cmd, "code": 0, "stdout": "", "stderr": "", "seconds": 0.0, "dry_run": True}
    t0 = time.monotonic()
    try:
        cp = subprocess.run(cmd, capture_output=capture, text=True, timeout=(timeout or None))
    except subprocess.TimeoutExpired:
        raise Failure("timeout", f"{cmd[0]} exceeded {timeout:.0f} s", "raise --timeout or split the job", EXIT_TIMEOUT)
    except FileNotFoundError:
        raise Failure("missing_tool", f"{cmd[0]} not found on PATH", None, EXIT_MISSING_TOOL)
    return {"cmd": cmd, "code": cp.returncode, "stdout": cp.stdout or "", "stderr": cp.stderr or "",
            "seconds": round(time.monotonic() - t0, 3)}


def run_or_fail(cmd: list[str], timeout: float, dry_run: bool = False, what: str = "") -> dict:
    """`run`, then Failure(tool_error) quoting the tool's last stderr line when it exits non-zero."""
    r = run(cmd, timeout, dry_run)
    if r["code"] != 0:
        last = (r["stderr"].strip().splitlines() or ["(no stderr)"])[-1]
        raise Failure("tool_error", f"{what or cmd[0]} exited {r['code']}: {last}")
    return r


def _fps(rate: str) -> float | None:
    try:
        n, d = rate.split("/") if "/" in rate else (rate, "1")
        return round(float(n) / float(d), 3) if float(d) else None
    except (ValueError, ZeroDivisionError):
        return None


def ffprobe(path: str, timeout: float = 60.0) -> dict:
    """Measured facts about a media file: the numbers a plan is built from and a result is verified by.
    Keys: duration, has_video, has_audio, width, height, fps, vcodec, pix_fmt, acodec, channels,
    sample_rate, rotation, vfr_suspected, hdr, size_bytes, container, raw (the ffprobe JSON)."""
    if not os.path.isfile(path):
        raise Failure("input", f"{path} does not exist")
    require("ffprobe")
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path], timeout)
    if r["code"] != 0:
        raise Failure("probe", f"ffprobe could not read {path}: {(r['stderr'].strip().splitlines() or [''])[-1]}")
    raw = json.loads(r["stdout"] or "{}")
    fmt = raw.get("format", {})
    v = next((s for s in raw.get("streams", []) if s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic", 0) == 0), None)
    a = next((s for s in raw.get("streams", []) if s.get("codec_type") == "audio"), None)
    out: dict[str, Any] = {
        "path": path,
        "container": fmt.get("format_name"),
        "duration": round(float(fmt.get("duration", 0) or 0), 3),
        "size_bytes": int(fmt.get("size", 0) or 0),
        "has_video": v is not None,
        "has_audio": a is not None,
    }
    if v:
        rotation = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rotation = int(sd["rotation"])
        rotation = rotation or int((v.get("tags") or {}).get("rotate", 0) or 0)
        avg, real = _fps(v.get("avg_frame_rate", "0")), _fps(v.get("r_frame_rate", "0"))
        out.update({
            "width": v.get("width"), "height": v.get("height"), "fps": avg or real,
            "vcodec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"), "rotation": rotation,
            "vfr_suspected": bool(avg and real and abs(avg - real) > 0.5),
            "hdr": (v.get("color_transfer") in ("smpte2084", "arib-std-b67")) or (v.get("color_primaries") == "bt2020"),
        })
    if a:
        out.update({"acodec": a.get("codec_name"), "channels": a.get("channels"),
                    "sample_rate": int(a.get("sample_rate", 0) or 0)})
    out["raw"] = raw
    return out


def finish(result: dict, as_json: bool, summary: str | None = None) -> int:
    """Print the result (JSON, or the one-line summary) and return the exit code."""
    result.setdefault("status", "ok")
    if as_json:
        slim = {k: v for k, v in result.items()}
        for key in ("input_probe", "output_probe"):
            if isinstance(slim.get(key), dict):
                slim[key] = {k: v for k, v in slim[key].items() if k != "raw"}
        print(json.dumps(slim, indent=2, ensure_ascii=False))
    else:
        print(summary or result.get("output") or result["status"])
    return EXIT_OK if result["status"] == "ok" else EXIT_FAIL


def main_guard(fn):
    """Wrap main(): a Failure becomes a JSON failure document and the right exit code;
    Ctrl-C exits 130; anything else is a bug and still reports as JSON when --json was asked."""
    def wrapper() -> None:
        as_json = "--json" in sys.argv
        try:
            sys.exit(fn())
        except Failure as f:
            doc = {"status": "failed", "error": f.as_dict()}
            print(json.dumps(doc, indent=2) if as_json else f"{f.kind}: {f.message}" + (f"\n  hint: {f.hint}" if f.hint else ""),
                  file=sys.stdout if as_json else sys.stderr)
            sys.exit(f.code)
        except KeyboardInterrupt:
            sys.exit(130)
    return wrapper
