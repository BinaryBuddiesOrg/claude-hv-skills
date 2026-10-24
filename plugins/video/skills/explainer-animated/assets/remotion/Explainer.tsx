// Explainer composition: renders Studio beats.json diagram beats with easing.
// Place beats.json in public/; register this component in src/Root.tsx (see README.md).
import React from "react";
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Sequence } from "remotion";

type Item = { label: string; icon?: string; value?: number };
type Diagram = { kind: string; items?: Item[]; value?: number; unit?: string; label?: string; from?: string; to?: string; before?: Item; after?: Item; text?: string; by?: string; accent?: string };
type Beat = { id: string; start_s: number; duration_s: number; on_screen?: string; visual?: { diagram?: Diagram } };
type Beats = { beats: Beat[]; aspect?: string };

const bg = "#0b0f19";
const fg = "#ffffff";

const Steps: React.FC<{ d: Diagram; frame: number; fps: number; vertical: boolean }> = ({ d, frame, fps, vertical }) => (
  <div style={{ display: "flex", flexDirection: vertical ? "column" : "row", gap: 48, alignItems: "center", justifyContent: "center", height: "100%" }}>
    {(d.items ?? []).map((it, i) => {
      const s = spring({ frame: frame - i * Math.round(0.4 * fps), fps, config: { damping: 14 } });
      return (
        <div key={i} style={{ transform: `scale(${s})`, opacity: s, background: "#161b2a", border: `3px solid ${d.accent ?? "#FFD400"}`, borderRadius: 24, padding: "28px 40px", minWidth: 260, textAlign: "center" }}>
          <div style={{ color: d.accent ?? "#FFD400", fontSize: 44, fontWeight: 800 }}>{i + 1}</div>
          <div style={{ color: fg, fontSize: 40, fontWeight: 700 }}>{it.label}</div>
        </div>
      );
    })}
  </div>
);

const Num: React.FC<{ d: Diagram; frame: number; fps: number }> = ({ d, frame, fps }) => {
  const v = Math.round(interpolate(frame, [0, 0.8 * fps], [0, d.value ?? 0], { extrapolateRight: "clamp" }));
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%" }}>
      <div style={{ color: d.accent ?? "#FFD400", fontSize: 220, fontWeight: 900, lineHeight: 1 }}>{v}{d.unit ?? ""}</div>
      <div style={{ color: fg, fontSize: 56, fontWeight: 600, marginTop: 24 }}>{d.label}</div>
    </div>
  );
};

const Label: React.FC<{ text?: string }> = ({ text }) => (
  <div style={{ position: "absolute", bottom: "18%", width: "100%", textAlign: "center", color: fg, fontSize: 72, fontWeight: 800, textShadow: "0 0 12px #000" }}>{text}</div>
);

export const Explainer: React.FC<{ beatsPath: string }> = ({ beatsPath }) => {
  const [data, setData] = React.useState<Beats | null>(null);
  const { fps } = useVideoConfig();
  React.useEffect(() => { fetch(staticFile(beatsPath)).then((r) => r.json()).then(setData); }, [beatsPath]);
  if (!data) return <AbsoluteFill style={{ background: bg }} />;
  const vertical = data.aspect === "9:16";
  return (
    <AbsoluteFill style={{ background: bg, fontFamily: "Inter, Arial, sans-serif" }}>
      {data.beats.map((b) => (
        <Sequence key={b.id} from={Math.round(b.start_s * fps)} durationInFrames={Math.max(1, Math.round(b.duration_s * fps))}>
          <BeatView beat={b} fps={fps} vertical={vertical} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const BeatView: React.FC<{ beat: Beat; fps: number; vertical: boolean }> = ({ beat, fps, vertical }) => {
  const frame = useCurrentFrame();
  const d = beat.visual?.diagram;
  return (
    <AbsoluteFill>
      {d?.kind === "steps" && <Steps d={d} frame={frame} fps={fps} vertical={vertical} />}
      {d?.kind === "number" && <Num d={d} frame={frame} fps={fps} />}
      {(!d || !["steps", "number"].includes(d.kind)) && <Label text={beat.on_screen} />}
      {d && ["steps", "number"].includes(d.kind) && beat.on_screen && <Label text={beat.on_screen} />}
    </AbsoluteFill>
  );
};
