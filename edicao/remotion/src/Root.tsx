import { Composition } from "remotion";
import { Capa } from "./Capa";
import { calcularInflacao, MotionInflacao } from "./MotionInflacao";
import { calcularReel, Reel } from "./Reel";
import { Camadas } from "./tipos";

// Exemplo para abrir no Studio (npx remotion studio). Na edição de verdade, o editar_reel.py passa o camadas.json.
const EXEMPLO: Camadas = {
  video: "base.mp4",
  total: 6,
  final: 3,
  legendas: [
    {
      ini: 0.2,
      fim: 1.4,
      palavras: [
        { ini: 0.2, fim: 0.6, texto: "Comprei", destaque: false },
        { ini: 0.6, fim: 0.9, texto: "dólar", destaque: true },
        { ini: 0.9, fim: 1.3, texto: "a R$ 4,98", destaque: true },
      ],
    },
  ],
  cartoes: [{ ini: 0, fim: 3, texto: "Comprei a *R$ 4,98* · hoje *R$ 5,59*", fonte: "" }],
  bordao: { ini: 4.2, fim: 5.6 },
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
    <Composition
      id="Reel"
      component={Reel}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={270}
      defaultProps={EXEMPLO}
      calculateMetadata={calcularReel}
    />
    <Composition
      id="Capa"
      component={Capa}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={1}
      defaultProps={{ foto: "foto.jpg", texto: "Dólar a *R$ 5,58*" }}
    />
    <Composition
      id="MotionInflacao"
      component={MotionInflacao}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={900}
      calculateMetadata={calcularInflacao}
      defaultProps={{
        anoBase: 2017,
        anos: [
          { ano: 2017, taxa: 2.95 }, { ano: 2018, taxa: 3.75 }, { ano: 2019, taxa: 4.31 }, { ano: 2020, taxa: 4.52 },
          { ano: 2021, taxa: 10.06, nota: "pandemia" }, { ano: 2022, taxa: 5.78 }, { ano: 2023, taxa: 4.62 }, { ano: 2024, taxa: 4.83 },
          { ano: 2025, taxa: 4.26 }, { ano: 2026, taxa: 4.1 },
        ],
        ultimoRotulo: "2026 (até outubro)",
        itens: ["🍚", "🫘", "🥛", "☕", "🍞", "🥚", "🧈", "🍌", "🍅", "🧻"],
        fonte: "IPCA/IBGE",
        pergunta: "Seu dinheiro cresceu mais que isso?",
      }}
    />
    </>
  );
};
