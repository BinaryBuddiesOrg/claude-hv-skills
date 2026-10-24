# Research source playbook

Per domain: where to look, which queries work, what to extract. newadder follows this
so two runs a month apart search the same way and the index stays comparable. Update
it when a source stops being useful; note the date.

## Every domain

| Source | How | Extract |
|---|---|---|
| GitHub topics | `https://github.com/topics/<topic>?o=desc&s=stars` and `s=updated` | stars, last push, licence, README hardware notes, install method |
| GitHub awesome-lists | search `awesome <domain>` and the list's recent commits | newly added entries = what practitioners noticed |
| GitHub releases of TOOLBOX tools | `/releases` page | breaking changes, new features that unlock a capability |
| Hugging Face | `https://huggingface.co/models?pipeline_tag=<tag>&sort=trending` | size, licence, CPU feasibility, maintainer |
| PyPI / npm | project page, release history | cadence, Python/Node floor, dependency weight |
| Hacker News | Algolia search `https://hn.algolia.com/?q=<term>&dateRange=pastYear` | what shipped, what people complain about |
| Reddit | search within the subreddits below; read top comments, not posts | pitfalls, real-world settings, tool comparisons |
| Stack Overflow | tag pages, sorted by votes and by newest | recurring errors → pitfalls section |
| Blogs / papers | search `"<technique>" site:arxiv.org` or the tool's blog | techniques, not tools |
| X / LinkedIn | search-engine snippets only | hints to verify elsewhere; never a sole source |

Freshness windows (from `research/INDEX.md`): tool landscape 30 days; a rejected tool
90 days; a technique 180 days.

## video

Topics: `video-editing`, `ffmpeg`, `motion-graphics`, `remotion`, `subtitles`,
`speech-to-text`, `video-generation`, `animation`, `2d-animation`, `anime`.
Subreddits: r/VideoEditing, r/ffmpeg, r/editors, r/StableDiffusion (for generation
hardware reality), r/animation. HF tags: `automatic-speech-recognition`,
`text-to-video`, `image-to-video`.
Questions to answer: what runs on CPU in minutes; what the install really costs; what
breaks headless.

## audio

Topics: `text-to-speech`, `tts`, `speech-synthesis`, `audio-processing`, `podcast`,
`music-generation`. Subreddits: r/podcasting, r/audioengineering, r/LocalLLaMA (for
local TTS threads). HF tags: `text-to-speech`, `text-to-audio`.
Questions: voice naturalness on CPU; licences of voices (not just code); languages.

## graphics

Topics: `image-processing`, `svg`, `background-removal`, `blender`, `pixel-art`,
`procedural-generation`. Subreddits: r/blender, r/PixelArt, r/graphic_design (sparingly).
Questions: headless reliability; CPU render times; output quality at small sizes.

## game

Topics: `godot`, `godot-engine`, `gdscript`, `phaser`, `threejs`, `game-development`,
`procedural-generation`, `game-assets`. Subreddits: r/godot, r/gamedev,
r/IndieDev. Asset sources: Kenney, OpenGameArt, itch.io free assets (licence per pack).
Questions: headless export from CLI; templates that compile today; licence clarity of
assets.

## apps

Topics: `vite`, `nextjs`, `expo`, `tauri`, `fastapi`, `playwright`, `boilerplate`.
Subreddits: r/webdev, r/reactnative, r/selfhosted. Questions: what proves the app works
(tests, screenshots, Lighthouse); scaffold versions that are stable this quarter.
