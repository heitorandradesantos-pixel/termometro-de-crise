"""Arquivo do site: nada do que foi publicado se perde.

- Panorama: cada dia útil tem página própria (/panorama/AAAA-MM-DD.html) e um arquivo por mês, em calendário.
- Notícias: todas as notícias conferidas ficam guardadas, por região e por país, 20 por página, as mais novas primeiro.
- Edições: 12 por página, com índice por mês e "anterior / próxima" dentro de cada edição.

Páginas numeradas, com botões grandes "Mais novas / Mais antigas": o Google lê, o leitor sabe onde está e o rodapé
(com as páginas legais) continua alcançável. Nenhuma página vazia é gerada.
"""

import html
import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd

from . import config, correspondente as corr

POR_PAGINA_NOTICIAS = 20
POR_PAGINA_EDICOES = 12
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

CSS = """
.paginacao{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;margin:28px 0 8px}
.paginacao .numeros{display:flex;flex-wrap:wrap;gap:6px}.paginacao .numeros a,.paginacao .numeros span{display:inline-flex;
align-items:center;justify-content:center;min-width:44px;min-height:44px;border-radius:10px;border:1px solid var(--linha);
color:var(--texto);text-decoration:none}.paginacao .numeros [aria-current]{background:var(--texto);color:var(--fundo);font-weight:700}
.dia-titulo{font:600 15px 'Space Grotesk',sans-serif;color:var(--suave);margin:26px 0 0;padding-bottom:6px;border-bottom:1px solid var(--linha)}
.calendario{display:grid;grid-template-columns:repeat(auto-fill,minmax(92px,1fr));gap:8px;margin:10px 0 24px}
.calendario a{display:block;background:var(--painel);border-radius:10px;padding:10px;text-decoration:none;color:var(--texto);
border-top:4px solid var(--linha);min-height:44px}.calendario small{display:block;color:var(--suave);font-size:12px}
.calendario strong{font:700 22px 'Space Grotesk',sans-serif}
.navdia{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin:20px 0}
"""


def _cor(valor) -> str:
    return config.nivel_de(valor)["cor"] if valor is not None else config.CORES["linha"]


def data_longa(d: str) -> str:
    t = pd.Timestamp(d)
    return f"{t.day} de {MESES[t.month - 1]} de {t.year}"


def paginacao(atual: int, total: int, url) -> str:
    """Navegação numerada; url(n) devolve o endereço relativo da página n."""
    if total <= 1:
        return ""
    novas = f'<a class="contorno" href="{url(atual - 1)}">Mais novas</a>' if atual > 1 else "<span></span>"
    antigas = f'<a class="contorno" href="{url(atual + 1)}">Mais antigas</a>' if atual < total else "<span></span>"
    janela = sorted({1, total, *range(max(1, atual - 2), min(total, atual + 2) + 1)})
    numeros, anterior = [], 0
    for n in janela:
        if n - anterior > 1:
            numeros.append('<span aria-hidden="true">…</span>')
        numeros.append(f'<span aria-current="page">{n}</span>' if n == atual else f'<a href="{url(n)}">{n}</a>')
        anterior = n
    return (f'<nav class="paginacao" aria-label="Páginas">{novas}<div class="numeros">{"".join(numeros)}</div>'
            f'{antigas}</nav>')


def _paginas(itens: list, tamanho: int) -> list[list]:
    return [itens[i:i + tamanho] for i in range(0, len(itens), tamanho)] or [[]]


# ---------------------------------------------------------------- dados do diário
def dias(pasta_diario: Path) -> list[dict]:
    """Todos os dias publicados, do mais novo para o mais antigo, com o que cada um tem."""
    from .paginas import dias_do_diario
    saida = []
    for d in reversed(dias_do_diario(pasta_diario)):
        mundo = json.loads((d / "mundo.json").read_text())
        corresp = json.loads((d / "correspondente.json").read_text()) if (d / "correspondente.json").exists() else {}
        saida.append({"data": d.name, "mundo": mundo, "correspondente": corresp,
                      "panorama": (d / "panorama.txt").read_text() if (d / "panorama.txt").exists() else ""})
    return saida


