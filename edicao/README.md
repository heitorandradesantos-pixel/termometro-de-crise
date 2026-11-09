# Edição dos Reels

Cada pasta guarda como um vídeo do Heitor foi editado: o script (`editar.py`), a transcrição com o tempo de cada
palavra (workflow Transcrever) e a legenda gerada. O vídeo bruto e o editado não ficam aqui.

Como o script funciona (vale para os próximos):
1. Transcrição no robô (`transcrever.yml`), com o áudio criptografado num ramo temporário que o próprio workflow apaga.
2. Cortes: pausas acima de 0,16 s (energia abaixo de -31 dB) e frases que saíram erradas, presos ao quadro de 1/30 s.
3. Um passe só para cortar vídeo (select) e áudio (atrim em amostras), com o atraso de início do áudio do iPhone
   compensado: imagem e som ficam presos do começo ao fim (conferido por correlação: 0 ms de desvio).
4. Zoom alternado de 8% nos cortes, cartões com a fonte no terço de cima, selo da marca e legenda de 2 a 3
   palavras (Inter Display Black, números e nomes em amarelo).
5. Áudio: passa-alta, redução de ruído leve, compressor e -14 LUFS, com os 25 ms de atraso dos filtros compensados.
