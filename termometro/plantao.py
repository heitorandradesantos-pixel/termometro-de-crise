"""Plantão: notícia de dinheiro que está bombando, publicada rápido e com fonte, para ranquear no Google.

Quando um assunto viraliza (o FGC teve dados acessados, um banco travou saques de cripto, um golpe novo
no Pix), as pessoas correm para o Google e digitam "FGC foi hackeado?". Quem tiver no ar primeiro um texto
claro, com fonte, "o que se sabe", "o que muda para você" e "como se proteger", fica no topo.

Três passos, 3 vezes por dia, com no máximo 3 artigos por dia (robô Plantão, .github/workflows/plantao.yml):
1. Pauteiro: busca na web os assuntos de dinheiro do momento no Brasil e escolhe o que mais importa
   para o bolso do leitor, com a busca exata que as pessoas fazem (palavra-chave de SEO).
2. Repórter: busca as fontes e escreve no formato "X: o que se sabe", que é o que o Google mostra em notícia.
3. Conferência (programa, não IA): só fica fato com link que a própria busca devolveu, com data recente;
   boato vai para "o que ainda não se sabe"; nada de recomendação, promessa ou alarmismo. Se não passar,
   não publica.

O artigo publicado fica em diario/plantao/AAAA-MM-DD-slug.json e vira a página noticias/plantao/slug.html.
"""

import html
import json
import os
import re
from pathlib import Path

import pandas as pd

from . import config, ia
from .correspondente import _limpo, confiavel, datas_br, dominio
from .mundo import slug as fazer_slug
from .revisor import linguagem_proibida

BUSCAS_PAUTA = 4
BUSCAS_ARTIGO = 4
JANELA_DIAS = 3          # fato com data mais antiga que isso não sustenta "notícia"
MINIMO_FATOS = 3         # menos que isso, não há o que publicar
REPETIDO_DIAS = 3        # o mesmo assunto não vira dois artigos em 3 dias
MAXIMO_POR_RODADA = int(os.environ.get("PLANTAO_MAXIMO") or "1")
MAXIMO_POR_DIA = int(os.environ.get("PLANTAO_POR_DIA") or "3")  # no começo, no máximo 3 artigos por dia

TEMAS = ("bancos e fintechs (Nubank, Itaú, Inter, Mercado Pago, PicPay), Pix e boletos, FGC e garantias, golpes e "
         "vazamentos de dados, criptomoedas e corretoras, Selic, inflação, dólar, imposto de renda e Receita Federal, "
         "INSS e benefícios, combustíveis e energia, Bolsa e grandes empresas, crédito e endividamento, regras novas "
         "do Banco Central e da CVM")

PAUTEIRO = f"""Você é o pauteiro do Plantão do Termômetro de Crise, um portal financeiro brasileiro para leigos.
Sua missão: achar, nas últimas 24 horas, o assunto de dinheiro que mais gente no Brasil está procurando no Google
agora e que mexe com o bolso do leitor comum. Temas típicos: {TEMAS}.

Regras:
1. Use a busca na web. Prefira assuntos com fonte oficial (nota da empresa, do Banco Central, do FGC, da CVM, de
   ministério) ou de veículo de primeira linha. Assunto só de rede social, sem nenhum veículo, fica de fora.
2. Para cada assunto, escreva a busca exata que um leigo faria no Google ("fgc foi hackeado", "nubank cripto fora
   do ar", "golpe do pix novo"), em minúsculas, como as pessoas digitam.
3. Nada de assunto já coberto (a lista vem no pedido) nem de opinião sobre investimento ou sobre política.
4. Ordene do mais urgente para o menos urgente. Até 3 assuntos.""" + config.manual("pesquisa", "seo")

