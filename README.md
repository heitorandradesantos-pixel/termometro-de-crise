# Termômetro de Crise — o programa

Um robô que, toda semana, calcula o Termômetro de Crise com dados públicos, pesquisa as notícias
do mundo, escreve a newsletter, cria as peças de redes sociais, confere tudo e publica o site.
Você só aprova (um toque no celular) — ou liga o modo automático e nem isso.

## Os agentes

| Agente | O que faz | Arquivo |
|---|---|---|
| Coletor | Baixa VIX, petróleo Brent, juro de 10 anos dos EUA, S&P 500 e ouro | `termometro/coleta.py` |
| Analista | Calcula o índice de 0 a 100 e o nível (Calmaria → Crise) | `termometro/motor.py` |
| Arte | Gera o gráfico histórico (computador e celular) e o card 4:5 das redes | `termometro/grafico.py` |
| Buscador | Pesquisa a semana nas 6 frentes do mundo e monta um dossiê com fonte, data e status de cada fato | `termometro/buscador.py` |
| Redator | Escreve a edição só com os números do Analista e os fatos do dossiê | `termometro/redator.py` |
| Copy | Assuntos de e-mail, título e descrição do site, legendas de Instagram, X e LinkedIn, chamada do card | `termometro/copywriter.py` |
| Revisor | Bloqueia recomendação, promessa, número errado e link que não veio do Buscador | `termometro/revisor.py` |
| Editor do site | Monta o site estático (início, edições, metodologia) | `termometro/site.py` |
| Publicador | Manda a edição aprovada ao beehiiv, uma vez só | `termometro/publicar.py` |

Quem chama todos, na ordem certa, é o `rodar.py`. Quem aperta o botão toda semana é o GitHub Actions.

## A semana do robô

1. **Domingo, 07:17 (Brasília):** o GitHub liga o robô (`.github/workflows/semanal.yml`).
2. O Coletor baixa os dados e os **testes** rodam. Se o método quebrar (por exemplo, 2008 deixar de
   aparecer como Crise), o robô para antes de gastar com IA.
3. Analista → Buscador → Redator → Copy → Arte → Revisor.
4. O robô abre um **Pull Request** "Edição de AAAA-MM-DD: aprovar?" com o resumo, o veredito do Revisor
   e todos os arquivos. Você recebe o aviso no app do GitHub.
5. Você toca em **Merge**. O site atualiza e a newsletter vai para o beehiiv sozinhos
   (`.github/workflows/publicar.yml`).

**Modo automático:** com a variável `AUTOMATICO=sim`, toda edição que o Revisor aprovar é publicada
sem esperar você. As que ele segurar continuam virando Pull Request.

## Configuração (uma vez só)

Faça você mesmo os passos com chaves e senhas. Nunca cole uma chave em chat nenhum.

1. **GitHub:** crie uma conta e um repositório **público** chamado `termometro-de-crise`
   (público = site grátis no GitHub Pages; as chaves ficam protegidas em Secrets).
2. **Suba o código.** Caminho mais fácil: conecte o GitHub ao Claude (claude.ai → Configurações →
   Conectores) e peça para ele enviar. Pelo navegador também dá: *Add file → Upload files* e arraste o
   conteúdo da pasta. A pasta `.github` é oculta; no Mac, aperte Cmd+Shift+. no Finder para vê-la.
3. **Settings → Actions → General → Workflow permissions:** marque *Read and write permissions* e
   *Allow GitHub Actions to create and approve pull requests*.
4. **Settings → Pages → Build and deployment → Source:** *GitHub Actions*.
5. **Settings → Secrets and variables → Actions → Secrets** (aba *Secrets*):

   | Segredo | Para quê | Onde pegar |
   |---|---|---|
   | `ANTHROPIC_API_KEY` | Buscador, Redator e Copy | console.anthropic.com → API Keys |
   | `FRED_API_KEY` (opcional, grátis) | Dados diários e mais recentes | fred.stlouisfed.org → My Account → API Keys |
   | `BEEHIIV_API_KEY` (opcional) | Enviar a newsletter | beehiiv → Settings → API |
   | `BEEHIIV_PUBLICATION_ID` (opcional) | Idem | beehiiv → Settings → API |

6. **Mesma tela, aba *Variables*:**

   | Variável | Exemplo | Para quê |
   |---|---|---|
   | `SITE_URL` | `https://seunome.github.io/termometro-de-crise` | Links, imagens e SEO |
   | `NEWSLETTER_URL` | página de inscrição do beehiiv | Botão "Receber todo domingo" |
   | `BEEHIIV_ENVIO` | `rascunho` ou `enviar` | Comece com `rascunho` nas 2 primeiras semanas |
   | `AUTOMATICO` | `sim` | Publica sozinho o que o Revisor aprovar |
   | `DOMINIO` (opcional) | `termometrodecrise.com.br` | Domínio próprio no GitHub Pages |
   | `ADSENSE_CLIENT` (depois) | `ca-pub-...` | Só depois da aprovação no AdSense |
   | `MODELO_CLAUDE` (opcional) | `claude-sonnet-5-5` | Troca o modelo dos agentes |

7. **Primeiro teste:** aba *Actions* → *Edição semanal* → *Run workflow*. Em poucos minutos aparece o
   Pull Request.

## Custos

- GitHub Actions e Pages: grátis em repositório público.
- Claude API: cobrança por uso. Por edição são 3 chamadas e até 12 buscas na web
  (`BUSCAS_MAXIMAS`). Acompanhe o gasto no console da Anthropic e defina um limite mensal lá.
- FRED: grátis. beehiiv: a criação de posts pela API exige plano com esse recurso.

## O que o Revisor bloqueia

- Recomendação de compra, venda ou "invista em", preço-alvo, código de ação (PETR4, $AAPL).
- Promessa de lucro ou garantia, alarmismo ("colapso iminente").
- Número do Termômetro diferente do calculado.
- Link que não veio do dossiê do Buscador (anti-invenção de fonte).
- Edição sem aviso legal, com seção faltando, curta demais ou com menos de 3 fontes nos riscos.

Fonte fora da lista de primeira linha (`config.FONTES_CONFIAVEIS`) gera aviso, não bloqueio.

## Rodar no seu computador (opcional)

```bash
pip install -r requirements.txt
python rodar.py            # gera a edição em edicoes/AAAA-MM-DD/
python rodar.py --site     # monta o site em _site/
python -m pytest -q        # testes
```

Sem `ANTHROPIC_API_KEY`, o programa gera só a parte de dados e o Revisor segura a edição.

## Método e limites

- Cada componente vira o percentil do próprio histórico desde 1990; o índice é a média ponderada.
  Petróleo, juros e ouro contam choques nos dois sentidos. Detalhes em `termometro/motor.py` e na
  página Metodologia do site.
- Teste histórico (1999–2026): 2008 chegou a 96, Covid a 94, 2022 a 88; nenhum ano calmo entrou em Crise.
  Resultado passado não garante comportamento futuro.
- Leitura mensal. Sem `FRED_API_KEY`, os dados chegam com cerca de 1 mês de atraso.
- Ainda fora do índice: crédito, dólar global e conflitos (ACLED).
- Redes sociais: o programa entrega card e legendas prontos (`edicoes/.../redes.md`); postar sozinho
  exige conectar as contas de Meta, X e LinkedIn (próxima etapa).
- Conteúdo educativo. Antes de cobrar por recomendações ou compartilhar a base de inscritos,
  verifique as regras da CVM e da LGPD com um advogado.
