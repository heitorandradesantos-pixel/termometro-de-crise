import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Easing,
  interpolate,
  interpolateColors,
  random,
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
// texto). Versão 2: a nota QUEIMA na proporção do poder de compra perdido, a tela esquenta como um termômetro, o ano
// de inflação alta dá um tranco e o gancho diz quanto a nota perdeu. Todo número vem dos props (IPCA do IBGE,
// conferido); o carrinho é ilustração da proporção e a tela avisa. A música entra no app, na hora de postar.
export type DadosInflacao = {
  anoBase: number; // o carrinho cheio é o do começo deste ano
  anos: { ano: number; taxa: number; nota?: string }[]; // IPCA de cada ano (o último pode ser parcial)
  ultimoRotulo: string; // "2026 (até outubro)"
  itens: string[]; // 10 emojis do carrinho
  fonte: string;
  pergunta: string;
  sons?: boolean;
};

const EMOJI = "'Noto Color Emoji', sans-serif";
const POR_ANO = 0.95;
const INICIO_ANOS = 3.1;
const brl = (v: number, casas = 0) =>
  "R$ " + v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
const pct = (v: number) => v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + "%";
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const tempos = (d: DadosInflacao) => {
  const fimAnos = INICIO_ANOS + d.anos.length * POR_ANO;
  const revela = fimAnos + 0.35;
  const pergunta = revela + 4.4;
  const bordao = pergunta + 3.0;
  const total = bordao + 3.2;
  return { fimAnos, revela, pergunta, bordao, total };
};

export const calcularInflacao: CalculateMetadataFunction<DadosInflacao> = ({ props }) => ({
  durationInFrames: Math.round(tempos(props).total * 30),
});

const Sfx: React.FC<{ arq: string; vol: number; em: number; ligado: boolean }> = ({ arq, vol, em, ligado }) => {
  const { fps } = useVideoConfig();
  if (!ligado) return null;
  return (
    <Sequence from={Math.max(0, Math.round(em * fps))} layout="none">
      <Audio src={staticFile(`sfx/${arq}.wav`)} volume={vol} />
    </Sequence>
  );
};

// A nota de R$ 100 (genérica, não é a cédula do Banco Central): queima da direita para a esquerda até sobrar só o
// poder de compra. Na borda, brasas que sobem.
const Nota: React.FC<{ resta: number; frame: number }> = ({ resta, frame }) => {
  const L = 680;
  const A = 320;
  const corte = L * resta;
  return (
    <div style={{ position: "relative", width: L, height: A, transform: "rotate(-4deg)" }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: 28, border: "4px dashed rgba(255,255,255,.18)" }} />
      <div style={{ position: "absolute", left: 0, top: 0, width: corte, height: A, overflow: "hidden", borderRadius: "28px 6px 6px 28px" }}>
        <div
          style={{
            width: L,
            height: A,
            borderRadius: 28,
            background: "linear-gradient(135deg, #6DB6E3 0%, #3A82B8 55%, #24597F 100%)",
            boxShadow: "0 30px 70px rgba(0,0,0,.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 50px",
            boxSizing: "border-box",
            fontFamily: FONTE,
            color: "#fff",
            position: "relative",
          }}
        >
          <div style={{ position: "absolute", inset: 18, borderRadius: 18, border: "3px solid rgba(255,255,255,.35)" }} />
          <div style={{ fontWeight: 900, fontSize: 168, letterSpacing: "-.04em", textShadow: "0 8px 0 rgba(0,0,0,.18)" }}>100</div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontWeight: 800, fontSize: 46, opacity: 0.92 }}>CEM</div>
            <div style={{ fontWeight: 800, fontSize: 46, opacity: 0.92 }}>REAIS</div>
            <div style={{ fontWeight: 900, fontSize: 70 }}>R$</div>
          </div>
        </div>
      </div>
      {resta < 0.999 ? (
        <>
          {/* borda queimada */}
          <div
            style={{
              position: "absolute",
              left: corte - 26,
              top: -6,
              width: 44,
              height: A + 12,
              background: "linear-gradient(90deg, rgba(40,12,4,0) 0%, #2A0E05 35%, #FF7A1A 62%, #FFD15C 75%, rgba(255,120,30,0) 100%)",
              filter: "blur(2px)",
              opacity: 0.95,
            }}
          />
          {new Array(18).fill(0).map((_, i) => {
            const r = (k: number) => random(`brasa-${i}-${k}`);
            const ciclo = 24 + r(1) * 20;
            const p = ((frame + r(2) * ciclo) % ciclo) / ciclo;
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: corte - 6 + r(3) * 30 + Math.sin(p * 6 + i) * 10,
                  top: A * r(4) - p * 140,
                  width: 6 + r(5) * 6,
                  height: 6 + r(5) * 6,
                  borderRadius: 99,
                  background: r(6) > 0.5 ? "#FFB347" : "#FF5E1A",
                  boxShadow: "0 0 12px #FF8A2A",
                  opacity: (1 - p) * 0.9,
                }}
              />
            );
          })}
        </>
      ) : null}
    </div>
  );
};

