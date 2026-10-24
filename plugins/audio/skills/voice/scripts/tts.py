#!/usr/bin/env python3
"""tts: local text-to-speech for narration — piper, macOS say, or espeak-ng.

Usage:
  tts.py voices [--language en] [--engine auto|piper|say|espeak-ng]
  tts.py say (--text "…" | --file script.txt) -o out.wav [--voice NAME] [--rate 1.0] [--engine …] [--no-level]
  tts.py beats BEATS.json --out-dir DIR [--voice NAME] [--rate 1.0] [--engine …] [--track-only]
  tts.py recording REC.wav --beats BEATS.json --out-dir DIR [--noise-db -35] [--min-silence 0.5]

`beats` writes one WAV per beat, writes measured_voice_s into the beats file, and builds DIR/track.wav
with each line at its beat's start_s, levelled to -16 LUFS. `--track-only` rebuilds the track from existing
per-beat files (after script.py time --measured --write). Shared flags go after the subcommand.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, common_flags, ffprobe, finish, main_guard, require, run, run_or_fail, which  # noqa: E402

LEVEL = "loudnorm=I=-16:TP=-1.5:LRA=7"


def voice_dirs() -> list[str]:
    dirs = [os.environ.get("STUDIO_PIPER_VOICES"), os.path.join(os.environ.get("CLAUDE_PLUGIN_DATA", ""), "piper", "voices"),
            os.path.expanduser("~/.local/share/piper/voices"), os.path.expanduser("~/piper/voices")]
    return [d for d in dirs if d and os.path.isdir(d)]


def piper_voices() -> list[dict]:
    out = []
    for d in voice_dirs():
        for onnx in sorted(glob.glob(os.path.join(d, "*.onnx"))):
            name = os.path.basename(onnx)[:-5]
            cfg = onnx + ".json"
            lang = name.split("-")[0].split("_")[0] if "-" in name else "?"
            out.append({"engine": "piper", "name": name, "language": lang, "path": onnx, "config_present": os.path.isfile(cfg)})
    return out


def say_voices(timeout: float) -> list[dict]:
    if sys.platform != "darwin" or not which("say"):
        return []
    r = run(["say", "-v", "?"], timeout)
    out = []
    for line in r["stdout"].splitlines():
        m = re.match(r"^(\S.*?)\s{2,}(\w\w)[_-](\w\w)\s", line)
        if m:
            out.append({"engine": "say", "name": m.group(1).strip(), "language": m.group(2).lower(), "path": None})
    return out


def pick_engine(name: str) -> str:
    if name != "auto":
        if name == "say" and sys.platform != "darwin":
            raise Failure("missing_tool", "say exists only on macOS", None, 127)
        if not which(name):
            raise Failure("missing_tool", f"{name} not found on PATH", "see core:doctor references/recipes.md § piper", 127)
        return name
    if which("piper") and piper_voices():
        return "piper"
    if sys.platform == "darwin" and which("say"):
        return "say"
    if which("espeak-ng"):
        return "espeak-ng"
    if which("piper"):
        raise Failure("input", "piper is installed but no voice files were found",
                      "put <voice>.onnx and <voice>.onnx.json under ${CLAUDE_PLUGIN_DATA}/piper/voices/ (see references/voices.md)")
    raise Failure("missing_tool", "no local TTS engine (piper, say, espeak-ng)", "install piper via core:doctor's recipe, or use text-on-screen", 127)


def resolve_voice(engine: str, voice: str | None, language: str | None) -> str | None:
    if engine == "piper":
        voices = piper_voices()
        if voice:
            if os.path.isfile(voice):
                return voice
            for v in voices:
                if v["name"] == voice or v["name"].startswith(voice):
                    return v["path"]
            raise Failure("input", f"piper voice '{voice}' not found", "tts.py voices lists what is installed")
        cands = [v for v in voices if not language or v["language"] == language] or voices
        if not cands:
            raise Failure("input", "no piper voices installed", "see references/voices.md")
        return cands[0]["path"]
    return voice


def synth(engine: str, text: str, out_wav: str, voice: str | None, rate: float, timeout: float, dry_run: bool) -> list[str]:
    """Synthesise text to a 48 kHz mono WAV at out_wav. Returns the commands run."""
    cmds = []
    tmp = out_wav + ".raw.wav"
    if engine == "piper":
        cmd = ["piper", "--model", voice, "--output_file", tmp, "--length_scale", f"{1.0 / max(rate, 0.5):.3f}"]
        cmds.append(cmd)
        if not dry_run:
            import subprocess
            try:
                cp = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=timeout or None)
            except subprocess.TimeoutExpired:
                raise Failure("timeout", "piper exceeded the timeout", None, 124)
            if cp.returncode != 0:
                raise Failure("tool_error", "piper exited " + str(cp.returncode) + ": " + (cp.stderr.strip().splitlines() or ["?"])[-1])
    elif engine == "say":
        aiff = out_wav + ".aiff"
        cmd = ["say"] + (["-v", voice] if voice else []) + ["-r", str(int(175 * rate)), "-o", aiff, text]
        cmds.append(cmd)
        run_or_fail(cmd, timeout, dry_run, what="say")
        tmp = aiff
    else:
        cmd = ["espeak-ng"] + (["-v", voice] if voice else []) + ["-s", str(int(160 * rate)), "-w", tmp, text]
        cmds.append(cmd)
        run_or_fail(cmd, timeout, dry_run, what="espeak-ng")
    conv = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", tmp, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", out_wav]
    cmds.append(conv)
    run_or_fail(conv, timeout, dry_run, what="ffmpeg convert")
    if not dry_run:
        for f in (tmp,):
            if os.path.isfile(f):
                os.remove(f)
    return cmds


def level(in_wav: str, out_wav: str, timeout: float, dry_run: bool) -> None:
    run_or_fail(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", in_wav, "-af", LEVEL + ",aresample=48000", "-ac", "1", "-c:a", "pcm_s16le", out_wav],
                timeout, dry_run, what="ffmpeg loudnorm")


def cmd_voices(a) -> int:
    voices = piper_voices() + say_voices(a.timeout)
    if which("espeak-ng"):
        voices.append({"engine": "espeak-ng", "name": "(any espeak-ng language code, e.g. en, hi, ja)", "language": "*", "path": None})
    if a.language:
        voices = [v for v in voices if v["language"] in (a.language, "*")]
    if a.engine != "auto":
        voices = [v for v in voices if v["engine"] == a.engine]
    lines = [f"{v['engine']:9} {v['language']:4} {v['name']}" for v in voices] or ["no voices found — see references/voices.md and core:doctor's piper recipe"]
    return finish({"status": "ok", "voices": voices, "piper_dirs": voice_dirs()}, a.json, summary="\n".join(lines))


def cmd_say(a) -> int:
    text = Path(a.file).read_text(encoding="utf-8") if a.file else a.text
    if not text or not text.strip():
        raise Failure("input", "no text (use --text or --file)")
    require("ffmpeg")
    engine = pick_engine(a.engine)
    voice = resolve_voice(engine, a.voice, a.language)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = str(out.with_suffix(".unlevelled.wav"))
    cmds = synth(engine, text.strip(), raw if not a.no_level else str(out), voice, a.rate, a.timeout, a.dry_run)
    if not a.no_level:
        level(raw, str(out), a.timeout, a.dry_run)
        if not a.dry_run and os.path.isfile(raw):
            os.remove(raw)
    p = None if a.dry_run else ffprobe(str(out), a.timeout)
    return finish({"status": "ok", "output": str(out), "engine": engine, "voice": voice, "duration_s": p and p["duration"], "commands": cmds, "dry_run": a.dry_run},
                  a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {out} ({engine}, {os.path.basename(str(voice)) if voice else 'default voice'}" + (f", {p['duration']} s" if p else "") + ")")


def build_track(beats: dict, out_dir: Path, timeout: float, dry_run: bool) -> tuple[str, list[str]]:
    inputs, parts = [], []
    for b in beats["beats"]:
        f = out_dir / f"{b['id']}.wav"
        if b.get("voice") and f.is_file():
            inputs += ["-i", str(f)]
            idx = len(inputs) // 2 - 1
            ms = int(float(b["start_s"]) * 1000)
            parts.append(f"[{idx}:a]adelay={ms}|{ms}[d{idx}]")
    if not inputs:
        raise Failure("input", "no per-beat voice files to build a track from")
    n = len(inputs) // 2
    total = sum(float(b["duration_s"]) for b in beats["beats"])
    fc = ";".join(parts) + ";" + "".join(f"[d{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:dropout_transition=0,apad=whole_dur={total:.3f},atrim=duration={total:.3f},{LEVEL}[a]"
    track = str(out_dir / "track.wav")
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs + ["-filter_complex", fc, "-map", "[a]", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", track]
    run_or_fail(cmd, timeout, dry_run, what="ffmpeg track")
    return track, cmd


def cmd_beats(a) -> int:
    require("ffmpeg")
    bpath = Path(a.beats)
    if not bpath.is_file():
        raise Failure("input", f"{a.beats} does not exist")
    beats = json.loads(bpath.read_text(encoding="utf-8"))
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = voice = None
    measured = []
    if not a.track_only:
        engine = pick_engine(a.engine)
        voice = resolve_voice(engine, a.voice or (beats.get("voice") or {}).get("voice") or None, a.language or beats.get("language"))
        rate = a.rate or float((beats.get("voice") or {}).get("rate") or 1.0)
        for b in beats["beats"]:
            if not b.get("voice"):
                continue
            f = out_dir / f"{b['id']}.wav"
            synth(engine, b["voice"], str(f), voice, rate, a.timeout, a.dry_run)
            if not a.dry_run:
                d = ffprobe(str(f), a.timeout)["duration"]
                b["measured_voice_s"] = round(d, 3)
                measured.append((b["id"], round(d, 2)))
        if not a.dry_run:
            beats["voice"]["engine"] = engine
            beats["voice"]["voice"] = os.path.basename(str(voice)) if voice else beats["voice"].get("voice")
            bpath.write_text(json.dumps(beats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    track, cmd = build_track(beats, out_dir, a.timeout, a.dry_run)
    p = None if a.dry_run else ffprobe(track, a.timeout)
    over = [bid for bid, d in measured if d + 0.3 > float(next(x for x in beats["beats"] if x["id"] == bid)["duration_s"]) + 0.01]
    notes = []
    if over:
        notes.append(f"{len(over)} line(s) longer than their beat ({', '.join(over)}): run script.py time --measured --write, then tts.py beats --track-only")
    result = {"status": "ok", "output": track, "engine": engine, "voice": voice, "lines": len(measured) if measured else sum(1 for b in beats['beats'] if b.get('voice')),
              "measured": measured, "beats_file": str(bpath), "track_duration_s": p and p["duration"], "notes": notes, "dry_run": a.dry_run}
    summary = (f"{'would write' if a.dry_run else 'wrote'} {track}" + (f" ({p['duration']} s)" if p else "") + f": {result['lines']} lines"
               + (f", {engine}" if engine else " (track only)") + ("\n" + "\n".join(notes) if notes else ""))
    return finish(result, a.json, summary=summary)


def cmd_recording(a) -> int:
    require("ffmpeg")
    beats = json.loads(Path(a.beats).read_text(encoding="utf-8"))
    lines = [b for b in beats["beats"] if b.get("voice")]
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.recording, "-af", f"silencedetect=noise={a.noise_db}dB:d={a.min_silence}", "-f", "null", "-"], a.timeout)
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", r["stderr"])]
    ends = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", r["stderr"])]
    total = ffprobe(a.recording, a.timeout)["duration"]
    # speech regions = gaps between silences
    regions, t = [], 0.0
    for s, e in zip(starts, ends):
        if s - t > 0.3:
            regions.append((t, s))
        t = e
    if total - t > 0.3:
        regions.append((t, total))
    note = None
    if len(regions) != len(lines):
        note = f"found {len(regions)} spoken regions but the script has {len(lines)} lines — aligning the first {min(len(regions), len(lines))}; check the pauses"
    for b, (s, e) in zip(lines, regions):
        f = out_dir / f"{b['id']}.wav"
        run_or_fail(["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", f"{max(0, s - 0.05):.3f}", "-to", f"{min(total, e + 0.05):.3f}", "-i", a.recording,
                     "-af", LEVEL, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(f)], a.timeout, a.dry_run, what="ffmpeg cut")
        if not a.dry_run:
            b["measured_voice_s"] = round(ffprobe(str(f), a.timeout)["duration"], 3)
    if not a.dry_run:
        beats["voice"]["mode"] = "recording"
        Path(a.beats).write_text(json.dumps(beats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    track, _ = build_track(beats, out_dir, a.timeout, a.dry_run)
    return finish({"status": "ok", "output": track, "regions": len(regions), "lines": len(lines), "notes": [note] if note else [], "dry_run": a.dry_run}, a.json,
                  summary=f"{len(regions)} regions -> {min(len(regions), len(lines))} lines; track {track}" + (f"\n{note}" if note else ""))


@main_guard
def main() -> int:
    p = argparse.ArgumentParser(description="Local TTS for narration. Shared flags go after the subcommand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    cf = [common_flags()]
    v = sub.add_parser("voices", parents=cf); v.add_argument("--language"); v.add_argument("--engine", default="auto", choices=["auto", "piper", "say", "espeak-ng"]); v.set_defaults(fn=cmd_voices)
    s = sub.add_parser("say", parents=cf); s.add_argument("--text"); s.add_argument("--file"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--voice"); s.add_argument("--language"); s.add_argument("--rate", type=float, default=1.0)
    s.add_argument("--engine", default="auto", choices=["auto", "piper", "say", "espeak-ng"]); s.add_argument("--no-level", action="store_true"); s.set_defaults(fn=cmd_say)
    b = sub.add_parser("beats", parents=cf); b.add_argument("beats"); b.add_argument("--out-dir", required=True); b.add_argument("--voice"); b.add_argument("--language")
    b.add_argument("--rate", type=float); b.add_argument("--engine", default="auto", choices=["auto", "piper", "say", "espeak-ng"]); b.add_argument("--track-only", action="store_true"); b.set_defaults(fn=cmd_beats)
    r = sub.add_parser("recording", parents=cf); r.add_argument("recording"); r.add_argument("--beats", required=True); r.add_argument("--out-dir", required=True)
    r.add_argument("--noise-db", type=float, default=-35); r.add_argument("--min-silence", type=float, default=0.5); r.set_defaults(fn=cmd_recording)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    main()
