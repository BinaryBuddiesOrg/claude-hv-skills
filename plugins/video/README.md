# video

The video plugin. Entry point: `/video:director` (triggers on any video request).
Executor: the `video:producer` agent. Capabilities: `capabilities.json`. Universe:
`../../taxonomy/video.md`.

Status: **draft — Phase 1 in progress**. No skill works yet; see `../../ROADMAP.md`.

```
/plugin install video --marketplace BinaryBuddiesOrg/claude-hv-skills
```

```
skills/director/           intake → brief → plan → hand-off
skills/screencast-motion/  recordings → framed, zoomed, captioned video
skills/clips-to-short/     footage → 9:16 short
skills/slideshow/          images → video
skills/captions/           SRT / burn-in / transcription
skills/platform-export/    destination specs, checks, contact sheet
agents/producer.md         probe → act → verify executor
evals/<skill>/<case>/      claude plugin eval cases
```

Needs the `core` plugin (doctor, brief, deliver) and, for voice-over, `audio`.
