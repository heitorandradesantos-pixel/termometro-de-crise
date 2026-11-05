"""Agente editor do site: gera o site estático a partir das edições aprovadas.

Saída: pasta _site/ pronta para o GitHub Pages (ou qualquer hospedagem estática).
"""

import html
import json
import math
import shutil
from pathlib import Path

import markdown
import pandas as pd

from . import config
from .grafico import mes_curto

C = config.CORES
ARCOS = ["M70.0 295.7 A230 230 0 0 1 111.4 168.3", "M116.5 161.3 A230 230 0 0 1 224.8 82.6",
         "M233.1 80.0 A230 230 0 0 1 366.9 80.0", "M375.2 82.6 A230 230 0 0 1 483.5 161.3",
         "M488.6 168.3 A230 230 0 0 1 530.0 295.7"]

CSS = f"""
:root{{--fundo:{C['fundo']};--painel:{C['painel']};--linha:{C['linha']};--texto:{C['texto']};--suave:{C['suave']}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--fundo);color:var(--texto);font:16px/1.6 'IBM Plex Sans',system-ui,sans-serif}}
a{{color:#7CC3E0}}a:hover{{color:#A9DAEE}}
.topo,.conteudo,.rodape{{max-width:1080px;margin:0 auto;padding:0 20px}}
.topo{{display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;align-items:center;padding-top:20px;padding-bottom:20px;border-bottom:1px solid var(--linha)}}
.marca{{font:600 15px 'Space Grotesk',sans-serif;letter-spacing:.14em;color:var(--texto);text-decoration:none}}
.topo nav a{{margin-left:20px;color:var(--suave);text-decoration:none;font-size:14px}}
.topo nav a:hover{{color:var(--texto)}}
h1,h2,h3{{font-family:'Space Grotesk',sans-serif;font-weight:600;line-height:1.2}}
.heroi{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:48px;align-items:center;padding:48px 0}}
.medidor{{text-align:center}}
.medidor svg{{width:100%;max-width:520px;height:auto}}
.valor{{font:700 104px/1 'Space Grotesk',sans-serif;margin-top:-8px}}
.nivel{{font:600 22px 'Space Grotesk',sans-serif;letter-spacing:.2em;margin-top:8px}}
.rotulo{{font-size:13px;font-weight:600;letter-spacing:.16em;color:var(--suave)}}
.heroi h1{{font-size:34px;margin:10px 0 16px}}
.suave{{color:var(--suave)}}
.faixas{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-top:24px}}
.faixas div{{font-size:13px}}.faixas i{{display:block;height:6px;border-radius:3px;margin-bottom:6px}}
.cartao{{background:var(--painel);border-radius:16px;padding:24px;margin:24px 0}}
table{{width:100%;border-collapse:collapse}}
td,th{{text-align:left;padding:12px 8px;border-bottom:1px solid var(--linha);vertical-align:middle}}
th{{font-size:13px;color:var(--suave);font-weight:500}}
.barra{{background:var(--linha);border-radius:3px;height:6px;min-width:120px}}
.barra i{{display:block;height:6px;border-radius:3px}}
.num{{font:600 18px 'Space Grotesk',sans-serif;text-align:right;white-space:nowrap}}
img.grafico{{width:100%;height:auto;border-radius:12px}}
.botao{{display:inline-block;background:var(--texto);color:var(--fundo);padding:12px 22px;border-radius:10px;font-weight:600;text-decoration:none}}
.botao:hover{{color:var(--fundo);opacity:.9}}
.edicao{{max-width:720px;margin:0 auto;padding:32px 0}}
.edicao h1{{font-size:32px}}.edicao h2{{font-size:24px;margin-top:40px}}
.edicao img{{max-width:100%;height:auto;border-radius:12px}}
hr{{border:0;border-top:1px solid var(--linha);margin:32px 0}}
.edicao em{{color:var(--suave)}}
.lista a{{display:block;padding:14px 0;border-bottom:1px solid var(--linha);text-decoration:none;color:var(--texto)}}
.anuncio{{margin:32px 0;min-height:90px}}
.abertura{{display:grid;grid-template-columns:minmax(0,340px) minmax(0,1fr);gap:28px;align-items:start;padding:28px 0 12px}}
.global{{background:var(--painel);border-radius:18px;padding:20px 20px 16px;text-align:center}}
.global svg{{width:100%;max-width:290px;height:auto}}.global .valor{{font-size:72px;margin-top:-4px}}.global .nivel{{font-size:18px}}
.global p{{margin:10px 0 0;font-size:15px}}.abertura h1{{font-size:28px;margin:0 0 6px}}
.legenda{{display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:12px;font-size:13px;color:var(--suave)}}
.legenda i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}}
.acoes{{display:flex;flex-wrap:wrap;gap:12px 20px;align-items:center;margin:4px 0 8px}}
.mapa{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;grid-template-areas:"na eu as" "la af me"}}
.regiao{{position:relative;display:flex;flex-direction:column;gap:8px;background:var(--painel);border-radius:14px;padding:16px;color:var(--texto);text-decoration:none;border-top:6px solid}}
.regiao:hover{{outline:1px solid #34485A}}.regiao .cabeca{{display:flex;flex-direction:column;gap:8px;color:var(--texto);text-decoration:none}}
.regiao .cabeca::after{{content:"";position:absolute;inset:0}}.regiao .paises a{{position:relative;z-index:1;color:var(--suave);text-decoration:underline dotted;text-underline-offset:3px}}
.regiao .paises a:hover{{color:var(--texto)}}.regiao .mais{{font-size:13px;color:#7CC3E0}}
.manchetes{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}.manchete{{background:var(--painel);border-radius:14px;padding:16px;border-left:4px solid var(--linha)}}
.manchete h3{{font-size:16px;margin:6px 0}}.manchete p{{margin:4px 0;font-size:14px;color:var(--suave)}}.manchete .meta{{display:flex;flex-wrap:wrap;gap:6px 10px;font-size:12px;color:var(--suave)}}
.manchete .tag{{border:1px solid var(--linha);border-radius:6px;padding:1px 7px;color:var(--suave);text-decoration:none}}.fontes{{font-size:13px}}.fontes a{{margin-right:10px}}
.zap{{background:#25D366;color:#0E141B}}.faixa-zap{{display:flex;flex-wrap:wrap;gap:12px 20px;align-items:center;justify-content:space-between;background:#0B1F17;border:1px solid #1F4D3A;border-radius:14px;padding:16px 18px;margin:24px 0}}
.regiao .v{{font:700 34px/1 'Space Grotesk',sans-serif}}.chip{{font-size:13px;font-weight:600;color:#0E141B;border-radius:6px;padding:2px 8px}}
.paises{{font-size:13px;color:var(--suave)}}
.rodape{{padding-top:32px;padding-bottom:48px;border-top:1px solid var(--linha);margin-top:48px;font-size:13px;color:var(--suave)}}
@media (max-width:760px){{.abertura{{grid-template-columns:1fr;gap:18px;padding:18px 0 8px}}.abertura h1{{font-size:24px}}.global{{padding:14px}}.global svg{{max-width:210px}}.global .valor{{font-size:56px}}.global .nivel{{font-size:16px}}.global p{{font-size:14px;margin-top:6px}}.regiao{{padding:12px}}.regiao .v{{font-size:28px}}.heroi{{grid-template-columns:1fr;gap:24px;padding:28px 0}}.valor{{font-size:84px}}.heroi h1{{font-size:26px}}
.topo nav a{{margin-left:12px}}.faixas div{{font-size:11px}}.barra{{min-width:60px}}
.marca{{font-size:13px;letter-spacing:.06em}}.mapa{{grid-template-columns:1fr 1fr;grid-template-areas:"na eu" "la af" "me as"}}.topo nav a{{font-size:13px}}
.topo nav a:first-child{{margin-left:0}}.manchetes{{grid-template-columns:1fr}}}}
"""


