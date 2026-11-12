import { Video } from "@remotion/media";
import { AbsoluteFill, CalculateMetadataFunction, Sequence, staticFile, useVideoConfig } from "remotion";
import { Cartoes } from "./Cartoes";
import { Bordao, TelaFinal } from "./Fim";
import { Legendas } from "./Legendas";
import { Simbolo } from "./Simbolo";
import { Som } from "./Som";
import { Camadas, CORES, FONTE } from "./tipos";

const Selo: React.FC = () => {
  return (
    <div
      style={{
        position: "absolute",
        left: 48,
        top: 150,
        display: "flex",
        alignItems: "center",
        gap: 14,
        background: "rgba(14,20,27,.78)",
        borderRadius: 999,
        padding: "10px 22px 10px 14px",
        fontFamily: FONTE,
        fontWeight: 800,
        fontSize: 28,
        letterSpacing: ".06em",
        color: CORES.texto,
        opacity: 0.9, // já no primeiro quadro (a capa)
      }}
    >
      <Simbolo tamanho={46} />
      TERMÔMETRO DE CRISE
    </div>
  );
};

export const Reel: React.FC<Camadas> = ({ video, total, legendas, cartoes, bordao, sons = true }) => {
  const { fps } = useVideoConfig();
  const fimVideo = Math.round(total * fps);
  return (
    <AbsoluteFill style={{ backgroundColor: CORES.fundo }}>
      <Sequence name="Vídeo" durationInFrames={fimVideo}>
        <Video src={staticFile(video)} objectFit="cover" style={{ width: "100%", height: "100%" }} />
        <Selo />
        <Cartoes cartoes={cartoes} total={total} sons={sons} />
        <Legendas blocos={legendas} total={total} />
        {bordao ? (
          <Sequence
            name="Bordão"
            from={Math.round(bordao.ini * fps)}
            durationInFrames={Math.max(1, Math.min(Math.round((bordao.fim + 0.6) * fps), fimVideo) - Math.round(bordao.ini * fps))}
            layout="none"
          >
            <Bordao />
            {sons ? <Som som="bordaoWhoosh" /> : null}
            {sons ? (
              <Sequence from={Math.round(0.45 * fps)} layout="none">
                <Som som="bordaoHit" />
              </Sequence>
            ) : null}
          </Sequence>
        ) : null}
      </Sequence>
      <Sequence name="Tela final" from={fimVideo}>
        <TelaFinal />
        {sons ? (
          <Sequence from={Math.round(0.5 * fps)} layout="none">
            <Som som="seguir" />
          </Sequence>
        ) : null}
      </Sequence>
    </AbsoluteFill>
  );
};

export const calcularReel: CalculateMetadataFunction<Camadas> = ({ props }) => ({
  durationInFrames: Math.max(1, Math.round((props.total + props.final) * 30)),
  fps: 30,
});
