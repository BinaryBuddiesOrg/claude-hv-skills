#!/usr/bin/env python3
"""doctor: what can this machine do? OS, CPU, RAM, GPU/VRAM, tools and versions, fonts by script, free disk.

Usage:  python3 doctor.py [--json] [--tools ffmpeg,piper] [--timeout 10]

Measurement only: it writes nothing, so --dry-run is accepted and changes nothing.
Exit 0 whenever the inventory ran — a missing tool is a fact, not a failure.
Standard library only; optional detail from nvidia-smi, lspci, system_profiler, fc-list.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import base_parser, finish, main_guard, run  # noqa: E402

# tool -> (argv that prints a version, regex with one group for the version; None = presence only)
TOOLS: dict[str, tuple[list[str], str | None]] = {
    "ffmpeg": (["ffmpeg", "-version"], r"ffmpeg version (\S+)"),
    "ffprobe": (["ffprobe", "-version"], r"ffprobe version (\S+)"),
    "python3": (["python3", "--version"], r"Python (\S+)"),
    "uv": (["uv", "--version"], r"uv (\S+)"),
    "node": (["node", "--version"], r"v?(\S+)"),
    "npm": (["npm", "--version"], r"(\S+)"),
    "pnpm": (["pnpm", "--version"], r"(\S+)"),
    "bun": (["bun", "--version"], r"(\S+)"),
    "godot": (["godot", "--version"], r"(\d[\w.]+)"),
    "blender": (["blender", "--version"], r"Blender (\S+)"),
    "magick": (["magick", "-version"], r"ImageMagick (\S+)"),
    "convert": (["convert", "-version"], r"ImageMagick (\S+)"),
    "inkscape": (["inkscape", "--version"], r"Inkscape (\S+)"),
    "rsvg-convert": (["rsvg-convert", "--version"], r"(\d\S*)"),
    "sox": (["sox", "--version"], r"v(\S+)"),
    "whisper-cli": (["whisper-cli", "--help"], None),
    "whisper-ctranslate2": (["whisper-ctranslate2", "--version"], r"(\d\S*)"),
    "piper": (["piper", "--help"], None),
    "yt-dlp": (["yt-dlp", "--version"], r"(\S+)"),
    "rembg": (["rembg", "--help"], None),
    "docker": (["docker", "--version"], r"Docker version (\S+?),"),
    "git": (["git", "--version"], r"git version (\S+)"),
    "gh": (["gh", "--version"], r"gh version (\S+)"),
    "java": (["java", "-version"], r'version "([^"]+)"'),
    "gcc": (["gcc", "--version"], r"gcc \([^)]*\) (\S+)"),
    "cmake": (["cmake", "--version"], r"cmake version (\S+)"),
    "make": (["make", "--version"], r"Make (\S+)"),
    "cargo": (["cargo", "--version"], r"cargo (\S+)"),
    "go": (["go", "version"], r"go version go(\S+)"),
    "fc-list": (["fc-list", "--version"], r"(\d\S*)"),
}

# capability group -> list of alternatives; each alternative is a list of tools that must all be present
USABLE: dict[str, list[list[str]]] = {
    "video_edit": [["ffmpeg", "ffprobe"]],
    "transcription": [["whisper-cli"], ["whisper-ctranslate2"]],
    "tts_voiceover": [["piper"]],
    "image_ops": [["magick"], ["convert"]],
    "vector_svg": [["inkscape"], ["rsvg-convert"]],
    "render_3d": [["blender"]],
    "game_godot": [["godot"]],
    "web_apps": [["node"]],
}

FONT_LANGS = ["en", "ja", "ko", "zh", "hi", "th", "ar"]


def tool_info(name: str, timeout: float) -> dict:
    argv, pattern = TOOLS.get(name, ([name, "--version"], r"(\d\S*)"))
    path = shutil.which(argv[0])
    if not path:
        return {"present": False, "path": None, "version": None}
    version = None
    try:
        r = run(argv, min(timeout, 20.0))
        text = (r["stdout"] or "") + "\n" + (r["stderr"] or "")
        if pattern:
            m = re.search(pattern, text)
            version = m.group(1) if m else None
    except Exception:  # a tool that hangs or crashes on --version is still present
        version = None
    return {"present": True, "path": path, "version": version}


def ram_gb() -> float | None:
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return round(int(line.split()[1]) / 1_048_576, 1)
        if sys.platform == "darwin":
            r = run(["sysctl", "-n", "hw.memsize"], 5)
            return round(int(r["stdout"].strip()) / 1_073_741_824, 1)
        pages, size = os.sysconf("SC_PHYS_PAGES"), os.sysconf("SC_PAGE_SIZE")  # type: ignore[attr-defined]
        return round(pages * size / 1_073_741_824, 1)
    except Exception:
        return None


def gpu_info(timeout: float, ram: float | None) -> dict:
    out: dict = {"name": None, "vram_gb": None, "source": None}
    if shutil.which("nvidia-smi"):
        try:
            r = run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], min(timeout, 10))
            line = (r["stdout"].strip().splitlines() or [""])[0]
            if line and r["code"] == 0:
                name, _, mem = line.partition(",")
                m = re.search(r"(\d+)\s*MiB", mem)
                out.update(name=name.strip(), vram_gb=round(int(m.group(1)) / 1024, 1) if m else None, source="nvidia-smi")
                return out
        except Exception:
            pass
    if sys.platform == "darwin" and shutil.which("system_profiler"):
        try:
            r = run(["system_profiler", "SPDisplaysDataType"], min(timeout, 20))
            m = re.search(r"Chipset Model:\s*(.+)", r["stdout"])
            if m:
                out.update(name=m.group(1).strip(), source="system_profiler")
                v = re.search(r"VRAM[^:]*:\s*(\d+)\s*(GB|MB)", r["stdout"])
                if v:
                    out["vram_gb"] = round(int(v.group(1)) / (1 if v.group(2) == "GB" else 1024), 1)
                elif "Apple" in out["name"] and ram:
                    out["vram_gb"], out["source"] = ram, "unified memory"
                return out
        except Exception:
            pass
    if shutil.which("lspci"):
        try:
            r = run(["lspci"], min(timeout, 10))
            for line in r["stdout"].splitlines():
                if re.search(r"VGA|3D|Display", line):
                    out.update(name=line.split(":", 2)[-1].strip(), source="lspci")
                    break
        except Exception:
            pass
    return out


def fonts(timeout: float) -> dict | None:
    if not shutil.which("fc-list"):
        return None
    try:
        total = len([ln for ln in run(["fc-list", ":", "family"], min(timeout, 20))["stdout"].splitlines() if ln.strip()])
        langs = {}
        for lang in FONT_LANGS:
            r = run(["fc-list", f":lang={lang}", "family"], min(timeout, 20))
            langs[lang] = bool(r["stdout"].strip())
        return {"families": total, "langs": langs}
    except Exception:
        return None


def inventory(names: list[str], timeout: float) -> dict:
    uname = platform.uname()
    ram = ram_gb()
    tools = {n: tool_info(n, timeout) for n in names}
    usable = {}
    for group, alternatives in USABLE.items():
        ok = any(all(tools.get(t, tool_info(t, timeout))["present"] for t in alt) for alt in alternatives)
        usable[group] = {"ok": ok, "needs_one_of": [" + ".join(alt) for alt in alternatives]}
    free = shutil.disk_usage(os.getcwd()).free / 1_073_741_824
    return {
        "status": "ok",
        "os": {"system": uname.system, "release": uname.release, "machine": uname.machine, "python": platform.python_version()},
        "cpu_cores": os.cpu_count(),
        "ram_gb": ram,
        "gpu": gpu_info(timeout, ram),
        "disk_free_gb": round(free, 1),
        "tools": tools,
        "usable": usable,
        "fonts": fonts(timeout),
        "cwd": os.getcwd(),
    }


def summary(inv: dict) -> str:
    g = inv["gpu"]
    gpu = f"GPU {g['name']} {g['vram_gb']} GB" if g.get("name") and g.get("vram_gb") else (f"GPU {g['name']} (VRAM unknown)" if g.get("name") else "no GPU found")
    present = [f"{n} {t['version'] or ''}".strip() for n, t in inv["tools"].items() if t["present"]]
    missing = [n for n, t in inv["tools"].items() if not t["present"]]
    usable = " · ".join(f"{k} ✓" if v["ok"] else f"{k} ✗ ({' or '.join(v['needs_one_of'])})" for k, v in inv["usable"].items())
    f = inv["fonts"]
    fonts_line = (f"{f['families']} families · " + " ".join(f"{l} {'✓' if ok else '✗'}" for l, ok in f["langs"].items())) if f else "fc-list not available"
    return "\n".join([
        f"Machine: {inv['os']['system']} {inv['os']['machine']} · {inv['cpu_cores']} cores · {inv['ram_gb']} GB RAM · {gpu} · {inv['disk_free_gb']} GB free",
        f"Present: {' · '.join(present) or 'nothing from the known list'}",
        f"Missing: {' · '.join(missing) or 'nothing'}",
        f"Usable:  {usable}",
        f"Fonts:   {fonts_line}",
    ])


@main_guard
def main() -> int:
    p = base_parser("Inventory this machine: hardware, tools, fonts, disk. Writes nothing.")
    p.add_argument("--tools", help="comma-separated subset to check (default: every known tool)")
    p.set_defaults(timeout=10.0)
    a = p.parse_args()
    names = [n.strip() for n in a.tools.split(",") if n.strip()] if a.tools else list(TOOLS)
    inv = inventory(names, a.timeout)
    return finish(inv, a.json, summary=summary(inv))


if __name__ == "__main__":
    main()