def medidor_svg(valor: int, cor: str) -> str:
    t = math.radians(180 - 1.8 * valor)
    nx, ny = 300 + 190 * math.cos(t), 300 - 190 * math.sin(t)
    mx, my = 300 + 230 * math.cos(t), 300 - 230 * math.sin(t)
    arcos = "".join(f'<path d="{d}" fill="none" stroke="{n["cor"]}" stroke-width="40"/>'
                    for d, n in zip(ARCOS, config.NIVEIS))
    marcas = "".join(f'<text x="{x}" y="{y}" text-anchor="middle" font-size="14" fill="{C["suave"]}">{v}</text>'
                     for v, (x, y) in zip(range(0, 101, 20), [(18, 305), (72, 139), (213, 37), (387, 37), (528, 139), (582, 305)]))
    return (f'<svg viewBox="0 0 600 320" role="img" aria-label="Termômetro marcando {valor} de 100">{arcos}{marcas}'
            f'<line x1="300" y1="300" x2="{nx:.1f}" y2="{ny:.1f}" stroke="{C["texto"]}" stroke-width="6" stroke-linecap="round"/>'
            f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="13" fill="{cor}" stroke="{C["fundo"]}" stroke-width="4"/>'
            f'<circle cx="300" cy="300" r="14" fill="{C["texto"]}"/><circle cx="300" cy="300" r="6" fill="{C["fundo"]}"/></svg>')


