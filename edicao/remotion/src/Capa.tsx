import { AbsoluteFill, Img, staticFile } from "remotion";
import { Simbolo } from "./Simbolo";
import { CORES, FONTE } from "./tipos";

// Capa do Reel no estilo "texto gigante" (teste de 12/11): o rosto do Heitor e 2 a 4 palavras enormes.
// Palavras entre *asteriscos* ficam em amarelo.
export type DadosCapa = { foto: string; texto: string };

export const Capa: React.FC<DadosCapa> = ({ foto, texto }) => {
  const partes = texto.split(/(\*[^*]+\*)/g).filter(Boolean);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Img src={staticFile(foto)} style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.7 }} />
      <AbsoluteFill
        style={{ background: "linear-gradient(180deg, rgba(8,12,17,0) 0%, rgba(8,12,17,0) 45%, rgba(8,12,17,.6) 65%, rgba(8,12,17,.9) 100%)" }}
      />
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
        }}
      >
        <Simbolo tamanho={46} />
        TERMÔMETRO DE CRISE
      </div>
      <div
        style={{
          position: "absolute",
          left: 60,
          right: 60,
          bottom: 330,
          fontFamily: FONTE,
          fontWeight: 900,
          fontSize: 150,
          lineHeight: 0.98,
          letterSpacing: "-.02em",
          color: "#FFFFFF",
          textAlign: "center",
          textShadow: "0 10px 30px rgba(0,0,0,.55)",
          WebkitTextStroke: "4px rgba(0,0,0,.35)",
          paintOrder: "stroke fill",
        }}
      >
        {partes.map((p, i) =>
          p.startsWith("*") ? (
            <span key={i} style={{ color: CORES.amarelo }}>
              {p.slice(1, -1).replace(/ /g, "\u00a0").replace(/-/g, "\u2011")}
            </span>
          ) : (
            <span key={i}>{p}</span>
          ),
        )}
      </div>
    </AbsoluteFill>
  );
};