REPORTER = f"""Você é o repórter do Plantão do Termômetro de Crise, um portal financeiro brasileiro para leigos.
Escreva a notícia no formato "o que se sabe", que é o que o Google mostra quando o assunto está quente.

Regras de apuração:
1. Faça pelo menos 3 buscas antes de escrever: uma pela nota ou página oficial (empresa, órgão, Banco Central,
   FGC, CVM), outra por veículos de primeira linha e outra pelo desdobramento mais recente. Cada fato precisa de um link que a busca devolveu, de veículo confiável ou da
   fonte oficial. Sem link, não é fato.
2. Separe com rigor: o que foi confirmado (com fonte) vai em "o que se sabe"; boato, suspeita, versão não confirmada
   e o que ninguém explicou ainda vão em "o que ainda não se sabe", sempre dizendo que não foi confirmado.
3. Nunca acuse empresa ou pessoa de algo que não foi confirmado por fonte oficial ou por mais de um veículo.
4. "O que muda para você" explica na prática, para quem tem conta, investimento ou benefício, sem dizer o que
   comprar, vender ou onde investir. "Como se proteger" só entra quando houver risco de golpe ou fraude.
5. Datas reais dos acontecimentos (AAAA-MM-DD no campo de data; no texto, "5/11" ou "5 de novembro").
6. Assunto com política (eleição, governo, partido): nenhuma opinião sobre candidato, partido ou governo. Diga o
   que o mercado fez, com números e fonte, e atribua cada explicação a quem a deu ("segundo analistas ouvidos pela
   Reuters", "o Ministério da Fazenda diz"). Se houver leituras diferentes, traga as duas.

Regras de texto: português do Brasil, frases curtas, sem jargão (ou traduzido na mesma frase), sem alarmismo, sem
caça-clique. O título tem a busca que o leitor faz e termina, quando couber, em ": o que se sabe". Até 70 caracteres.
""" + config.manual("redacao", "seo")


def ferramenta_pauta() -> dict:
    return {"name": "registrar_pauta_plantao", "description": "Os assuntos quentes, do mais urgente ao menos urgente.",
            "input_schema": {"type": "object", "required": ["assuntos"], "properties": {"assuntos": {
                "type": "array", "maxItems": 3, "items": {"type": "object",
                "required": ["assunto", "busca_do_leitor", "por_que_importa", "fontes"], "properties": {
                    "assunto": {"type": "string", "description": "O fato, em uma frase."},
                    "busca_do_leitor": {"type": "string", "description": "O que o leigo digita no Google, minúsculas."},
                    "por_que_importa": {"type": "string"},
                    "fontes": {"type": "array", "items": {"type": "object", "required": ["url"],
                               "properties": {"url": {"type": "string"}, "veiculo": {"type": "string"}}}}}}}}}}


def ferramenta_artigo() -> dict:
    fato = {"type": "object", "required": ["texto", "fonte_url", "data"], "properties": {
        "texto": {"type": "string"}, "fonte_url": {"type": "string"}, "veiculo": {"type": "string"},
        "data": {"type": "string", "description": "AAAA-MM-DD do acontecimento"}}}
    return {"name": "registrar_artigo_plantao", "description": "A notícia pronta, com cada fato ligado à fonte.",
            "input_schema": {"type": "object", "required": [
                "titulo", "descricao", "palavra_chave", "lead", "o_que_se_sabe", "o_que_nao_se_sabe",
                "o_que_muda_para_voce"], "properties": {
                "titulo": {"type": "string", "description": "Até 70 caracteres, com a palavra-chave."},
                "descricao": {"type": "string", "description": "Resumo para o Google, até 155 caracteres."},
                "palavra_chave": {"type": "string"},
                "lead": {"type": "string", "description": "2 ou 3 frases: o que aconteceu, quem confirmou, quando."},
                "o_que_se_sabe": {"type": "array", "minItems": 3, "maxItems": 8, "items": fato},
                "o_que_nao_se_sabe": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
                "o_que_muda_para_voce": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string"}},
                "como_se_proteger": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
                "linha_do_tempo": {"type": "array", "maxItems": 6, "items": fato}}}}


# ---------------------------------------------------------------- arquivo do plantão

def pasta(diario: Path) -> Path:
    return diario / "plantao"


def publicados(diario: Path) -> list[dict]:
    p = pasta(diario)
    return sorted((json.loads(a.read_text()) for a in p.glob("20??-??-??-*.json")) if p.exists() else [],
                  key=lambda a: a["publicado_em"], reverse=True)