def pagina(titulo: str, descricao: str, corpo: str, raiz: str = "", imagem: str = "", caminho: str = "",
           extra_css: str = "") -> str:
    url = f"{config.SITE_URL}/{caminho}" if config.SITE_URL else ""
    og_img = f"{config.SITE_URL}/{imagem}" if config.SITE_URL and imagem else ""
    adsense = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={config.ADSENSE_CLIENT}" '
               f'crossorigin="anonymous"></script>') if config.ADSENSE_CLIENT else ""
    t, d = html.escape(titulo), html.escape(descricao)
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t}</title><meta name="description" content="{d}">
<meta property="og:title" content="{t}"><meta property="og:description" content="{d}"><meta property="og:type" content="website">
{f'<meta property="og:url" content="{url}"><link rel="canonical" href="{url}">' if url else ''}
{f'<meta property="og:image" content="{og_img}"><meta name="twitter:card" content="summary_large_image">' if og_img else ''}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}{extra_css}</style>{adsense}</head>
<body><header class="topo"><a class="marca" href="{raiz}index.html">TERMÔMETRO DE CRISE</a>
<nav><a href="{raiz}mundo.html">Países</a><a href="{raiz}panorama.html">Panorama</a><a href="{raiz}edicoes/index.html">Edições</a><a href="{raiz}metodologia.html">Método</a></nav></header>
<main class="conteudo">{corpo}</main>
<footer class="rodape"><p>{html.escape(config.AVISO)}</p>
<p>Dados: datahub.io, FRED (Federal Reserve Bank of St. Louis), Yahoo Finance e as fontes citadas em cada página.</p></footer>
</body></html>"""


def grafico_html(pasta: str) -> str:
    return (f'<picture><source media="(max-width:760px)" srcset="{pasta}/historico_celular.png">'
            f'<img class="grafico" src="{pasta}/historico.png" alt="Histórico do Termômetro de Crise desde 1999"></picture>')


AREAS = {"América do Norte": "na", "América Latina": "la", "Europa": "eu", "Oriente Médio": "me",
         "África": "af", "Ásia e Pacífico": "as"}


def secao_mundo(m: dict) -> tuple[str, str]:
    """Mapa de regiões com o termômetro de cada uma (motor mundial). Cada região e cada país são clicáveis."""
    from .mundo import slug
    blocos = []
    for r in m.get("regioes", []):
        if r.get("valor") is None:
            continue
        paises = ", ".join(f'<a href="paises/{p.get("slug") or slug(p["nome"])}.html">{html.escape(p["nome"])} {p["valor"]}</a>'
                           for p in r["paises"] if p.get("valor") is not None)
        blocos.append(f'<div class="regiao" style="grid-area:{AREAS.get(r["nome"], "auto")};border-top-color:{r["cor"]}">'
                      f'<a class="cabeca" href="regioes/{r.get("slug") or slug(r["nome"])}.html">'
                      f'<strong style="font-family:\'Space Grotesk\',sans-serif;font-size:18px">{html.escape(r["nome"])}</strong>'
                      f'<span><span class="v">{r["valor"]}</span> <span class="chip" style="background:{r["cor"]}">{r["nivel"]}</span></span></a>'
                      f'<span class="paises">{paises}</span><span class="mais">Entender por quê →</span></div>')
    if not blocos:
        return "", ""
    b = m.get("brasil") or {}
    brasil = ""
    if b.get("valor") is not None:
        sinais = b.get("sinais", {})
        nomes = {"bolsa": "Queda da bolsa", "volatilidade": "Sobe e desce da bolsa", "moeda": "Dólar contra o real"}
        itens = "".join(f'<li>{nomes.get(k, k)}: percentil {v}</li>' for k, v in sinais.items() if v is not None and k in nomes)
        brasil = (f'<section class="cartao"><span class="rotulo">BRASIL EM DESTAQUE</span>'
                  f'<h2 style="margin:8px 0">Termômetro Brasil: <span style="color:{b["cor"]}">{b["valor"]} · {b["nivel"]}</span></h2>'
                  f'<ul class="suave" style="margin:0;padding-left:20px">{itens}</ul>'
                  f'<p class="suave" style="font-size:13px">Leitura de {mes_curto(b["referencia"])}. Cada sinal comparado com a história '
                  f'do próprio Brasil: 90 significa mais tenso do que em 90% dos meses.</p>'
                  f'<p style="margin:0"><a href="paises/brasil.html">Entender o Brasil em detalhe →</a></p></section>')
    return f'<div class="mapa">{"".join(blocos)}</div>', brasil


def curto(texto: str, limite: int = 170) -> str:
    texto = " ".join(str(texto or "").split())
    return texto if len(texto) <= limite else texto[:limite].rsplit(" ", 1)[0] + "…"


def manchetes(noticias: list[dict]) -> str:
    """As notícias que mais mexem com o termômetro, na página inicial."""
    from .mundo import REGIOES, slug
    from .paginas import COR_DIRECAO, TEXTO_DIRECAO, data_curta
    if not noticias:
        return ""
    cartoes = []
    for n in noticias[:6]:
        cor = COR_DIRECAO.get(n.get("direcao") or "", C["linha"])
        regiao = (f'<a class="tag" href="regioes/{slug(n["regiao"])}.html">{html.escape(n["regiao"])}</a>'
                  if n.get("regiao") in REGIOES else f'<span class="tag">{html.escape(n.get("regiao") or "")}</span>')
        mexe = (f'<span style="color:{cor}">Mexe em: {html.escape(", ".join(n["mexe_em"]))} · '
                f'{TEXTO_DIRECAO.get(n.get("direcao"), "")}</span>' if n.get("mexe_em") else "")
        fontes = "".join(f'<a href="{html.escape(f["url"])}" target="_blank" rel="noopener noreferrer">'
                         f'{html.escape(f.get("veiculo") or "fonte")}</a>' for f in n.get("fontes", [])[:2])
        cartoes.append(f'<article class="manchete" style="border-left-color:{cor}"><div class="meta">{regiao}'
                       f'<span>{data_curta(n.get("data", ""))}</span><span>{html.escape(n.get("status") or "")}</span></div>'
                       f'<h3>{html.escape(n["titulo"])}</h3><p>{html.escape(curto(n.get("resumo", "")))}</p>'
                       f'<div class="meta">{mexe}</div><div class="fontes">{fontes}</div></article>')
    return (f'<section><h2>O que está mexendo no termômetro</h2><div class="manchetes">{"".join(cartoes)}</div>'
            f'<p class="suave" style="font-size:13px">Só entram notícias com fonte e com o status do fato. '
            f'Toque na região para ver todas.</p></section>')


def linha_componente(c: dict) -> str:
    pct = c["percentil"]
    cor = config.nivel_de(pct or 0)["cor"]
    variacao = "" if c["variacao_mes"] is None else f"{c['variacao_mes']:+d} no mês"
    return (f'<tr><td><strong>{c["nome"]}</strong><br><span class="suave" style="font-size:13px">{c["descricao"]}</span></td>'
            f'<td><div class="barra"><i style="width:{pct or 0}%;background:{cor}"></i></div></td>'
            f'<td class="num">{"–" if pct is None else pct}<br>'
            f'<span class="suave" style="font-size:12px;font-weight:400">{variacao}</span></td></tr>')


def _edicoes(pasta: Path) -> list[Path]:
    return sorted((p for p in pasta.iterdir() if p.is_dir() and (p / "edicao.md").exists()), reverse=True)


def gerar(pasta_edicoes: Path, saida: Path, pasta_diario: Path | None = None) -> None:
    if saida.exists():
        shutil.rmtree(saida)
    (saida / "edicoes").mkdir(parents=True)
    edicoes = _edicoes(pasta_edicoes)
    if not edicoes:
        raise SystemExit("Nenhuma edição encontrada em edicoes/.")

    lista = []
    for pasta in edicoes:
        dia = pasta.name
        dados = json.loads((pasta / "atual.json").read_text())
        copy = json.loads((pasta / "copy.json").read_text())
        destino = saida / "edicoes" / dia
        destino.mkdir()
        for img in ("historico.png", "historico_celular.png", "card.png"):
            shutil.copy(pasta / img, destino / img)
        texto = (pasta / "edicao.md").read_text()
        corpo_html = markdown.markdown(texto, extensions=["extra", "sane_lists"])
        # o gráfico entra logo depois da leitura do Termômetro, antes dos riscos
        marco = "<h2>Os 3 riscos"
        if marco in corpo_html:
            corpo_html = corpo_html.replace(marco, f"<p>{grafico_html(dia)}</p>\n{marco}", 1)
        corpo = f'<article class="edicao">{corpo_html}</article>'
        (saida / "edicoes" / f"{dia}.html").write_text(
            pagina(copy["titulo_site"], copy["descricao_seo"], corpo, raiz="../", imagem=f"edicoes/{dia}/card.png",
                   caminho=f"edicoes/{dia}.html"))
        lista.append((dia, dados, copy))

    itens = "".join(f'<a href="{d}.html"><strong>{pd.Timestamp(d):%d/%m/%Y}</strong> · {dd["valor"]}, {dd["nivel"]}'
                    f'<br><span class="suave">{html.escape(cc["pre_cabecalho"])}</span></a>' for d, dd, cc in lista)
    (saida / "edicoes" / "index.html").write_text(
        pagina(f"Edições · {config.NOME}", "Todas as edições do Termômetro de Crise.",
               f'<section class="edicao"><h1>Edições</h1><div class="lista">{itens}</div></section>', raiz="../",
               caminho="edicoes/index.html"))

    dia, dados, copy = lista[0]
    from . import paginas  # aqui dentro para não haver importação circular
    fonte = paginas.fonte(pasta_edicoes / dia, pasta_diario or pasta_edicoes.parent / "diario")
    mundo = fonte["mundo"]
    faixas = "".join(f'<div><i style="background:{n["cor"]};opacity:{1 if n["nome"] == dados["nivel"] else .4}"></i>'
                     f'{n["nome"]}<br><span class="suave">{n["min"]}–{n["max"]}</span></div>' for n in config.NIVEIS)
    linhas = "".join(linha_componente(c) for c in dados["componentes"])
    assinar = config.NEWSLETTER_URL or f"edicoes/{dia}.html"
    mapa, brasil = secao_mundo(mundo)
    zap = (f'<div class="faixa-zap"><div><strong>Panorama do fim de tarde no WhatsApp</strong><br>'
           f'<span class="suave" style="font-size:14px">Todo dia útil, o termômetro do mundo, das regiões e do Brasil, '
           f'com as notícias que mexeram com ele.</span></div>'
           f'<a class="botao zap" href="{html.escape(config.WHATSAPP_URL or "panorama.html")}">'
           f'{"Entrar no canal" if config.WHATSAPP_URL else "Ver o panorama de hoje"}</a></div>')
    if mapa:  # com o motor mundial, as regiões abrem a página, ao lado do termômetro do mundo
        legenda = "".join(f'<span><i style="background:{n["cor"]}"></i>{n["nome"]} {n["min"]}–{n["max"]}</span>'
                          for n in config.NIVEIS)
        g = mundo.get("mundo") or {}
        if g.get("valor") is not None:  # o mundo de hoje é a média das regiões que aparecem ao lado
            nivel_g = config.nivel_de(g["valor"])
            g_valor, g_cor, g_nivel, g_frase = g["valor"], nivel_g["cor"], nivel_g["nome"], nivel_g["leitura"]
            g_nota = f"Média das 6 regiões · atualizado em {pd.Timestamp(fonte['data']):%d/%m/%Y}"
        else:
            g_valor, g_cor, g_nivel, g_frase = dados["valor"], dados["cor"], dados["nivel"], dados["leitura"]
            g_nota = f"Leitura de {mes_curto(dados['referencia'])} · atualizado em {pd.Timestamp(dia):%d/%m/%Y}"
        topo = f"""
