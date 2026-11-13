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
import { brl, clamp, EMOJI, Fecho, Gancho, Pergunta, Selo, Sfx, VERMELHO } from "./MotionComparar";
import { CORES, FONTE } from "./tipos";

// Série "direitos do seu bolso" (13/11), só motion. Regras conferidas em fonte oficial:
// - Nome limpo: Súmula 548 do STJ (5 dias úteis após o pagamento integral) e CDC art. 43 §1º (máximo 5 anos).
// - Pix: MED do Banco Central (vítima pede em até 80 dias; MED 2.0 rastreia até 5 transferências).
const VERDE = "#4CC38A";

const Cena: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 70px", fontFamily: FONTE,
    color: CORES.texto }}>{children}</AbsoluteFill>
);

// ======================================================================= NOME LIMPO
export type DadosNomeLimpo = { pergunta: string; opcoes: [string, string]; rodape: string };
export const temposNome = { gancho: 4.2, quitou: 5.0, prazo: 11.0, passou: 7.5, cinco: 6.0, pergunta: 5.0, bordao: 3.8 };
const totalN = () => Object.values(temposNome).reduce((a, b) => a + b, 0);
export const calcularNome: CalculateMetadataFunction<DadosNomeLimpo> = () => ({ durationInFrames: Math.round(totalN() * 30) });

export const MotionNomeLimpo: React.FC<DadosNomeLimpo> = (d) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const T = temposNome;
  const t1 = T.gancho, t2 = t1 + T.quitou, t3 = t2 + T.prazo, t4 = t3 + T.passou, t5 = t4 + T.cinco, t6 = t5 + T.pergunta;
  const seq = (ini: number, el: React.ReactNode) => <Sequence from={Math.round(ini * fps)} layout="none">{el}</Sequence>;
  const fundo = interpolateColors(t < t3 ? interpolate(t, [t2, t3], [0, 1], clamp) : 1, [0, 1], ["#132230", "#14301F"]);
  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, ${fundo} 0%, #0B0F14 75%)` }} />
      <Selo />
      {t < t1 ? (
        <>
          <Gancho l1={<>Pagou a dívida e o nome <span style={{ color: VERMELHO }}>continua sujo?</span></>} l2="Isso tem prazo. E é curto." />
          <div style={{ position: "absolute", top: 800, left: 0, right: 0, textAlign: "center", fontFamily: EMOJI, fontSize: 300,
            transform: `rotate(${Math.sin(t * 3) * 5}deg)` }}>🧾</div>
        </>
      ) : null}
      {t >= t1 && t < t2 ? seq(t1, <Quitou />) : null}
      {t >= t2 && t < t3 ? seq(t2, <Calendario dur={T.prazo} />) : null}
      {t >= t3 && t < t4 ? seq(t3, <Passou />) : null}
      {t >= t4 && t < t5 ? seq(t4, <CincoAnos />) : null}
      {t >= t5 && t < t6 ? seq(t5, <Pergunta texto={d.pergunta} opcoes={d.opcoes} rodape={d.rodape} />) : null}
      {t >= t6 ? seq(t6, <Fecho />) : null}
      <Sfx arq="cartao" vol={0.4} em={0.05} />
      <Sfx arq="impacto" vol={0.5} em={t1 + 1.2} />
      {[0, 1, 2, 3, 4].map((i) => <Sfx key={i} arq="tick" vol={0.5} em={t2 + 2.2 + i * 1.5} />)}
      <Sfx arq="destaque" vol={0.45} em={t2 + 2.2 + 4 * 1.5 + 0.6} />
      <Sfx arq="choque" vol={0.4} em={t3 + 0.3} />
      <Sfx arq="subida" vol={0.3} em={t4 + 0.3} />
      <Sfx arq="seguir" vol={0.35} em={t5} />
      <Sfx arq="bordao-whoosh" vol={0.35} em={t6} />
    </AbsoluteFill>
  );
};