export const MotionInflacao: React.FC<DadosInflacao> = (d) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const T = tempos(d);
  const som = d.sons !== false;

  const fatores = d.anos.reduce<number[]>((acc, a) => [...acc, (acc.length ? acc[acc.length - 1] : 1) * (1 + a.taxa / 100)], []);
  const fatorFinal = fatores[fatores.length - 1];
  const perda = 100 - 100 / fatorFinal;

  // fator contínuo: dentro de cada ano, a inflação daquele ano entra aos poucos (a nota queima sem saltos)
  const k = Math.floor((t - INICIO_ANOS) / POR_ANO);
  const progresso = interpolate((t - INICIO_ANOS) % POR_ANO, [0, POR_ANO * 0.7], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const fator =
    t < INICIO_ANOS ? 1 : k >= d.anos.length ? fatorFinal : (k ? fatores[k - 1] : 1) * Math.pow(1 + d.anos[k].taxa / 100, progresso);
  const anoIdx = t < INICIO_ANOS ? -1 : Math.min(k, d.anos.length - 1);
  const poder = 100 / fator;
  const itensAgora = Math.round(d.itens.length / fator);
  const calor = interpolate(fator, [1, fatorFinal], [0, 1], clamp);

  // tranco no ano de inflação mais alta
  const maiorIdx = d.anos.reduce((m, a, i) => (a.taxa > d.anos[m].taxa ? i : m), 0);
  const tMaior = INICIO_ANOS + maiorIdx * POR_ANO;
  const tranco = interpolate(t, [tMaior, tMaior + 0.45], [1, 0], clamp) * (t >= tMaior ? 1 : 0);
  const tremor = tranco * 16;
  const dx = Math.sin(frame * 2.7) * tremor;
  const dy = Math.cos(frame * 3.3) * tremor;

  // câmera que respira: um zoom lento contínuo deixa a tela viva
  const camera = 1 + 0.05 * interpolate(t, [0, T.revela], [0, 1], clamp);

  const fundo = interpolateColors(calor, [0, 0.5, 1], ["#132230", "#2A2232", "#3A1414"]);
  const principal = t < T.revela;
  const g1 = spring({ frame, fps, config: { damping: 13, stiffness: 190 } });
  const g2 = spring({ frame: frame - 14, fps, config: { damping: 13, stiffness: 190 } });

  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 38%, ${fundo} 0%, #0B0F14 75%)` }} />
      <AbsoluteFill style={{ background: "#FF3B2F", opacity: tranco * 0.28 }} />

      <AbsoluteFill style={{ transform: `translate(${dx}px, ${dy}px) scale(${camera})` }}>
        {/* selo */}
        <div style={{ position: "absolute", top: 110, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14, background: "rgba(10,14,19,.75)", borderRadius: 999,
            padding: "10px 24px 10px 14px", fontWeight: 800, fontSize: 28, letterSpacing: ".06em" }}>
            <Simbolo tamanho={44} />
            TERMÔMETRO DE CRISE
          </div>
        </div>

        {principal ? (
          <>
            {/* gancho e manchete que muda */}
            <div style={{ position: "absolute", top: 220, left: 50, right: 50, textAlign: "center" }}>
              {anoIdx < 0 ? (
                <>
                  <div style={{ fontWeight: 900, fontSize: 92, lineHeight: 1.02, letterSpacing: "-.025em",
                    opacity: g1, transform: `translateY(${(1 - g1) * 40}px)` }}>
                    Essa nota perdeu <span style={{ color: "#FF6B5E" }}>{brl(perda)}</span>
                  </div>
                  <div style={{ fontWeight: 800, fontSize: 58, color: CORES.apagado, marginTop: 14, opacity: g2,
                    transform: `translateY(${(1 - g2) * 30}px)` }}>
                    sem você gastar nada.
                  </div>
                </>
              ) : (
                <>
                  <div style={{ fontWeight: 800, fontSize: 52, color: CORES.apagado }}>{"R$ 100"} hoje compram o que</div>
                  <div style={{ fontWeight: 900, fontSize: 150, lineHeight: 1, letterSpacing: "-.04em",
                    color: interpolateColors(calor, [0, 1], [CORES.texto, "#FF6B5E"]) }}>
                    {brl(poder, 2)}
                  </div>
                  <div style={{ fontWeight: 800, fontSize: 44, color: CORES.apagado }}>compravam em {d.anoBase}</div>
                </>
              )}
            </div>

            {/* a nota queimando */}
            <div style={{ position: "absolute", top: 640, left: 0, right: 0, display: "flex", justifyContent: "center",
              transform: `scale(${0.85 + 0.15 * g1})` }}>
              <Nota resta={1 / fator} frame={frame} />
            </div>

            {/* termômetro da inflação acumulada */}
            <div style={{ position: "absolute", top: 1010, left: 90, right: 90 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", fontWeight: 800 }}>
                <span style={{ fontSize: 40 }}>
                  {anoIdx < 0 ? (
                    <span style={{ color: CORES.apagado }}>Desde {d.anoBase} 👇</span>
                  ) : (
                    <Ano texto={anoIdx === d.anos.length - 1 ? d.ultimoRotulo : String(d.anos[anoIdx].ano)} chave={anoIdx}
                      taxa={d.anos[anoIdx].taxa} nota={d.anos[anoIdx].nota} />
                  )}
                </span>
                <span style={{ fontSize: 40, color: interpolateColors(calor, [0, 1], [CORES.amarelo, "#FF6B5E"]) }}>
                  +{pct((fator - 1) * 100)}
                </span>
              </div>
              <div style={{ marginTop: 14, height: 34, borderRadius: 999, background: "rgba(255,255,255,.08)", overflow: "hidden" }}>
                <div style={{ width: `${((fator - 1) / (fatorFinal - 1)) * 100}%`, height: "100%", borderRadius: 999,
                  background: "linear-gradient(90deg, #3B82C4, #7CC3E0 25%, #F2C14E 50%, #EE8A3C 75%, #E5554A)" ,
                  backgroundSize: `${(1080 - 180)}px 100%` }} />
              </div>
              <div style={{ marginTop: 8, fontSize: 28, fontWeight: 600, color: CORES.apagado }}>inflação acumulada (IPCA)</div>
            </div>

            {/* carrinho */}
            <div style={{ position: "absolute", top: 1240, left: 80, right: 80, display: "flex", flexWrap: "wrap",
              justifyContent: "center", gap: 16 }}>
              {d.itens.map((e, i) => {
                const entra = spring({ frame: frame - 6 - i * 2, fps, config: { damping: 12 } });
                const idxSaida = fatores.findIndex((f) => Math.round(d.itens.length / f) <= i);
                const tSaida = idxSaida >= 0 ? INICIO_ANOS + idxSaida * POR_ANO + 0.25 : 999;
                const q = interpolate(t, [tSaida, tSaida + 0.5], [0, 1], { ...clamp, easing: Easing.in(Easing.quad) });
                const fora = t >= tSaida;
                return (
                  <div key={i} style={{ width: 160, height: 150, borderRadius: 28, position: "relative",
                    background: fora ? "rgba(255,59,47,.08)" : "rgba(255,255,255,.07)",
                    border: `2px solid ${fora ? "rgba(255,107,94,.45)" : "rgba(255,255,255,.12)"}`,
                    display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <span style={{ fontFamily: EMOJI, fontSize: 92, opacity: fora ? 1 - q : entra,
                      transform: `scale(${fora ? 1 - 0.4 * q : entra}) translateY(${q * 300}px) rotate(${q * 50}deg)` }}>
                      {e}
                    </span>
                    {fora ? (
                      <span style={{ position: "absolute", fontSize: 30, fontWeight: 900, color: "#FF6B5E", opacity: q,
                        transform: `rotate(-12deg) scale(${0.6 + 0.4 * q})` }}>SUMIU</span>
                    ) : null}
                  </div>
                );
              })}
            </div>
            <div style={{ position: "absolute", top: 1590, left: 0, right: 0, textAlign: "center", fontWeight: 900, fontSize: 56 }}>
              {anoIdx < 0 ? (
                <span style={{ color: CORES.apagado, fontSize: 46 }}>o carrinho de {"R$ 100"} em {d.anoBase}</span>
              ) : (
                <>
                  cabem <span style={{ color: CORES.amarelo }}>{itensAgora} de {d.itens.length}</span> itens
                </>
              )}
            </div>
            <div style={{ position: "absolute", top: 1700, left: 80, right: 80, textAlign: "center", fontWeight: 600, fontSize: 26,
              color: CORES.apagado }}>
              Carrinho ilustrativo na proporção da inflação oficial · Fonte: {d.fonte}
            </div>
          </>
        ) : null}
      </AbsoluteFill>

      {/* revelação */}
      {t >= T.revela && t < T.pergunta ? (
        <Sequence from={Math.round(T.revela * fps)} layout="none">
          <Revela fator={fatorFinal} anoBase={d.anoBase} fonte={d.fonte} ultimo={d.ultimoRotulo} />
        </Sequence>
      ) : null}
      {t >= T.pergunta && t < T.bordao ? (
        <Sequence from={Math.round(T.pergunta * fps)} layout="none">
          <Pergunta texto={d.pergunta} />
        </Sequence>
      ) : null}
      {t >= T.bordao ? (
        <Sequence from={Math.round(T.bordao * fps)} layout="none">
          <Bordao />
          <div style={{ position: "absolute", top: 1560, left: 60, right: 60, textAlign: "center" }}>
            <div style={{ fontWeight: 900, fontSize: 56 }}>@termometrodecrise</div>
            <div style={{ fontWeight: 600, fontSize: 32, color: CORES.apagado, marginTop: 14, lineHeight: 1.3 }}>
              Não recomendamos: só mostramos a temperatura do mundo.
            </div>
          </div>
        </Sequence>
      ) : null}

      {/* sons */}
      <Sfx arq="cartao" vol={0.4} em={0.05} ligado={som} />
      {d.anos.map((_, i) => (
        <Sfx key={`t${i}`} arq="tick" vol={0.55} em={INICIO_ANOS + i * POR_ANO} ligado={som} />
      ))}
      {d.anos.map((_, i) =>
        Math.round(d.itens.length / fatores[i]) < Math.round(d.itens.length / (i ? fatores[i - 1] : 1)) ? (
          <Sfx key={`s${i}`} arq="cartao" vol={0.4} em={INICIO_ANOS + i * POR_ANO + 0.25} ligado={som} />
        ) : null,
      )}
      <Sfx arq="choque" vol={0.5} em={tMaior} ligado={som} />
      <Sfx arq="subida" vol={0.35} em={T.revela - 1.6} ligado={som} />
      <Sfx arq="impacto" vol={0.45} em={T.revela + 0.55} ligado={som} />
      <Sfx arq="seguir" vol={0.35} em={T.pergunta} ligado={som} />
      <Sfx arq="bordao-whoosh" vol={0.35} em={T.bordao} ligado={som} />
    </AbsoluteFill>
  );
};

const Ano: React.FC<{ texto: string; chave: number; taxa: number; nota?: string }> = ({ texto, chave, taxa, nota }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // o número do ano rola de baixo para cima a cada troca
  const inicio = Math.round((INICIO_ANOS + chave * POR_ANO) * fps);
  const s = spring({ frame: frame - inicio, fps, config: { damping: 14, stiffness: 220 } });
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 16 }}>
      <span style={{ display: "inline-block", fontSize: 64, fontWeight: 900, transform: `translateY(${(1 - s) * 40}px)`, opacity: s }}>
        {texto}
      </span>
      <span style={{ fontSize: 38, fontWeight: 900, color: "#14181D", background: taxa >= 8 ? "#FF6B5E" : CORES.amarelo,
        borderRadius: 999, padding: "4px 18px", transform: `scale(${0.6 + 0.4 * s})` }}>
        +{pct(taxa)}
      </span>
      {nota ? <span style={{ fontSize: 34, fontWeight: 800, color: "#FF6B5E", opacity: s }}>{nota}</span> : null}
    </span>
  );
};

