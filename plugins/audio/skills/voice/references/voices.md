# Voices

## Default voice per language (piper)

piper voice names are `<locale>-<speaker>-<quality>`; `medium` is the CPU sweet spot
(`low` is faster and flatter, `high` is slower and only slightly better). Download the
`.onnx` and `.onnx.json` pair for a voice from the piper voices index (Hugging Face,
`rhasspy/piper-voices`) into `${CLAUDE_PLUGIN_DATA}/piper/voices/`.

| Language | Default | Alternatives |
|---|---|---|
| en (US) | `en_US-amy-medium` | `en_US-lessac-medium` (neutral male), `en_US-ryan-high` |
| en (GB) | `en_GB-alan-medium` | `en_GB-jenny_dioco-medium` |
| es | `es_ES-davefx-medium` | `es_MX-claude-high` |
| fr | `fr_FR-siwis-medium` | `fr_FR-upmc-medium` |
| de | `de_DE-thorsten-medium` | `de_DE-eva_k-x_low` |
| pt (BR) | `pt_BR-faber-medium` | — |
| hi | `hi_IN-pratham-medium` *(unverified)* | — |
| it | `it_IT-riccardo-x_low` | — |
| ja | no piper default — use macOS `say -v Kyoko` or add a voice when one is vetted | — |
| zh | `zh_CN-huayan-medium` | — |

Names marked unverified have not been proven on a Studio machine; `tts.py voices` only
lists voices that are actually present, so a missing default is reported, never
assumed. Check each voice's licence card before commercial use.

## macOS `say`

`say -v ?` lists installed voices with their locales ("Samantha en_US", "Daniel en_GB",
"Kyoko ja_JP", "Lekha hi_IN"). Quality is good for English; enhanced/premium voices are
downloaded in System Settings → Accessibility → Spoken Content.

## espeak-ng

Intelligible in ~100 languages, unmistakably synthetic. Fine for drafts, timing tests
and accessibility; say so in the report when it is the engine used.

## Timing

TTS at 150 wpm is a planning estimate. The truth is the file: `tts.py beats` measures
each line and writes `measured_voice_s`; `script.py time --measured --write` makes the
beats exactly as long as their lines plus a 0.3 s breath. Never trust the estimate for
the final render — a 7-beat promo can drift 3–4 s.

## A good sample line

Pick the beat with a brand name, a number and a comma — the three things engines get
wrong — and let the user hear that one before synthesising the whole script.
