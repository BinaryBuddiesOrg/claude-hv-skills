# AI video tools (2026 snapshot — newadder re-vets this table)

Studio never calls these; the user generates in their own account and drops clips into
`work/ai/`. Numbers are planning constraints, not promises.

| Tool | Clip length | Aspects | Reference image | Native audio | Strength | Notes |
|---|---|---|---|---|---|---|
| Google Veo 3.1 | 8 s native, extend to 60 s+ | 16:9, 9:16 | yes (image-to-video) | yes | realism, marketing, 4K | native audio is good for ambience; drop under a voice-over |
| Runway Gen-4.5 | 5–10 s | 16:9, 9:16, 1:1 | yes, strong character refs | optional | control, consistency, in-video edits (Aleph) | best for recurring characters/products |
| Kling 3.0 | 5–15 s, multi-shot | 16:9, 9:16, 1:1 | yes | yes, lip-sync | motion, humans, price | multi-shot prompts can carry a whole scene |
| Seedance 2.0 | 15–20 s | 16:9, 9:16 | yes | synced | narrative multi-shot | longest native clips |
| Pika 2.5 | 5–10 s | 16:9, 9:16, 1:1 | yes | lip-sync (Pikaformance) | social effects, cheap entry | effects presets (Pikaffects) |
| PixVerse V6 | 5–8 s | 16:9, 9:16 | yes | no | free tier, cinematic controls | good for tests before paying |
| HeyGen | any (avatar) | 16:9, 9:16 | avatar from photo | yes | talking head / avatar | not a scene generator |
| Local: Wan 2.x / CogVideoX / AnimateDiff pipelines | 2–6 s | varies | varies | no | offline, free per clip | ≥ 12–24 GB VRAM, minutes per clip; heavy route in TOOLBOX |

Sora: discontinued for web/app in April 2026; do not plan on it.

## Choosing

| Need | First choice | Because |
|---|---|---|
| cinematic story, recurring character | Runway | reference consistency |
| realistic marketing, 16:9 long shots | Veo | extension, 4K, realism |
| people moving, dance, sport | Kling | motion quality, cost |
| one scene with several shots | Seedance or Kling multi-shot | continuity in one generation |
| social effects, low budget | Pika or PixVerse | price |
| anime / cartoon | Kling or Runway with a character-sheet reference | 2D style adherence with references |

`shots.py --tool` rounds each shot's duration up to the tool's native lengths and marks
reference slots where the tool supports them.