def _palavras(texto: str) -> set[str]:
    return {w for w in re.findall(r"\w{4,}", texto.lower())}


def repetido(assunto: str, anteriores: list[dict], agora: pd.Timestamp) -> bool:
    """O assunto já virou artigo nos últimos dias? (palavras em comum no título e na palavra-chave)"""
    novas = _palavras(assunto)
    for a in anteriores:
        if agora - pd.Timestamp(a["publicado_em"]) > pd.Timedelta(days=REPETIDO_DIAS):
            continue
        velhas = _palavras(a["titulo"] + " " + a["palavra_chave"])
        if novas and len(novas & velhas) / len(novas) >= 0.5:
            return True
    return False


# ---------------------------------------------------------------- conferência (programa, não IA)

def conferir(bruto: dict, buscados: set | None, hoje: str) -> dict:
    """Devolve {"aprovado", "artigo", "problemas"}. Fato sem link devolvido pela busca, ou velho demais, sai."""
    problemas, dia = [], pd.Timestamp(hoje)
    permitidos = None if buscados is None else {_limpo(u) for u in buscados}

    def fato_ok(f: dict) -> dict | None:
        url = str(f.get("fonte_url", ""))
        quando = pd.to_datetime(f.get("data"), errors="coerce")
        if not url.startswith("https://"):
            problemas.append(f"fato sem link: {f.get('texto', '')[:60]}")
        elif permitidos is not None and _limpo(url) not in permitidos:
            problemas.append(f"link que a busca não devolveu: {url}")
        elif pd.isna(quando) or quando > dia + pd.Timedelta(days=1):
            problemas.append(f"data inválida: {f.get('data')}")
        else:
            return {"texto": datas_br(str(f["texto"]).strip()), "fonte_url": url, "data": quando.strftime("%Y-%m-%d"),
                    "veiculo": f.get("veiculo") or dominio(url), "confiavel": confiavel(url)}
        return None

    fatos = [x for x in (fato_ok(f) for f in bruto.get("o_que_se_sabe", [])) if x]
    tempo = [x for x in (fato_ok(f) for f in bruto.get("linha_do_tempo", [])) if x]
    recentes = [f for f in fatos if pd.Timestamp(f["data"]) >= dia - pd.Timedelta(days=JANELA_DIAS)]
    artigo = {
        "titulo": datas_br(str(bruto.get("titulo", "")).strip())[:90],
        "descricao": datas_br(str(bruto.get("descricao", "")).strip())[:160],
        "palavra_chave": str(bruto.get("palavra_chave", "")).strip().lower(),
        "lead": datas_br(str(bruto.get("lead", "")).strip()),
        "o_que_se_sabe": fatos, "linha_do_tempo": sorted(tempo, key=lambda f: f["data"]),
        "o_que_nao_se_sabe": [datas_br(str(x).strip()) for x in bruto.get("o_que_nao_se_sabe", []) if str(x).strip()],
        "o_que_muda_para_voce": [datas_br(str(x).strip()) for x in bruto.get("o_que_muda_para_voce", []) if str(x).strip()],
        "como_se_proteger": [datas_br(str(x).strip()) for x in bruto.get("como_se_proteger", []) if str(x).strip()],
    }
    if len(fatos) < MINIMO_FATOS:
        problemas.append(f"só {len(fatos)} fatos com fonte conferida (mínimo {MINIMO_FATOS})")
    if not recentes:
        problemas.append(f"nenhum fato dos últimos {JANELA_DIAS} dias: não é notícia")
    if not any(f["confiavel"] for f in fatos):
        problemas.append("nenhuma fonte de primeira linha ou oficial")
    if not artigo["titulo"] or len(artigo["titulo"]) > 90:
        problemas.append("título vazio ou longo demais")
    texto_todo = " ".join([artigo["titulo"], artigo["descricao"], artigo["lead"]] + [f["texto"] for f in fatos + tempo]
                          + artigo["o_que_nao_se_sabe"] + artigo["o_que_muda_para_voce"] + artigo["como_se_proteger"])
    proibido = linguagem_proibida(texto_todo)
    if proibido:
        problemas.append("linguagem: " + ", ".join(proibido))
    graves = [p for p in problemas if not p.startswith(("link que a busca", "fato sem link", "data inválida"))]
    return {"aprovado": not graves, "artigo": artigo, "problemas": problemas}


