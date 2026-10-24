# Prompting for AI video

## Contents

The formula · Order inside a prompt · Vocabulary · Genre blocks · Anime / cartoon block
· Consistency · Negatives · Durations and cuts

## The formula

`[SHOT TYPE + ANGLE] + [SUBJECT + ACTION] + [ENVIRONMENT + LIGHTING] + [CAMERA MOVEMENT] + [MOOD / STYLE]`

Directive, not descriptive: "Medium close-up, eye level — a woman in her 30s, short
black hair, red wool coat, lifts a paper cup and smiles at someone off-frame. Rain-wet
Lisbon street at blue hour, neon reflections, practical shop lights. Slow steadicam
push-in. Warm, hopeful. 35 mm, shallow depth of field, soft film grain, 24 fps."

## Order inside a prompt (adherence improves in this order)

1. environment (where, when, weather) 2. subject (who/what, appearance, position)
3. action (specific verbs) 4. camera (shot type → angle → movement) 5. lighting
(source, quality, direction) 6. style (genre, stock, fps, aspect)

## Vocabulary

Shots: ECU, CU, MCU, MS, MLS, LS, EWS/establishing. Angles: eye level, low, high,
over-the-shoulder, top-down, dutch. Moves: dolly in/out, tracking, pan, tilt, crane,
orbit, handheld, steadicam, locked-off, rack focus. Light: golden hour, blue hour,
Rembrandt, hard side light, chiaroscuro, volumetric/god rays, practical lights, overcast
soft, silhouette, neon. Style: 24 fps film, anamorphic flares, 2.39:1 letterbox,
documentary handheld, commercial clean, 16 mm grain.

## Genre blocks (append to style)

- **Cinematic drama**: "35 mm film grain, anamorphic, 24 fps, letterbox 2.39:1, muted palette."
- **Commercial / product**: "clean studio, three-point lighting, slow smooth orbit, premium, editorial."
- **Documentary / nature**: "natural diffused light, locked-off or slow push, true colours."
- **Action**: "handheld, slight shake, motion blur on fast elements, 60 fps slow-motion burst on the key moment."
- **Sci-fi**: "volumetric neon, atmospheric haze, holographic elements, anamorphic flares."

## Anime / cartoon block

"2D anime style, clean line art, flat cel shading with two-tone shadows, limited
animation (12 fps feel), consistent character design: [character sheet], soft
painterly background, no photorealism, no 3D render look, no text." For a webtoon
look: "vertical panel composition, bold outlines, pastel palette." Generate a
**character sheet image** first (front, three-quarter, expressions) in the user's
image tool and attach it as the reference to every shot that has the character.

## Consistency

- `anchors.json` text repeated verbatim in every prompt: character(s), wardrobe,
  palette, lens, time of day, film style.
- One reference image per recurring subject, attached to every shot that shows it.
- Same tool for all shots of one scene; mixing tools mixes looks.
- Keep lighting continuity inside a scene (all blue hour or all golden hour).
- Name the off-frame logic ("smiles at someone off-frame") so eyelines match across shots.

## Negatives (always)

"no text, no captions, no logos, no watermark, no extra people, no distorted hands,
no morphing, no sudden cuts, no camera shake" — plus the redo reason when a shot is redone.

## Durations and cuts

Tools make 4–20 s clips; a beat needs its `duration_s` + 0.5 s of handle. Plan one
shot per beat; a beat longer than the tool's max becomes two shots with a cut on
action. Trailers cut 1–3 s from 5 s shots; explainers hold 4–6 s.
