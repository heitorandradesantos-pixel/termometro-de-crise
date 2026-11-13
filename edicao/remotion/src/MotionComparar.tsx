import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Easing,
  interpolate,
  interpolateColors,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Bordao } from "./Fim";
import { Simbolo } from "./Simbolo";
import { CORES, FONTE } from "./tipos";

// Reels só de motion, sem o Heitor gravar (13/11): "antes x hoje" com dado oficial.
// Dois moldes: GASOLINA (o tanque/bomba) e CESTA (corrida cesta x salário + relógio de horas de trabalho).
// Todo número vem dos props, conferido na fonte oficial (ANP, DIEESE); exemplo com hipótese (km/l) é rotulado.
const EMOJI = "'Noto Color Emoji', sans-serif";
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
const num = (v: number, c = 0) => v.toLocaleString("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c });
const brl = (v: number, c = 0) => "R$ " + num(v, c);
const VERMELHO = "#FF6B5E";

const Sfx: React.FC<{ arq: string; vol: number; em: number }> = ({ arq, vol, em }) => {
  const { fps } = useVideoConfig();
  return (
    <Sequence from={Math.max(0, Math.round(em * fps))} layout="none">
      <Audio src={staticFile(`sfx/${arq}.wav`)} volume={vol} />
    </Sequence>
  );
};

const Selo: React.FC = () => (
  <div style={{ position: "absolute", top: 110, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
    <div style={{ display: "flex", alignItems: "center", gap: 14, background: "rgba(10,14,19,.75)", borderRadius: 999,
      padding: "10px 24px 10px 14px", fontWeight: 800, fontSize: 28, letterSpacing: ".06em", fontFamily: FONTE, color: CORES.texto }}>
      <Simbolo tamanho={44} />
      TERMÔMETRO DE CRISE
    </div>
  </div>
);

const Pergunta: React.FC<{ texto: string; opcoes: [string, string] }> = ({ texto, opcoes }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 12 } });
  const pulso = 1 + 0.05 * Math.max(0, Math.sin((frame / fps) * Math.PI * 2.4));
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 70px",
      fontFamily: FONTE, color: CORES.texto, background: "radial-gradient(ellipse at 50% 45%, #1C2A38 0%, #0B0F14 75%)" }}>
      <div style={{ fontWeight: 900, fontSize: 92, lineHeight: 1.06, letterSpacing: "-.02em", opacity: s,
        transform: `translateY(${(1 - s) * 40}px)` }}>{texto}</div>
      <div style={{ marginTop: 64, display: "flex", gap: 30, transform: `scale(${pulso})` }}>
        {opcoes.map((x, i) => (
          <span key={x} style={{ fontWeight: 900, fontSize: 68, background: i === 0 ? CORES.amarelo : "rgba(255,255,255,.12)",
            color: i === 0 ? "#14181D" : CORES.texto, borderRadius: 30, padding: "18px 54px" }}>{x}</span>
        ))}
      </div>
      <div style={{ marginTop: 54, fontWeight: 800, fontSize: 50, color: CORES.apagado }}>
        Comenta aí <span style={{ fontFamily: EMOJI }}>👇</span>
      </div>
    </AbsoluteFill>
  );
};

const Fecho: React.FC = () => (
  <>
    <Bordao topo={700} />
    <div style={{ position: "absolute", top: 1250, left: 60, right: 60, textAlign: "center", fontFamily: FONTE, color: CORES.texto }}>
      <div style={{ fontWeight: 900, fontSize: 56 }}>@termometrodecrise</div>
      <div style={{ fontWeight: 600, fontSize: 32, color: CORES.apagado, marginTop: 14, lineHeight: 1.3 }}>
        Não recomendamos: só mostramos a temperatura do mundo.
      </div>
    </div>
  </>
);

