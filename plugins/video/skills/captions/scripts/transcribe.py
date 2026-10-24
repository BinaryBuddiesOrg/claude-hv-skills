#!/usr/bin/env python3
"""transcribe: speech → SRT (and word timings) with a local engine. No cloud.

Usage:
  transcribe.py INPUT -o transcript.srt [--engine auto|whisper-cli|whisper-ctranslate2] [--model base]
                [--model-path FILE] [--language en] [--words] [--max-chars 32] [--dry-run] [--json] [--timeout S]

Engines (core:doctor → usable.transcription):
  whisper-cli          whisper.cpp; model file ggml-<model>.bin under $STUDIO_WHISPER_MODELS or ${CLAUDE_PLUGIN_DATA}/whisper/
  whisper-ctranslate2  faster-whisper CLI; downloads the model on first run (say the size first)
Writes transcript.srt, transcript.json (engine output) and, with --words, transcript.words.json.
Confidence is not a number this script can promise: read the SRT before burning it.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Failure, base_parser, finish, main_guard, require, run_or_fail, which  # noqa: E402

HERE = Path(__file__).resolve().parent
MODEL_SIZES_MB = {"tiny": 75, "base": 142, "small": 466, "medium": 1500, "large": 3100, "large-v3": 3100}


def pick_engine(name: str) -> str:
    if name != "auto":
        if not which(name):
            raise Failure("missing_tool", f"{name} not found on PATH", "see core:doctor references/recipes.md § whisper", 127)
        return name
    for cand in ("whisper-cli", "whisper-ctranslate2"):
        if which(cand):
            return cand
    raise Failure("missing_tool", "no local transcription engine (whisper-cli or whisper-ctranslate2)",
                  "install one via core:doctor's recipe, or provide the text/SRT and use srt.py from-text", 127)


def whisper_cpp_model(model: str, model_path: str | None) -> str:
    if model_path:
        if not os.path.isfile(model_path):
            raise Failure("input", f"model file {model_path} does not exist")
        return model_path
    roots = [os.environ.get("STUDIO_WHISPER_MODELS"), os.path.join(os.environ.get("CLAUDE_PLUGIN_DATA", ""), "whisper"),
             os.path.expanduser("~/.cache/whisper.cpp"), os.path.expanduser("~/whisper.cpp/models")]
    for root in [r for r in roots if r]:
        for cand in (f"ggml-{model}.bin", f"ggml-{model}.en.bin"):
            p = os.path.join(root, cand)
            if os.path.isfile(p):
                return p
    raise Failure("input", f"no ggml-{model}.bin model file found",
                  f"download it (~{MODEL_SIZES_MB.get(model, '?')} MB) into ${{CLAUDE_PLUGIN_DATA}}/whisper/ with whisper.cpp's models/download-ggml-model.sh {model}, or pass --model-path")


@main_guard
def main() -> int:
    ap = base_parser("Transcribe speech to SRT with a local whisper engine.")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", required=True, help="SRT path")
    ap.add_argument("--engine", default="auto", choices=["auto", "whisper-cli", "whisper-ctranslate2"])
    ap.add_argument("--model", default="base", help="tiny|base|small|medium|large-v3 (base is the CPU sweet spot)")
    ap.add_argument("--model-path", help="whisper.cpp ggml model file")
    ap.add_argument("--language", default="auto")
    ap.add_argument("--words", action="store_true", help="also write word timings for karaoke captions")
    ap.add_argument("--max-chars", type=int, default=32)
    a = ap.parse_args()

    require("ffmpeg")
    engine = pick_engine(a.engine)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    tmpdir = tempfile.mkdtemp(prefix="studio-transcribe-")
    wav = os.path.join(tmpdir, "audio16k.wav")
    run_or_fail(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", a.input, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav],
                a.timeout, a.dry_run, what="ffmpeg audio extract")

    json_path = f"{stem}.json"
    if engine == "whisper-cli":
        model = whisper_cpp_model(a.model, a.model_path) if not a.dry_run else (a.model_path or f"ggml-{a.model}.bin")
        base = os.path.join(tmpdir, "out")
        cmd = ["whisper-cli", "-m", model, "-f", wav, "-oj", "-of", base, "-ml", "1" if a.words else "0"]
        if a.language != "auto":
            cmd += ["-l", a.language]
        run_or_fail(cmd, a.timeout, a.dry_run, what="whisper-cli")
        if not a.dry_run:
            shutil.copyfile(base + ".json", json_path)
    else:
        cmd = ["whisper-ctranslate2", wav, "--model", a.model, "--output_format", "json", "--output_dir", tmpdir, "--compute_type", "int8"]
        if a.language != "auto":
            cmd += ["--language", a.language]
        if a.words:
            cmd += ["--word_timestamps", "True"]
        run_or_fail(cmd, a.timeout, a.dry_run, what="whisper-ctranslate2")
        if not a.dry_run:
            produced = [p for p in os.listdir(tmpdir) if p.endswith(".json")]
            if not produced:
                raise Failure("tool_error", "whisper-ctranslate2 wrote no JSON")
            shutil.copyfile(os.path.join(tmpdir, produced[0]), json_path)

    words_path = f"{stem}.words.json" if a.words else None
    cmd = [sys.executable, str(HERE / "srt.py"), "from-whisper", json_path, "-o", str(out), "--max-chars", str(a.max_chars)]
    if words_path:
        cmd += ["--words-out", words_path]
    run_or_fail(cmd, a.timeout, a.dry_run, what="srt from-whisper")
    shutil.rmtree(tmpdir, ignore_errors=True)
    result = {"status": "ok", "output": str(out), "engine": engine, "model": a.model, "json": json_path, "words": words_path, "dry_run": a.dry_run,
              "notes": ["read the SRT before burning: names and brand words are often misspelt"]}
    return finish(result, a.json, summary=f"{'would write' if a.dry_run else 'wrote'} {out} with {engine} ({a.model})" + (f" + {words_path}" if words_path else ""))


if __name__ == "__main__":
    main()
