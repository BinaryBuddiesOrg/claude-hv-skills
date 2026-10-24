---
tags: [video, director]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash, AskUserQuestion]
---

I need a promo video for my coffee ordering app. I've got screen recordings of the app in ./rec/ (three .mp4 files, each around 20 seconds, 1080x2340 portrait phone captures). Dont ask me a million questions, just figure out what you need and go — I'm happy with auto for most things. If ./rec is empty, generate three 20s test clips there with ffmpeg testsrc at 1080x2340 so you have something to work with.
