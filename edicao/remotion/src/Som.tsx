import { Audio } from "@remotion/media";
import { staticFile } from "remotion";

// Efeitos sonoros do Termômetro (feitos em código com o earshot, MIT; ficam em edicao/remotion/sfx).
// Volume baixo de propósito: o som tem de ajudar o olho, nunca brigar com a voz do Heitor.
export const SONS = {
  cartao: { arquivo: "sfx/cartao.wav", volume: 0.32 },
  bordaoWhoosh: { arquivo: "sfx/bordao-whoosh.wav", volume: 0.3 },
  bordaoHit: { arquivo: "sfx/bordao-hit.wav", volume: 0.28 },
  seguir: { arquivo: "sfx/seguir.wav", volume: 0.3 },
};

export const Som: React.FC<{ som: keyof typeof SONS }> = ({ som }) => (
  <Audio src={staticFile(SONS[som].arquivo)} volume={SONS[som].volume} />
);
