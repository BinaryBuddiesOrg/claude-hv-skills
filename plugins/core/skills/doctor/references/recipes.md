# Install recipes

The only recipes doctor may offer. Each block is read to the user before anything runs:
what it is, licence, what it needs, the exact command, what proves it worked, what it
unlocks, how big it is, what goes wrong. Pinned where the registry allows; never
`curl | bash`; never "clone main and build".

**Vetting status matters.** A block marked `vetted: no` was written from the tool's
documentation and has not yet been proven on a Studio machine by newadder (see the repo's
TOOLBOX.md). Offer it with that caveat and watch the proving command.

Model files and caches go under `${CLAUDE_PLUGIN_DATA}` (per-plugin, survives updates),
never into the plugin folder.

## Contents

ffmpeg · imagemagick · whisper (two options) · piper · yt-dlp · inkscape · rsvg-convert ·
sox · blender · godot · node

---

## ffmpeg

```
tool: ffmpeg + ffprobe            licence: LGPL/GPL (build-dependent)      vetted: yes (8.1.3, Linux, 2026-10-24)
needs: CPU only
linux:  sudo apt install ffmpeg            # Debian/Ubuntu; distro version may be old — fine for most jobs
        # newer static builds: download a tagged release from the project's downloads page, unpack to ~/.local/bin
macos:  brew install ffmpeg
windows: winget install Gyan.FFmpeg
proves: ffmpeg -version && ffprobe -version
unlocks: everything in the video and audio plugins
size: ~100 MB
traps: encoders are build options — `ffmpeg -hide_banner -encoders | grep -E "libx264|libx265|libaom"`;
       libass is needed for styled captions — `ffmpeg -hide_banner -filters | grep subtitles`
```

## imagemagick

```
tool: magick (ImageMagick 7) / convert (6)   licence: ImageMagick (Apache-2.0-compatible)   vetted: no
needs: CPU only
linux:  sudo apt install imagemagick        # usually v6: the command is `convert`
macos:  brew install imagemagick            # v7: the command is `magick`
windows: winget install ImageMagick.ImageMagick
proves: magick -version || convert -version
unlocks: image_ops (thumbnails, resize, contact sheets, format conversion)
size: ~50 MB
traps: v6 policy.xml may forbid PDF/PS reads; `convert` on Windows collides with a system tool — use `magick`
```

## whisper — local transcription (choose one)

Option A, whisper.cpp (C++, fastest on CPU, Apple Silicon friendly):

```
tool: whisper-cli (whisper.cpp)   licence: MIT                              vetted: no
needs: CPU ok; models 75 MB (tiny) … 3 GB (large) downloaded on first use
macos:  brew install whisper-cpp
linux:  download the tagged release source archive from the project's releases page, then
        cmake -B build && cmake --build build -j && install build/bin/whisper-cli ~/.local/bin/
        (needs cmake + a C++ compiler; a distro package may exist on newer releases)
proves: whisper-cli --help
unlocks: transcription (captions from speech, silence-aware cuts, talking-head jump cuts)
size: ~30 MB binary + model; put models in ${CLAUDE_PLUGIN_DATA}/whisper/
traps: model download is a separate step (`models/download-ggml-model.sh base.en` from the release archive);
       the `base`/`small` models are the CPU sweet spot; `large` is slow on CPU
```

Option B, whisper-ctranslate2 (Python CLI over faster-whisper):

```
tool: whisper-ctranslate2          licence: MIT (CLI) / MIT (faster-whisper)   vetted: no
needs: CPU ok (int8); GPU optional
any:    uv tool install whisper-ctranslate2        # isolated; needs uv (recipe: https://docs.astral.sh/uv/)
proves: whisper-ctranslate2 --version
unlocks: transcription
size: ~500 MB of Python packages + models (75 MB … 1.5 GB) cached on first run
traps: first run downloads the model silently — tell the user the size; set HF_HOME to ${CLAUDE_PLUGIN_DATA}/hf
```

