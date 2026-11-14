import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brl, clamp, EMOJI, Selo, Sfx, VERMELHO } from "./MotionComparar";
import { CORES, FONTE } from "./tipos";

// Criativos de anúncio do funil Quiz → Manual do Investidor (14/11). 9:16, ~20 s, sem fala (legenda na tela).
// Números iguais aos da página de venda: Selic 13,75% (Copom 04/11/2026); rotativo 451,7% a.a. (BC, set/2026).
// Nada de promessa de ganho; nenhum banco ou corretora citado pelo nome. Fecho único: livro + "faça o teste".
const VERDE = "#4CC38A";

const Cena: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 70px", fontFamily: FONTE,
    color: CORES.texto }}>{children}</AbsoluteFill>
);

const Fundo: React.FC<{ cor?: string }> = ({ cor = "#132230" }) => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, ${cor} 0%, #0B0F14 75%)` }} />
);

const Txt: React.FC<{ de: number; children: React.ReactNode; tam?: number; cor?: string; peso?: number }> = ({ de, children, tam = 84, cor, peso = 900 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - de, fps, config: { damping: 13, stiffness: 180 } });
  return (
    <div style={{ fontWeight: peso, fontSize: tam, lineHeight: 1.06, letterSpacing: "-.02em", color: cor, opacity: s,
      transform: `translateY(${(1 - s) * 40}px)` }}>{children}</div>
  );
};

// Fecho comum: mockup do livro + chamada para o teste (o anúncio leva ao /quiz/)
export const FechoAnuncio: React.FC<{ chamada?: string }> = ({ chamada = "Faça o teste grátis" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 12 } });
  const b = spring({ frame: frame - 18, fps, config: { damping: 12 } });
  const pulso = 1 + 0.04 * Math.max(0, Math.sin((frame / fps) * Math.PI * 2.2));
  return (
    <Cena>
      <div style={{ position: "relative", width: 560, transform: `scale(${0.8 + 0.2 * a}) rotate(${(1 - a) * -6}deg)`, opacity: a }}>
        <div style={{ position: "absolute", inset: "8% 4%", borderRadius: "50%", filter: "blur(40px)",
          background: "radial-gradient(closest-side, rgba(242,193,78,.45), rgba(242,193,78,0))" }} />
        <Img src={staticFile("mockup.webp")} style={{ position: "relative", width: "100%", filter: "drop-shadow(0 30px 40px rgba(0,0,0,.6))" }} />
      </div>
      <div style={{ marginTop: 30, fontWeight: 900, fontSize: 70, letterSpacing: "-.02em", opacity: b }}>
        Manual do <span style={{ color: CORES.amarelo }}>Investidor</span>
      </div>
      <div style={{ fontWeight: 700, fontSize: 40, color: CORES.apagado, marginTop: 8, opacity: b }}>
        Entenda o seu dinheiro em uma tarde.
      </div>
      <div style={{ marginTop: 44, fontWeight: 900, fontSize: 54, color: "#14181D", background: CORES.amarelo, borderRadius: 26,
        padding: "22px 46px", transform: `scale(${pulso})`, opacity: b }}>
        {chamada} <span style={{ fontFamily: EMOJI }}>👇</span>
      </div>
      <div style={{ marginTop: 26, fontWeight: 600, fontSize: 28, color: CORES.apagado, opacity: b }}>
        Conteúdo educativo. Não é recomendação de investimento.
      </div>
    </Cena>
  );
};

// ================================================================== A: o teste (quiz)
export const AnuncioTeste: React.FC = () => {
  const { fps } = useVideoConfig();
  const s = (ini: number, el: React.ReactNode, dur?: number) => (
    <Sequence from={Math.round(ini * fps)} durationInFrames={dur ? Math.round(dur * fps) : undefined} layout="none">{el}</Sequence>
  );
  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto, overflow: "hidden" }}>
      <Fundo />
      <Selo />
      {s(0, <Cena><Txt de={0}>Seu gerente de banco torce pra você <span style={{ color: VERMELHO }}>errar</span> isso.</Txt>
        <div style={{ height: 40 }} /><Txt de={30} tam={50} cor={CORES.apagado} peso={700}>Responde rápido: verdade ou mito?</Txt></Cena>, 3.4)}
      {s(3.4, <QuizCena p="A poupança é o investimento mais seguro do Brasil." certa={false}
        exp="O Tesouro Direto tem garantia do Tesouro Nacional." />, 5.2)}
      {s(8.6, <QuizCena p="Título de capitalização é investimento." certa={false}
        exp="Nem a Susep, que fiscaliza, chama de investimento." />, 5.2)}
      {s(13.8, <Cena><Txt de={0}>São <span style={{ color: CORES.amarelo }}>8 perguntas</span>.</Txt><div style={{ height: 24 }} />
        <Txt de={14} tam={60} peso={800}>Quantas você acerta?</Txt><div style={{ height: 30 }} />
        <Txt de={28} tam={40} cor={CORES.apagado} peso={700}>1 minuto · sem cadastro · resposta na hora</Txt></Cena>, 3.4)}
      {s(17.2, <FechoAnuncio />)}
      <Sfx arq="choque" vol={0.4} em={0.05} />
      <Sfx arq="tick" vol={0.45} em={4.6} /><Sfx arq="impacto" vol={0.45} em={5.9} />
      <Sfx arq="tick" vol={0.45} em={9.8} /><Sfx arq="impacto" vol={0.45} em={11.1} />
      <Sfx arq="subida" vol={0.3} em={13.9} />
      <Sfx arq="seguir" vol={0.4} em={17.3} />
    </AbsoluteFill>
  );
};

