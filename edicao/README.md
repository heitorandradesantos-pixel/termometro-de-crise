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

## Apresentação no fim (a partir de 11/11)
O vídeo abre no gancho. "Eu sou o Heitor, do Termômetro de Crise. Não recomendamos: só mostramos a temperatura do
mundo." vem no fim, antes do bordão. Não há mais teste com e sem apresentação.

## Motor gráfico: Remotion (a partir de 11/11)
- O corte, o zoom e o som continuam no ffmpeg. Legendas, cartões, selo, bordão e tela final agora são animados em
  React com a Remotion (pasta `edicao/remotion`), seguindo as skills oficiais (`npx skills add remotion-dev/skills`).
- O que ganhou animação: a legenda entra com um "pop" e a palavra falada sobe um pouco; o cartão desce, o destaque
  ganha marca-texto e o número conta como placar (menos no cartão do gancho, que já nasce pronto para a capa); o
  ponteiro do medidor varre no bordão e na tela final; o botão "Seguir" pulsa.
- `python editar_reel.py <pasta>` usa a Remotion por padrão; `"motor": "ffmpeg"` no config.json volta ao jeito antigo.
- Licença: a Remotion é grátis para pessoa física e empresa com até 3 pessoas (nosso caso). Acima disso, licença de empresa.
- Aqui, a Remotion usa o Chromium que já vem instalado (a rede bloqueia o download do navegador dela).

## Efeitos sonoros (a partir de 12/11)
- Pasta `edicao/remotion/sfx`: pop na entrada de cada cartão, whoosh + impacto no bordão e ding no "Seguir" da tela final.
  Feitos em código com o earshot (github.com/Leonxlnx/earshot, MIT): `earshot sfx render pro_pop_in/round -o cartao.wav --peak -3`.
- Volume baixo (0,28 a 0,32) para não brigar com a voz. `"sons": false` no config.json desliga.

## Fluxo completo (revisado na retrospectiva de 12/11)
1. **Chegam os vídeos** → copie cada um para `pasta/vN/original.mov`.
2. **Transcrever todos de uma vez:** `edicao/ferramentas/transcrever.sh -p "nomes próprios" pasta/v1 pasta/v2 ...`
   (um disparo só no robô, large-v3, tempo por palavra).
3. **Ler a transcrição procurando:** frase repetida ou recomeçada (corte com `remover`), número errado (não dá para
   consertar o áudio: avise o Heitor e corrija na legenda e no cartão), palavrão, gancho improvisado (os cartões seguem
   a fala, não o roteiro). Palavra com "?" baixo: confira na energia do áudio antes de cortar. Duplicata na virada de
   dois trechos da transcrição costuma ser alucinação, não repetição: confira no áudio.
4. **config.json** por vídeo (roteiro de `diario/.../roteiros/*.json`, cartões com fonte, `corrigir` para erros da
   transcrição, `bordao` só se ele falou o bordão padrão) → `python editar_reel.py pasta/vN` (Remotion, ~6 min cada
   com 2 núcleos: rode em fila, em segundo plano).
5. **Conferência:** `transcrever.sh -e pasta/v1 ...` (transcreve o editado) e uma folha de quadros. Nada pode sumir.
6. **Entrega:** vídeo + legenda do roteiro (sem #cambio) + capa (`ferramentas/capa.sh quadro.jpg "texto *destaque*"`).
   Notícia do dia: avisar que posta no mesmo dia. O Heitor posta pelo app (a API entregou menos, teste de 11/11).
7. Guardar `config.json` e `transcricao.json` em `edicao/AAAA-MM-DD-vN/`.

## Lições (retrospectiva de 12/11)
- Nunca gravar arquivo novo com nome de um que já existe sem conferir (o `publicar.py` da newsletter foi
  sobrescrito por engano e quebrou os testes do Plantão por 2 h). Antes de criar: `ls` e `git log` do caminho.
- Pedidos ao Plantão: um de cada vez (`ferramentas/pedir_roteiros.sh`); dois juntos, a fila cancela um.
- Mudou o fluxo de um robô? O disparo que já estava na fila roda a versão antiga: confira o próximo, não aquele.
- A Remotion daqui usa o Chromium do Playwright (a rede bloqueia o download dela); no robô do GitHub ela baixa sozinha.