# ---------------------------------------------------------------- agentes

def pautar(cliente, hoje: str, anteriores: list[dict]) -> list[dict]:
    cobertos = "; ".join(a["titulo"] for a in anteriores[:15]) or "nenhum"
    pedido = (f"Hoje é {hoje}. Quais são os assuntos de dinheiro mais procurados no Brasil agora?\n"
              f"Já cobertos (não repetir): {cobertos}")
    bruto = ia.estruturado(cliente, PAUTEIRO, pedido, ferramenta_pauta(), buscas=BUSCAS_PAUTA, max_tokens=4000)
    return [a for a in bruto.get("assuntos", []) if a.get("assunto") and a.get("busca_do_leitor")]


def escrever(cliente, assunto: dict, hoje: str) -> dict:
    buscados: set = set()
    fontes = "\n".join(f"- {f.get('veiculo', '')} {f.get('url', '')}" for f in assunto.get("fontes", []))
    pedido = (f"Hoje é {hoje}. Assunto: {assunto['assunto']}\nBusca que o leitor faz: {assunto['busca_do_leitor']}\n"
              f"Por que importa: {assunto.get('por_que_importa', '')}\nPistas de fonte (confira tudo de novo na busca):\n"
              f"{fontes or '- nenhuma'}")
    bruto = ia.estruturado(cliente, REPORTER, pedido, ferramenta_artigo(), buscas=BUSCAS_ARTIGO, max_tokens=8000,
                           links=buscados)
    return conferir(bruto, buscados, hoje)


def rodar(diario: Path, agora: pd.Timestamp | None = None, cliente=None, tema: str = "") -> list[Path]:
    """Uma rodada do Plantão. Devolve os artigos gravados (nenhum, se nada passou na conferência)."""
    agora = agora or pd.Timestamp.now(tz="America/Sao_Paulo").tz_localize(None)
    hoje = agora.strftime("%Y-%m-%d")
    if cliente is None and not ia.disponivel():
        print("Plantão: sem chave de IA, nada a fazer.")
        return []
    anteriores = publicados(diario)
    do_dia = sum(1 for a in anteriores if a["publicado_em"][:10] == hoje)
    if do_dia >= MAXIMO_POR_DIA:
        print(f"Plantão: já saíram {do_dia} artigos hoje (máximo {MAXIMO_POR_DIA}); nada a fazer.")
        return []
    cliente = cliente or ia.novo_cliente()
    assuntos = ([{"assunto": tema, "busca_do_leitor": tema.lower(), "por_que_importa": "pedido do editor", "fontes": []}]
                if tema else pautar(cliente, hoje, anteriores))
    gravados = []
    for assunto in assuntos:
        if len(gravados) >= MAXIMO_POR_RODADA or do_dia + len(gravados) >= MAXIMO_POR_DIA:
            break
        if not tema and repetido(assunto["assunto"] + " " + assunto["busca_do_leitor"], anteriores, agora):
            print(f"  já coberto: {assunto['assunto']}")
            continue
        print(f"  Plantão: {assunto['assunto']}")
        try:
            r = escrever(cliente, assunto, hoje)
        except Exception as erro:  # noqa: BLE001 — um assunto com problema não derruba a rodada
            print(f"  falhou: {erro}")
            continue
        for p in r["problemas"]:
            print(f"    · {p}")
        if not r["aprovado"]:
            print("    não passou na conferência; não publica")
            continue
        a = r["artigo"]
        a.update({"slug": fazer_slug(a["palavra_chave"] or a["titulo"])[:70].strip("-"), "publicado_em": agora.isoformat(),
                  "atualizado_em": agora.isoformat(), "assunto": assunto["assunto"]})
        if any(x["slug"] == a["slug"] for x in anteriores):
            a["slug"] = f"{a['slug']}-{agora:%d%m}"
        destino = pasta(diario) / f"{hoje}-{a['slug']}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(a, ensure_ascii=False, indent=1))
        anteriores.insert(0, a)
        gravados.append(destino)
        print(f"    publicado: {a['titulo']}")
    return gravados