const Gancho: React.FC<{ l1: React.ReactNode; l2: string }> = ({ l1, l2 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 13, stiffness: 190 } });
  const b = spring({ frame: frame - 30, fps, config: { damping: 13, stiffness: 190 } });
  return (
    <div style={{ position: "absolute", top: 230, left: 50, right: 50, textAlign: "center", fontFamily: FONTE, color: CORES.texto }}>
      <div style={{ fontWeight: 900, fontSize: 88, lineHeight: 1.03, letterSpacing: "-.025em", opacity: a,
        transform: `translateY(${(1 - a) * 40}px)` }}>{l1}</div>
      <div style={{ fontWeight: 800, fontSize: 54, color: CORES.apagado, marginTop: 14, opacity: b }}>{l2}</div>
    </div>
  );
};

// ======================================================================= GASOLINA
export type DadosGasolina = {
  antes: { rotulo: string; preco: number }; // R$/litro (ANP)
  hoje: { rotulo: string; preco: number };
  kmPorLitro: number; // hipótese do exemplo, rotulada na tela
  tanque: number; // litros, exemplo
  fonte: string;
  pergunta: string;
  opcoes: [string, string];
};

export const temposGasolina = { gancho: 4.0, anima: 17.0, revela: 7.5, pergunta: 4.5, bordao: 3.8 };
const totalG = () => Object.values(temposGasolina).reduce((a, b) => a + b, 0);
export const calcularGasolina: CalculateMetadataFunction<DadosGasolina> = () => ({ durationInFrames: Math.round(totalG() * 30) });

const Bomba: React.FC<{ preco: number; litros: number; calor: number }> = ({ preco, litros, calor }) => (
  <div style={{ width: 520, borderRadius: 34, padding: "26px 30px", background: "linear-gradient(180deg,#1E2A36,#121A22)",
    border: `4px solid ${interpolateColors(calor, [0, 1], ["#3B82C4", VERMELHO])}`, boxShadow: "0 24px 60px rgba(0,0,0,.5)",
    fontFamily: FONTE, color: CORES.texto }}>
    <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 800, fontSize: 30, color: CORES.apagado }}>
      <span>PREÇO / LITRO</span><span style={{ fontFamily: EMOJI }}>⛽</span>
    </div>
    <div style={{ fontFamily: "'DejaVu Sans Mono', monospace", fontWeight: 700, fontSize: 92, color: interpolateColors(calor, [0, 1], [CORES.amarelo, VERMELHO]),
      background: "#05080B", borderRadius: 14, padding: "6px 18px", margin: "8px 0 18px", textAlign: "right" }}>{num(preco, 2)}</div>
    <div style={{ fontWeight: 800, fontSize: 30, color: CORES.apagado }}>LITROS COM R$ 100</div>
    <div style={{ fontFamily: "'DejaVu Sans Mono', monospace", fontWeight: 700, fontSize: 92, color: "#7CC3E0",
      background: "#05080B", borderRadius: 14, padding: "6px 18px", marginTop: 8, textAlign: "right" }}>{num(litros, 1)}</div>
  </div>
);

const Tanque: React.FC<{ nivel: number; max: number }> = ({ nivel, max }) => {
  const h = 520;
  const p = nivel / max;
  return (
    <div style={{ position: "relative", width: 230, height: h, borderRadius: 40, border: "6px solid rgba(255,255,255,.35)",
      overflow: "hidden", background: "rgba(255,255,255,.04)" }}>
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: h * p,
        background: "linear-gradient(180deg,#F2C14E,#EE8A3C)", boxShadow: "inset 0 10px 20px rgba(255,255,255,.25)" }} />
      {[0.25, 0.5, 0.75].map((m) => (
        <div key={m} style={{ position: "absolute", left: 0, width: 40, bottom: h * m, borderTop: "4px solid rgba(255,255,255,.4)" }} />
      ))}
    </div>
  );
};