def todas_noticias(lista_dias: list[dict], membros: dict[str, list[str]], cores: dict[str, str]) -> list[dict]:
    """Notícias de todos os dias, sem repetir (a mesma notícia pode voltar em dias seguidos)."""
    vistas, saida = set(), []
    for dia in lista_dias:
        for regiao, r in (dia["correspondente"].get("regioes") or {}).items():
            for n in r.get("noticias", []):
                chave = (n.get("regiao"), n["titulo"].strip().lower())
                if chave in vistas:
                    continue
                vistas.add(chave)
                n = {**n, "titulo": corr.datas_br(n["titulo"]), "resumo": corr.datas_br(n.get("resumo", "")),
                     "cor": cores.get(n.get("regiao"))}
                if not n.get("paises"):
                    n["paises"] = corr.citados(f"{n['titulo']} {n['resumo']}", membros.get(n.get("regiao"), []))
                saida.append(n)
    return sorted(saida, key=lambda n: (n.get("data", ""), n.get("relevancia", 0)), reverse=True)


# ---------------------------------------------------------------- páginas
def _lista_por_dia(noticias: list[dict], raiz: str, mostrar_regiao: bool) -> str:
    from .paginas import noticia_html
    partes, atual = [], None
    for n in noticias:
        if n.get("data") != atual:
            atual = n.get("data")
            partes.append(f'<h2 class="dia-titulo">{data_longa(atual) if atual else "Sem data"}</h2>')
        partes.append(noticia_html(n, raiz, mostrar_regiao))
    return "".join(partes)


def paginas_noticias(saida: Path, noticias: list[dict], m: dict) -> list[str]:
    from .site import pagina
    from .paginas import CSS as CSS_PAGINAS, de
    (saida / "noticias").mkdir(exist_ok=True)
    caminhos = []

    def grupo(nome_arquivo: str, titulo: str, descricao: str, itens: list[dict], mostrar_regiao: bool, volta: str):
        blocos = _paginas(itens, POR_PAGINA_NOTICIAS)
        total = len(blocos)

        def url(n: int) -> str:
            if n == 1:
                return f"{nome_arquivo}.html"
            return f"pagina-{n}.html" if nome_arquivo == "index" else f"{nome_arquivo}-{n}.html"
        for i, bloco in enumerate(blocos, 1):
            sufixo = "" if i == 1 else f" (página {i})"
            corpo = (f'<section class="edicao" style="max-width:820px"><p class="trilha">{volta}</p><h1>{html.escape(titulo)}{sufixo}</h1>'
                     f'<p class="suave">{html.escape(descricao)} {len(itens)} notícias guardadas, das mais novas para as mais antigas.</p>'
                     f'{_lista_por_dia(bloco, "../", mostrar_regiao)}{paginacao(i, total, url)}</section>')
            caminho = f"noticias/{url(i)}"
            (saida / caminho).write_text(pagina(f"{titulo}{sufixo} · {config.NOME}", descricao, corpo, raiz="../",
                                                caminho=caminho, extra_css=CSS_PAGINAS + CSS))
            caminhos.append(caminho)

    regioes = [r for r in m.get("regioes", []) if r.get("valor") is not None]
    filtros = " · ".join(f'<a href="{r["slug"]}.html">{html.escape(r["nome"])}</a>' for r in regioes
                         if any(n.get("regiao") == r["nome"] for n in noticias))
    if noticias:
        grupo("index", "Todas as notícias que mexeram com o termômetro",
              "Cada notícia com fonte, status do fato e o sinal que ela mexe.", noticias, True,
              f'<a href="../index.html">Início</a> › Notícias' + (f" · Por região: {filtros}" if filtros else ""))
    for r in regioes:
        da_regiao = [n for n in noticias if n.get("regiao") == r["nome"]]
        if da_regiao:
            grupo(r["slug"], f"Notícias {de(r['nome'])}", f"O que mexeu com o termômetro {de(r['nome'])}.", da_regiao, False,
                  f'<a href="../index.html">Início</a> › <a href="index.html">Notícias</a> › '
                  f'<a href="../regioes/{r["slug"]}.html">{html.escape(r["nome"])}</a>')
        for p in r.get("paises", []):
            do_pais = [n for n in da_regiao if p["nome"] in n.get("paises", [])]
            if do_pais:
                grupo(p["slug"], f"Notícias {de(p['nome'])}", f"O que mexeu com o termômetro {de(p['nome'])}.", do_pais, False,
                      f'<a href="../index.html">Início</a> › <a href="index.html">Notícias</a> › '
                      f'<a href="../paises/{p["slug"]}.html">{html.escape(p["nome"])}</a>')
    return caminhos