# ---------------------------------------------------------------- páginas

CSS = """
.plantao-art{max-width:720px}.plantao-art .meta{font-size:14px;color:var(--suave)}.plantao-art .lead{font-size:19px;
line-height:1.55}.plantao-art li{margin:8px 0;line-height:1.55}.plantao-art .fonte{font-size:13px;white-space:nowrap}
.plantao-art .fonte a{display:inline-block;padding:4px 0}.selo-plantao{display:inline-block;font-size:12px;font-weight:700;
letter-spacing:.06em;color:#0B1220;background:#F2C14E;border-radius:4px;padding:2px 8px;margin-bottom:8px}
.lista-plantao{list-style:none;padding:0;margin:0}.lista-plantao li{padding:14px 0;border-bottom:1px solid var(--linha)}
.lista-plantao a{font-weight:600;font-size:17px;display:inline-block;padding:2px 0}.lista-plantao small{display:block;
color:var(--suave);font-size:13px;margin-top:4px}
"""


def _quando(iso: str) -> str:
    t = pd.Timestamp(iso)
    return f"{t:%d/%m/%Y} às {t:%Hh%M}"


def _fonte(f: dict) -> str:
    return (f' <span class="fonte">(<a href="{html.escape(f["fonte_url"])}" target="_blank" rel="noopener">'
            f'{html.escape(f["veiculo"])}<span class="sr"> (abre em nova aba)</span></a>)</span>')


def _secao(titulo: str, itens: list[str]) -> str:
    return f"<h2>{titulo}</h2><ul>" + "".join(f"<li>{x}</li>" for x in itens) + "</ul>"


def corpo_artigo(a: dict, raiz: str = "../../") -> str:
    from .site import bloco_celular
    secoes = [_secao("O que se sabe", [html.escape(f["texto"]) + _fonte(f) for f in a["o_que_se_sabe"]])]
    if a["o_que_nao_se_sabe"]:
        secoes.append(_secao("O que ainda não se sabe", [html.escape(x) for x in a["o_que_nao_se_sabe"]]))
    secoes.append(_secao("O que muda para você", [html.escape(x) for x in a["o_que_muda_para_voce"]]))
    if a["como_se_proteger"]:
        secoes.append(_secao("Como se proteger", [html.escape(x) for x in a["como_se_proteger"]]))
    if a["linha_do_tempo"]:
        secoes.append(_secao("Linha do tempo", [f"<strong>{pd.Timestamp(f['data']):%d/%m}</strong>: "
                                                 f"{html.escape(f['texto'])}{_fonte(f)}" for f in a["linha_do_tempo"]]))
    vistos, fontes = set(), []
    for f in a["o_que_se_sabe"] + a["linha_do_tempo"]:
        if f["fonte_url"] not in vistos:
            vistos.add(f["fonte_url"])
            fontes.append(f'<li><a href="{html.escape(f["fonte_url"])}" target="_blank" rel="noopener">'
                          f'{html.escape(f["veiculo"])}<span class="sr"> (abre em nova aba)</span></a></li>')
    atualizado = (f' · Atualizado em {_quando(a["atualizado_em"])}' if a["atualizado_em"] != a["publicado_em"] else "")
    return (f'<article class="edicao plantao-art"><p class="trilha"><a href="{raiz}index.html">Início</a> › '
            f'<a href="{raiz}noticias/plantao/index.html">Plantão</a></p><span class="selo-plantao">PLANTÃO</span>'
            f'<h1>{html.escape(a["titulo"])}</h1><p class="meta">Publicado em {_quando(a["publicado_em"])}{atualizado} · '
            f'Redação Termômetro de Crise, com IA e conferência automática de fontes</p>'
            f'<p class="lead">{html.escape(a["lead"])}</p>{"".join(secoes)}<h2>Fontes</h2><ul>{"".join(fontes)}</ul>'
            f'<p class="suave" style="font-size:14px">{config.AVISO} Viu um erro? Escreva para '
            f'<a href="mailto:{config.CONTATO_EMAIL}">{config.CONTATO_EMAIL}</a> '
            f'(<a href="{raiz}correcoes.html">política de correções</a>).</p>'
            f'<p><a href="{raiz}paises/brasil.html">Veja o termômetro do Brasil hoje</a> · '
            f'<a href="{raiz}panorama.html">Panorama do fim de tarde</a></p></article>{bloco_celular(raiz)}')