const Quitou: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const s = spring({ frame: frame - 36, fps, config: { damping: 7, stiffness: 220 } });
  return (
    <Cena>
      <div style={{ fontWeight: 800, fontSize: 56, color: CORES.apagado, opacity: a }}>Você quitou a dívida.</div>
      <div style={{ position: "relative", marginTop: 50, width: 700, height: 420, borderRadius: 24, background: "#F4F1EA", color: "#14181D",
        padding: "40px 46px", textAlign: "left", boxShadow: "0 30px 70px rgba(0,0,0,.5)", transform: `translateY(${(1 - a) * 60}px)` }}>
        <div style={{ fontWeight: 900, fontSize: 40 }}>Boleto · Quitação</div>
        <div style={{ height: 3, background: "#CCC", margin: "18px 0" }} />
        <div style={{ fontSize: 34, fontWeight: 700 }}>Valor: {brl(850, 2)}</div>
        <div style={{ fontSize: 30, marginTop: 10, color: "#555" }}>|| ||| | |||| || ||| || |||| |</div>
        <div style={{ position: "absolute", right: 30, bottom: 50, fontWeight: 900, fontSize: 92, color: VERDE, border: `10px solid ${VERDE}`,
          borderRadius: 18, padding: "4px 26px", transform: `rotate(-12deg) scale(${1.6 - 0.6 * s})`, opacity: s }}>PAGO</div>
      </div>
      <div style={{ fontWeight: 900, fontSize: 64, marginTop: 50, opacity: s }}>E agora? Quanto tempo o credor tem?</div>
    </Cena>
  );
};

