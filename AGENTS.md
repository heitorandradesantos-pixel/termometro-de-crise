# Termômetro de Crise: índice para agentes

Leia isto antes de abrir arquivos. Detalhes ficam nos arquivos apontados; não releia o repositório inteiro.
Dono: Heitor (não programa, fala português informal). Responda sempre em português, curto e direto.

## O que é
Portal termometrodecrise.com (índice de estresse dos mercados, notícias com fonte) + Reels do @termometrodecrise +
funil de venda do e-book "Manual do Investidor". Contexto completo: `termometro/manuais/contexto_do_projeto.md`.

## Onde fica cada coisa
| Assunto | Arquivo |
|---|---|
| Site estático (build) | `rodar.py`, `termometro/site.py`, `termometro/paginas.py`; publica na Cloudflare Pages a cada push em `main` |
| APIs do site (Cloudflare Functions) | `functions/api/*.js` |
| Funil de venda: quiz `/quiz/` e página `/manual/` (sem menu, sem fuga) | `termometro/lp.py`, imagens em `lp/manual/` |
| Pixel do Meta e eventos | `termometro/lp.py` (`PIXEL_JS`, `tc_evento`); regras em `termometro/manuais/trackeamento.md` |
| Política de privacidade e termos | `termometro/legal.py` |
| Plantão (notícia do dia) | `termometro/plantao.py`, dados em `diario/plantao/` |
| Roteiros de Reel | `termometro/roteirista.py` → `estrategista.py` (marca) → `viral.py` (nota mínima 8); saída em `diario/AAAA-MM-DD/roteiros/` |
| Envio ao WhatsApp do Heitor | `termometro/whatsapp.py`, workflow `whatsapp.yml` (acao=roteiros, data, aviso; mensagens separadas por `---`) |
| Referências do Instagram | `termometro/referencias.py` (`PERFIS`), workflows `referencias.yml` e `ler-post.yml` |
| Edição de Reel (vídeo do Heitor) | `edicao/editar_reel.py` + `edicao/remotion/src/*`; guia `edicao/README.md` |
| Vídeos só de motion e anúncios | `edicao/remotion/src/Motion*.tsx`, `MotionAnuncios.tsx`; composições em `Root.tsx` |
| Transcrição (Whisper + alinhamento) | `edicao/ferramentas/transcrever.sh` → workflow `transcrever.yml` → `termometro/transcrever.py` |
| Manuais dos especialistas | `termometro/manuais/*.md` (marca, voz do Heitor, viralização, roteiro, compliance, trackeamento, vendas, SEO, UX/UI) |

## Comandos
- Testes: `python3 -m pytest -q`
- Editar Reel: `python3 edicao/editar_reel.py pasta/vN` (um por vez; dois juntos estouram memória)
- Transcrever: `edicao/ferramentas/transcrever.sh -m large-v3 pasta1 [pasta2 ...]`; conferir o editado com `-e`
- Disparar workflow: `gh api -X POST repos/heitorandradesantos-pixel/termometro-de-crise/actions/workflows/X.yml/dispatches -f ref=main -f "inputs[k]=v"` (`gh workflow run` não funciona aqui)
- Render Remotion: `npx remotion render <Id> out.mp4 --public-dir=<pub> --browser-executable=<chrome-headless-shell>`

## Regras que não se quebram
- Repositório PÚBLICO: nenhum segredo, token ou senha em código, log ou commit. Áudio/vídeo só sobe cifrado em ramo temporário.
- Nunca pedir nem digitar senha, token ou código; o Heitor coloca segredos nos painéis (GitHub, Cloudflare, Kiwify, Meta).
- Conteúdo educativo: sem recomendação de investimento (CVM), sem promessa de ganho, sem lado político, sempre com fonte.
- Sem escassez ou contagem regressiva falsa (CDC). Nunca citar banco ou corretora como vilão pelo nome.
- Hashtags proibidas: `#cambio`, `#cvm`. Nada de bingo neste projeto.
- No máximo 6 roteiros por dia no WhatsApp: a pauta das 6h17 manda 5 (2 polêmicos + 3 informativos, mesclando bolso e mercado financeiro) e a 6ª vaga fica para a notícia quente da tarde (Plantão). O balanço da bolsa (fechamento, 18h17) é fixo e fica fora do limite. Só passa do limite algo bombástico, com `"urgente": true`. Referências: manhã, tarde e noite.
- Commit só de conteúdo/ferramenta que não muda o site: adicionar `[CF-Pages-Skip]` na mensagem.
- Vídeo que veio do app Fotos (`copy_*.mov`): transcrever cada arquivo do jeito que veio; conferir a sincronia com `-e`.

## Economia de contexto
- Comece por este índice e abra só o arquivo da tarefa. Use `grep -n` / `sed -n` em vez de ler arquivos grandes inteiros.
- Filtre saída de comando (`| tail`, `| grep`) e de logs do GitHub (`gh run view --log | grep ...`).
- Resposta ao Heitor: curta, em linguagem simples, sem jargão técnico.
