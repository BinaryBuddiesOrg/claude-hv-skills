# Inventory of screen recordings

Before the script claims anything, write what the recordings show. One line per
2–6 s span, from a 4×3 contact sheet (`look.py REC -o work/look/rec_a.png --tiles 4x3`)
and the probe:

```
rec/a.mp4  20.1 s  1080x2340 30fps VFR
  00.0–05.8  onboarding: welcome screen, "Get started" button (lower third)
  05.8–11.2  menu: list of drinks, scrolling
  11.2–16.0  drink detail: size selector, "Add" button (bottom right)
  16.0–20.1  cart: total, "Pay" button (bottom centre)
rec/b.mp4 …
```

Then map each script beat to one span: `visual.source`, `in_s` (span start + 0.3 s),
`focus` from the element's position on the sheet (x and y as fractions of the frame —
"bottom centre" ≈ `[0.5, 0.85]`, "top right" ≈ `[0.8, 0.12]`), `zoom` by what the beat
needs (overview 1.0–1.2, tap 1.5, text field 1.7). A beat that no span supports is
rewritten, not faked.

Keep `work/inventory.md` in the job folder: a re-render after "show the loyalty screen
instead" starts from it, not from re-watching everything.
