import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Easing,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Bordao } from "./Fim";
import { Simbolo } from "./Simbolo";
import { CORES, FONTE } from "./tipos";

// Reel só de motion, sem o Heitor gravar (13/11, inspirado no da nota de R$ 100 do Tiago Reis, que é só música e
// texto). A nota de R$ 100 perde poder de compra ano a ano pelo IPCA (IBGE). Todo número vem dos props (dado
// oficial conferido); o carrinho é ilustração da proporção, e a tela diz isso. A música entra no app, ao postar.
export type DadosInflacao = {
  anoBase: number; // o carrinho cheio é o do começo deste ano
  anos: { ano: number; taxa: number }[]; // IPCA de cada ano (o último pode ser parcial)
  ultimoRotulo: string; // "2026 (até outubro)"
  itens: string[]; // 10 emojis do carrinho
  fonte: string;
  pergunta: string;
  sons?: boolean;
};

const EMOJI = "'Noto Color Emoji', sans-serif";
const POR_ANO = 1.15; // segundos em cada ano
const INICIO_ANOS = 3.2;
const brl = (v: number, casas = 0) =>
  "R$ " + v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
const pct = (v: number) => v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + "%";

export const tempos = (d: DadosInflacao) => {
  const fimAnos = INICIO_ANOS + d.anos.length * POR_ANO;
  const revela = fimAnos + 0.3;
  const pergunta = revela + 4.6;
  const bordao = pergunta + 3.2;
  const total = bordao + 3.4;
  return { fimAnos, revela, pergunta, bordao, total };
};

export const calcularInflacao: CalculateMetadataFunction<DadosInflacao> = ({ props }) => ({
  durationInFrames: Math.round(tempos(props).total * 30),
});

const surge = (frame: number, atraso: number, fps: number) =>
  spring({ frame: frame - atraso, fps, config: { damping: 14, stiffness: 170 } });

const Nota: React.FC<{ escala: number; desbotar: number }> = ({ escala, desbotar }) => (
  <div
    style={{
      width: 620,
      height: 300,
      borderRadius: 26,
      background: `linear-gradient(135deg, #5FA8D8, #2E6E9E)`,
      border: "6px solid rgba(255,255,255,.55)",
      boxShadow: "0 24px 60px rgba(0,0,0,.45)",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 46px",
      boxSizing: "border-box",
      transform: `scale(${escala}) rotate(-3deg)`,
      filter: `saturate(${1 - 0.75 * desbotar}) brightness(${1 - 0.25 * desbotar})`,
      fontFamily: FONTE,
      color: "#fff",
    }}
  >
    <div style={{ fontWeight: 900, fontSize: 150, letterSpacing: "-.03em", textShadow: "0 6px 0 rgba(0,0,0,.18)" }}>100</div>
    <div style={{ textAlign: "right" }}>
      <div style={{ fontWeight: 800, fontSize: 44, opacity: 0.9 }}>CEM</div>
      <div style={{ fontWeight: 800, fontSize: 44, opacity: 0.9 }}>REAIS</div>
      <div style={{ fontWeight: 900, fontSize: 64 }}>R$</div>
    </div>
  </div>
);