export const MotionGasolina: React.FC<DadosGasolina> = (d) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const T = temposGasolina;
  const t1 = T.gancho;
  const t2 = t1 + T.anima;
  const t3 = t2 + T.revela;
  const t4 = t3 + T.pergunta;
  const litrosA = 100 / d.antes.preco;
  const litrosH = 100 / d.hoje.preco;
  const p = interpolate(t, [t1 + 2.0, t2 - 2.2], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const preco = d.antes.preco + (d.hoje.preco - d.antes.preco) * p;
  const litros = 100 / preco;
  const km = litros * d.kmPorLitro;
  const ano = p < 0.5 ? d.antes.rotulo : d.hoje.rotulo;
  const tremor = interpolate(t, [t2 - 2.2, t2 - 1.6], [12, 0], clamp) * (t > t2 - 2.2 ? 1 : 0);
  const fundo = interpolateColors(p, [0, 1], ["#132230", "#3A1414"]);
  const perdidos = litrosA - litrosH;
  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, ${fundo} 0%, #0B0F14 75%)` }} />
      <Selo />
      {t < t2 ? (
        <AbsoluteFill style={{ transform: `translate(${Math.sin(frame * 2.7) * tremor}px, ${Math.cos(frame * 3.1) * tremor}px)` }}>
          {t < t1 ? (
            <Gancho l1={<>Seus R$ 100 de gasolina <span style={{ color: VERMELHO }}>perderam {num(perdidos, 0)} litros</span></>}
              l2={`de ${d.antes.rotulo} pra cá.`} />
          ) : (
            <div style={{ position: "absolute", top: 230, left: 0, right: 0, textAlign: "center" }}>
              <div style={{ fontWeight: 900, fontSize: 96, letterSpacing: "-.02em" }}>{ano}</div>
              <div style={{ fontWeight: 800, fontSize: 46, color: CORES.apagado }}>
                com R$ 100 você roda <span style={{ color: CORES.amarelo }}>{num(km, 0)} km</span>
              </div>
            </div>
          )}
          <div style={{ position: "absolute", top: 600, left: 90, right: 90, transform: "scale(1.04)", transformOrigin: "50% 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Bomba preco={t < t1 ? d.antes.preco : preco} litros={t < t1 ? litrosA : litros} calor={p} />
            <Tanque nivel={t < t1 ? litrosA : litros} max={litrosA} />
          </div>
          <div style={{ position: "absolute", top: 1300, left: 70, right: 70, textAlign: "center", fontWeight: 900, fontSize: 72 }}>
            {t < t1 ? (
              <span style={{ color: CORES.apagado, fontSize: 48 }}>Em {d.antes.rotulo}: {num(litrosA, 1)} litros</span>
            ) : (
              <>
                {num(litros, 1)} litros <span style={{ color: VERMELHO }}>(−{num(litrosA - litros, 1)})</span>
              </>
            )}
          </div>
          <div style={{ position: "absolute", top: 1450, left: 80, right: 80, textAlign: "center", fontWeight: 600, fontSize: 28, color: CORES.apagado }}>
            Preço médio da gasolina comum no Brasil · Fonte: {d.fonte} · km num carro que faz {d.kmPorLitro} km/l (exemplo)
          </div>
        </AbsoluteFill>
      ) : null}
      {t >= t2 && t < t3 ? (
        <Sequence from={Math.round(t2 * fps)} layout="none">
          <RevelaGasolina d={d} />
        </Sequence>
      ) : null}
      {t >= t3 && t < t4 ? (
        <Sequence from={Math.round(t3 * fps)} layout="none">
          <Pergunta texto={d.pergunta} opcoes={d.opcoes} />
        </Sequence>
      ) : null}
      {t >= t4 ? (
        <Sequence from={Math.round(t4 * fps)} layout="none">
          <Fecho />
        </Sequence>
      ) : null}
      <Sfx arq="cartao" vol={0.4} em={0.05} />
      {Array.from({ length: Math.floor((T.anima - 4.2) / 0.8) + 1 }, (_, i) => (
        <Sfx key={i} arq="tick" vol={0.4} em={t1 + 2.0 + i * 0.8} />
      ))}
      <Sfx arq="choque" vol={0.5} em={t2 - 2.2} />
      <Sfx arq="subida" vol={0.3} em={t2 - 2.4} />
      <Sfx arq="impacto" vol={0.45} em={t2 + 1.4} />
      <Sfx arq="seguir" vol={0.35} em={t3} />
      <Sfx arq="bordao-whoosh" vol={0.35} em={t4} />
    </AbsoluteFill>
  );
};

const RevelaGasolina: React.FC<{ d: DadosGasolina }> = ({ d }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const conta = interpolate(frame, [20, 80], [d.tanque * d.antes.preco, d.tanque * d.hoje.preco], { ...clamp, easing: Easing.out(Easing.cubic) });
  const b = spring({ frame: frame - 30, fps, config: { damping: 9, stiffness: 160 } });
  const c = spring({ frame: frame - 100, fps, config: { damping: 14 } });
  const alta = (d.hoje.preco / d.antes.preco - 1) * 100;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 60px", fontFamily: FONTE,
      color: CORES.texto, background: "radial-gradient(ellipse at 50% 45%, #3A1414 0%, #0B0F14 75%)" }}>
      <div style={{ fontWeight: 800, fontSize: 58, color: CORES.apagado, opacity: a }}>
        Encher um tanque de {d.tanque} litros: em {d.antes.rotulo}, {brl(d.tanque * d.antes.preco)}
      </div>
      <div style={{ fontWeight: 900, fontSize: 230, color: CORES.amarelo, letterSpacing: "-.045em", lineHeight: 1, margin: "26px 0 10px",
        transform: `scale(${0.7 + 0.3 * b})`, textShadow: "0 0 60px rgba(242,193,78,.35)" }}>{brl(conta)}</div>
      <div style={{ fontWeight: 900, fontSize: 64, opacity: b }}>hoje.</div>
      <div style={{ marginTop: 56, fontWeight: 900, fontSize: 48, color: "#14181D", background: VERMELHO, borderRadius: 999, padding: "12px 34px", opacity: c }}>
        O litro subiu {num(alta, 1)}%
      </div>
      <div style={{ marginTop: 24, fontWeight: 600, fontSize: 30, color: CORES.apagado, opacity: c }}>
        {d.fonte}: {brl(d.antes.preco, 3)} ({d.antes.rotulo}) → {brl(d.hoje.preco, 2)} ({d.hoje.rotulo})
      </div>
    </AbsoluteFill>
  );
};