<section class="abertura">
 <div class="global"><span class="rotulo">O MUNDO HOJE</span>{medidor_svg(g_valor, g_cor)}
  <div class="valor">{g_valor}</div><div class="nivel" style="color:{g_cor}">{g_nivel.upper()}</div>
  <p>{html.escape(g_frase)}</p>
  <p class="suave" style="font-size:13px">{g_nota} · <a href="mundo.html">ranking dos países</a></p></div>
 <div><h1>Como está cada região do mundo</h1>
  <p class="suave" style="margin:0 0 14px">De 0 (calmo) a 100 (crise). Toque em uma região ou em um país para entender o porquê.</p>
  {mapa}
  <div class="legenda">{legenda}</div></div>
</section>
<div class="acoes"><a class="botao" href="{assinar}">Receber todo domingo, grátis</a>
 <a href="edicoes/{dia}.html">Ler a análise da semana</a></div>
{manchetes(fonte["noticias"])}
{zap}
{brasil}"""
        titulo_tabela = (f"Termômetro dos mercados globais: {dados['valor']} · {dados['nivel']}"
                         f" <span class=\"suave\" style=\"font-size:15px;font-weight:400\">leitura de {mes_curto(dados['referencia'])}</span>")
    else:
        topo = f"""
<section class="heroi">
 <div class="medidor">{medidor_svg(dados['valor'], dados['cor'])}
  <div class="valor">{dados['valor']}</div><div class="nivel" style="color:{dados['cor']}">{dados['nivel'].upper()}</div>
  <p class="suave" style="font-size:14px">Leitura de {mes_curto(dados['referencia'])} · atualizado em {pd.Timestamp(dia):%d/%m/%Y}</p></div>
 <div><span class="rotulo">TERMÔMETRO GLOBAL</span><h1>{html.escape(dados['leitura'])}</h1>
  <p class="suave">Um índice de 0 a 100 que mede o estresse dos mercados globais com 5 indicadores públicos,
  cada um comparado com o próprio histórico desde 1990.</p>
  <div class="faixas">{faixas}</div>
  <p style="margin-top:28px"><a class="botao" href="{assinar}">Receber todo domingo</a>
  &nbsp; <a href="edicoes/{dia}.html">Ler a edição da semana</a></p></div>