const Calendario: React.FC<{ dur: number }> = ({ dur }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const contados = Math.max(0, Math.min(5, Math.floor((t - 2.2) / 1.5) + 1));
  const fim = spring({ frame: frame - Math.round((2.2 + 4 * 1.5 + 0.6) * fps), fps, config: { damping: 9 } });
  void dur;
  // 5 dias úteis: SEX, SEG, TER, QUA, QUI → mostro 2 semanas compactas
  const grade = ["QUI", "SEX", "SÁB", "DOM", "SEG", "TER", "QUA", "QUI"];
  const util = [null, 1, null, null, 2, 3, 4, 5];
  return (
    <Cena>
      <div style={{ fontWeight: 800, fontSize: 52, color: CORES.apagado, lineHeight: 1.15 }}>Pagou numa quinta-feira:</div>
      <div style={{ marginTop: 40, display: "grid", gridTemplateColumns: "repeat(4, 210px)", gap: 22 }}>
        {grade.map((dia, i) => {
          const n = util[i];
          const ativo = n !== null && n <= contados;
          const fds = n === null && i > 0;
          return (
            <div key={i} style={{ height: 210, borderRadius: 26, display: "flex", flexDirection: "column", alignItems: "center",
              justifyContent: "center", background: i === 0 ? "rgba(76,195,138,.25)" : ativo ? CORES.amarelo : "rgba(255,255,255,.07)",
              color: ativo ? "#14181D" : fds ? "rgba(255,255,255,.35)" : CORES.texto, border: i === 0 ? `4px solid ${VERDE}` : "none",
              transform: ativo && n === contados ? `scale(${1 + 0.06 * Math.max(0, 1 - ((t - 2.2) % 1.5) * 3)})` : undefined }}>
              <div style={{ fontWeight: 800, fontSize: 38 }}>{dia}</div>
              <div style={{ fontWeight: 900, fontSize: 70, marginTop: 6 }}>{i === 0 ? "✓" : n ?? "—"}</div>
              {fds ? <div style={{ fontWeight: 700, fontSize: 24 }}>não conta</div> : null}
              {i === 0 ? <div style={{ fontWeight: 700, fontSize: 24, color: VERDE }}>pagou</div> : null}
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: 50, fontWeight: 900, fontSize: 76, lineHeight: 1.05, opacity: fim, transform: `scale(${0.8 + 0.2 * fim})` }}>
        <span style={{ color: CORES.amarelo }}>5 dias úteis</span> pra tirar seu nome
      </div>
      <div style={{ marginTop: 18, fontWeight: 600, fontSize: 30, color: CORES.apagado, opacity: fim }}>
        Súmula 548 do STJ · contados a partir do pagamento da dívida
      </div>
    </Cena>
  );
};

const Passou: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const itens = ["Cobre o credor (guarde o comprovante)", "Reclame no Procon e no consumidor.gov.br", "Nome sujo depois de pago pode dar indenização"];
  return (
    <Cena>
      <div style={{ fontWeight: 900, fontSize: 84, lineHeight: 1.05, opacity: a }}>Passou do prazo?</div>
      <div style={{ marginTop: 50, display: "flex", flexDirection: "column", gap: 26, width: "100%" }}>
        {itens.map((x, i) => {
          const s = spring({ frame: frame - 25 - i * 30, fps, config: { damping: 13 } });
          return (
            <div key={x} style={{ display: "flex", alignItems: "center", gap: 26, textAlign: "left", background: "rgba(255,255,255,.07)",
              borderRadius: 26, padding: "26px 30px", opacity: s, transform: `translateX(${(1 - s) * 80}px)` }}>
              <span style={{ flex: "none", width: 76, height: 76, borderRadius: 99, background: CORES.amarelo, color: "#14181D",
                fontWeight: 900, fontSize: 44, display: "flex", alignItems: "center", justifyContent: "center" }}>{i + 1}</span>
              <span style={{ fontWeight: 800, fontSize: 46, lineHeight: 1.15 }}>{x}</span>
            </div>
          );
        })}
      </div>
    </Cena>
  );
};

const CincoAnos: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const b = spring({ frame: frame - 30, fps, config: { damping: 9, stiffness: 160 } });
  const c = spring({ frame: frame - 80, fps, config: { damping: 14 } });
  return (
    <Cena>
      <div style={{ fontWeight: 800, fontSize: 54, color: CORES.apagado, opacity: a, lineHeight: 1.15 }}>
        E mesmo sem pagar, a negativação tem limite:
      </div>
      <div style={{ fontWeight: 900, fontSize: 240, color: CORES.amarelo, letterSpacing: "-.04em", lineHeight: 1, margin: "30px 0 0",
        transform: `scale(${0.7 + 0.3 * b})` }}>5 anos</div>
      <div style={{ fontWeight: 800, fontSize: 48, opacity: b }}>no máximo no cadastro</div>
      <div style={{ marginTop: 44, fontWeight: 700, fontSize: 38, color: CORES.apagado, opacity: c, lineHeight: 1.25 }}>
        A dívida não some. Mas o nome sai da lista.
      </div>
      <div style={{ marginTop: 22, fontWeight: 600, fontSize: 30, color: CORES.apagado, opacity: c }}>
        Código de Defesa do Consumidor, art. 43
      </div>
    </Cena>
  );
};

// ======================================================================= PIX GOLPE
export type DadosPix = { valor: number; pergunta: string; opcoes: [string, string]; rodape: string };
export const temposPix = { gancho: 4.2, oitenta: 7.0, corre: 9.0, rastro: 7.5, passos: 8.0, pergunta: 5.0, bordao: 3.8 };
const totalP = () => Object.values(temposPix).reduce((a, b) => a + b, 0);
export const calcularPix: CalculateMetadataFunction<DadosPix> = () => ({ durationInFrames: Math.round(totalP() * 30) });

