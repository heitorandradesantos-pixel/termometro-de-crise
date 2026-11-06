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

import pandas as pd

from . import config, correspondente as corr

POR_PAGINA_NOTICIAS = 20
PLANTAO_LINK = ('<p class="cartao" style="padding:12px 16px"><strong>Plantão:</strong> os assuntos de dinheiro mais '
                'procurados do dia, com o que se sabe e a fonte de cada fato. <a href="plantao/index.html">Abrir o Plantão</a></p>')
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
.trilha{font-size:13px;color:var(--suave);margin:20px 0 0}.trilha a{color:var(--suave);display:inline-block;padding:4px 0}
.navdia{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin:20px 0}
.faixa-arquivo{background:#2A2414;border:1px solid #6B5A2A;border-radius:10px;padding:10px 14px;font-size:14px;margin:16px 0 0}
.faixa-arquivo a{color:#F2D78A;display:inline-block;padding:4px 0}
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


def faixa_arquivo(data: str, tipo: str, raiz: str) -> str:
    """Aviso fixo no topo de toda página arquivada: um nível antigo não pode parecer alarme de hoje."""
    return (f'<p class="faixa-arquivo">{tipo} de {pd.Timestamp(data):%d/%m/%Y}. Não reflete o mercado de hoje. '
            f'<a href="{raiz}index.html">Ver a leitura de hoje</a></p>')


def resumo_mes(itens: list[dict], nome: str, mes: str) -> str:
    """Texto próprio de cada arquivo mensal (exigência do SEO: nada de página que só repete manchetes)."""
    from collections import Counter
    t = pd.Timestamp(mes + "-01")
    sinais = Counter(s for n in itens for s in n.get("mexe_em", []))
    pressiona = sum(1 for n in itens if n.get("direcao") == "pressiona")
    alivia = sum(1 for n in itens if n.get("direcao") == "alivia")
    principais = ", ".join(f"{s} ({q})" for s, q in sinais.most_common(3))
    return (f"Em {MESES[t.month - 1]} de {t.year}, {len(itens)} notícias conferidas mexeram com o termômetro {nome}. "
            + (f"Os sinais mais citados foram {principais}. " if principais else "")
            + f"{pressiona} aumentaram a tensão e {alivia} aliviaram.")


def paginas_noticias(saida: Path, noticias: list[dict], m: dict, hoje: str) -> tuple[list[str], list[str]]:
    """Notícias do mês em curso por região e país, e arquivos mensais estáveis (mês fechado, 5 ou mais itens) para o
    mundo e o Brasil, como decidiu o time. Devolve (todas as páginas, as que entram no mapa do site)."""
    from .site import pagina
    from .paginas import CSS as CSS_PAGINAS, de
    (saida / "noticias").mkdir(exist_ok=True)
    caminhos, sitemap = [], []
    mes_atual = hoje[:7]

    def escrever(arquivo_html: str, titulo: str, descricao: str, corpo_lista: str, volta: str, faixa: str = "") -> str:
        corpo = (f'<section class="edicao" style="max-width:820px">{faixa}<p class="trilha">{volta}</p>'
                 f'<h1>{html.escape(titulo)}</h1>{PLANTAO_LINK if arquivo_html == "index.html" else ""}'
                 f'{corpo_lista}</section>')
        caminho = f"noticias/{arquivo_html}"
        (saida / caminho).write_text(pagina(f"{titulo} · {config.NOME}", descricao, corpo, raiz="../", caminho=caminho,
                                            extra_css=CSS_PAGINAS + CSS, sem_faixa=True))
        caminhos.append(caminho)
        return caminho

    def grupo(slug: str, nome: str, itens: list[dict], mostrar_regiao: bool, volta: str, mensal: bool):
        do_mes = [n for n in itens if n.get("data", "")[:7] == mes_atual]
        antigos = sorted({n.get("data", "")[:7] for n in itens if n.get("data", "")[:7] < mes_atual}, reverse=True)
        meses_validos = [ms for ms in antigos if mensal and sum(1 for n in itens if n.get("data", "")[:7] == ms) >= 5]
        links_meses = " · ".join(f'<a href="{slug}-{ms}.html">{MESES[int(ms[5:]) - 1]} de {ms[:4]}</a>' for ms in meses_validos)
        blocos = _paginas(do_mes, POR_PAGINA_NOTICIAS) if do_mes else [[]]
        total = len(blocos)

        def url(n: int) -> str:
            return f"{slug}.html" if n == 1 else f"{slug}-pagina-{n}.html"
        t = pd.Timestamp(mes_atual + "-01")
        for i, bloco in enumerate(blocos, 1):
            if not bloco and not links_meses:
                return
            cabeca = (f'<p class="suave">Notícias de {MESES[t.month - 1]} de {t.year}, das mais novas para as mais antigas, '
                      f'cada uma com fonte, status do fato e o sinal que ela mexe.'
                      + (f" Página {i} de {total}." if total > 1 else "") + "</p>")
            meses_html = f'<p class="suave">Meses anteriores: {links_meses}</p>' if links_meses else ""
            caminho = escrever(url(i), f"Notícias {nome}" + (f" (página {i})" if i > 1 else ""),
                               f"O que mexeu com o termômetro {nome} em {MESES[t.month - 1]} de {t.year}.",
                               cabeca + _lista_por_dia(bloco, "../", mostrar_regiao) + paginacao(i, total, url) + meses_html,
                               volta)
            if i == 1 and mensal:
                sitemap.append(caminho)
        for ms in meses_validos:  # arquivo mensal estável: o endereço nunca muda de conteúdo
            do_ms = [n for n in itens if n.get("data", "")[:7] == ms]
            tm = pd.Timestamp(ms + "-01")
            ultimo_dia = (tm + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
            caminho = escrever(f"{slug}-{ms}.html", f"Notícias {nome}: {MESES[tm.month - 1]} de {tm.year}",
                               resumo_mes(do_ms, nome, ms),
                               f'<p>{html.escape(resumo_mes(do_ms, nome, ms))}</p>' + _lista_por_dia(do_ms, "../", mostrar_regiao),
                               volta + f' › {MESES[tm.month - 1]} de {tm.year}', faixa_arquivo(ultimo_dia, "Arquivo de notícias", "../"))
            sitemap.append(caminho)

    regioes = [r for r in m.get("regioes", []) if r.get("valor") is not None]
    filtros = " · ".join(f'<a href="{r["slug"]}.html">{html.escape(r["nome"])}</a>' for r in regioes
                         if any(n.get("regiao") == r["nome"] for n in noticias))
    if noticias:
        grupo("index", "do mundo", noticias, True,
              '<a href="../index.html">Início</a> › Notícias' + (f" · Por região: {filtros}" if filtros else ""), mensal=True)
    for r in regioes:
        da_regiao = [n for n in noticias if n.get("regiao") == r["nome"]]
        if da_regiao:
            grupo(r["slug"], de(r["nome"]), da_regiao, False,
                  f'<a href="../index.html">Início</a> › <a href="index.html">Notícias</a> › '
                  f'<a href="../regioes/{r["slug"]}.html">{html.escape(r["nome"])}</a>', mensal=False)
        for p in r.get("paises", []):
            do_pais = [n for n in da_regiao if p["nome"] in n.get("paises", [])]
            if do_pais:
                grupo(p["slug"], de(p["nome"]), do_pais, False,
                      f'<a href="../index.html">Início</a> › <a href="index.html">Notícias</a> › '
                      f'<a href="../paises/{p["slug"]}.html">{html.escape(p["nome"])}</a>', mensal=p["nome"] == "Brasil")
    return caminhos, sitemap


def _valor_mundo(d: dict):
    return (d["mundo"].get("mundo") or {}).get("valor")


def resumo_dia(d: dict, anterior: dict | None) -> str:
    """Texto próprio de cada panorama (3 a 5 frases), feito com os números do dia."""
    mundo = d["mundo"].get("mundo") or {}
    regioes = sorted((r for r in d["mundo"].get("regioes", []) if r.get("valor") is not None), key=lambda r: -r["valor"])
    b = d["mundo"].get("brasil") or {}
    frases = [f"Em {data_longa(d['data'])}, o termômetro do mundo marcou {mundo.get('valor', '–')} ({mundo.get('nivel', '')})"]
    if anterior and _valor_mundo(anterior) is not None and mundo.get("valor") is not None:
        dif = mundo["valor"] - _valor_mundo(anterior)
        frases[0] += (", igual ao panorama anterior." if dif == 0 else
                      f", {abs(dif)} {'ponto' if abs(dif) == 1 else 'pontos'} {'acima' if dif > 0 else 'abaixo'} do panorama anterior.")
    else:
        frases[0] += "."
    if regioes:
        frases.append(f"A região mais tensa foi {regioes[0]['nome']} ({regioes[0]['valor']}), e a mais calma, "
                      f"{regioes[-1]['nome']} ({regioes[-1]['valor']}).")
    if b.get("valor") is not None:
        frases.append(f"O Brasil ficou em {b['valor']} ({b['nivel']}).")
    return " ".join(frases)


def comparar_dia(lista: list[dict], i: int, regioes_csv) -> list[tuple[str, int]]:
    """Ontem, 1 semana, mês passado e 1 ano, para o painel de cada panorama."""
    d, hoje = lista[i], pd.Timestamp(lista[i]["data"])
    saida = []
    if i + 1 < len(lista) and _valor_mundo(lista[i + 1]) is not None:
        saida.append(("Panorama anterior", _valor_mundo(lista[i + 1])))
    semana = next((x for x in lista[i + 1:] if (hoje - pd.Timestamp(x["data"])).days >= 7 and _valor_mundo(x) is not None), None)
    if semana:
        saida.append(("1 semana", _valor_mundo(semana)))
    mes = (d["mundo"].get("mundo") or {}).get("mes_anterior")
    if mes is not None:
        saida.append(("Mês passado", mes))
    if regioes_csv is not None and "Mundo (média das regiões)" in regioes_csv:
        serie = regioes_csv["Mundo (média das regiões)"].dropna()
        serie = serie[serie.index <= hoje]
        if len(serie) > 12:
            saida.append(("1 ano atrás", round(float(serie.iloc[-13]))))
    return saida


def paginas_panorama(saida: Path, lista_dias: list[dict], noticias: list[dict], regioes_csv=None) -> list[str]:
    from .site import bloco_celular, pagina
    from .paginas import CSS as CSS_PAGINAS, comparacoes_html, noticia_html
    com_texto = [d for d in lista_dias if d["panorama"] and pd.Timestamp(d["data"]).weekday() < 5]  # só dia útil
    if not com_texto:
        return []
    (saida / "panorama").mkdir(exist_ok=True)
    caminhos = []
    for i, d in enumerate(com_texto):
        mais_novo = com_texto[i - 1]["data"] if i > 0 else None
        mais_antigo = com_texto[i + 1]["data"] if i + 1 < len(com_texto) else None
        anterior = com_texto[i + 1] if i + 1 < len(com_texto) else None
        m = (d["mundo"].get("mundo") or {})
        nav = (f'<nav class="navdia" aria-label="Outros dias">'
               + (f'<a class="contorno" href="{mais_antigo}.html">Dia anterior</a>' if mais_antigo else "<span></span>")
               + '<a class="contorno" href="index.html">Todos os dias</a>'
               + (f'<a class="contorno" href="{mais_novo}.html">Próximo dia</a>' if mais_novo else "<span></span>") + "</nav>")
        do_dia = [n for n in noticias if n.get("data") == d["data"]][:3]
        leia = (f'<section style="margin-top:24px"><h2>Leia também</h2><p class="suave" style="font-size:13px">As notícias '
                f'mais relevantes deste dia, com fonte.</p>{"".join(noticia_html(n, "../", True) for n in do_dia)}</section>'
                if do_dia else "")
        faixa = faixa_arquivo(d["data"], "Panorama", "../") if i > 0 else ""
        corpo = (f'<section class="edicao">{faixa}<p class="trilha"><a href="../index.html">Início</a> › '
                 f'<a href="index.html">Panoramas</a> › {pd.Timestamp(d["data"]):%d/%m/%Y}</p>'
                 f'<h1>Panorama de {data_longa(d["data"])}</h1>'
                 f'<p>{html.escape(resumo_dia(d, anterior))}</p>'
                 f'{comparacoes_html(comparar_dia(com_texto, i, regioes_csv))}'
                 f'<p class="suave" style="margin-top:20px">O panorama completo deste dia, com as regiões e as '
                 f'notícias, foi para o grupo do WhatsApp do Termômetro de Crise.</p>'
                 f'{leia}{bloco_celular("../")}{nav}</section>')
        caminho = f"panorama/{d['data']}.html"
        titulo = f"Panorama {pd.Timestamp(d['data']):%d/%m/%Y}: mundo em {m.get('valor', '–')} ({m.get('nivel', '')})"
        (saida / caminho).write_text(pagina(titulo, resumo_dia(d, anterior), corpo, raiz="../", caminho=caminho,
                                            extra_css=CSS_PAGINAS + CSS, sem_faixa=True))
        caminhos.append(caminho)
    # hub: calendário com 10 dias ou mais; antes disso, lista simples (calendário vazio parece abandonado)
    if len(com_texto) >= 10:
        meses = {}
        for d in com_texto:
            meses.setdefault(d["data"][:7], []).append(d)
        blocos = []
        for mes, dias_mes in meses.items():
            t = pd.Timestamp(mes + "-01")
            quadros = "".join(
                f'<a href="{d["data"]}.html" style="border-top-color:{_cor(_valor_mundo(d))}">'
                f'<small>{DIAS_SEMANA[pd.Timestamp(d["data"]).weekday()]} {pd.Timestamp(d["data"]).day}</small>'
                f'<strong>{_valor_mundo(d) if _valor_mundo(d) is not None else "–"}</strong>'
                f'<small>{(d["mundo"].get("mundo") or {}).get("nivel", "")}</small></a>'
                for d in sorted(dias_mes, key=lambda x: x["data"]))
            blocos.append(f'<h2 class="dia-titulo">{MESES[t.month - 1].capitalize()} de {t.year}</h2>'
                          f'<div class="calendario">{quadros}</div>')
        conteudo = "".join(blocos)
    else:
        conteudo = '<div class="lista">' + "".join(
            f'<a href="{d["data"]}.html" style="border-left:4px solid {_cor(_valor_mundo(d))};padding-left:12px">'
            f'<strong>{data_longa(d["data"])}</strong> · mundo em {_valor_mundo(d) if _valor_mundo(d) is not None else "–"} '
            f'({(d["mundo"].get("mundo") or {}).get("nivel", "")})</a>' for d in com_texto) + "</div>"
    corpo = (f'<section class="edicao" style="max-width:820px"><p class="trilha"><a href="../index.html">Início</a> › Panoramas</p>'
             f'<h1>Todos os panoramas do fim de tarde</h1><p class="suave">Cada dia útil, o termômetro do mundo, das regiões e do '
             f'Brasil, com as notícias que mexeram com ele. A cor é o nível do mundo naquele dia, que também vem escrito.</p>'
             f'{conteudo}</section>')
    (saida / "panorama" / "index.html").write_text(
        pagina(f"Arquivo dos panoramas · {config.NOME}", "Todos os panoramas diários do Termômetro de Crise, por mês.",
               corpo, raiz="../", caminho="panorama/index.html", extra_css=CSS_PAGINAS + CSS, sem_faixa=True))
    return caminhos + ["panorama/index.html"]


def paginas_edicoes(saida: Path, lista: list[tuple]) -> list[str]:
    """As 12 edições mais recentes em /edicoes e um índice por ano (/edicoes/AAAA.html), como decidiu o time."""
    from .site import pagina

    def linhas(itens: list[tuple]) -> str:
        partes, mes_atual = [], None
        for dia, dados, copy in itens:
            if dia[:7] != mes_atual:
                mes_atual = dia[:7]
                partes.append(f'<h2 class="dia-titulo">{MESES[int(mes_atual[5:]) - 1].capitalize()} de {mes_atual[:4]}</h2>')
            partes.append(f'<a href="{dia}.html" style="border-left:4px solid {dados["cor"]};padding-left:12px">'
                          f'<strong>{pd.Timestamp(dia):%d/%m/%Y}</strong> · índice {dados["valor"]}, {dados["nivel"]}'
                          f'<br><span class="suave">{html.escape(copy["pre_cabecalho"])}</span></a>')
        return f'<div class="lista">{"".join(partes)}</div>'
    anos = sorted({dia[:4] for dia, _, _ in lista}, reverse=True)
    links_anos = " · ".join(f'<a href="{a}.html">{a}</a>' for a in anos)
    corpo = (f'<section class="edicao"><h1>Edições</h1><p class="suave">A análise de domingo, das mais recentes para as mais '
             f'antigas. Todas as edições por ano: {links_anos}</p>{linhas(lista[:POR_PAGINA_EDICOES])}</section>')
    (saida / "edicoes" / "index.html").write_text(pagina(f"Edições · {config.NOME}", "Todas as edições do Termômetro de Crise.",
                                                         corpo, raiz="../", caminho="edicoes/index.html", extra_css=CSS))
    caminhos = ["edicoes/index.html"]
    for a in anos:
        do_ano = [x for x in lista if x[0][:4] == a]
        corpo = (f'<section class="edicao"><p class="trilha"><a href="index.html">Edições</a> › {a}</p><h1>Edições de {a}</h1>'
                 f'<p class="suave">{len(do_ano)} edições, por mês.</p>{linhas(do_ano)}</section>')
        (saida / "edicoes" / f"{a}.html").write_text(pagina(f"Edições de {a} · {config.NOME}", f"As edições do Termômetro de Crise em {a}.",
                                                            corpo, raiz="../", caminho=f"edicoes/{a}.html", extra_css=CSS))
        caminhos.append(f"edicoes/{a}.html")
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


def gerar(saida: Path, pasta_diario: Path, m: dict, hoje: str, regioes_csv=None) -> tuple[list[str], list[str]]:
    """Gera o arquivo. Devolve (todas as páginas, as que entram no mapa do site)."""
    lista_dias = dias(pasta_diario)
    membros = {r["nome"]: [p["nome"] for p in r.get("paises", [])] for r in m.get("regioes", [])}
    cores = {r["nome"]: r.get("cor") for r in m.get("regioes", [])}
    noticias = todas_noticias(lista_dias, membros, cores)
    panoramas = paginas_panorama(saida, lista_dias, noticias, regioes_csv)
    todas, sitemap = paginas_noticias(saida, noticias, m, hoje)
    return panoramas + todas, panoramas + sitemap


def existe_arquivo_noticias(saida: Path, slug: str) -> bool:
    return (saida / "noticias" / f"{slug}.html").exists()
