import { Easing, interpolate, useCurrentFrame } from "remotion";
import { CORES, FONTE } from "./tipos";

// Gráficos e recortes que entram dentro do cartão (pedido do Heitor em 13/11: "mostrar em gráficos essas alterações
// de um para o outro, em dados reais, para deixar o vídeo mais dinâmico"). Cada um anima em ~0,6 s e fica parado
// para a pessoa ler. Os números vêm do roteiro conferido: nada de gráfico ilustrativo com número inventado.
export type Grafico =
  | { tipo: "barras"; itens: { rotulo: string; valor: number; texto: string }[] } // antes x depois, lado a lado
  | { tipo: "variacao"; de: string; para: string; delta?: string; sobe?: boolean } // R$ 1.500 → R$ 1.251 (−16%)
  | { tipo: "linha"; pontos: { rotulo: string; valor: number; texto: string }[] } // a trajetória (Black Friday)
  | { tipo: "manchete"; veiculo: string; titulo: string; data?: string }; // recorte do jornal, com o veículo

const VERMELHO = "#FF6B5E";
const VERDE = "#5EE08A";
const ease = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const, easing: Easing.out(Easing.cubic) };

const Barras: React.FC<{ g: Extract<Grafico, { tipo: "barras" }> }> = ({ g }) => {
  const frame = useCurrentFrame();
  const max = Math.max(...g.itens.map((i) => i.valor), 1);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 18 }}>
      {g.itens.map((it, k) => {
        const p = interpolate(frame, [6 + k * 8, 26 + k * 8], [0, 1], ease);
        const ultimo = k === g.itens.length - 1;
        return (
          <div key={k} style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <div style={{ width: 170, fontSize: 34, fontWeight: 700, color: CORES.apagado, textAlign: "right" }}>{it.rotulo}</div>
            <div style={{ flex: 1, height: 58, background: "rgba(255,255,255,.07)", borderRadius: 14, overflow: "hidden" }}>
              <div
                style={{
                  width: `${(it.valor / max) * 100 * p}%`,
                  height: "100%",
                  borderRadius: 14,
                  background: ultimo ? CORES.amarelo : "rgba(169,180,196,.55)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "flex-end",
                  paddingRight: 14,
                  boxSizing: "border-box",
                }}
              >
                <span style={{ fontSize: 36, fontWeight: 900, color: ultimo ? "#14181D" : CORES.texto, opacity: p > 0.6 ? 1 : 0 }}>
                  {it.texto}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const Variacao: React.FC<{ g: Extract<Grafico, { tipo: "variacao" }> }> = ({ g }) => {
  const frame = useCurrentFrame();
  const seta = interpolate(frame, [8, 20], [0, 1], ease);
  const para = interpolate(frame, [16, 28], [0, 1], ease);
  const cor = g.sobe ? VERDE : VERMELHO;
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 24, marginTop: 16, fontWeight: 900 }}>
      <span style={{ fontSize: 64, color: CORES.apagado, textDecoration: para > 0.5 ? "line-through" : "none" }}>{g.de}</span>
      <span style={{ fontSize: 70, color: cor, opacity: seta, transform: `translateX(${(1 - seta) * -30}px)` }}>➜</span>
      <span style={{ fontSize: 76, color: CORES.amarelo, opacity: para, transform: `scale(${0.7 + 0.3 * para})` }}>{g.para}</span>
      {g.delta ? (
        <span
          style={{
            fontSize: 40,
            color: "#14181D",
            background: cor,
            borderRadius: 999,
            padding: "6px 18px",
            opacity: interpolate(frame, [26, 34], [0, 1], ease),
          }}
        >
          {g.sobe ? "▲" : "▼"} {g.delta}
        </span>
      ) : null}
    </div>
  );
};

const Linha: React.FC<{ g: Extract<Grafico, { tipo: "linha" }> }> = ({ g }) => {
  const frame = useCurrentFrame();
  const L = 800;
  const A = 230;
  const vals = g.pontos.map((p) => p.valor);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const xy = g.pontos.map((p, i) => ({
    x: 50 + (i * (L - 100)) / Math.max(1, g.pontos.length - 1),
    y: 40 + (1 - (p.valor - min) / Math.max(1e-9, max - min)) * (A - 90),
  }));
  const caminho = xy.map((p, i) => `${i ? "L" : "M"}${p.x},${p.y}`).join(" ");
  const comp = xy.reduce((s, p, i) => (i ? s + Math.hypot(p.x - xy[i - 1].x, p.y - xy[i - 1].y) : 0), 0);
  const p = interpolate(frame, [6, 36], [0, 1], ease);
  return (
    <svg width={L} height={A} style={{ marginTop: 14, overflow: "visible" }}>
      <path d={caminho} fill="none" stroke={CORES.amarelo} strokeWidth={9} strokeLinecap="round" strokeLinejoin="round"
        strokeDasharray={comp} strokeDashoffset={comp * (1 - p)} />
      {xy.map((q, i) => {
        const aparece = interpolate(frame, [6 + (i * 30) / Math.max(1, xy.length - 1), 12 + (i * 30) / Math.max(1, xy.length - 1)], [0, 1], ease);
        return (
          <g key={i} opacity={aparece}>
            <circle cx={q.x} cy={q.y} r={13} fill={CORES.amarelo} stroke="#14181D" strokeWidth={4} />
            <text x={q.x} y={q.y - 26} textAnchor="middle" fontFamily={FONTE} fontWeight={900} fontSize={36} fill={CORES.texto}>
              {g.pontos[i].texto}
            </text>
            <text x={q.x} y={A - 4} textAnchor="middle" fontFamily={FONTE} fontWeight={700} fontSize={30} fill={CORES.apagado}>
              {g.pontos[i].rotulo}
            </text>
          </g>
        );
      })}
    </svg>
  );
};

// Recorte de jornal: papel claro levemente inclinado, nome do veículo, a manchete entre aspas e a data.
// Sempre o título real da matéria que está na fonte do roteiro, com o veículo escrito: é citação, não imitação.
export const Manchete: React.FC<{ g: Extract<Grafico, { tipo: "manchete" }>; duracao: number }> = ({ g, duracao }) => {
  const frame = useCurrentFrame();
  const entra = interpolate(frame, [0, 10], [0, 1], { ...ease, easing: Easing.bezier(0.34, 1.56, 0.64, 1) });
  const sai = interpolate(frame, [duracao - 6, duracao], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const sublinha = interpolate(frame, [12, 26], [0, 100], ease);
  return (
    <div style={{ position: "absolute", top: 230, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: sai }}>
      <div
        style={{
          width: 900,
          background: "#F7F3EA",
          color: "#16130F",
          borderRadius: 6,
          padding: "26px 36px 28px",
          boxShadow: "0 20px 50px rgba(0,0,0,.5)",
          transform: `rotate(${-1.6 + (1 - entra) * -5}deg) scale(${0.85 + 0.15 * entra})`,
          opacity: entra,
          // borda serrilhada de recorte
          clipPath:
            "polygon(0 2%, 4% 0, 9% 1.5%, 15% 0, 22% 1.2%, 30% 0, 38% 1.6%, 46% 0, 54% 1.3%, 62% 0, 70% 1.5%, 78% 0, 86% 1.2%, 93% 0, 100% 1.8%, 100% 98%, 95% 100%, 88% 98.4%, 80% 100%, 72% 98.6%, 64% 100%, 56% 98.3%, 48% 100%, 40% 98.7%, 32% 100%, 24% 98.4%, 16% 100%, 8% 98.6%, 0 100%)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", borderBottom: "3px solid #16130F", paddingBottom: 8 }}>
          <span style={{ fontFamily: FONTE, fontWeight: 900, fontSize: 34, letterSpacing: ".08em", textTransform: "uppercase" }}>{g.veiculo}</span>
          {g.data ? <span style={{ fontFamily: FONTE, fontWeight: 600, fontSize: 28, color: "#5A5348" }}>{g.data}</span> : null}
        </div>
        <div
          style={{
            marginTop: 16,
            fontFamily: "Georgia, 'DejaVu Serif', serif",
            fontWeight: 700,
            fontSize: 54,
            lineHeight: 1.12,
            backgroundImage: `linear-gradient(${CORES.amarelo}AA, ${CORES.amarelo}AA)`,
            backgroundRepeat: "no-repeat",
            backgroundPosition: "0 92%",
            backgroundSize: `${sublinha}% 30%`,
            display: "inline",
          }}
        >
          “{g.titulo}”
        </div>
      </div>
    </div>
  );
};

export const GraficoNoCartao: React.FC<{ g: Grafico }> = ({ g }) => {
  if (g.tipo === "barras") return <Barras g={g} />;
  if (g.tipo === "variacao") return <Variacao g={g} />;
  if (g.tipo === "linha") return <Linha g={g} />;
  return null;
};
