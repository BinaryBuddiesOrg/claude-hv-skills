# Motion reference

## Contents

Moves · zoompan · Frames · Backgrounds · Text sizes and positions · ASS animation tags
· Cards

## Moves (`beat.visual.motion`)

| Motion | What happens | Default zoom |
|---|---|---|
| `push-in` | zoom from 1.0 to `zoom`, anchored on `focus` | 1.15 (footage), 1.4 (screen) |
| `pull-out` | zoom from `zoom` to 1.0 | 1.15 |
| `hold` | static at `zoom` on `focus` | 1.0 |
| `pan-left` / `pan-right` | at `zoom`, the view slides horizontally across the frame | 1.2 |
| `ken-burns` | slow push-in with a slight drift toward `focus` (photos) | 1.12 |

`focus` is `[x, y]` in 0–1 of the *source* frame; the point stays where it is while the
view tightens around it.

## zoompan

`zoompan=z='<expr>':x='<fx>*(iw-iw/zoom)':y='<fy>*(ih-ih/zoom)':d=1:s=WxH:fps=F` on a
video conformed to the target aspect and upsampled 1.5× (`scale=iw*1.5:ih*1.5`) to hide
integer rounding. `on` is the output frame index, `N` the frame count:
push-in `z='min(1+(Z-1)*on/N,Z)'`, pull-out `z='max(Z-(Z-1)*on/N,1)'`, pan-right
`x='(iw-iw/zoom)*on/N'`. Photos use the same filter with `d=N` on a single image input.

## Frames

| Frame | Inner box | Corner radius | Bezel | Notes |
|---|---|---|---|---|
| `phone` | fits inside 84 % × 82 % of the canvas, source aspect kept | 5 % of inner width | 2 % of inner width, `#15181d` | portrait recordings on 9:16 |
| `browser` | fits inside 90 % × 80 % | 1.5 % | 1 % + a 3.6 % top bar `#2a2f36` | desktop captures on 16:9 |
| `none` | the full canvas (cover crop on focus, or pad) | — | — | footage, photos |

Rounded corners: a white RGBA mask the size of the inner box, alpha from a rounded-rect
`geq` expression, rendered once to PNG and applied with `alphamerge`; the bezel is the
same mask in the bezel colour, slightly larger, overlaid first.

## Backgrounds (`--bg`)

`blur` — the clip itself scaled to cover the canvas, `boxblur=30:3`, darkened 25 %;
`#RRGGBB` — solid; `gradient` — `gradients=s=WxH:c0=#141821:c1=#2b3244:x0=0:y0=0:x1=0:y1=H`
(diagonal when `--gradient-angle` is set).

## Text sizes and positions (ASS, PlayRes = canvas)

| Element | Size | Position (`\an` + `\pos`) |
|---|---|---|
| on-screen line (`kinetic`) | 0.09 × min(W, H) | `center`: (W/2, H×0.46); `lower`: (W/2, H×(1−bottom_zone)−1.4×size); `upper`: (W/2, H×0.22) |
| title | 0.11 × min(W, H) (+ subtitle 0.045) | centre |
| lower third | name 0.05 × min, role 0.035 × min | `\an1` at (W×0.06, H×0.80) |
| end card | text 0.08 × min, url 0.05 × min in accent | centre, url 1.6 × size below |
| caption band (from video:captions) | 0.042 × H | bottom, above the safe zone |

Line length: wrap `on_screen` at 14 characters per line on 9:16, 24 on 16:9 (two lines
max — the script's word limits keep it there).

## ASS animation tags used

- pop-in: `{\an5\pos(x,y)\fad(120,160)\fscx80\fscy80\t(0,140,\fscx100\fscy100)}`
- word reveal: each word `{\alpha&HFF&\t(t1,t2,\alpha&H00&)}word` with t1 = 300 + i×110 ms
- emphasis `*word*`: `{\b1\c&H<accent BGR>&}word{\b0\c&HFFFFFF&}`
- lower third slide: `{\an1\move(x-80,y,x,y,0,220)\fad(150,150)}`
- end card: title `\fad(200,0)`, url `\fad(500,0)` 0.4 s later
- outline 3 px at 1080p (`ScaledBorderAndShadow: yes`), shadow 0

## Cards (`cards.py`)

PNG with alpha for timeline overlays: `end` (text + url + optional logo), `title`,
`badge` (logo resized, 8 px padding, optional 50 % black rounded plate). Text via
`drawtext` (Latin scripts); for other scripts make the card as an ASS event instead.