</section>"""
        titulo_tabela = "O que compõe a leitura"
    corpo = topo + f"""
{'<div class="anuncio"></div>' if config.ADSENSE_CLIENT else ''}
<section class="cartao"><h2 style="margin-top:0">{titulo_tabela}</h2>
 <p class="suave" style="margin-top:0">O índice da newsletter: 5 indicadores dos mercados globais, cada um comparado com o próprio histórico desde 1990.</p>
 <table><tr><th>Componente</th><th>Estresse (percentil)</th><th style="text-align:right">Agora</th></tr>{linhas}</table>
 <p class="suave" style="font-size:13px">Percentil: 90 significa que o indicador está mais estressado do que em 90% dos meses desde 1990.
 Ainda fora do índice: {', '.join(dados['componentes_ausentes'])}.</p></section>
<section><h2>Desde 1999</h2>{grafico_html(f"edicoes/{dia}")}</section>"""
    (saida / "index.html").write_text(pagina(copy["titulo_site"], copy["descricao_seo"], corpo,
                                             imagem=f"edicoes/{dia}/card.png"))
    (saida / "metodologia.html").write_text(pagina(f"Metodologia · {config.NOME}",
                                                   "Como o Termômetro de Crise é calculado.", metodologia(dados)))
    novas = paginas.gerar(saida, fonte) if mundo.get("regioes") else []
    extras(saida, [""] + ["metodologia.html", "edicoes/index.html"] + [f"edicoes/{d}.html" for d, _, _ in lista] + novas)
    print(f"Site gerado em {saida} com {len(lista)} edição(ões).")


def metodologia(dados: dict) -> str:
    comps = "".join(f'<tr><td><strong>{c["nome"]}</strong></td><td>{c["descricao"]}</td><td class="num">{c["peso"]}</td></tr>'
                    for c in dados["componentes"])
    picos = "".join(f'<tr><td>{k}</td><td class="num">{v["valor"]}</td><td>{mes_curto(v["mes"])}</td></tr>'
                    for k, v in dados["picos_historicos"].items())
    return f"""<section class="edicao"><h1>Metodologia</h1>