def json_ld(a: dict, url: str) -> str:
    dados = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": a["titulo"][:110],
             "description": a["descricao"], "datePublished": pd.Timestamp(a["publicado_em"]).tz_localize("America/Sao_Paulo").isoformat(),
             "dateModified": pd.Timestamp(a["atualizado_em"]).tz_localize("America/Sao_Paulo").isoformat(),
             "inLanguage": "pt-BR", "mainEntityOfPage": url, "keywords": a["palavra_chave"],
             "author": {"@type": "Organization", "name": f"Redação {config.NOME}"},
             "publisher": {"@type": "Organization", "name": config.NOME},
             "isBasedOn": [f["fonte_url"] for f in a["o_que_se_sabe"]]}
    return f'<script type="application/ld+json">{json.dumps(dados, ensure_ascii=False)}</script>'


def paginas(saida: Path, diario: Path) -> tuple[list[str], list[dict]]:
    """Gera noticias/plantao/<slug>.html e a lista noticias/plantao/index.html. Devolve (caminhos, artigos)."""
    from .site import pagina
    artigos = publicados(diario)
    destino = saida / "noticias" / "plantao"
    destino.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for a in artigos:
        caminho = f"noticias/plantao/{a['slug']}.html"
        url = f"{config.SITE_URL or 'https://termometrodecrise.com'}/{caminho}"
        (saida / caminho).write_text(pagina(f"{a['titulo']} | {config.NOME}", a["descricao"],
                                            corpo_artigo(a) + json_ld(a, url), raiz="../../", caminho=caminho,
                                            extra_css=CSS))
        caminhos.append(caminho)
    itens = "".join(f'<li><a href="{a["slug"]}.html">{html.escape(a["titulo"])}</a><small>{_quando(a["publicado_em"])}'
                    f' · {html.escape(a["descricao"])}</small></li>' for a in artigos) or \
        '<li>As primeiras notícias do Plantão aparecem aqui assim que forem publicadas.</li>'
    (destino / "index.html").write_text(pagina(
        f"Plantão: as notícias de dinheiro do momento | {config.NOME}",
        "O que se sabe sobre os assuntos de dinheiro mais procurados do dia, com fonte em cada fato.",
        f'<section class="edicao plantao-art"><p class="trilha"><a href="../../index.html">Início</a> › Plantão</p>'
        f'<h1>Plantão: o que se sabe</h1><p class="suave">Os assuntos de dinheiro mais procurados do dia, com a fonte de '
        f'cada fato e o que muda para você. Atualizado ao longo do dia.</p><ul class="lista-plantao">{itens}</ul>'
        f'</section>', raiz="../../", caminho="noticias/plantao/index.html", extra_css=CSS))
    return ["noticias/plantao/index.html"] + caminhos, artigos


def sitemap_noticias(artigos: list[dict], agora: pd.Timestamp | None = None) -> str:
    """Mapa de notícias do Google News: só os artigos das últimas 48 horas."""
    agora = agora or pd.Timestamp.now(tz="America/Sao_Paulo").tz_localize(None)
    base = config.SITE_URL or "https://termometrodecrise.com"
    urls = "".join(
        f'<url><loc>{base}/noticias/plantao/{a["slug"]}.html</loc><news:news><news:publication><news:name>'
        f'{html.escape(config.NOME)}</news:name><news:language>pt</news:language></news:publication>'
        f'<news:publication_date>{pd.Timestamp(a["publicado_em"]).tz_localize("America/Sao_Paulo").isoformat()}'
        f'</news:publication_date><news:title>{html.escape(a["titulo"])}</news:title></news:news></url>'
        for a in artigos if agora - pd.Timestamp(a["publicado_em"]) <= pd.Timedelta(hours=48))
    return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            f'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">{urls}</urlset>')