// ======================================================================= CESTA BÁSICA
export type DadosCesta = {
  cidade: string;
  antes: { rotulo: string; cesta: number; salario: number; horas: string; pct: number };
  hoje: { rotulo: string; cesta: number; salario: number; horas: string; pct: number };
  fonte: string;
  pergunta: string;
  opcoes: [string, string];
};

export const temposCesta = { gancho: 4.0, corrida: 12.0, relogio: 8.0, revela: 7.5, pergunta: 4.5, bordao: 3.8 };
const totalC = () => Object.values(temposCesta).reduce((a, b) => a + b, 0);
export const calcularCesta: CalculateMetadataFunction<DadosCesta> = () => ({ durationInFrames: Math.round(totalC() * 30) });

const horasEmNumero = (h: string) => {
  const m = h.match(/(\d+)h(\d+)?/);
  return m ? Number(m[1]) + Number(m[2] || 0) / 60 : 0;
};

export const MotionCesta: React.FC<DadosCesta> = (d) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const T = temposCesta;
  const t1 = T.gancho;
  const t2 = t1 + T.corrida;
  const t3 = t2 + T.relogio;
  const t4 = t3 + T.revela;
  const t5 = t4 + T.pergunta;
  const altaCesta = (d.hoje.cesta / d.antes.cesta - 1) * 100;
  const altaSal = (d.hoje.salario / d.antes.salario - 1) * 100;
  const p = interpolate(t, [t1 + 1.2, t2 - 2.0], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const g = spring({ frame, fps, config: { damping: 13 } });
  const barra = (rotulo: string, emoji: string, alta: number, de: number, para: number, cor: string, i: number) => {
    const v = de + (para - de) * p;
    const largura = (alta / Math.max(altaCesta, altaSal)) * p;
    return (
      <div style={{ marginBottom: 70 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", fontWeight: 900, fontSize: 52 }}>
          <span><span style={{ fontFamily: EMOJI }}>{emoji}</span> {rotulo}</span>
          <span style={{ color: cor }}>{brl(v, 2)}</span>
        </div>
        <div style={{ marginTop: 12, height: 90, borderRadius: 22, background: "rgba(255,255,255,.08)", overflow: "hidden" }}>
          <div style={{ width: `${Math.max(4, largura * 100)}%`, height: "100%", background: cor, borderRadius: 22, display: "flex",
            alignItems: "center", justifyContent: "flex-end", paddingRight: 18, boxSizing: "border-box" }}>
            <span style={{ fontWeight: 900, fontSize: 44, color: "#14181D", opacity: p > 0.3 ? 1 : 0 }}>+{num(alta * p, 1)}%</span>
          </div>
        </div>
        <div style={{ fontWeight: 600, fontSize: 30, color: CORES.apagado, marginTop: 8 }}>{d.antes.rotulo}: {brl(de, 2)}</div>
      </div>
    );
  };
  const hA = horasEmNumero(d.antes.horas);
  const hH = horasEmNumero(d.hoje.horas);
  const q = interpolate(t, [t2 + 1.2, t3 - 1.8], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const horasAgora = hA + (hH - hA) * q;
  const fundo = interpolateColors(Math.max(p, q), [0, 1], ["#132230", "#3A1414"]);
  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, ${fundo} 0%, #0B0F14 75%)` }} />
      <Selo />
      {t < t1 ? (
        <>
          <Gancho l1={<>A cesta básica de {d.cidade} <span style={{ color: VERMELHO }}>mais que dobrou.</span></>}
            l2="E o salário? Olha a corrida." />
          <div style={{ position: "absolute", top: 760, left: 0, right: 0, textAlign: "center", fontFamily: EMOJI, fontSize: 340,
            transform: `scale(${0.7 + 0.3 * g}) rotate(${(1 - g) * -12}deg)` }}>🛒</div>
        </>
      ) : null}
      {t >= t1 && t < t2 ? (
        <div style={{ position: "absolute", top: 420, left: 70, right: 70, transform: "scale(1.1)", transformOrigin: "50% 0" }}>
          <div style={{ fontWeight: 900, fontSize: 80, textAlign: "center", marginBottom: 60, letterSpacing: "-.02em" }}>
            {p < 0.5 ? d.antes.rotulo : d.hoje.rotulo}
          </div>
          {barra("Cesta básica", "🛒", altaCesta, d.antes.cesta, d.hoje.cesta, VERMELHO, 0)}
          {barra("Salário mínimo", "💼", altaSal, d.antes.salario, d.hoje.salario, CORES.amarelo, 1)}
          <div style={{ fontWeight: 600, fontSize: 26, color: CORES.apagado, textAlign: "center", marginTop: 60 }}>
            Cesta básica de {d.cidade} · Fonte: {d.fonte}
          </div>
        </div>
      ) : null}
      {t >= t2 && t < t3 ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 70px" }}>
          <div style={{ fontWeight: 800, fontSize: 54, color: CORES.apagado, lineHeight: 1.15 }}>
            Horas de trabalho, com salário mínimo, pra pagar a cesta
          </div>
          <div style={{ fontFamily: EMOJI, fontSize: 200, margin: "30px 0", transform: `rotate(${q * 720}deg)` }}>⏰</div>
          <div style={{ fontWeight: 900, fontSize: 200, letterSpacing: "-.04em", lineHeight: 1,
            color: interpolateColors(q, [0, 1], [CORES.texto, VERMELHO]) }}>
            {Math.floor(horasAgora)}h{String(Math.round((horasAgora % 1) * 60)).padStart(2, "0")}
          </div>
          <div style={{ fontWeight: 700, fontSize: 40, color: CORES.apagado, marginTop: 20 }}>
            {d.antes.rotulo}: {d.antes.horas} · {d.hoje.rotulo}: {d.hoje.horas}
          </div>
        </AbsoluteFill>
      ) : null}
      {t >= t3 && t < t4 ? (
        <Sequence from={Math.round(t3 * fps)} layout="none">
          <RevelaCesta d={d} />
        </Sequence>
      ) : null}
      {t >= t4 && t < t5 ? (
        <Sequence from={Math.round(t4 * fps)} layout="none">
          <Pergunta texto={d.pergunta} opcoes={d.opcoes} />
        </Sequence>
      ) : null}
      {t >= t5 ? (
        <Sequence from={Math.round(t5 * fps)} layout="none">
          <Fecho />
        </Sequence>
      ) : null}
      <Sfx arq="cartao" vol={0.4} em={0.05} />
      <Sfx arq="subida" vol={0.3} em={t1 + 1.0} />
      <Sfx arq="choque" vol={0.45} em={t2 - 2.0} />
      {Array.from({ length: 7 }, (_, i) => (
        <Sfx key={i} arq="tick" vol={0.45} em={t2 + 1.2 + i * 0.75} />
      ))}
      <Sfx arq="impacto" vol={0.45} em={t3 + 1.4} />
      <Sfx arq="seguir" vol={0.35} em={t4} />
      <Sfx arq="bordao-whoosh" vol={0.35} em={t5} />
    </AbsoluteFill>
  );
};

const RevelaCesta: React.FC<{ d: DadosCesta }> = ({ d }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const b = spring({ frame: frame - 30, fps, config: { damping: 9, stiffness: 160 } });
  const c = spring({ frame: frame - 100, fps, config: { damping: 14 } });
  const conta = interpolate(frame, [20, 80], [d.antes.pct, d.hoje.pct], { ...clamp, easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 60px", fontFamily: FONTE,
      color: CORES.texto, background: "radial-gradient(ellipse at 50% 45%, #3A1414 0%, #0B0F14 75%)" }}>
      <div style={{ fontWeight: 800, fontSize: 58, color: CORES.apagado, opacity: a, lineHeight: 1.15 }}>
        Quanto do salário mínimo líquido vai só na cesta
      </div>
      <div style={{ fontWeight: 900, fontSize: 250, color: CORES.amarelo, letterSpacing: "-.045em", lineHeight: 1, margin: "26px 0 10px",
        transform: `scale(${0.7 + 0.3 * b})`, textShadow: "0 0 60px rgba(242,193,78,.35)" }}>{num(conta, 0)}%</div>
      <div style={{ fontWeight: 900, fontSize: 58, opacity: b }}>em {d.hoje.rotulo} (era {num(d.antes.pct, 0)}%)</div>
      <div style={{ marginTop: 56, fontWeight: 900, fontSize: 46, color: "#14181D", background: VERMELHO, borderRadius: 999, padding: "12px 34px", opacity: c }}>
        Cesta +{num((d.hoje.cesta / d.antes.cesta - 1) * 100, 1)}% · salário +{num((d.hoje.salario / d.antes.salario - 1) * 100, 1)}%
      </div>
      <div style={{ marginTop: 24, fontWeight: 600, fontSize: 30, color: CORES.apagado, opacity: c }}>
        Fonte: {d.fonte}, cesta de {d.cidade}
      </div>
    </AbsoluteFill>
  );
};
