import { Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { Cartao, CORES, FONTE } from "./tipos";

// Número em formato brasileiro (1.234,56) dentro do destaque: conta de zero até o valor, como um placar.
const NUMERO = /^(.*?)(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)(.*)$/s;

const formatar = (v: number, casas: number, milhar: boolean) => {
  const [int, dec] = v.toFixed(casas).split(".");
  const inteiro = milhar ? int.replace(/\B(?=(\d{3})+(?!\d))/g, ".") : int;
  return dec ? `${inteiro},${dec}` : inteiro;
};

const Placar: React.FC<{ texto: string; inicio: number; contar: boolean }> = ({ texto, inicio, contar }) => {
  const frame = useCurrentFrame();
  const m = texto.match(NUMERO);
  if (!m || !contar) return <>{texto}</>;
  const [, antes, num, depois] = m;
  const casas = num.includes(",") ? num.split(",")[1].length : 0;
  const valor = Number(num.replace(/\./g, "").replace(",", "."));
  const p = interpolate(frame - inicio, [0, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  // largura fixa pelo número final, para o cartão não "pular" enquanto conta
  return (
    <>
      {antes}
      <span style={{ display: "inline-grid" }}>
        <span style={{ gridArea: "1/1", visibility: "hidden" }}>{num}</span>
        <span style={{ gridArea: "1/1", textAlign: "right" }}>{formatar(valor * p, casas, num.includes("."))}</span>
      </span>
      {depois}
    </>
  );
};

// o cartão do gancho (no primeiro segundo) já nasce com o número: é o quadro que aparece na capa e no feed
const CartaoAnimado: React.FC<{ cartao: Cartao; duracao: number }> = ({ cartao, duracao }) => {
  const contar = cartao.ini >= 1;
  const frame = useCurrentFrame();
  const partes = cartao.texto.split(/(\*[^*]+\*)/g).filter(Boolean);
  const cor = cartao.cor || CORES.amarelo;
  return (
    <div
      style={{
        position: "absolute",
        top: 245,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        opacity: interpolate(frame, [0, contar ? 5 : 0.01, duracao - 6, duracao], [contar ? 0 : 1, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        }),
        translate: interpolate(frame, [0, 9], [contar ? "0px -46px" : "0px 0px", "0px 0px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
      }}
    >
      <div
        style={{
          maxWidth: 900,
          background: CORES.painel,
          border: `2px solid ${CORES.borda}`,
          borderRadius: 30,
          padding: "26px 34px 24px",
          fontFamily: FONTE,
          color: CORES.texto,
          boxShadow: "0 12px 40px rgba(0,0,0,.35)",
        }}
      >
        <div style={{ fontWeight: 800, fontSize: 60, lineHeight: 1.12, letterSpacing: "-.01em" }}>
          {partes.map((p, i) =>
            p.startsWith("*") ? (
              <span
                key={i}
                style={{
                  color: cor,
                  // marca-texto que passa por baixo do destaque logo depois que o cartão entra
                  backgroundImage: `linear-gradient(${cor}38, ${cor}38)`,
                  backgroundRepeat: "no-repeat",
                  backgroundPosition: "0 88%",
                  backgroundSize: `${interpolate(frame, [8, 20], [0, 100], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                    easing: Easing.out(Easing.cubic),
                  })}% 32%`,
                }}
              >
                <Placar texto={p.slice(1, -1)} inicio={4} contar={contar} />
              </span>
            ) : (
              <span key={i}>{p}</span>
            ),
          )}
        </div>
        {cartao.fonte ? (
          <div style={{ marginTop: 12, fontWeight: 600, fontSize: 30, color: CORES.apagado }}>{cartao.fonte}</div>
        ) : null}
      </div>
    </div>
  );
};

export const Cartoes: React.FC<{ cartoes: Cartao[]; total: number }> = ({ cartoes, total }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {cartoes.map((c, i) => {
        const ini = c.ini < 0.5 ? 0 : Math.round(c.ini * fps); // o cartão do gancho já está na capa
        const fim = Math.min(Math.round(c.fim * fps), Math.round(total * fps));
        const dur = Math.max(fim - ini, Math.round(0.3 * fps));
        return (
          <Sequence key={i} name={`Cartão ${i + 1}`} from={ini} durationInFrames={dur} layout="none">
            <CartaoAnimado cartao={c} duracao={dur} />
          </Sequence>
        );
      })}
    </>
  );
};