const Revela: React.FC<{ fator: number; anoBase: number; fonte: string; ultimo: string }> = ({ fator, anoBase, fonte, ultimo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const conta = interpolate(frame, [10, 34], [100, 100 * fator], { ...clamp, easing: Easing.out(Easing.cubic) });
  const b = spring({ frame: frame - 16, fps, config: { damping: 9, stiffness: 160 } });
  const c = spring({ frame: frame - 40, fps, config: { damping: 14 } });
  const ate = ultimo.replace(/^(\d{4}) \(até (\w+)\)$/, "$2 de $1");
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 60px",
      background: "radial-gradient(ellipse at 50% 45%, #3A1414 0%, #0B0F14 75%)" }}>
      <div style={{ fontWeight: 800, fontSize: 58, color: CORES.apagado, opacity: a, lineHeight: 1.15 }}>
        O carrinho que custava {"R$ 100"} em {anoBase}
      </div>
      <div style={{ fontWeight: 900, fontSize: 230, color: CORES.amarelo, letterSpacing: "-.045em", lineHeight: 1,
        transform: `scale(${0.7 + 0.3 * b})`, margin: "26px 0 10px", textShadow: "0 0 60px rgba(242,193,78,.35)" }}>
        {brl(conta)}
      </div>
      <div style={{ fontWeight: 900, fontSize: 64, opacity: b }}>custa hoje.</div>
      <div style={{ marginTop: 56, fontWeight: 900, fontSize: 48, color: "#14181D", background: "#FF6B5E", borderRadius: 999,
        padding: "12px 34px", opacity: c, transform: `translateY(${(1 - c) * 30}px)` }}>
        Inflação acumulada: +{pct((fator - 1) * 100)}
      </div>
      <div style={{ marginTop: 24, fontWeight: 600, fontSize: 30, color: CORES.apagado, opacity: c }}>
        {fonte}, de janeiro de {anoBase} a {ate}
      </div>
    </AbsoluteFill>
  );
};