export const MotionInflacao: React.FC<DadosInflacao> = (d) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const T = tempos(d);

  // fator acumulado até cada ano e quantos itens sobram no carrinho
  const fatores = d.anos.reduce<number[]>((acc, a) => [...acc, (acc.length ? acc[acc.length - 1] : 1) * (1 + a.taxa / 100)], []);
  const fatorFinal = fatores[fatores.length - 1] ?? 1;
  const idxAno = Math.min(d.anos.length - 1, Math.floor((t - INICIO_ANOS) / POR_ANO));
  const noAno = t >= INICIO_ANOS ? idxAno : -1;
  const fatorAgora = noAno >= 0 ? fatores[noAno] : 1;
  const itensAgora = Math.round(d.itens.length / fatorAgora);
  const poder = 100 / fatorAgora;

  const fundo = (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 30%, #1A2A3A 0%, ${CORES.fundo} 70%)` }} />
  );

  // ---------- abertura e anos ----------
  const cenaPrincipal = t < T.revela;
  const titulo = surge(frame, 0, fps);
  const notaEscala = 0.9 + 0.1 * surge(frame, 2, fps);
  const desbotar = interpolate(fatorAgora, [1, fatorFinal], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto }}>
      {fundo}
      {/* selo da marca */}
      <div
        style={{
          position: "absolute", top: 120, left: 0, right: 0, display: "flex", justifyContent: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14, background: "rgba(14,20,27,.8)", borderRadius: 999,
          padding: "10px 24px 10px 14px", fontWeight: 800, fontSize: 28, letterSpacing: ".06em" }}>
          <Simbolo tamanho={44} />
          TERMÔMETRO DE CRISE
        </div>
      </div>

      {cenaPrincipal ? (
        <>
          <div style={{ position: "absolute", top: 230, left: 60, right: 60, textAlign: "center", fontWeight: 900,
            fontSize: 84, lineHeight: 1.05, letterSpacing: "-.02em", opacity: titulo, transform: `translateY(${(1 - titulo) * 30}px)` }}>
            {noAno < 0 ? (
              <>A mesma nota de <span style={{ color: CORES.amarelo }}>{"R$\u00a0100"}</span>…</>
            ) : (
              <>
                <span style={{ color: CORES.amarelo }}>{"R$\u00a0100"}</span> hoje valem
              </>
            )}
          </div>
          {noAno >= 0 ? (
            <div style={{ position: "absolute", top: 330, left: 0, right: 0, textAlign: "center", fontWeight: 900, fontSize: 130,
              color: poder < 80 ? "#FF6B5E" : CORES.texto, letterSpacing: "-.03em" }}>
              {brl(poder, 2)}
              <div style={{ fontSize: 40, fontWeight: 700, color: CORES.apagado, letterSpacing: 0 }}>em dinheiro de {d.anoBase}</div>
            </div>
          ) : null}

          <div style={{ position: "absolute", top: 640, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
            <Nota escala={notaEscala} desbotar={desbotar} />
          </div>

          {/* ano e inflação do ano */}
          {noAno >= 0 ? (
            <Sequence from={Math.round((INICIO_ANOS + noAno * POR_ANO) * fps)} key={noAno} layout="none">
              <AnoChip ano={noAno === d.anos.length - 1 ? d.ultimoRotulo : String(d.anos[noAno].ano)} taxa={d.anos[noAno].taxa} />
            </Sequence>
          ) : (
            <div style={{ position: "absolute", top: 1010, left: 0, right: 0, textAlign: "center", fontWeight: 800, fontSize: 52,
              color: CORES.apagado, opacity: surge(frame, 26, fps) }}>
              …em {d.anoBase} enchia este carrinho:
            </div>
          )}

          {/* carrinho */}
          <div style={{ position: "absolute", top: 1170, left: 90, right: 90, display: "flex", flexWrap: "wrap",
            justifyContent: "center", gap: 18 }}>
            {d.itens.map((e, i) => {
              const entra = surge(frame, 30 + i * 3, fps);
              const sai = i >= itensAgora;
              // quando sai: o item cai e some, no ano em que deixou de caber
              const anoSaida = fatores.findIndex((f) => Math.round(d.itens.length / f) <= i);
              const tSaida = anoSaida >= 0 ? INICIO_ANOS + anoSaida * POR_ANO : 999;
              const q = interpolate(t, [tSaida, tSaida + 0.45], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp",
                easing: Easing.in(Easing.quad) });
              return (
                <div key={i} style={{ width: 150, height: 150, borderRadius: 28, background: "rgba(255,255,255,.06)",
                  border: "2px solid rgba(255,255,255,.12)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <span style={{ fontFamily: EMOJI, fontSize: 92, opacity: sai ? 1 - q : entra,
                    transform: `scale(${sai ? 1 - 0.3 * q : entra}) translateY(${sai ? q * 260 : 0}px) rotate(${sai ? q * 40 : 0}deg)` }}>
                    {e}
                  </span>
                </div>
              );
            })}
          </div>
          <div style={{ position: "absolute", top: 1560, left: 0, right: 0, textAlign: "center", fontWeight: 900, fontSize: 56 }}>
            {noAno >= 0 ? (
              <>
                cabem <span style={{ color: CORES.amarelo }}>{itensAgora} de {d.itens.length}</span> itens
              </>
            ) : null}
          </div>
          <div style={{ position: "absolute", top: 1660, left: 80, right: 80, textAlign: "center", fontWeight: 600, fontSize: 28,
            color: CORES.apagado }}>
            Carrinho ilustrativo: a proporção segue a inflação oficial. Fonte: {d.fonte}
          </div>
          {d.sons !== false
            ? d.anos.map((_, k) =>
                Math.round(d.itens.length / fatores[k]) < Math.round(d.itens.length / (k ? fatores[k - 1] : 1)) ? (
                  <Sequence key={k} from={Math.round((INICIO_ANOS + k * POR_ANO) * fps)} layout="none">
                    <Audio src={staticFile("sfx/cartao.wav")} volume={0.45} />
                  </Sequence>
                ) : null,
              )
            : null}
        </>
      ) : null}

      {/* ---------- revelação ---------- */}
      {t >= T.revela && t < T.pergunta ? (
        <Sequence from={Math.round(T.revela * fps)} layout="none">
          <Revela fator={fatorFinal} anoBase={d.anoBase} fonte={d.fonte} ultimo={d.ultimoRotulo} />
          {d.sons !== false ? <Audio src={staticFile("sfx/bordao-hit.wav")} volume={0.4} /> : null}
        </Sequence>
      ) : null}

      {/* ---------- pergunta (engajamento) ---------- */}
      {t >= T.pergunta && t < T.bordao ? (
        <Sequence from={Math.round(T.pergunta * fps)} layout="none">
          <Pergunta texto={d.pergunta} />
          {d.sons !== false ? <Audio src={staticFile("sfx/seguir.wav")} volume={0.35} /> : null}
        </Sequence>
      ) : null}

      {/* ---------- bordão e assinatura ---------- */}
      {t >= T.bordao ? (
        <Sequence from={Math.round(T.bordao * fps)} layout="none">
          <Bordao />
          <div style={{ position: "absolute", top: 1560, left: 60, right: 60, textAlign: "center" }}>
            <div style={{ fontWeight: 900, fontSize: 56 }}>@termometrodecrise</div>
            <div style={{ fontWeight: 600, fontSize: 32, color: CORES.apagado, marginTop: 14, lineHeight: 1.3 }}>
              Não recomendamos: só mostramos a temperatura do mundo.
            </div>
          </div>
          {d.sons !== false ? <Audio src={staticFile("sfx/bordao-whoosh.wav")} volume={0.35} /> : null}
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};

const AnoChip: React.FC<{ ano: string; taxa: number }> = ({ ano, taxa }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 12, stiffness: 200 } });
  return (
    <div style={{ position: "absolute", top: 1010, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 22,
      alignItems: "center", transform: `scale(${0.7 + 0.3 * s})`, opacity: s }}>
      <span style={{ fontWeight: 900, fontSize: 76 }}>{ano}</span>
      <span style={{ fontWeight: 900, fontSize: 52, color: "#14181D", background: taxa >= 8 ? "#FF6B5E" : CORES.amarelo,
        borderRadius: 999, padding: "8px 26px" }}>
        +{pct(taxa)}
      </span>
    </div>
  );
};

