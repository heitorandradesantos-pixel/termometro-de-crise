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
    return [{"ini": round(s.start, 2), "fim": round(s.end, 2), "texto": s.text.strip(),
             "palavras": [[round(w.start, 2), round(w.end, 2), w.word.strip(), round(w.probability, 2)] for w in s.words]}
            for s in segs]


if __name__ == "__main__":
    print("TRANSCRICAO_INICIO")
    print(json.dumps(rodar(sys.argv[1]), ensure_ascii=False))
    print("TRANSCRICAO_FIM")