const Pergunta: React.FC<{ texto: string }> = ({ texto }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 12 } });
  const pulso = 1 + 0.05 * Math.max(0, Math.sin((frame / fps) * Math.PI * 2.4));
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 70px",
      background: "radial-gradient(ellipse at 50% 45%, #1C2A38 0%, #0B0F14 75%)" }}>
      <div style={{ fontWeight: 900, fontSize: 96, lineHeight: 1.06, letterSpacing: "-.02em", opacity: s,
        transform: `translateY(${(1 - s) * 40}px)` }}>
        {texto}
      </div>
      <div style={{ marginTop: 64, display: "flex", gap: 30, transform: `scale(${pulso})` }}>
        {["SIM", "NÃO"].map((x) => (
          <span key={x} style={{ fontWeight: 900, fontSize: 74, background: x === "SIM" ? CORES.amarelo : "rgba(255,255,255,.12)",
            color: x === "SIM" ? "#14181D" : CORES.texto, borderRadius: 30, padding: "18px 64px" }}>
            {x}
          </span>
        ))}
      </div>
      <div style={{ marginTop: 54, fontWeight: 800, fontSize: 50, color: CORES.apagado }}>
        Comenta aí <span style={{ fontFamily: EMOJI }}>👇</span>
      </div>
    </AbsoluteFill>
  );
};
