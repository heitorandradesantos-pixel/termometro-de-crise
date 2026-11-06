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
| Correspondente | A cada dia útil, pesquisa cada uma das 6 regiões e explica por que cada país está no nível em que está, ligando cada notícia ao sinal que ela mexe (bolsa, sobe e desce, moeda, energia, juros, comércio) | `termometro/correspondente.py` |
| Panorama | Monta o texto do fim de tarde para o canal do WhatsApp com os números do motor e as manchetes conferidas | `termometro/panorama.py` |
| Revisor | Bloqueia recomendação, promessa, número errado e link que não veio do Buscador | `termometro/revisor.py` |
| SEO | Antes do Redator, define a palavra-chave principal, as secundárias, as perguntas a responder, o título e a descrição para o Google | `termometro/seo.py` |
| Analista de marketing, Analista de comportamento do lead, Vendedor especialista, Guardião de regras | Formam, com o SEO e o UX, o conselho de monetização, que debate em rodadas e fecha um plano | `termometro/conselho.py` |
| Agente de UI | Toda semana olha os prints do site (celular e computador) e avalia hierarquia, tipografia, cor e contraste, gráficos e consistência | `termometro/design.py` |
| Agente de UX | Toda semana avalia se um leigo entende, confia e age: heurísticas de Nielsen, WCAG 2.2 AA, celular e conversão | `termometro/design.py` |
| Editor do site | Monta o site estático (início, regiões, países, ranking, panorama, edições, metodologia); o Cloudflare Pages publica | `termometro/site.py`, `termometro/paginas.py` |
| Publicador | Manda a edição aprovada ao beehiiv, uma vez só | `termometro/publicar.py` |

Quem chama todos, na ordem certa, é o `rodar.py`. Quem aperta o botão toda semana é o GitHub Actions.

## A semana do robô

1. **Domingo, 07:17 (Brasília):** o GitHub liga o robô (`.github/workflows/semanal.yml`).
2. O Coletor baixa os dados e os **testes** rodam. Se o método quebrar (por exemplo, 2008 deixar de
   aparecer como Crise), o robô para antes de gastar com IA.
3. Analista → Buscador → Redator → Copy → Arte → Revisor.
4. O robô abre um **Pull Request** "Edição de AAAA-MM-DD: aprovar?" com o resumo, o veredito do Revisor
   e todos os arquivos. Você recebe o aviso no app do GitHub.
5. Você toca em **Merge**. O Cloudflare Pages reconstrói o site (termometrodecrise.com) e a newsletter
   vai para o beehiiv sozinha (`.github/workflows/publicar.yml`).

## O site

- **Início:** termômetro do mundo (média das 6 regiões) com comparação com o mês passado e um ano atrás, **mapa-múndi
  clicável** (cada região na cor do nível; os 19 países medidos levam à própria página), lista das regiões, notícias
  que mexem com o termômetro, Brasil em destaque com "o que isso muda no seu bolso" e o índice dos mercados globais.
- **Faixa de mercados** no topo de todas as páginas (Ibovespa, dólar, euro, S&P 500, DAX, Nikkei…), com o último
  fechamento, atualizada pelo robô diário.
- Páginas de região, país, ranking, panorama, edições, metodologia, **política de privacidade** e **termos de uso**
  (links no rodapé). Variáveis: `CONTATO_EMAIL` (padrão contato@termometrodecrise.com) e `RESPONSAVEL`
  (nome ou razão social e CNPJ do responsável).
- Mapa: Natural Earth via world-atlas (ISC), nomes de i18n-iso-countries (MIT), gerado uma vez em `termometro/mapa_mundo.json`.

## Arquivo (decidido em consulta ao time, issue #13)

- **Panorama:** cada dia útil tem página própria (`/panorama/AAAA-MM-DD.html`) com texto próprio do dia, comparação
  (panorama anterior, 1 semana, mês passado, 1 ano), o texto do WhatsApp, "Leia também" (até 3 notícias) e dia
  anterior/próximo. O hub `/panorama/` vira calendário a partir de 10 dias; antes disso, lista.