const Revela: React.FC<{ fator: number; anoBase: number; fonte: string; ultimo: string }> = ({ fator, anoBase, fonte, ultimo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const b = spring({ frame: frame - 18, fps, config: { damping: 14 } });
  const c = spring({ frame: frame - 36, fps, config: { damping: 14 } });
  const custo = 100 * fator;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 70px",
      fontFamily: FONTE }}>
      <div style={{ fontWeight: 800, fontSize: 56, color: CORES.apagado, opacity: a }}>O carrinho que custava R$ 100 em {anoBase}</div>
      <div style={{ fontWeight: 900, fontSize: 200, color: CORES.amarelo, letterSpacing: "-.04em", lineHeight: 1,
        transform: `scale(${0.6 + 0.4 * b})`, opacity: b, margin: "20px 0" }}>
        {brl(custo)}
      </div>
      <div style={{ fontWeight: 800, fontSize: 56, opacity: b }}>é o que ele custa hoje</div>
      <div style={{ marginTop: 60, fontWeight: 900, fontSize: 50, color: "#14181D", background: "#FF6B5E", borderRadius: 999,
        padding: "12px 34px", opacity: c, transform: `translateY(${(1 - c) * 30}px)` }}>
        Inflação acumulada: +{pct((fator - 1) * 100)}
      </div>
      <div style={{ marginTop: 26, fontWeight: 600, fontSize: 30, color: CORES.apagado, opacity: c }}>
        {fonte}, de janeiro de {anoBase} a {ultimo.replace(/^(\d{4}) \(até (\w+)\)$/, "$2 de $1")}
      </div>
    </AbsoluteFill>
  );
};

const Pergunta: React.FC<{ texto: string }> = ({ texto }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 12 } });
  const pulso = 1 + 0.04 * Math.max(0, Math.sin((frame / fps) * Math.PI * 2.4));
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 70px" }}>
      <div style={{ fontWeight: 900, fontSize: 92, lineHeight: 1.08, letterSpacing: "-.02em", opacity: s,
        transform: `translateY(${(1 - s) * 40}px)` }}>
        {texto}
      </div>
      <div style={{ marginTop: 60, display: "flex", gap: 30, transform: `scale(${pulso})` }}>
        {["SIM", "NÃO"].map((x) => (
          <span key={x} style={{ fontWeight: 900, fontSize: 70, background: x === "SIM" ? CORES.amarelo : "rgba(255,255,255,.12)",
            color: x === "SIM" ? "#14181D" : CORES.texto, borderRadius: 30, padding: "18px 60px" }}>
            {x}
          </span>
        ))}
      </div>
      <div style={{ marginTop: 50, fontWeight: 800, fontSize: 48, color: CORES.apagado }}>Comenta aí 👇</div>
    </AbsoluteFill>
  );
};
