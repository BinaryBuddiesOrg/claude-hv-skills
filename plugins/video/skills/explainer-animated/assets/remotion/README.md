# Remotion route (optional, richer motion)

Everything here is run by the user, on their machine, after the Director offers it.
Studio does not install Node packages on its own.

## Scaffold

```
npm create video@latest -- --template blank studio-explainer   # pick the "Blank" template
cd studio-explainer && npm install
```

Pin the Remotion version the template gives you in `package.json`; do not float `latest`
across a project.

## Composition

Copy `Explainer.tsx` from this folder into `src/`, register it in `src/Root.tsx` as
`<Composition id="Explainer" component={Explainer} durationInFrames={…} fps={30} width={1920} height={1080} defaultProps={{ beatsPath: "beats.json" }} />`,
and place the job's `beats.json` (and `brand/` icons) in `public/`. The composition
reads the beats and renders each `visual.diagram` kind with spring easing, item reveals
and counting numbers at the beat's `start_s`.

## Render

```
npx remotion render Explainer out/explainer.mp4 --codec h264 --crf 18
```

Then back in Studio: `video:captions` → `audio:music` → `video:assemble` (the Remotion
file is one `video` segment) → `video:platform-export`.

## Pitfalls

- Fonts: load with `@remotion/google-fonts` or a local `@font-face`; the system font
  differs between machines.
- Duration: `durationInFrames = ceil(total_s × fps)`; the composition reads `total_s`
  from the beats so a retime needs no code change.
- 60 fps looks nicer in the preview and doubles render time; 30 fps for delivery.
- Keep Remotion's output as an intermediate; loudness and platform specs are applied by
  `platform-export`.
