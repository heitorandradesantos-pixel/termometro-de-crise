// O que o editar_reel.py entrega para a Remotion (camadas.json). Tempos em segundos, já na linha do tempo do vídeo editado.
export type Palavra = { ini: number; fim: number; texto: string; destaque: boolean };
export type Bloco = { ini: number; fim: number; palavras: Palavra[] };
export type Cartao = { ini: number; fim: number; texto: string; fonte: string; cor?: string | null };

export type Camadas = {
  video: string; // arquivo dentro da pasta pública (o vídeo cortado, com o som tratado)
  total: number; // duração do vídeo cortado
  final: number; // segundos da tela final "siga"
  legendas: Bloco[];
  cartoes: Cartao[];
  bordao: { ini: number; fim: number } | null;
};

export const CORES = {
  fundo: "#0E141B",
  painel: "rgba(14,20,27,.92)",
  borda: "rgba(124,195,224,.55)",
  texto: "#EEF2F5",
  apagado: "#A9B4C4",
  amarelo: "#F2C14E",
};
export const FONTE = "'Inter Display', 'Inter', sans-serif";
