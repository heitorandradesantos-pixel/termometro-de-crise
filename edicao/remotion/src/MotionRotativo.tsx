import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Easing,
  interpolate,
  interpolateColors,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brl, clamp, EMOJI, Fecho, Gancho, num, Pergunta, Selo, Sfx, VERMELHO } from "./MotionComparar";
import { CORES, FONTE } from "./tipos";

// Reel só de motion (13/11): o teto do rotativo do cartão (juros + encargos ≤ 100% da dívida original, Lei 14.690/2023,
// vale desde jan/2024). Juro médio do rotativo vem do Banco Central (props). A dívida de R$ 1.000 é exemplo, rotulado.
export type DadosRotativo = {
  divida: number;
  jurosAno: number; // % ao ano, média do BC
  mesRef: string; // ex.: "set/2026"
  meses: number;
  fonte: string;
  pergunta: string;
  opcoes: [string, string];
  rodape: string;
};

export const temposRotativo = { gancho: 4.2, juro: 6.0, corrida: 14.0, revela: 8.0, pergunta: 5.0, bordao: 3.8 };
const total = () => Object.values(temposRotativo).reduce((a, b) => a + b, 0);
export const calcularRotativo: CalculateMetadataFunction<DadosRotativo> = () => ({ durationInFrames: Math.round(total() * 30) });

export const MotionRotativo: React.FC<DadosRotativo> = (d) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const T = temposRotativo;
  const t1 = T.gancho;
  const t2 = t1 + T.juro;
  const t3 = t2 + T.corrida;
  const t4 = t3 + T.revela;
  const t5 = t4 + T.pergunta;
  const mensal = Math.pow(1 + d.jurosAno / 100, 1 / 12) - 1;
  const teto = d.divida * 2;
  const semRegraFim = d.divida * Math.pow(1 + mensal, d.meses);
  const mesTeto = Math.log(2) / Math.log(1 + mensal);
  // corrida: mês 0 → meses
  const p = interpolate(t, [t2 + 1.0, t3 - 2.0], [0, d.meses], { ...clamp, easing: Easing.inOut(Easing.quad) });
  const k = Math.floor(p);
  const passo = k + interpolate(p - k, [0.65, 1], [0, 1], clamp);
  const sem = d.divida * Math.pow(1 + mensal, passo);
  const com = Math.min(teto, sem);
  const bateu = p >= mesTeto;
  const tBateu = t2 + 1.0 + (mesTeto / d.meses) * (t3 - 3.0 - t2);
  const tremor = bateu ? interpolate(t, [tBateu, tBateu + 0.5], [14, 0], clamp) : 0;
  const escala = semRegraFim * 1.05;
  const H = 820;
  const fundo = interpolateColors(Math.min(1, sem / semRegraFim), [0, 1], ["#132230", "#3A1414"]);
  const g = spring({ frame: frame - Math.round(t1 * fps), fps, config: { damping: 12 } });
  const contaJuro = interpolate(t, [t1 + 0.6, t1 + 2.6], [0, d.jurosAno], { ...clamp, easing: Easing.out(Easing.cubic) });
  const carimbo = spring({ frame: frame - Math.round(tBateu * fps), fps, config: { damping: 8, stiffness: 200 } });

  const barra = (rotulo: string, valor: number, cor: string, fantasma: boolean) => (
    <div style={{ width: 300, display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ fontWeight: 900, fontSize: 52, color: cor, marginBottom: 14 }}>{brl(valor)}</div>
      <div style={{ position: "relative", width: 220, height: H, display: "flex", alignItems: "flex-end" }}>
        <div style={{ width: "100%", height: (valor / escala) * H, borderRadius: "24px 24px 8px 8px",
          background: fantasma ? "repeating-linear-gradient(45deg, rgba(255,107,94,.55) 0 18px, rgba(255,107,94,.25) 18px 36px)" : cor,
          border: fantasma ? `4px dashed ${VERMELHO}` : "none", boxSizing: "border-box" }} />
      </div>
      <div style={{ fontWeight: 800, fontSize: 40, marginTop: 18, textAlign: "center", lineHeight: 1.1 }}>{rotulo}</div>
    </div>
  );

  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, ${fundo} 0%, #0B0F14 75%)` }} />
      <Selo />
      {t < t1 ? (
        <>
          <Gancho l1={<>Seu cartão <span style={{ color: VERMELHO }}>NÃO pode</span> cobrar mais que o dobro da dívida.</>}
            l2="É lei desde 2024. Olha a conta." />
          <div style={{ position: "absolute", top: 820, left: 0, right: 0, textAlign: "center", fontFamily: EMOJI, fontSize: 320,
            transform: `rotate(${Math.sin(t * 3) * 6}deg)` }}>💳</div>
        </>
      ) : null}
      {t >= t1 && t < t2 ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 70px" }}>
          <div style={{ fontWeight: 800, fontSize: 54, color: CORES.apagado, lineHeight: 1.2, opacity: g }}>
            Pagou menos que o total da fatura?<br />O resto cai no <span style={{ color: CORES.texto }}>rotativo</span>.
          </div>
          <div style={{ fontWeight: 900, fontSize: 210, color: VERMELHO, letterSpacing: "-.04em", lineHeight: 1, margin: "50px 0 10px",
            textShadow: "0 0 60px rgba(255,107,94,.35)" }}>{num(contaJuro, 1)}%</div>
          <div style={{ fontWeight: 900, fontSize: 60 }}>de juros ao ano</div>
          <div style={{ fontWeight: 600, fontSize: 30, color: CORES.apagado, marginTop: 30 }}>
            Média do rotativo em {d.mesRef} · Fonte: {d.fonte}
          </div>
        </AbsoluteFill>
      ) : null}
      {t >= t2 && t < t3 ? (
        <AbsoluteFill style={{ transform: `translate(${Math.sin(frame * 2.7) * tremor}px, ${Math.cos(frame * 3.1) * tremor}px)` }}>
          <div style={{ position: "absolute", top: 220, left: 0, right: 0, textAlign: "center" }}>
            <div style={{ fontWeight: 800, fontSize: 44, color: CORES.apagado }}>Dívida de {brl(d.divida)} no rotativo (exemplo)</div>
            <div style={{ fontWeight: 900, fontSize: 90, marginTop: 6 }}>mês {Math.floor(p)}</div>
          </div>
          <div style={{ position: "absolute", top: 420, left: 120, right: 120, display: "flex", justifyContent: "space-between" }}>
            {barra("Sem a regra", sem, VERMELHO, true)}
            {barra("Com a regra", com, CORES.amarelo, false)}
          </div>
          {/* linha do teto */}
          <div style={{ position: "absolute", left: 80, right: 80, top: 420 + 66 + H - (teto / escala) * H, borderTop: `6px dashed ${CORES.texto}` }}>
            <span style={{ position: "absolute", right: 0, top: -60, fontWeight: 900, fontSize: 38, background: "#0B0F14",
              padding: "4px 14px", borderRadius: 12 }}>TETO: {brl(teto)}</span>
          </div>
          {bateu ? (
            <div style={{ position: "absolute", top: 1560, left: 0, right: 0, textAlign: "center" }}>
              <span style={{ display: "inline-block", fontWeight: 900, fontSize: 64, color: "#14181D", background: CORES.amarelo,
                borderRadius: 20, padding: "12px 34px", transform: `scale(${0.6 + 0.4 * carimbo}) rotate(-4deg)` }}>
                TRAVOU NO DOBRO
              </span>
            </div>
          ) : null}
        </AbsoluteFill>
      ) : null}
      {t >= t3 && t < t4 ? (
        <Sequence from={Math.round(t3 * fps)} layout="none">
          <Revela d={d} teto={teto} semRegraFim={semRegraFim} />
        </Sequence>
      ) : null}
      {t >= t4 && t < t5 ? (
        <Sequence from={Math.round(t4 * fps)} layout="none">
          <Pergunta texto={d.pergunta} opcoes={d.opcoes} rodape={d.rodape} />
        </Sequence>
      ) : null}
      {t >= t5 ? (
        <Sequence from={Math.round(t5 * fps)} layout="none">
          <Fecho />
        </Sequence>
      ) : null}
      <Sfx arq="cartao" vol={0.4} em={0.05} />
      <Sfx arq="choque" vol={0.45} em={t1 + 0.6} />
      {Array.from({ length: d.meses }, (_, i) => (
        <Sfx key={i} arq="tick" vol={0.4} em={t2 + 1.0 + ((i + 1) / d.meses) * (t3 - 3.0 - t2)} />
      ))}
      <Sfx arq="impacto" vol={0.55} em={tBateu} />
      <Sfx arq="subida" vol={0.3} em={t3 + 0.3} />
      <Sfx arq="seguir" vol={0.35} em={t4} />
      <Sfx arq="bordao-whoosh" vol={0.35} em={t5} />
    </AbsoluteFill>
  );
};

