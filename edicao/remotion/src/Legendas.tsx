import { Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { Bloco, CORES, FONTE } from "./tipos";

// Legenda de 2 a 3 palavras: o bloco entra com um "pop" e a palavra que está sendo dita cresce um pouco.
const BlocoLegenda: React.FC<{ bloco: Bloco }> = ({ bloco }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const agora = bloco.ini + frame / fps;
  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        right: 80,
        bottom: 600,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "baseline",
        columnGap: 40,
        fontFamily: FONTE,
        fontWeight: 900,
        fontSize: 84,
        lineHeight: 1.08,
        textAlign: "center",
        scale: interpolate(frame, [0, 5], [0.86, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.34, 1.56, 0.64, 1),
        }),
        opacity: interpolate(frame, [0, 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}
    >
      {bloco.palavras.map((p, i) => {
        const falando = agora >= p.ini - 0.02 && agora < p.fim + 0.05;
        return (
          <span
            key={i}
            style={{
              color: p.destaque ? CORES.amarelo : "#FFFFFF",
              WebkitTextStroke: "12px #000",
              paintOrder: "stroke fill",
              textShadow: "0 6px 14px rgba(0,0,0,.45)",
              display: "inline-block",
              scale: falando ? 1.05 : 1,
              translate: falando ? "0px -4px" : "0px 0px",
            }}
          >
            {p.texto}
          </span>
        );
      })}
    </div>
  );
};

export const Legendas: React.FC<{ blocos: Bloco[]; total: number }> = ({ blocos, total }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {blocos.map((b, i) => {
        const ini = Math.round(b.ini * fps);
        const fim = Math.min(Math.round(b.fim * fps), Math.round(total * fps));
        if (fim <= ini) return null;
        return (
          <Sequence key={i} name={`Legenda ${i + 1}`} from={ini} durationInFrames={fim - ini} layout="none">
            <BlocoLegenda bloco={b} />
          </Sequence>
        );
      })}
    </>
  );
};
