# video

The video plugin. Entry point: `/video:director` (triggers on any video request).
Executor: the `video:producer` agent. Capabilities: `capabilities.json`. Universe:
`../../taxonomy/video.md`. Needs `core`; voice, music and recording clean-up come from
`audio`.

```
/plugin install video --marketplace BinaryBuddiesOrg/claude-hv-skills
/plugin install audio --marketplace BinaryBuddiesOrg/claude-hv-skills
```

Status: **draft — every capability shipped, none yet eval-tested** (see `../../ROADMAP.md`).

| Skill | Role | What it does |
|---|---|---|
| `director` | intake | parse → inventory → probe → one question round with Auto → brief + plan → hand-off → relay the report |
| `script` | stage | beats.json: hook, beats, voice lines, on-screen text, visuals, timing at a real pace |
| `captions` | stage | SRT/ASS at the video's resolution, social/clean/minimal/karaoke, safe zones, fonts by script, local transcription |
| `motion` | stage | per-beat zoom/pan clips, phone/browser frames, animated text, title/lower-third/end cards, badges |
| `assemble` | stage | timeline.json → one edit: segments, dissolves, voice, ducked music, sfx, captions, overlays |
| `platform-export` | stage | export for 10 destinations, 13-row spec check with loudness, contact sheet with safe zones |
| `screencast-motion` | style | app/software videos from screen recordings |
| `clips-to-short` | style | footage → short: scene/energy/transcript selection, exact cuts, reframe |
| `slideshow` | style | photos/slides → video with Ken Burns, dissolves, chapters |
| `talking-head-broll` | style | jump cuts, filler removal, b-roll inserts, lower third |
| `audiogram` | style | audio → video with cover, moving waveform, captions |
| `lyric` | style | lyrics timed to the song (LRC / aligned / spread), karaoke or reveals |
| `kinetic-typography` | style | text as the picture: grouped beats, word reveal, emphasis |
| `explainer-animated` | style | diagram beats (steps, numbers, arrows, charts) via ffmpeg cards or Remotion |
| `ai-shots` | style | shot lists and prompts for the user's AI video tool, clip verification, assembly (also anime/cartoon) |

Evals: `evals/<skill>/<case>/`.