const Revela: React.FC<{ d: DadosRotativo; teto: number; semRegraFim: number }> = ({ d, teto, semRegraFim }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const b = spring({ frame: frame - 30, fps, config: { damping: 9, stiffness: 160 } });
  const c = spring({ frame: frame - 100, fps, config: { damping: 14 } });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 60px", fontFamily: FONTE,
      color: CORES.texto, background: "radial-gradient(ellipse at 50% 45%, #1C2A38 0%, #0B0F14 75%)" }}>
      <div style={{ fontWeight: 800, fontSize: 56, color: CORES.apagado, opacity: a, lineHeight: 1.15 }}>
        Juros e encargos do rotativo não podem passar de <span style={{ color: CORES.texto }}>100% da dívida</span>.
      </div>
      <div style={{ fontWeight: 900, fontSize: 120, letterSpacing: "-.03em", lineHeight: 1.05, margin: "40px 0 10px",
        transform: `scale(${0.7 + 0.3 * b})` }}>
        {brl(d.divida)}<br /><span style={{ fontSize: 80, color: CORES.apagado }}>vira no máximo</span><br />
        <span style={{ color: CORES.amarelo }}>{brl(teto)}</span>
      </div>
      <div style={{ fontWeight: 700, fontSize: 40, color: CORES.apagado, opacity: b }}>
        e não {brl(semRegraFim)} em {d.meses} meses, no juro médio
      </div>
      <div style={{ marginTop: 60, fontWeight: 900, fontSize: 44, color: "#14181D", background: CORES.amarelo, borderRadius: 999,
        padding: "14px 34px", opacity: c }}>
        Passou disso? Reclame no banco e no Banco Central.
      </div>
      <div style={{ marginTop: 26, fontWeight: 600, fontSize: 30, color: CORES.apagado, opacity: c }}>
        Lei 14.690/2023 · vale desde janeiro de 2024
      </div>
    </AbsoluteFill>
  );
};
