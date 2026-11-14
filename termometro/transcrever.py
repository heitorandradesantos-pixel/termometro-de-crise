"""Transcrição dos vídeos gravados pelo Heitor (faster-whisper, em português, com o tempo de cada palavra).
Roda no robô (workflow Transcrever); a edição usa o resultado para cortar erros e pausas e legendar."""
import json
import os
import subprocess
import sys

import numpy as np


def rodar(arquivo: str) -> list[dict]:
    from faster_whisper import WhisperModel
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", arquivo, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                           check=True, capture_output=True).stdout
    audio = np.frombuffer(bruto, dtype=np.float32)
    modelo = WhisperModel(os.environ.get("MODELO") or "medium", device="cpu", compute_type="int8")
    # o começo do prompt ensina o modelo a escrever ao pé da letra (com "de de", "é... é"), para a edição achar
    # palavra repetida e gaguejo; o resto traz os nomes do roteiro
    prompt = "Então, então, é... é isso. O, o mercado de de hoje. " + (os.environ.get("TEXTO") or "")
    segs, _ = modelo.transcribe(audio, language="pt", word_timestamps=True, vad_filter=False, beam_size=5,
                                condition_on_previous_text=False, initial_prompt=prompt)
    saida = [{"ini": round(s.start, 2), "fim": round(s.end, 2), "texto": s.text.strip(),
              "palavras": [[round(w.start, 2), round(w.end, 2), w.word.strip(), round(w.probability, 2)] for w in s.words]}
             for s in segs]
    if os.environ.get("ALINHAR", "1") != "0":
        try:
            alinhar(audio, saida)
        except Exception as erro:  # alinhamento é melhoria: se falhar, fica o tempo do Whisper
            print(f"alinhamento falhou, mantendo o tempo do Whisper: {erro}", file=sys.stderr)
    return saida


def _letras(palavra: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", palavra.lower()).encode("ascii", "ignore").decode()
    return "".join(c for c in t if "a" <= c <= "z")


def alinhar(audio, saida: list[dict]) -> None:
    """Acerta o tempo de cada palavra no áudio (alinhamento forçado com o modelo MMS da Meta, via torchaudio).
    O Whisper acerta o TEXTO, mas em fala corrida erra o tempo em até 2 s (a legenda escorrega). Aqui o texto do
    Whisper é encaixado no áudio letra a letra; número e símbolo (sem letras) ficam entre os vizinhos."""
    import torch
    import torchaudio
    pacote = torchaudio.pipelines.MMS_FA
    modelo = pacote.get_model(with_star=False)
    dicionario = pacote.get_dict(star=None)
    taxa = pacote.sample_rate  # 16 kHz, igual ao áudio
    onda = torch.from_numpy(np.ascontiguousarray(audio)).unsqueeze(0)
    passo, emissoes = taxa * 20, []
    with torch.inference_mode():
        for i in range(0, onda.size(1), passo):
            pedaco = onda[:, i:i + passo]
            if pedaco.size(1) < 400:
                continue
            emissoes.append(modelo(pedaco)[0][0])
    emissao = torch.cat(emissoes)
    seg_por_quadro = onda.size(1) / taxa / emissao.size(0)
    palavras = [w for s in saida for w in s["palavras"]]
    letras = [_letras(w[2]) for w in palavras]
    idx = [i for i, t in enumerate(letras) if t]
    tokens = [dicionario[c] for i in idx for c in letras[i]]
    if not tokens:
        return
    alvo = torch.tensor([tokens], dtype=torch.int32)
    rotulos, _ = torchaudio.functional.forced_align(emissao.unsqueeze(0), alvo, blank=0)
    spans = torchaudio.functional.merge_tokens(rotulos[0], torch.zeros(len(rotulos[0])))
    k = 0
    for i in idx:
        n = len(letras[i])
        grupo = spans[k:k + n]
        k += n
        palavras[i][0] = round(grupo[0].start * seg_por_quadro, 2)
        palavras[i][1] = round(grupo[-1].end * seg_por_quadro, 2)
    # palavras sem letras (números, %): entre o fim da anterior e o começo da próxima
    for i, t in enumerate(letras):
        if t:
            continue
        ant = next((palavras[j][1] for j in range(i - 1, -1, -1) if letras[j]), 0.0)
        prox = next((palavras[j][0] for j in range(i + 1, len(palavras)) if letras[j]), ant + 0.3)
        palavras[i][0], palavras[i][1] = round(ant, 2), round(max(ant, prox), 2)
    for s in saida:
        if s["palavras"]:
            s["ini"], s["fim"] = s["palavras"][0][0], s["palavras"][-1][1]


if __name__ == "__main__":
    resultado = rodar(sys.argv[1])  # antes do marcador: avisos e barras de download não podem cair no meio do JSON
    print("TRANSCRICAO_INICIO")
    print(json.dumps(resultado, ensure_ascii=False))
    print("TRANSCRICAO_FIM")
