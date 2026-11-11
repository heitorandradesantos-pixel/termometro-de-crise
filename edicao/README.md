# Edição dos Reels

Cada pasta guarda como um vídeo do Heitor foi editado: o script (`editar.py`), a transcrição com o tempo de cada
palavra (workflow Transcrever) e a legenda gerada. O vídeo bruto e o editado não ficam aqui.

Como o script funciona (vale para os próximos):
1. Transcrição no robô (`transcrever.yml`), com o áudio criptografado num ramo temporário que o próprio workflow apaga.
2. Cortes: pausas e frases que saíram erradas, presos ao quadro de 1/30 s. Lição do Reel da Nvidia (o Heitor
   notou palavras comidas nos cortes e uma palavra repetida no começo):
   - nenhum corte entra numa palavra: cada palavra da transcrição fica protegida de 0,05 s antes a 0,08 s depois
     (o fim de palavra com "s", "f", "x" tem pouca energia e o corte só por volume engolia);
   - folga de 0,09 s antes e 0,07 s depois de cada pausa cortada, e só pausa de 0,25 s ou mais;
   - palavra repetida e gaguejo ("de de", "o o"): a transcrição sai ao pé da letra e cada palavra longa demais ou
     com silêncio no meio é conferida; fica só a última tentativa;
   - conferência final: o vídeo editado é transcrito de novo e comparado com o texto pretendido. Palavra faltando
     ou repetida volta para o corte antes de mandar.
3. Um passe só para cortar vídeo (select) e áudio (atrim em amostras), com o atraso de início do áudio do iPhone
   compensado: imagem e som ficam presos do começo ao fim (conferido por correlação: 0 ms de desvio).
4. Zoom alternado de 8% nos cortes, cartões com a fonte no terço de cima, selo da marca e legenda de 2 a 3
   palavras (Inter Display Black, números e nomes em amarelo).
5. Áudio: passa-alta, redução de ruído leve, compressor e -14 LUFS, com os 25 ms de atraso dos filtros compensados.
6. Tela final de 3 s (pedido do Heitor, a partir de 10/11): "Siga o @termometrodecrise para atualizações diárias
   do mercado financeiro", com o logo e o botão "Seguir". Curta de propósito: tela parada longa faz a pessoa
   passar o Reel antes do fim e derruba o alcance. Duração ajustável com `"final"` no config.json (ex.: 5).

## Teste da apresentação (a partir de 11/11)
O roteiro traz "Muito prazer, eu sou o Heitor, do Termômetro de Crise." depois do gancho. Na edição, alterne:
um vídeo sai COM a frase, o seguinte SEM (corte com `"remover"` no config.json). Anote no config `"teste": "com"`
ou `"teste": "sem"`. No sábado, o painel compara o tempo médio dos dois grupos.
