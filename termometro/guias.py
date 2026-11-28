"""Guias: artigos longos e originais do Termômetro de Crise (28/11/2026).

Nasceram dos roteiros dos vídeos longos do YouTube. Cada guia é um arquivo .md em termometro/guias/, com cabeçalho
simples (titulo, descricao, data, revisado, video, calculadora), parágrafos, "## " para seção, "- " e "1. " para lista,
**negrito**, *itálico*, [texto](link) e, no fim, "fontes:" com uma fonte por linha.

Regras: conteúdo educativo, com fonte, sem recomendação de investimento e sem promessa de ganho.
"""

import html
import json
import re
from pathlib import Path

from . import config

PASTA = Path(__file__).parent / "guias"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
CALCS = {"dolar-cartao": "Dólar no cartão com IOF", "inflacao": "Calculadora de inflação (IPCA)",
         "rendimento-selic": "Quanto rende na Selic", "juros-compostos": "Juros compostos"}

CSS = """
.guia{max-width:760px}.guia h1{font-size:34px;line-height:1.15;margin:8px 0 10px}.guia .linha-fina{font-size:19px;color:var(--suave);margin:0 0 10px}
.guia .meta{font-size:14px;color:var(--suave);margin:0 0 26px}.guia h2{font-size:24px;margin:36px 0 10px}
.guia p,.guia li{font-size:18px;line-height:1.65}.guia li{margin:6px 0}.guia .aviso{font-size:15px;color:var(--suave);border-top:1px solid var(--linha);padding-top:14px;margin-top:30px}
.guia .fontes li{font-size:15px}.guia .relacionados{background:var(--painel);border:1px solid #233140;border-radius:14px;padding:16px 20px;margin:28px 0}
.guia .relacionados p{margin:4px 0;font-size:16px}
.lista-guias{display:grid;gap:14px;max-width:820px}.lista-guias a{display:block;background:var(--painel);border:1px solid #233140;border-radius:14px;padding:18px 20px;color:var(--texto);text-decoration:none}
.lista-guias a:hover{border-color:#3A5066}.lista-guias strong{display:block;font-size:20px;margin-bottom:4px}.lista-guias span{color:var(--suave);font-size:15px}
"""


def _inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{m[2]}">{m[1]}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    return re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)


def ler(arq: Path) -> dict:
    cab, corpo, fontes, lendo_fontes = {}, [], [], False
    linhas = arq.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(linhas) and linhas[i].strip() and re.match(r"^[a-z]+: ", linhas[i]):
        k, v = linhas[i].split(": ", 1)
        cab[k] = v.strip()
        i += 1
    for ln in linhas[i:]:
        if ln.strip() == "fontes:":
            lendo_fontes = True
        elif lendo_fontes and ln.startswith("- "):
            fontes.append(ln[2:].strip())
        elif not lendo_fontes:
            corpo.append(ln)
    return {"slug": arq.stem, **cab, "corpo": corpo, "fontes": fontes}


