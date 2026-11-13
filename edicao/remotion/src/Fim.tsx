import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Simbolo } from "./Simbolo";
import { CORES, FONTE } from "./tipos";

const entrar = (frame: number, atraso: number) => ({
  opacity: interpolate(frame - atraso, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
  translate: interpolate(frame - atraso, [0, 10], ["0px 30px", "0px 0px"], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  }),
});

// O bordão em letra grande, no meio da tela, enquanto o Heitor fala "Sem alarde. Eu sou só o termômetro!"
export const Bordao: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div style={{ position: "absolute", top: 1130, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          maxWidth: 960,
          background: "rgba(14,20,27,.88)",
          border: "2px solid rgba(242,193,78,.6)",
          borderRadius: 40,
          padding: "34px 48px 38px",
          fontFamily: FONTE,
          color: CORES.texto,
          textAlign: "center",
          boxShadow: "0 16px 50px rgba(0,0,0,.4)",
          opacity: interpolate(frame, [0, 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          scale: interpolate(frame, [0, 8], [0.8, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.34, 1.56, 0.64, 1),
          }),
        }}
      >
        <Simbolo tamanho={110} varrer atraso={2} />
        <div style={{ fontWeight: 800, fontSize: 58, color: CORES.apagado, lineHeight: 1.1 }}>Sem alarde.</div>
        <div style={{ fontWeight: 900, fontSize: 82, lineHeight: 1.05, letterSpacing: "-.01em" }}>
          Eu sou só o <span style={{ color: CORES.amarelo }}>termômetro!</span>
        </div>
      </div>
    </div>
  );
};

// A tela final de 3 s: o ponteiro do medidor varre, o convite sobe linha a linha e o botão "Seguir" pulsa.
export const TelaFinal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(circle at 50% 38%, #1A2430 0%, #0E141B 62%)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 18,
        fontFamily: FONTE,
        color: CORES.texto,
        textAlign: "center",
        opacity: interpolate(frame, [0, 7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}
    >
      <Simbolo tamanho={260} varrer atraso={3} />
      <div style={{ fontWeight: 700, fontSize: 64, color: CORES.apagado, marginTop: 30, ...entrar(frame, 6) }}>Siga o</div>
      <div style={{ fontWeight: 900, fontSize: 86, letterSpacing: "-.01em", ...entrar(frame, 10) }}>@termometrodecrise</div>
      <div style={{ fontWeight: 600, fontSize: 50, lineHeight: 1.25, color: "#C9D3DE", marginTop: 6, ...entrar(frame, 14) }}>
        para atualizações diárias
        <br />
        do mercado financeiro
      </div>
      <div
        style={{
          marginTop: 46,
          background: CORES.amarelo,
          color: "#0B1220",
          fontWeight: 900,
          fontSize: 56,
          borderRadius: 999,
          padding: "22px 84px",
          ...entrar(frame, 18),
          scale: 1 + 0.045 * Math.max(0, Math.sin(((frame - 26) / fps) * Math.PI * 2.2)) * (frame > 26 ? 1 : 0),
        }}
      >
        Seguir
      </div>
      {/* Desde 13/11 a apresentação e o aviso não são mais falados: ficam aqui, na tela final. */}
      <div style={{ fontWeight: 600, fontSize: 34, lineHeight: 1.3, color: CORES.apagado, marginTop: 40, ...entrar(frame, 22) }}>
        Eu sou o Heitor, do Termômetro de Crise.
        <br />
        Não recomendamos: só mostramos a temperatura do mundo.
      </div>
    </AbsoluteFill>
  );
};