<p>O Termômetro de Crise resume em um número de 0 a 100 o estresse dos mercados globais. O método é aberto e
reprodutível: qualquer pessoa pode recalcular com os mesmos dados públicos.</p>
<h2>Como funciona</h2>
<ol><li>Cada componente é medido todo mês.</li>
<li>O valor do mês vira um percentil: a porcentagem dos meses desde 1990 em que o indicador esteve mais calmo do que agora.
O cálculo só usa o passado até aquele mês, nunca o futuro.</li>
<li>O Termômetro é a média ponderada dos percentis. Se faltar um componente, os pesos dos demais são redistribuídos;
com menos de 4 de 5, não há leitura.</li></ol>
<h2>Componentes e pesos</h2><table><tr><th>Componente</th><th>O que mede</th><th style="text-align:right">Peso</th></tr>{comps}</table>
<p class="suave">Petróleo, juros e ouro contam choques nos dois sentidos: em crises de liquidez, como 2008 e 2020,
petróleo e ouro despencam, e isso também é sinal de estresse.</p>
<h2>Teste histórico</h2><table><tr><th>Episódio</th><th style="text-align:right">Pico</th><th>Mês</th></tr>{picos}</table>
<p class="suave">Nenhum ano calmo do teste (2005, 2017, 2019, 2021) entrou na faixa Crise. Um bom resultado no passado
não garante o mesmo comportamento no futuro.</p>
<h2>Limites</h2><ul><li>Leitura mensal: o índice reage a crises, não as prevê.</li>
<li>Ainda fora do índice: {', '.join(dados['componentes_ausentes'])}.</li>
<li>Os pesos são uma escolha de método, não uma verdade estatística.</li></ul>
<h2 id="mundo">Termômetro por país e por região</h2>
<p>Cada país tem três sinais, todos medidos mês a mês com os fechamentos diários:</p>
<ol><li><strong>Queda da bolsa:</strong> quanto o índice principal está abaixo do ponto mais alto dos últimos 12 meses.</li>
<li><strong>Sobe e desce:</strong> quanto a bolsa oscila de um dia para o outro no mês (volatilidade realizada).</li>
<li><strong>Moeda:</strong> quanto a moeda mudou contra o dólar em 3 meses, para qualquer lado.</li></ol>
<p>Cada sinal vira o percentil da história do próprio país (é preciso ter 5 anos de dados antes da primeira leitura,
e o cálculo nunca olha o futuro). O termômetro do país é a média dos sinais; o da região, a média dos países; e o do
mundo, a média das 6 regiões. Nos dias úteis, os números são atualizados no fim da tarde, com o mês ainda em andamento.</p>
<p>As explicações de cada país juntam duas coisas: o que os números mostram (escrito pelo programa) e o contexto das
notícias (escrito pelo agente Correspondente, que pesquisa a semana na web). Toda notícia publicada tem link para a fonte,
status do fato (confirmado, operação em curso, ameaça, negociação ou hipótese) e passa por uma conferência automática:
só entram links que a busca devolveu de verdade, datas dos últimos dias e textos sem recomendação, promessa ou alarmismo.</p>
<p class="suave">Limites: alguns países têm menos sinais (o Egito e a Nigéria ainda sem bolsa; EUA e Hong Kong sem moeda,
porque o dólar é a referência e o dólar de Hong Kong é atrelado a ele). Os dados de bolsa e de parte das moedas vêm do
Yahoo Finance e do FRED.</p></section>"""


def extras(saida: Path, caminhos: list[str]) -> None:
    (saida / ".nojekyll").write_text("")
    (saida / "robots.txt").write_text("User-agent: *\nAllow: /\n" +
                                      (f"Sitemap: {config.SITE_URL}/sitemap.xml\n" if config.SITE_URL else ""))
    if config.SITE_URL:
        urls = "".join(f"<url><loc>{config.SITE_URL}/{c}</loc></url>" for c in caminhos)
        (saida / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>'
                                           f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    if config.DOMINIO:
        (saida / "CNAME").write_text(config.DOMINIO + "\n")
    if config.ADSENSE_CLIENT:
        pub = config.ADSENSE_CLIENT.replace("ca-", "")
        (saida / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