def paginas_panorama(saida: Path, lista_dias: list[dict]) -> list[str]:
    from .site import pagina
    from .paginas import CSS as CSS_PAGINAS, whatsapp_html
    com_texto = [d for d in lista_dias if d["panorama"]]
    if not com_texto:
        return []
    (saida / "panorama").mkdir(exist_ok=True)
    caminhos = []
    for i, d in enumerate(com_texto):
        mais_novo = com_texto[i - 1]["data"] if i > 0 else None
        mais_antigo = com_texto[i + 1]["data"] if i + 1 < len(com_texto) else None
        m = (d["mundo"].get("mundo") or {})
        nav = (f'<nav class="navdia" aria-label="Outros dias">'
               + (f'<a class="contorno" href="{mais_antigo}.html">Dia anterior</a>' if mais_antigo else "<span></span>")
               + '<a class="contorno" href="index.html">Todos os dias</a>'
               + (f'<a class="contorno" href="{mais_novo}.html">Dia seguinte</a>' if mais_novo else "<span></span>") + "</nav>")
        corpo = (f'<section class="edicao"><p class="trilha"><a href="../index.html">Início</a> › '
                 f'<a href="index.html">Panoramas</a> › {pd.Timestamp(d["data"]):%d/%m/%Y}</p>'
                 f'<h1>Panorama de {data_longa(d["data"])}</h1>'
                 f'<p class="suave">Termômetro do mundo: {m.get("valor", "–")} ({m.get("nivel", "")}). O texto que foi para o '
                 f'canal do WhatsApp neste dia:</p>'
                 f'<div class="acoes" style="margin:12px 0"><a class="acao" href="https://wa.me/?text={quote(d["panorama"])}" '
                 f'target="_blank" rel="noopener">Enviar pelo WhatsApp</a></div>'
                 f'<div class="pano">{whatsapp_html(d["panorama"])}</div>{nav}</section>')
        caminho = f"panorama/{d['data']}.html"
        (saida / caminho).write_text(pagina(f"Panorama de {pd.Timestamp(d['data']):%d/%m/%Y}: mundo em {m.get('valor', '–')} · {config.NOME}",
                                            f"O resumo do termômetro de crise do mundo, das regiões e do Brasil em {data_longa(d['data'])}.",
                                            corpo, raiz="../", caminho=caminho, extra_css=CSS_PAGINAS + CSS))
        caminhos.append(caminho)
    # arquivo em calendário, um bloco por mês
    meses = {}
    for d in com_texto:
        meses.setdefault(d["data"][:7], []).append(d)
    blocos = []
    for mes, dias_mes in meses.items():
        t = pd.Timestamp(mes + "-01")
        quadros = "".join(
            f'<a href="{d["data"]}.html" style="border-top-color:{_cor((d["mundo"].get("mundo") or {}).get("valor"))}">'
            f'<small>{DIAS_SEMANA[pd.Timestamp(d["data"]).weekday()]} {pd.Timestamp(d["data"]).day}</small>'
            f'<strong>{(d["mundo"].get("mundo") or {}).get("valor", "–")}</strong>'
            f'<small>{(d["mundo"].get("mundo") or {}).get("nivel", "")}</small></a>'
            for d in sorted(dias_mes, key=lambda x: x["data"]))
        blocos.append(f'<h2 class="dia-titulo">{MESES[t.month - 1].capitalize()} de {t.year}</h2>'
                      f'<div class="calendario">{quadros}</div>')
    corpo = (f'<section class="edicao" style="max-width:820px"><p class="trilha"><a href="../index.html">Início</a> › Panoramas</p>'
             f'<h1>Todos os panoramas do fim de tarde</h1><p class="suave">Cada dia útil, o termômetro do mundo e as notícias '
             f'que mexeram com ele. Toque num dia para ver o texto. A cor é o nível do mundo naquele dia.</p>'
             f'{"".join(blocos)}</section>')
    (saida / "panorama" / "index.html").write_text(
        pagina(f"Arquivo dos panoramas · {config.NOME}", "Todos os panoramas diários do Termômetro de Crise, por mês.",
               corpo, raiz="../", caminho="panorama/index.html", extra_css=CSS_PAGINAS + CSS))
    return caminhos + ["panorama/index.html"]