const QuizCena: React.FC<{ p: string; certa: boolean; exp: string }> = ({ p, certa, exp }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const rev = Math.round(2.5 * fps);
  const r = spring({ frame: frame - rev, fps, config: { damping: 10 } });
  const cont = Math.max(0, 3 - Math.floor(frame / (0.8 * fps)));
  const op = (rot: string, ok: boolean) => {
    const vence = frame >= rev && ok === certa;
    const perde = frame >= rev && ok !== certa;
    return (
      <div style={{ flex: 1, fontWeight: 900, fontSize: 56, padding: "34px 0", borderRadius: 30,
        background: vence ? "#173A2A" : perde ? "rgba(255,255,255,.04)" : "rgba(255,255,255,.08)",
        border: `5px solid ${vence ? VERDE : "rgba(255,255,255,.18)"}`, opacity: perde ? 0.4 : 1,
        transform: vence ? `scale(${1 + 0.06 * r})` : undefined }}>{rot}</div>
    );
  };
  return (
    <Cena>
      <Txt de={0} tam={74}>{p}</Txt>
      <div style={{ display: "flex", gap: 26, width: "100%", marginTop: 60 }}>{op("VERDADE", true)}{op("MITO", false)}</div>
      <div style={{ marginTop: 40, height: 140 }}>
        {frame < rev ? (
          <div style={{ fontWeight: 900, fontSize: 110, color: CORES.amarelo }}>{cont || ""}</div>
        ) : (
          <div style={{ opacity: r, fontWeight: 800, fontSize: 44, lineHeight: 1.2 }}>
            <span style={{ color: VERMELHO }}>Mito.</span> {exp}
          </div>
        )}
      </div>
    </Cena>
  );
};

// ================================================================== B: o extrato (quanto custa não saber)
export const AnuncioExtrato: React.FC = () => {
  const { fps } = useVideoConfig();
  const s = (ini: number, el: React.ReactNode, dur?: number) => (
    <Sequence from={Math.round(ini * fps)} durationInFrames={dur ? Math.round(dur * fps) : undefined} layout="none">{el}</Sequence>
  );
  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto, overflow: "hidden" }}>
      <Fundo />
      <Selo />
      {s(0, <Cena><Txt de={0}>Você deixou <span style={{ color: VERMELHO }}>R$ 292</span> na mesa.</Txt><div style={{ height: 30 }} />
        <Txt de={24} tam={56} cor={CORES.apagado} peso={700}>E nem percebeu.</Txt></Cena>, 3.2)}
      {s(3.2, <Extrato />, 10.3)}
      {s(13.5, <Cena><Txt de={0} tam={74}>Não é falta de inteligência.</Txt><div style={{ height: 24 }} />
        <Txt de={18} tam={74} cor={CORES.amarelo}>É falta de informação.</Txt><div style={{ height: 34 }} />
        <Txt de={40} tam={44} cor={CORES.apagado} peso={700}>E tem gente do outro lado do balcão que ganha com isso.</Txt></Cena>, 4.4)}
      {s(17.9, <FechoAnuncio />)}
      <Sfx arq="choque" vol={0.4} em={0.05} />
      <Sfx arq="cartao" vol={0.4} em={3.4} /><Sfx arq="tick" vol={0.45} em={5.0} /><Sfx arq="tick" vol={0.45} em={7.0} />
      <Sfx arq="impacto" vol={0.5} em={9.4} />
      <Sfx arq="subida" vol={0.3} em={13.6} />
      <Sfx arq="seguir" vol={0.4} em={18.0} />
    </AbsoluteFill>
  );
};