export const MotionPixGolpe: React.FC<DadosPix> = (d) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const T = temposPix;
  const t1 = T.gancho, t2 = t1 + T.oitenta, t3 = t2 + T.corre, t4 = t3 + T.rastro, t5 = t4 + T.passos, t6 = t5 + T.pergunta;
  const seq = (ini: number, el: React.ReactNode) => <Sequence from={Math.round(ini * fps)} layout="none">{el}</Sequence>;
  const fundo = interpolateColors(t > t2 && t < t3 ? 1 : 0, [0, 1], ["#132230", "#3A1414"]);
  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: CORES.texto, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, ${fundo} 0%, #0B0F14 75%)` }} />
      <Selo />
      {t < t1 ? (
        <>
          <Gancho l1={<>Caiu num golpe do Pix? <span style={{ color: CORES.amarelo }}>Dá pra pedir o dinheiro de volta.</span></>}
            l2="Mas tem prazo, e tem pressa." />
          <div style={{ position: "absolute", top: 820, left: 0, right: 0, textAlign: "center", fontFamily: EMOJI, fontSize: 300,
            transform: `scale(${1 + 0.05 * Math.sin(t * 6)})` }}>🚨</div>
        </>
      ) : null}
      {t >= t1 && t < t2 ? seq(t1, <Oitenta />) : null}
      {t >= t2 && t < t3 ? seq(t2, <Corre valor={d.valor} dur={T.corre} />) : null}
      {t >= t3 && t < t4 ? seq(t3, <Rastro />) : null}
      {t >= t4 && t < t5 ? seq(t4, <Passos />) : null}
      {t >= t5 && t < t6 ? seq(t5, <Pergunta texto={d.pergunta} opcoes={d.opcoes} rodape={d.rodape} />) : null}
      {t >= t6 ? seq(t6, <Fecho />) : null}
      <Sfx arq="choque" vol={0.4} em={0.05} />
      <Sfx arq="impacto" vol={0.45} em={t1 + 1.0} />
      {Array.from({ length: 8 }, (_, i) => <Sfx key={i} arq="tick" vol={0.45} em={t2 + 1.0 + i * 0.85} />)}
      {[0, 1, 2, 3, 4].map((i) => <Sfx key={`r${i}`} arq="cartao" vol={0.35} em={t3 + 1.0 + i * 0.8} />)}
      <Sfx arq="subida" vol={0.3} em={t4 + 0.2} />
      <Sfx arq="seguir" vol={0.35} em={t5} />
      <Sfx arq="bordao-whoosh" vol={0.35} em={t6} />
    </AbsoluteFill>
  );
};

const Oitenta: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const conta = Math.round(interpolate(frame, [15, 70], [0, 80], { ...clamp, easing: Easing.out(Easing.cubic) }));
  const p = interpolate(frame, [15, 70], [0, 1], clamp);
  const c = spring({ frame: frame - 90, fps, config: { damping: 14 } });
  return (
    <Cena>
      <div style={{ fontWeight: 800, fontSize: 52, color: CORES.apagado, opacity: a, lineHeight: 1.15 }}>
        O nome disso é <span style={{ color: CORES.texto }}>MED</span>, o mecanismo de devolução do Pix.
      </div>
      <div style={{ fontWeight: 900, fontSize: 230, color: CORES.amarelo, letterSpacing: "-.04em", lineHeight: 1, marginTop: 40 }}>{conta} dias</div>
      <div style={{ fontWeight: 800, fontSize: 46 }}>pra pedir, contando do dia do Pix</div>
      <div style={{ marginTop: 40, width: 860, height: 34, borderRadius: 99, background: "rgba(255,255,255,.1)", overflow: "hidden" }}>
        <div style={{ width: `${p * 100}%`, height: "100%", background: CORES.amarelo }} />
      </div>
      <div style={{ marginTop: 34, fontWeight: 700, fontSize: 40, color: VERMELHO, opacity: c }}>Mas não espere 80 dias. Veja por quê:</div>
    </Cena>
  );
};