def _html_corpo(linhas: list[str]) -> str:
    out, lista = [], None

    def fecha():
        nonlocal lista
        if lista:
            out.append(f"</{lista}>")
        lista = None

    for ln in linhas:
        s = ln.strip()
        if not s:
            fecha()
            continue
        if s.startswith("## "):
            fecha()
            titulo = s[3:]
            ancora = re.sub(r"[^a-z0-9]+", "-", titulo.lower().translate(str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc"))).strip("-")
            out.append(f'<h2 id="{ancora}">{_inline(titulo)}</h2>')
        elif s.startswith("- ") or re.match(r"^\d+\. ", s):
            tipo = "ul" if s.startswith("- ") else "ol"
            if lista != tipo:
                fecha()
                out.append(f"<{tipo}>")
                lista = tipo
            out.append(f"<li>{_inline(re.sub(r'^(- |\d+\. )', '', s))}</li>")
        else:
            fecha()
            out.append(f"<p>{_inline(s)}</p>")
    fecha()
    return "\n".join(out)


def _data(iso: str) -> str:
    a, m, d = iso.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def palavras(g: dict) -> int:
    return len(re.sub(r"[#*\[\]()]", " ", " ".join(g["corpo"])).split())


def todos() -> list[dict]:
    return sorted((ler(a) for a in PASTA.glob("*.md")), key=lambda g: g.get("data", ""), reverse=True)


def pagina_guia(g: dict, outros: list[dict]) -> str:
    calc = g.get("calculadora", "")
    rel = []
    if calc in CALCS:
        rel.append(f'<p>Faça a conta: <a href="../ferramentas/{calc}.html">{CALCS[calc]}</a></p>')
    if g.get("video"):
        rel.append(f'<p>Prefere vídeo? <a href="{html.escape(g["video"])}" target="_blank" rel="noopener">Assista a este guia no YouTube</a></p>')
    rel += [f'<p>Leia também: <a href="{o["slug"]}.html">{html.escape(o["titulo"])}</a></p>' for o in outros[:2]]
    fontes = "".join(f"<li>{html.escape(f)}</li>" for f in g["fontes"])
    rev = f" · revisado em {_data(g['revisado'])}" if g.get("revisado") and g["revisado"] != g.get("data") else ""
    url = f"{config.SITE_URL}/guias/{g['slug']}.html" if config.SITE_URL else ""
    dados = {"@context": "https://schema.org", "@type": "Article", "headline": g["titulo"], "description": g["descricao"],
             "datePublished": g["data"], "dateModified": g.get("revisado", g["data"]), "inLanguage": "pt-BR",
             "author": {"@type": "Person", "name": "Heitor", "url": f"{config.SITE_URL}/quem-somos.html"},
             "publisher": {"@type": "Organization", "name": config.NOME, "logo": f"{config.SITE_URL}/icone-512.png"},
             "mainEntityOfPage": url}
    return f"""<article class="guia"><p class="trilha"><a href="../index.html">Início</a> › <a href="index.html">Guias</a></p>
<h1>{html.escape(g["titulo"])}</h1><p class="linha-fina">{html.escape(g["descricao"])}</p>
<p class="meta">Por Heitor, do {config.NOME} · publicado em {_data(g["data"])}{rev} · {max(1, round(palavras(g) / 200))} min de leitura</p>
{_html_corpo(g["corpo"])}
<div class="relacionados">{"".join(rel)}</div>
<h2>Fontes</h2><ul class="fontes">{fontes}</ul>
<p class="aviso">Conteúdo educativo. Não é recomendação de investimento. Os números foram conferidos nas fontes acima na
data de revisão e podem mudar. Viu um erro? <a href="../correcoes.html">Veja como pedir correção</a>.</p>
</article><script type="application/ld+json">{json.dumps(dados, ensure_ascii=False)}</script>"""


def indice(gs: list[dict]) -> str:
    itens = "".join(f'<a href="{g["slug"]}.html"><strong>{html.escape(g["titulo"])}</strong>'
                    f'<span>{html.escape(g["descricao"])}</span></a>' for g in gs)
    return f"""<section class="edicao"><h1>Guias</h1>
<p>Explicações completas, em português simples, sobre o que mexe no seu bolso: dólar, juros, inflação, combustível e
crises. Cada guia traz as contas, os exemplos e a fonte de cada número. Um guia novo sai junto com cada vídeo longo do
canal do {config.NOME} no YouTube.</p>
<div class="lista-guias">{itens}</div>
<p class="suave">Conteúdo educativo. Não é recomendação de investimento.</p></section>"""


def gerar(saida: Path, pagina) -> list[str]:
    gs = todos()
    pasta = saida / "guias"
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for g in gs:
        outros = [o for o in gs if o["slug"] != g["slug"]]
        (pasta / f"{g['slug']}.html").write_text(pagina(f"{g['titulo']} · {config.NOME}", g["descricao"],
                                                        pagina_guia(g, outros), raiz="../",
                                                        caminho=f"guias/{g['slug']}.html", extra_css=CSS))
        caminhos.append(f"guias/{g['slug']}.html")
    (pasta / "index.html").write_text(pagina(f"Guias: dólar, juros, inflação e crises explicados · {config.NOME}",
                                             "Guias completos e com fonte sobre o que mexe no seu bolso: dólar, Selic, "
                                             "inflação, combustível e crises.", indice(gs), raiz="../",
                                             caminho="guias/index.html", extra_css=CSS))
    return ["guias/index.html"] + caminhos
