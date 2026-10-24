# Built-in SFX (synthesised with ffmpeg)

When the user has no sound pack, `music.py sfx --synth NAME -o file.wav` writes one of
these. They are deliberately simple and clean; a licensed pack always sounds better.

| Name | How it is made | Use |
|---|---|---|
| `whoosh` | filtered white noise, 0.5 s, band-pass sweep 300 → 4000 Hz, fast fade | titles flying in, transitions |
| `pop` | 80 ms sine at 900 Hz with a pitch drop and 10 ms attack | words appearing, icons |
| `click` | 20 ms noise burst, high-pass 2 kHz | UI taps in screencasts |
| `riser` | 2 s noise with a rising band-pass and a crescendo | before a reveal |
| `ding` | 1.2 s sine 1320 Hz + 2640 Hz harmonic, long decay | success, checkmarks |
| `thud` | 150 ms sine 60 → 40 Hz, fast decay | impacts, logo lands |

Cue names in `beats.json` (`beat.sfx`) map to these when no path is given. All are
written at 48 kHz mono, peak −6 dBFS.

## Adding the user's packs

Point `music.py sfx --pack DIR` at a folder of WAV/MP3s; cue names resolve by file-name
prefix (`whoosh-01.wav` serves `whoosh`). Record the pack's licence in the brief.