const Extrato: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const conta = (de: number, ate: number, ini: number) =>
    interpolate(frame, [ini * fps, (ini + 1.2) * fps], [de, ate], { ...clamp, easing: Easing.out(Easing.cubic) });
  const l = (ini: number) => spring({ frame: frame - Math.round(ini * fps), fps, config: { damping: 13 } });
  const linha = (rot: React.ReactNode, val: React.ReactNode, ini: number, cor = "#14181D", forte = false) => (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "26px 0",
      borderBottom: forte ? "none" : "3px dashed #BFB8A8", opacity: l(ini), transform: `translateX(${(1 - l(ini)) * 60}px)` }}>
      <span style={{ fontWeight: forte ? 900 : 700, fontSize: 42, textAlign: "left" }}>{rot}</span>
      <b style={{ fontWeight: 900, fontSize: 58, color: cor, whiteSpace: "nowrap" }}>{val}</b>
    </div>
  );
  return (
    <Cena>
      <div style={{ width: "100%", background: "#F4F1EA", color: "#14181D", borderRadius: 30, padding: "34px 40px 24px",
        boxShadow: "0 40px 90px rgba(0,0,0,.55)", transform: `rotate(-1.5deg) translateY(${(1 - a) * 80}px)`, opacity: a }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "5px solid #14181D",
          paddingBottom: 16, fontWeight: 900, fontSize: 44 }}>
          <span>R$ 10 mil por 1 ano</span>
          <span style={{ fontSize: 22, letterSpacing: ".1em", background: "#14181D", color: "#F4F1EA", borderRadius: 10, padding: "6px 12px" }}>SIMULAÇÃO</span>
        </div>
        {linha(<>🏦 Na poupança</>, <>+ {brl(conta(0, 834, 1.6))}</>, 1.4)}
        {linha(<>📄 CDB 100% do CDI<br /><span style={{ fontSize: 30, color: "#6B6458" }}>já sem o imposto</span></>,
          <>+ {brl(conta(0, 1126, 3.6))}</>, 3.4, "#B07A00")}
        {linha(<>Deixou na mesa</>, <>− {brl(conta(0, 292, 6.2))}</>, 6.0, "#C0392B", true)}
        <div style={{ fontSize: 22, color: "#6B6458", textAlign: "left", marginTop: 6, lineHeight: 1.35 }}>
          Selic 13,75% (Copom, 04/11/2026), CDI 13,65%, IR 17,5%, poupança 0,5% ao mês + TR. Não é promessa de rendimento.
        </div>
      </div>
    </Cena>
  );
};

// ================================================================== C: 8% x 451%
export const AnuncioJuros: React.FC = () => {
  const { fps } = useVideoConfig();
  const s = (ini: number, el: React.ReactNode, dur?: number) => (
    <Sequence from={Math.round(ini * fps)} durationInFrames={dur ? Math.round(dur * fps) : undefined} layout="none">{el}</Sequence>
  );
  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto, overflow: "hidden" }}>
      <Fundo />
      <Selo />
      {s(0, <Cena><Txt de={0}>O banco te paga <span style={{ color: VERDE }}>8%</span>.</Txt><div style={{ height: 20 }} />
        <Txt de={26}>E te cobra <span style={{ color: VERMELHO }}>451%</span>.</Txt></Cena>, 3.6)}
      {s(3.6, <Barras />, 8.4)}
      {s(12.0, <Cena><Txt de={0} tam={70}>Quem entende essa conta,</Txt><div style={{ height: 14 }} />
        <Txt de={18} tam={70} cor={CORES.amarelo}>para de pagar pra não saber.</Txt><div style={{ height: 34 }} />
        <Txt de={44} tam={44} cor={CORES.apagado} peso={700}>Poupança, CDB, Tesouro, FGC, cartão e golpes. Em linguagem de gente.</Txt></Cena>, 5.4)}
      {s(17.4, <FechoAnuncio />)}
      <Sfx arq="choque" vol={0.4} em={0.05} /><Sfx arq="impacto" vol={0.45} em={0.95} />
      <Sfx arq="subida" vol={0.35} em={5.0} /><Sfx arq="impacto" vol={0.55} em={7.6} />
      <Sfx arq="cartao" vol={0.35} em={12.1} />
      <Sfx arq="seguir" vol={0.4} em={17.5} />
    </AbsoluteFill>
  );
};

const Barras: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const H = 980;
  const p = interpolate(frame, [0.8 * fps, 4.0 * fps], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const tremor = interpolate(frame, [4.0 * fps, 4.6 * fps], [14, 0], clamp) * (frame > 4.0 * fps ? 1 : 0);
  const c = spring({ frame: frame - Math.round(5.0 * fps), fps, config: { damping: 14 } });
  const barra = (rot: string, sub: string, v: number, cor: string) => (
    <div style={{ width: 330, display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ fontWeight: 900, fontSize: 84, color: cor }}>{(v * p).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%</div>
      <div style={{ height: H, width: 240, display: "flex", alignItems: "flex-end" }}>
        <div style={{ width: "100%", height: Math.max(10, (v / 451.7) * H * p), background: cor, borderRadius: "26px 26px 8px 8px" }} />
      </div>
      <div style={{ fontWeight: 900, fontSize: 44, marginTop: 18 }}>{rot}</div>
      <div style={{ fontWeight: 600, fontSize: 30, color: CORES.apagado }}>{sub}</div>
    </div>
  );
  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto, transform: `translate(${Math.sin(frame * 2.7) * tremor}px,0)` }}>
      <div style={{ position: "absolute", top: 230, left: 90, right: 90, display: "flex", justifyContent: "space-between" }}>
        {barra("Poupança", "o que te pagam", 8.3, VERDE)}
        {barra("Rotativo", "o que te cobram", 451.7, VERMELHO)}
      </div>
      <div style={{ position: "absolute", top: 1610, left: 60, right: 60, textAlign: "center", fontWeight: 600, fontSize: 28,
        color: CORES.apagado, opacity: c }}>
        Ao ano. Poupança com Selic de 13,75%. Rotativo: média de set/2026, Banco Central.
      </div>
    </AbsoluteFill>
  );
};