def paginas_edicoes(saida: Path, lista: list[tuple]) -> list[str]:
    """Lista de edições, 12 por página, com índice por mês."""
    from .site import pagina
    blocos = _paginas(lista, POR_PAGINA_EDICOES)
    total = len(blocos)

    def url(n: int) -> str:
        return "index.html" if n == 1 else f"pagina-{n}.html"
    meses = {}
    for i, bloco in enumerate(blocos, 1):
        for dia, _, _ in bloco:
            meses.setdefault(dia[:7], url(i))
    indice = " · ".join(f'<a href="{pg}#m{mes}">{MESES[int(mes[5:]) - 1]} de {mes[:4]}</a>' for mes, pg in meses.items())
    caminhos = []
    for i, bloco in enumerate(blocos, 1):
        partes, mes_atual = [], None
        for dia, dados, copy in bloco:
            if dia[:7] != mes_atual:
                mes_atual = dia[:7]
                partes.append(f'<h2 class="dia-titulo" id="m{mes_atual}">{MESES[int(mes_atual[5:]) - 1].capitalize()} de {mes_atual[:4]}</h2>')
            partes.append(f'<a href="{dia}.html" style="border-left:4px solid {dados["cor"]};padding-left:12px">'
                          f'<strong>{pd.Timestamp(dia):%d/%m/%Y}</strong> · índice {dados["valor"]}, {dados["nivel"]}'
                          f'<br><span class="suave">{html.escape(copy["pre_cabecalho"])}</span></a>')
        sufixo = "" if i == 1 else f" (página {i})"
        corpo = (f'<section class="edicao"><h1>Edições{sufixo}</h1><p class="suave">A análise de domingo, da mais nova para a '
                 f'mais antiga.' + (f' Por mês: {indice}' if len(meses) > 1 else "") + '</p>'
                 f'<div class="lista">{"".join(partes)}</div>{paginacao(i, total, url)}</section>')
        caminho = f"edicoes/{url(i)}"
        (saida / caminho).write_text(pagina(f"Edições{sufixo} · {config.NOME}", "Todas as edições do Termômetro de Crise.",
                                            corpo, raiz="../", caminho=caminho, extra_css=CSS))
        caminhos.append(caminho)
    return caminhos


def navegacao_edicao(dias_edicoes: list[str], dia: str) -> str:
    """Anterior / próxima dentro de cada edição."""
    i = dias_edicoes.index(dia)
    mais_nova = dias_edicoes[i - 1] if i > 0 else None
    mais_antiga = dias_edicoes[i + 1] if i + 1 < len(dias_edicoes) else None
    if not (mais_nova or mais_antiga):
        return '<nav class="navdia"><a class="contorno" href="index.html">Todas as edições</a></nav>'
    return ('<nav class="navdia" aria-label="Outras edições">'
            + (f'<a class="contorno" href="{mais_antiga}.html">Edição anterior</a>' if mais_antiga else "<span></span>")
            + '<a class="contorno" href="index.html">Todas as edições</a>'
            + (f'<a class="contorno" href="{mais_nova}.html">Próxima edição</a>' if mais_nova else "<span></span>") + "</nav>")


def gerar(saida: Path, pasta_diario: Path, m: dict) -> list[str]:
    lista_dias = dias(pasta_diario)
    membros = {r["nome"]: [p["nome"] for p in r.get("paises", [])] for r in m.get("regioes", [])}
    cores = {r["nome"]: r.get("cor") for r in m.get("regioes", [])}
    noticias = todas_noticias(lista_dias, membros, cores)
    return paginas_panorama(saida, lista_dias) + paginas_noticias(saida, noticias, m)


def existe_arquivo_noticias(saida: Path, slug: str) -> bool:
    return (saida / "noticias" / f"{slug}.html").exists()