const Corre: React.FC<{ valor: number; dur: number }> = ({ valor, dur }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  void dur;
  const p = interpolate(t, [1.0, 7.8], [0, 1], { ...clamp, easing: Easing.in(Easing.quad) });
  const saldo = valor * (1 - p);
  const horas = ["10 min", "1 hora", "3 horas", "1 dia"];
  const h = horas[Math.min(3, Math.floor(p * 4))];
  return (
    <Cena>
      <div style={{ fontWeight: 800, fontSize: 52, color: CORES.apagado, lineHeight: 1.15 }}>
        O golpista tira o dinheiro da conta rápido.<br />Só volta o que <span style={{ color: CORES.texto }}>ainda estiver lá</span>.
      </div>
      <div style={{ marginTop: 50, width: 760, borderRadius: 30, padding: "36px 40px", background: "rgba(255,255,255,.07)",
        border: `4px solid ${VERMELHO}` }}>
        <div style={{ fontWeight: 800, fontSize: 38, color: CORES.apagado }}>Conta do golpista · depois de {h}</div>
        <div style={{ fontWeight: 900, fontSize: 150, color: interpolateColors(p, [0, 1], [CORES.texto, VERMELHO]), letterSpacing: "-.03em" }}>
          {brl(saldo)}
        </div>
        <div style={{ height: 30, borderRadius: 99, background: "rgba(255,255,255,.1)", overflow: "hidden" }}>
          <div style={{ width: `${(1 - p) * 100}%`, height: "100%", background: VERMELHO }} />
        </div>
      </div>
      <div style={{ marginTop: 40, fontWeight: 900, fontSize: 70, color: CORES.amarelo }}>Avise o banco no mesmo dia.</div>
      <div style={{ marginTop: 14, fontWeight: 600, fontSize: 28, color: CORES.apagado }}>Ilustração: o tempo varia de caso a caso</div>
    </Cena>
  );
};

const Rastro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const c = spring({ frame: frame - 170, fps, config: { damping: 14 } });
  return (
    <Cena>
      <div style={{ fontWeight: 900, fontSize: 70, lineHeight: 1.05, opacity: a }}>
        O <span style={{ color: CORES.amarelo }}>MED 2.0</span> segue o dinheiro
      </div>
      <div style={{ fontWeight: 700, fontSize: 42, color: CORES.apagado, marginTop: 14 }}>por até 5 transferências, inclusive em contas "laranja"</div>
      <div style={{ marginTop: 60, display: "flex", gap: 10, alignItems: "center" }}>
        {[1, 2, 3, 4, 5].map((n, i) => {
          const s = spring({ frame: frame - 30 - i * 24, fps, config: { damping: 11 } });
          return (
            <div key={n} style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <div style={{ width: 132, height: 132, borderRadius: 28, background: "rgba(255,255,255,.08)", border: `4px solid ${CORES.amarelo}`,
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", transform: `scale(${s})` }}>
                <span style={{ fontFamily: EMOJI, fontSize: 64 }}>🏦</span>
                <span style={{ fontWeight: 900, fontSize: 36 }}>{n}ª</span>
              </div>
              {i < 4 ? <span style={{ fontSize: 50, opacity: s, color: CORES.amarelo }}>›</span> : null}
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: 60, fontWeight: 800, fontSize: 46, opacity: c }}>
        e os bancos bloqueiam juntos o que acharem.
      </div>
    </Cena>
  );
};

const Passos: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 14 } });
  const itens = ["Ligue pro seu banco e peça o MED", "Faça o boletim de ocorrência", "Guarde prints e comprovantes"];
  return (
    <Cena>
      <div style={{ fontWeight: 900, fontSize: 84, lineHeight: 1.05, opacity: a }}>Caiu? Faça hoje:</div>
      <div style={{ marginTop: 50, display: "flex", flexDirection: "column", gap: 26, width: "100%" }}>
        {itens.map((x, i) => {
          const s = spring({ frame: frame - 25 - i * 30, fps, config: { damping: 13 } });
          return (
            <div key={x} style={{ display: "flex", alignItems: "center", gap: 26, textAlign: "left", background: "rgba(255,255,255,.07)",
              borderRadius: 26, padding: "26px 30px", opacity: s, transform: `translateX(${(1 - s) * 80}px)` }}>
              <span style={{ flex: "none", width: 76, height: 76, borderRadius: 99, background: CORES.amarelo, color: "#14181D",
                fontWeight: 900, fontSize: 44, display: "flex", alignItems: "center", justifyContent: "center" }}>{i + 1}</span>
              <span style={{ fontWeight: 800, fontSize: 48, lineHeight: 1.15 }}>{x}</span>
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: 40, fontWeight: 600, fontSize: 30, color: CORES.apagado }}>
        Não vale pra Pix enviado por engano nem compra arrependida · Fonte: Banco Central
      </div>
    </Cena>
  );
};