## piper — local text-to-speech

```
tool: piper (piper-tts)            licence: MIT (engine); voices have their own licences   vetted: no
needs: CPU only
any:    uv tool install piper-tts
proves: piper --help
unlocks: tts_voiceover (voice-over for promos, explainers, slideshows)
size: ~100 MB + 20–60 MB per voice; voices to ${CLAUDE_PLUGIN_DATA}/piper/voices/
traps: a voice is two files (.onnx + .onnx.json) downloaded separately; check the voice's licence before
       commercial use; quality varies a lot by voice — test the sentence the user will hear
```

## yt-dlp — download media the user is allowed to use

```
tool: yt-dlp                       licence: Unlicense                        vetted: no
needs: CPU only; ffmpeg for merging formats
any:    uv tool install yt-dlp
proves: yt-dlp --version
unlocks: fetching reference footage or audio from a URL the user owns or has rights to
size: ~15 MB
traps: downloading content without rights is the user's responsibility — say so once per job;
       sites change often; `uv tool upgrade yt-dlp` fixes most "unable to extract" errors
```

## inkscape — SVG rendering and editing from the CLI

```
tool: inkscape                     licence: GPL-2.0                          vetted: no
needs: CPU only
linux:  sudo apt install inkscape
macos:  brew install --cask inkscape
windows: winget install Inkscape.Inkscape
proves: inkscape --version
unlocks: vector_svg (SVG → PNG/PDF at any size, text-to-path, icon sets)
size: ~300 MB
traps: headless export flags differ between 0.92 and 1.x (`--export-filename` is 1.x)
```

## rsvg-convert — lighter SVG rasteriser

```
tool: rsvg-convert (librsvg)       licence: LGPL-2.1                         vetted: no
needs: CPU only
linux:  sudo apt install librsvg2-bin
macos:  brew install librsvg
proves: rsvg-convert --version
unlocks: vector_svg (rasterising only)
size: ~10 MB
traps: no editing; some SVG filters unsupported
```

## sox

```
tool: sox                          licence: GPL-2.0                          vetted: no
linux:  sudo apt install sox libsox-fmt-all
macos:  brew install sox
proves: sox --version
unlocks: quick audio transforms where ffmpeg is clumsier (trim by silence, simple effects)
size: ~5 MB
traps: mp3 needs libsox-fmt-mp3 on some distros; ffmpeg already covers most needs
```

## blender — 3D renders and motion, headless

```
tool: blender                      licence: GPL-3.0                          vetted: no
needs: CPU ok (slow); GPU speeds Cycles/EEVEE a lot
linux:  download the tagged release .tar.xz from blender.org/download, unpack, symlink `blender` into ~/.local/bin
macos:  brew install --cask blender
windows: winget install BlenderFoundation.Blender
proves: blender --version
unlocks: render_3d (product shots, 3D titles, camera moves)
size: ~300 MB download, ~1 GB installed
traps: headless is `blender -b file.blend -P script.py`; a simple 5 s title at 1080p can take minutes on CPU
```

## godot — game engine, headless export

```
tool: godot                        licence: MIT                              vetted: yes (present on the dev machine)
needs: CPU ok
linux/macos/windows: download the tagged release binary from godotengine.org/download, put it on PATH as `godot`
proves: godot --version
unlocks: game_godot (scaffold, run headless, export presets)
size: ~150 MB; export templates are a separate ~1 GB download
traps: exports need the matching export templates version; `--headless` for CI-style runs
```

## node — JavaScript runtime for web apps and games

```
tool: node (+ npm)                 licence: MIT                              vetted: yes (22.x present on the dev machine)
any:    install via the project's official installer or a version manager (nvm, fnm); pick the current LTS
proves: node --version && npm --version
unlocks: web_apps, web games (Phaser/Three.js), programmatic video (Remotion / Motion Canvas)
size: ~100 MB
traps: global installs in a system Node need sudo — prefer a version manager
```