- **Notícias:** `/noticias/` (mundo) e uma página por região e país com as notícias do mês em curso, 20 por página.
  Meses fechados com 5 ou mais notícias viram arquivo mensal estável, com resumo próprio (mundo e Brasil no começo).
- **Edições:** as 12 mais recentes em `/edicoes/` e o índice por ano (`/edicoes/AAAA.html`), com anterior/próxima.
- Toda página arquivada traz a faixa "Não reflete o mercado de hoje" e não mostra a faixa de cotações.
- Mapa do site enxuto: entram panoramas, edições, páginas de país e região, notícias do mundo e do Brasil e os
  arquivos mensais; páginas 2 em diante ficam fora (com link real e endereço próprio, sem noindex).
- Página de correções no rodapé (`correcoes.html`, lista em `termometro/legal.py`).

## Hospedagem

O site é servido pelo **Cloudflare Pages** (projeto `termometro-de-crise`), ligado a este repositório:
a cada mudança no ramo principal ele roda `pip install -q pandas matplotlib markdown requests && python rodar.py --site`
e publica a pasta `_site`. Variáveis no Cloudflare: `PYTHON_VERSION=3.12` e `SITE_URL=https://termometrodecrise.com`.
Cada Pull Request de edição ganha também um link de prévia do Cloudflare, para conferir antes de aprovar.

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

## O dia útil do robô

1. **Segunda a sexta, 18:17 (Brasília):** o GitHub liga `.github/workflows/diario.yml`, depois do fechamento de Nova York.
2. O motor mundial baixa bolsa e moeda dos 19 países e recalcula os termômetros (mês em andamento).
3. O **Correspondente** pesquisa cada região (até `BUSCAS_POR_REGIAO` buscas, padrão 3) e explica cada país.
   O programa confere tudo: só ficam links que a busca devolveu de verdade, datas dos últimos 10 dias, países da
   região e textos sem recomendação, promessa ou alarmismo. O que não passa é descartado e a página do país usa
   a explicação automática feita só com os números.
4. O **Panorama** monta o texto do WhatsApp (`diario/AAAA-MM-DD/panorama.txt`) e confere que os números batem.
5. Se a conferência aprovar, o robô publica sozinho no site. Se segurar (por exemplo, muitos países sem dado),
   abre um Pull Request "Panorama de AAAA-MM-DD: aprovar?". Com a variável `DIARIO_AUTOMATICO=nao`, sempre pede.
6. O texto do dia fica em termometrodecrise.com/panorama.html, com os botões **Copiar texto** e
   **Enviar pelo WhatsApp**, e também no resumo da execução, na aba *Actions*.

O WhatsApp não tem um jeito oficial de um programa postar sozinho em Canal ou Comunidade: a API de grupos
da Meta só aceita grupos de até 8 pessoas, e automações não oficiais levam a banimento do número. Por isso o
texto fica pronto e alguém do time cola no canal (leva 10 segundos). Com a variável `WHATSAPP_URL` (link do
canal), o site passa a mostrar o botão **Entrar no canal**.

## A squad de design (toda segunda)

`.github/workflows/design.yml` abre o site num navegador de verdade, no celular e no computador, e:

1. **Auditoria automática:** rolagem horizontal, alvos de toque (mínimo 24×24px), fonte mínima, contraste WCAG AA,
   títulos, textos alternativos, foco visível, link para pular ao conteúdo, links quebrados e o **axe-core**,
   o motor de acessibilidade mais usado do mundo.
2. **Agentes de UI e UX:** recebem os prints e os números e avaliam com os manuais de especialista.
3. **Relatório:** abre uma issue "Squad de design: relatório de AAAA-MM-DD", com notas, o que está bom,
   problemas por gravidade (escala de Nielsen) e o plano da semana. Os prints ficam nos arquivos da execução.

A squad não muda o site sozinha: as correções entram por Pull Request, com a sua aprovação.

## O conselho de monetização (dia 1 de cada mês)

`.github/workflows/conselho.yml` reúne o analista de marketing, o analista de comportamento do lead, o vendedor
especialista em produtos financeiros, o especialista em SEO, o agente de UX e o guardião de regras:

1. **Propostas:** cada um pesquisa o mercado e propõe ideias com receita estimada, custo, prazo, métrica e riscos.
2. **Debate:** cada um lê as propostas de todos, concorda, discorda e vota; o guardião de regras libera, libera com
   cuidados ou veta (CVM, CONAR, CDC, LGPD).
3. **Decisão:** o presidente do conselho monta o mapa de divergências e o plano por fases, com as mudanças no site.

A ata vira uma issue "Conselho de monetização: ata de AAAA-MM-DD". É uma recomendação para você decidir.

## Manuais de especialista

Cada agente de IA recebe um manual em `termometro/manuais/`, escrito a partir das melhores referências públicas,
sempre com a fonte e a licença no fim:

| Manual | Agentes | Referências principais |
|---|---|---|
| `pesquisa.md` | Buscador, Correspondente | Padrões de agentes de pesquisa da Anthropic (claude-cookbooks), verificação de fontes |
| `redacao.md` | Redator, Copy, Correspondente | 18F Content Guide (domínio público), GOV.UK, skill frontend-design da Anthropic |
| `ui.md` | Agente de UI | Skill frontend-design (Anthropic), Visual Vocabulary do Financial Times, WCAG 2.2, A11Y Project |
| `seo.md` | SEO | marketingskills (seo-audit, programmatic-seo, ai-seo, schema), knowledge-work-plugins, diretrizes do Google |
| `marketing.md` | Analista de marketing | marketingskills (Corey Haines, MIT), knowledge-work-plugins (Anthropic) |
| `comportamento.md` | Analista de comportamento do lead | marketingskills (marketing-psychology), modelos de Fogg e de hábito, LGPD |
| `vendas.md` | Vendedor especialista | marketingskills (offers, pricing), knowledge-work-plugins (sales), CDC |
| `compliance.md` | Guardião de regras | Resoluções CVM 19, 20 e 178, ANBIMA, guia do CONAR (2026), CDC, LGPD |
| `ux.md` | Agente de UX | Heurísticas de Nielsen, WCAG 2.2 AA, A11Y Project, GOV.UK, 18F |

O Revisor também ganhou dois avisos de linguagem simples (não bloqueiam): frases com mais de 35 palavras e
jargão sem tradução (spread, yield, hawkish…).

## Custos

- GitHub Actions e Pages: grátis em repositório público.
- Claude API: cobrança por uso. Por edição são 3 chamadas e até 12 buscas na web
  (`BUSCAS_MAXIMAS`). Por dia útil, o Correspondente faz 6 chamadas (uma por região) com até 3 buscas
  cada (`BUSCAS_POR_REGIAO`). Acompanhe o gasto no console da Anthropic e defina um limite mensal lá.
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

## Termômetro Mundial (motor por região)

`termometro/mundo.py` calcula um termômetro para 19 países e 6 regiões (América do Norte, América Latina,
Europa, Oriente Médio, África, Ásia e Pacífico) e um para o Brasil. Para cada país: queda da bolsa desde a
máxima de 12 meses, volatilidade realizada da bolsa no mês e variação da moeda contra o dólar em 3 meses,
cada um comparado com a história do próprio país. Teste histórico: aba *Actions* → *Teste do motor mundial*.

Cada região e cada país têm uma página (`regioes/…html`, `paises/…html`) que responde: quanto está, por quê
(os sinais em palavras simples, o contexto do Correspondente e as notícias com fonte) e se já foi pior (histórico
com os picos e o nome da época). O ranking dos países fica em `mundo.html`.

## Fontes de dados e licenças

- **FRED** (Fed de St. Louis): câmbio e juros. Algumas séries têm direitos de terceiros; confira a nota de
  cada série antes de uso comercial.
- **Yahoo Finance**: bolsas e moedas de emergentes. Os termos do Yahoo restringem uso comercial dos dados.
  Serve para o protótipo; antes de monetizar em escala, troque por um provedor com licença comercial
  (por exemplo, planos pagos de dados de mercado) ou pelas fontes oficiais de cada bolsa e banco central.
- **datahub.io**: históricos de VIX, Brent, juros, S&P 500 e ouro.

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
