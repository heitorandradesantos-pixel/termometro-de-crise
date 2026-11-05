"""Páginas do Termômetro Mundial: uma por região, uma por país, o ranking e o panorama do WhatsApp.

Cada página responde, para um leigo, três perguntas:
1. Quanto está o termômetro e o que isso quer dizer?
2. Por quê? (os sinais em palavras simples e as notícias que mexem com eles, sempre com fonte)
3. Já foi pior? (o histórico desde o começo dos dados, com o nome das épocas mais tensas)
"""

import html
import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd

from . import config, correspondente as corr, mundo as motor, panorama
from .grafico import mes_curto
from .site import medidor_svg, pagina

C = config.CORES
FEMININAS = {"libra", "lira turca", "libra egípcia", "naira", "rupia"}
NOMES_SINAIS = {"bolsa": "Queda da bolsa", "volatilidade": "Sobe e desce", "moeda": "Moeda"}
NA_FRASE = {"bolsa": "a queda da bolsa", "volatilidade": "o sobe e desce da bolsa", "moeda": "a moeda"}
COR_DIRECAO = {"pressiona": "#EE8A3C", "alivia": "#7CC3E0", "incerto": C["suave"]}
TEXTO_DIRECAO = {"pressiona": "aumenta a tensão", "alivia": "alivia", "incerto": "efeito incerto"}
ARTIGOS = {"EUA": "os", "Canadá": "o", "México": "o", "Brasil": "o", "Argentina": "a", "Alemanha": "a", "França": "a",
           "Reino Unido": "o", "Turquia": "a", "Israel": "", "Egito": "o", "África do Sul": "a", "Nigéria": "a",
           "Japão": "o", "China": "a", "Hong Kong": "", "Índia": "a", "Coreia do Sul": "a", "Austrália": "a",
           "América do Norte": "a", "América Latina": "a", "Europa": "a", "Oriente Médio": "o", "África": "a",
           "Ásia e Pacífico": "a"}


def de(nome: str) -> str:
    """"do Brasil", "dos EUA", "de Israel"."""
    return {"o": "do", "a": "da", "os": "dos"}.get(ARTIGOS.get(nome, ""), "de") + " " + nome


def em(nome: str) -> str:
    return {"o": "no", "a": "na", "os": "nos"}.get(ARTIGOS.get(nome, ""), "em") + " " + nome


def com_artigo(nome: str) -> str:
    a = ARTIGOS.get(nome, "")
    return f"{a} {nome}" if a else nome


def sujeito(nome: str) -> tuple[str, str]:
    """("Os EUA", "estão"), ("Israel", "está")."""
    a = ARTIGOS.get(nome, "")
    return (f"{a.capitalize()} {nome}" if a else nome), ("estão" if a == "os" else "está")

CSS = """
.trilha{font-size:13px;color:var(--suave);margin:20px 0 0}.trilha a{color:var(--suave)}
.ficha{display:grid;grid-template-columns:minmax(0,300px) minmax(0,1fr);gap:28px;align-items:center;padding:16px 0 8px}
.ficha .global{padding:16px}.ficha h1{font-size:34px;margin:0 0 8px}.ficha .lead{font-size:18px;margin:0 0 10px}
.chip{font-size:13px;font-weight:600;color:#0E141B;border-radius:6px;padding:2px 8px;white-space:nowrap}
.grade{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.grade2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.caixa{background:var(--painel);border-radius:14px;padding:16px;color:var(--texto);text-decoration:none;display:block}
a.caixa:hover{outline:1px solid #34485A}
.caixa h3{margin:0 0 6px;font-size:18px}.caixa p{margin:6px 0 0;font-size:14px;color:var(--suave)}
.mini{display:grid;grid-template-columns:96px 1fr 28px;gap:8px;align-items:center;font-size:12px;color:var(--suave);margin-top:6px}
.mini .barra{min-width:0}
.sinal{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,220px);gap:18px;padding:16px 0;border-bottom:1px solid var(--linha)}
.sinal:last-child{border-bottom:0}.sinal h3{margin:0 0 4px;font-size:18px}.sinal p{margin:0}
.sinal .pct{font:700 28px/1 'Space Grotesk',sans-serif}.sinal .barra{margin:8px 0 6px}
.noticia{border-left:4px solid var(--linha);padding:2px 0 2px 14px;margin:18px 0}
.noticia h3{font-size:17px;margin:4px 0}.noticia p{margin:4px 0;font-size:15px}
.meta{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:12px;color:var(--suave)}
.tag{border:1px solid var(--linha);border-radius:6px;padding:1px 7px}
.fontes{font-size:13px}.fontes a{margin-right:10px}
.hist svg{width:100%;height:auto;display:block}.hist .cel{display:none}
.picos{margin:10px 0 0;padding-left:20px}.picos li{margin:4px 0}
.ranking td{padding:10px 8px}.ranking a{color:var(--texto);text-decoration:none;font-weight:600}
.ranking .r{color:var(--suave);font-size:13px}
.pano{white-space:pre-wrap;background:#0B1F17;border:1px solid #1F4D3A;border-radius:14px;padding:18px;font:15px/1.55 'IBM Plex Sans',sans-serif}
.zap{background:#25D366;color:#0E141B}
@media (max-width:760px){.ficha{grid-template-columns:1fr;gap:14px}.ficha h1{font-size:26px}.ficha .lead{font-size:16px}
.grade,.grade2{grid-template-columns:1fr}.sinal{grid-template-columns:1fr;gap:6px}.hist .desk{display:none}.hist .cel{display:block}
.ranking .esconde{display:none}}
"""


# ---------------------------------------------------------------- pedaços
def chip(nivel: str, cor: str) -> str:
    return f'<span class="chip" style="background:{cor}">{html.escape(nivel)}</span>'


def barra(pct) -> str:
    cor = config.nivel_de(pct or 0)["cor"]
    return f'<div class="barra"><i style="width:{pct or 0}%;background:{cor}"></i></div>'


def variacao(agora, antes, texto: str = "mês passado") -> str:
    if agora is None or antes is None:
        return ""
    d = agora - antes
    seta = "▲" if d > 0 else ("▼" if d < 0 else "=")
    return f"{seta} {abs(d) if d else ''} em relação ao {texto} ({antes})".replace("  ", " ")


def num(x: float, casas: int = 1) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def artigo(moeda: str) -> str:
    return "A" if moeda in FEMININAS else "O"


def data_curta(d: str) -> str:
    t = pd.to_datetime(d, errors="coerce")
    return "" if pd.isna(t) else f"{t:%d/%m}"


def grafico_svg(serie: pd.Series, picos: list[dict], largura: int, classe: str, nome: str) -> str:
    """Linha do termômetro ao longo do tempo sobre as faixas de cor, com os picos marcados."""
    s = serie.dropna()
    if len(s) < 3:
        return ""
    altura, ml, mr, mt, mb = 250, 30, 14, 14, 26
    w, h = largura - ml - mr, altura - mt - mb
    t0, t1 = s.index[0], s.index[-1]
    dias = max((t1 - t0).days, 1)

    def x(t):
        return ml + w * (t - t0).days / dias

    def y(v):
        return mt + h * (1 - v / 100)
    faixas = "".join(f'<rect x="{ml}" y="{y(n["max"] if n["max"] < 100 else 100):.1f}" width="{w}" '
                     f'height="{y(n["min"] - (1 if n["min"] else 0)) - y(n["max"]):.1f}" fill="{n["cor"]}" opacity=".13"/>'
                     for n in config.NIVEIS)
    grade = "".join(f'<text x="{ml - 6}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="{C["suave"]}">{v}</text>'
                    for v in (0, 20, 40, 60, 80, 100))
    anos = list(range(t0.year + 1, t1.year + 1))
    passo = next((p for p in (1, 2, 5, 10) if len(anos) / p <= (8 if largura > 500 else 4)), 20)
    marcos = "".join(f'<text x="{x(pd.Timestamp(a, 1, 1)):.1f}" y="{altura - 8}" text-anchor="middle" font-size="11" '
                     f'fill="{C["suave"]}">{a}</text>' for a in anos if a % passo == 0)
    trilha = " ".join(f"{'M' if i == 0 else 'L'}{x(t):.1f},{y(v):.1f}" for i, (t, v) in enumerate(s.items()))
    ult_t, ult_v = s.index[-1], s.iloc[-1]
    cor = config.nivel_de(ult_v)["cor"]
    marcas = ""
    for p in picos:
        t = pd.Timestamp(p["mes"] + "-01")
        if t < t0:
            continue
        px, py = x(t), y(p["valor"])
        tx = min(max(px, ml + 18), ml + w - 18)
        marcas += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="none" stroke="{C["texto"]}" stroke-width="1.5"/>'
                   f'<text x="{tx:.1f}" y="{max(py - 9, mt + 10):.1f}" text-anchor="middle" font-size="11" '
                   f'fill="{C["texto"]}">{p["valor"]} · {p["mes"][:4]}</text>')
    return (f'<svg class="{classe}" viewBox="0 0 {largura} {altura}" role="img" '
            f'aria-label="Histórico do termômetro {html.escape(de(nome))}">{faixas}{grade}{marcos}'
            f'<path d="{trilha}" fill="none" stroke="{C["texto"]}" stroke-width="1.6" stroke-linejoin="round"/>{marcas}'
            f'<circle cx="{x(ult_t):.1f}" cy="{y(ult_v):.1f}" r="6" fill="{cor}" stroke="{C["fundo"]}" stroke-width="2"/></svg>')


def historico_html(serie: pd.Series | None, picos: list[dict], nome: str, valor) -> str:
    if serie is None or serie.dropna().empty:
        return ""
    s = serie.dropna()
    ano = s.index[0].year
    figura = (f'<figure class="hist" style="margin:0">{grafico_svg(s, picos, 760, "desk", nome)}'
              f'{grafico_svg(s, picos, 380, "cel", nome)}</figure>')
    resposta = ""
    if valor is not None:
        antes = s.iloc[:-1]
        vezes = int((antes >= valor).sum())
        if vezes == 0:
            resposta = f"Não: a leitura de agora é a mais alta {de(nome)} desde {ano}, quando começam os dados."
        else:
            pct = 100 * vezes / len(antes)
            parte = "menos de 1%" if pct < 1 else f"{round(pct)}%"
            topo = antes.idxmax()
            resposta = (f"Sim. Desde {ano}, o termômetro {de(nome)} esteve em {valor} ou mais em {vezes} "
                        f"{'mês' if vezes == 1 else 'meses'} ({parte} do tempo). O ponto mais alto foi "
                        f"{round(float(antes.max()))}, em {mes_curto(topo.strftime('%Y-%m'))}.")
    itens = "".join(f'<li><strong>{mes_curto(p["mes"])}: {p["valor"]}</strong>'
                    f'{" · " + html.escape(p["epoca"]) if p.get("epoca") else ""}</li>' for p in picos)
    lista = f'<p style="margin:14px 0 0">Os momentos mais tensos:</p><ul class="picos">{itens}</ul>' if itens else ""
    return (f'<section class="cartao"><h2 style="margin-top:0">Já foi pior?</h2><p>{resposta}</p>{figura}{lista}'
            f'<p class="suave" style="font-size:13px">As faixas coloridas são os níveis: azul é calmaria, vermelho é crise.</p>'
            f'</section>')


def noticia_html(n: dict, raiz: str, mostrar_regiao: bool = True) -> str:
    direcao = n.get("direcao") or ""
    cor = COR_DIRECAO.get(direcao, C["linha"])
    meta = []
    if mostrar_regiao and n.get("regiao"):
        if n["regiao"] in motor.REGIOES:
            meta.append(f'<a class="tag" href="{raiz}regioes/{motor.slug(n["regiao"])}.html">{html.escape(n["regiao"])}</a>')
        else:
            meta.append(f'<span class="tag">{html.escape(n["regiao"])}</span>')
    if n.get("status"):
        meta.append(f'<span class="tag">{html.escape(n["status"])}</span>')
    if n.get("data"):
        meta.append(f"<span>{data_curta(n['data'])}</span>")
    if n.get("mexe_em"):
        meta.append(f'<span style="color:{cor}">Mexe em: {html.escape(", ".join(n["mexe_em"]))}'
                    f'{" · " + TEXTO_DIRECAO.get(direcao, "") if direcao else ""}</span>')
    fontes = "".join(f'<a href="{html.escape(f["url"])}" target="_blank" rel="noopener noreferrer">'
                     f'{html.escape(f.get("veiculo") or "fonte")}</a>' for f in n.get("fontes", [])[:3])
    canal = (f'<p class="suave" style="font-size:14px">Como chega ao Brasil: {html.escape(n["canal_brasil"])}</p>'
             if n.get("canal_brasil") else "")
    return (f'<article class="noticia" style="border-left-color:{cor}"><div class="meta">{"".join(meta)}</div>'
            f'<h3>{html.escape(n["titulo"])}</h3><p>{html.escape(n.get("resumo", ""))}</p>{canal}'
            f'<div class="fontes">Fonte: {fontes}</div></article>')


def noticias_secao(noticias: list[dict], titulo: str, raiz: str, mostrar_regiao: bool = True, vazio: str = "") -> str:
    if not noticias:
        return (f'<section class="cartao"><h2 style="margin-top:0">{titulo}</h2><p class="suave">{vazio}</p></section>'
                if vazio else "")
    itens = "".join(noticia_html(n, raiz, mostrar_regiao) for n in noticias)
    return (f'<section class="cartao"><h2 style="margin-top:0">{titulo}</h2>{itens}'
            f'<p class="suave" style="font-size:13px">Cada notícia traz o status do fato (confirmado, ameaça, negociação…) '
            f'e o link da fonte. Laranja: aumenta a tensão. Azul: alivia.</p></section>')


# ---------------------------------------------------------------- explicações a partir dos números
def sinais_explicados(p: dict) -> list[dict]:
    s, b = p.get("sinais", {}), p.get("brutos", {}) or {}
    desde = b.get("desde", {})
    moeda = p.get("moeda_nome") or motor.MOEDAS.get(p["nome"])
    bolsa = p.get("bolsa_nome") or motor.BOLSAS.get(p["nome"])
    saida = []
    if s.get("bolsa") is not None:
        q = b.get("bolsa_queda_pct")
        if q is None:
            frase = f"Mede quanto a bolsa{f' ({bolsa})' if bolsa else ''} caiu desde o ponto mais alto dos últimos 12 meses."
        elif q < 1:
            frase = f"A bolsa ({bolsa}) está no topo dos últimos 12 meses, ou muito perto dele."
        else:
            frase = f"A bolsa ({bolsa}) está {num(q)}% abaixo do ponto mais alto dos últimos 12 meses."
        saida.append({"chave": "bolsa", "pct": s["bolsa"], "frase": frase})
    if s.get("volatilidade") is not None:
        o = b.get("oscilacao_diaria_pct")
        frase = (f"Neste mês, a bolsa anda em média {num(o)}% por dia, para cima ou para baixo." if o is not None
                 else "Mede o quanto a bolsa oscila de um dia para o outro neste mês.")
        saida.append({"chave": "volatilidade", "pct": s["volatilidade"], "frase": frase})
    if s.get("moeda") is not None and moeda:
        v, a = b.get("moeda_variacao_3m_pct"), artigo(moeda)
        if v is None:
            frase = f"Mede quanto {a.lower()} {moeda} mudou contra o dólar em 3 meses, para qualquer lado."
        elif v > 0.5:
            frase = (f"{a} {moeda} perdeu {num(v)}% de valor contra o dólar em 3 meses: é preciso mais {moeda} "
                     f"para comprar 1 dólar.")
        elif v < -0.5:
            frase = (f"{a} {moeda} ganhou {num(abs(v))}% contra o dólar em 3 meses. Uma alta forte também conta, "
                     f"porque movimento brusco para qualquer lado é sinal de tensão.")
        else:
            frase = f"{a} {moeda} está praticamente estável contra o dólar nos últimos 3 meses."
        saida.append({"chave": "moeda", "pct": s["moeda"], "frase": frase})
    for item in saida:
        ano = desde.get(item["chave"])
        item["comparacao"] = (f"Mais tenso do que em {item['pct']}% dos meses desde {ano}" if ano
                              else f"Mais tenso do que em {item['pct']}% dos meses da história do país")
        item["nome"] = NOMES_SINAIS[item["chave"]]
    return saida


def por_que_automatico(p: dict) -> str:
    sinais = sorted(sinais_explicados(p), key=lambda x: -x["pct"])
    if not sinais:
        return ""
    tensos = [x for x in sinais if x["pct"] >= 61]
    nome = p["nome"]
    quem, verbo = sujeito(nome)
    if len(tensos) >= 2:
        nomes = [NA_FRASE[x["chave"]] for x in tensos]
        lista = ", ".join(nomes[:-1]) + " e " + nomes[-1]
        texto = f"{quem} {verbo} em {p['valor']} porque {len(tensos)} sinais estão tensos ao mesmo tempo: {lista}."
    elif tensos:
        texto = (f"O que mais pesa {em(nome)} é {NA_FRASE[tensos[0]['chave']]} (percentil {tensos[0]['pct']}); "
                 f"os outros sinais estão mais perto do normal.")
    else:
        texto = (f"Nenhum sinal {de(nome)} está fora do normal: o mais alto é {NA_FRASE[sinais[0]['chave']]}, "
                 f"no percentil {sinais[0]['pct']}.")
    if "moeda" not in {x["chave"] for x in sinais} and p["nome"] in ("EUA", "Hong Kong"):
        texto += " A moeda não entra na conta: " + ("o dólar é a própria referência." if p["nome"] == "EUA"
                                                     else "o dólar de Hong Kong é atrelado ao dólar americano.")
    if "bolsa" not in {x["chave"] for x in sinais}:
        texto += " Sem um índice de bolsa com histórico confiável, a leitura usa só a moeda."
    return texto


def mais_pesa(p: dict) -> str:
    sinais = sorted(sinais_explicados(p), key=lambda x: -x["pct"])
    return f"O que mais pesa: {NA_FRASE[sinais[0]['chave']]} ({sinais[0]['pct']})" if sinais else ""


# ---------------------------------------------------------------- dados
def _csv(caminho: Path) -> pd.DataFrame | None:
    return pd.read_csv(caminho, index_col=0, parse_dates=True) if caminho.exists() else None


def _json(caminho: Path) -> dict | None:
    return json.loads(caminho.read_text()) if caminho.exists() else None


def dias_do_diario(pasta: Path) -> list[Path]:
    if not pasta.exists():
        return []
    return sorted(p for p in pasta.iterdir() if p.is_dir() and len(p.name) == 10 and p.name[:2] == "20"
                  and (p / "mundo.json").exists())


def fonte(pasta_edicao: Path, pasta_diario: Path) -> dict:
    """Escolhe os dados mais novos: a atualização diária, se for mais recente que a edição semanal."""
    f = {"data": pasta_edicao.name, "mundo": _json(pasta_edicao / "mundo.json") or {},
         "paises": _csv(pasta_edicao / "mundo_paises.csv"), "regioes": _csv(pasta_edicao / "mundo_regioes.csv"),
         "correspondente": None, "panorama": None, "dossie": _json(pasta_edicao / "pesquisa.json") or {}}
    dias = dias_do_diario(pasta_diario)
    if dias and dias[-1].name >= pasta_edicao.name:
        d = dias[-1]
        hist = pasta_diario / "historico"
        f.update(data=d.name, mundo=_json(d / "mundo.json"),
                 paises=_csv(hist / "mundo_paises.csv"), regioes=_csv(hist / "mundo_regioes.csv"),
                 correspondente=_json(d / "correspondente.json"),
                 panorama=(d / "panorama.txt").read_text() if (d / "panorama.txt").exists() else None)
    membros = {r["nome"]: [p["nome"] for p in r.get("paises", [])] for r in f["mundo"].get("regioes", [])}
    if f["correspondente"] and corr.todas_as_noticias(f["correspondente"]):
        f["noticias"] = corr.todas_as_noticias(f["correspondente"])
    else:
        f["noticias"] = corr.noticias_do_dossie(f["dossie"], membros)
    # completa o que os arquivos antigos não tinham (endereço da página e picos do histórico)
    for r in f["mundo"].get("regioes", []):
        r.setdefault("slug", motor.slug(r["nome"]))
        if "picos" not in r and f["regioes"] is not None and r["nome"] in f["regioes"]:
            r["picos"] = motor.picos(f["regioes"][r["nome"]], r["nome"])
        for p in r.get("paises", []):
            p.setdefault("slug", motor.slug(p["nome"]))
            if "picos" not in p and f["paises"] is not None and p["nome"] in f["paises"]:
                p["picos"] = motor.picos(f["paises"][p["nome"]], p["nome"], r["nome"])
    return f


def explicacao(f: dict, regiao: str) -> dict:
    return ((f.get("correspondente") or {}).get("regioes") or {}).get(regiao) or {}


def noticias_da_regiao(f: dict, regiao: str) -> list[dict]:
    """As notícias da própria região (a lista geral da página inicial tira as repetidas entre regiões)."""
    if f.get("correspondente") and corr.todas_as_noticias(f["correspondente"]):
        return explicacao(f, regiao).get("noticias", [])
    return [n for n in f["noticias"] if n.get("regiao") == regiao]


# ---------------------------------------------------------------- páginas
def ficha(nome: str, valor, nivel: str, cor: str, lead: str, extra: str, rotulo: str) -> str:
    return (f'<section class="ficha"><div class="global"><span class="rotulo">{rotulo}</span>{medidor_svg(valor, cor)}'
            f'<div class="valor">{valor}</div><div class="nivel" style="color:{cor}">{nivel.upper()}</div></div>'
            f'<div><h1>{html.escape(nome)}</h1><p class="lead">{lead}</p>{extra}</div></section>')


def pagina_regiao(f: dict, r: dict) -> str:
    ex = explicacao(f, r["nome"])
    paises = [p for p in r["paises"] if p.get("valor") is not None]
    ordenados = sorted(paises, key=lambda p: -p["valor"])
    if ex.get("resumo"):
        por_que = html.escape(ex["resumo"])
    else:
        lista = ", ".join(f"{p['nome']} ({p['valor']})" for p in ordenados)
        por_que = (f"O termômetro da região é a média dos países: {lista}. "
                   f"Quem mais puxa para cima é {com_artigo(ordenados[0]['nome'])}." if ordenados else "")
    nivel = config.nivel_de(r["valor"])
    lead = f"{r['valor']} de 100: {nivel['leitura'].lower()}."
    extra = (f'<p class="suave" style="margin:0 0 10px">{variacao(r["valor"], r.get("mes_anterior"))}</p>'
             f'<p><strong>Por que está assim.</strong> {por_que}</p>')
    cartoes = []
    for p in ordenados:
        texto = (ex.get("paises") or {}).get(p["nome"]) or por_que_automatico(p)
        curto = texto if len(texto) <= 170 else texto[:170].rsplit(" ", 1)[0] + "…"
        minis = "".join(f'<div class="mini"><span>{s["nome"]}</span>{barra(s["pct"])}<span>{s["pct"]}</span></div>'
                        for s in sinais_explicados(p))
        cartoes.append(f'<a class="caixa" href="../paises/{p["slug"]}.html" style="border-top:5px solid {p["cor"]}">'
                       f'<h3>{html.escape(p["nome"])} <span style="float:right">{p["valor"]} {chip(p["nivel"], p["cor"])}</span></h3>'
                       f'{minis}<p>{html.escape(curto)}</p><p style="color:#7CC3E0">Entender {html.escape(p["nome"])} →</p></a>')
    noticias = noticias_da_regiao(f, r["nome"])
    serie = f["regioes"][r["nome"]] if f["regioes"] is not None and r["nome"] in f["regioes"] else None
    corpo = (f'<p class="trilha"><a href="../index.html">Início</a> › {html.escape(r["nome"])}</p>'
             + ficha(r["nome"], r["valor"], r["nivel"], r["cor"], lead, extra, "TERMÔMETRO DA REGIÃO")
             + f'<section><h2>Os países</h2><div class="grade">{"".join(cartoes)}</div></section>'
             + noticias_secao(noticias, "Notícias que mexem com o termômetro", "../", mostrar_regiao=False,
                              vazio="Nenhuma notícia conferida com fonte nos últimos dias para esta região.")
             + historico_html(serie, r.get("picos", []), r["nome"], r["valor"])
             + observar_html(ex.get("observar", []))
             + metodo_curto("../"))
    return pagina(f"{r['nome']}: termômetro em {r['valor']} ({r['nivel']}) · {config.NOME}",
                  f"Por que o termômetro de crise {de(r['nome'])} está em {r['valor']} de 100, país por país, com as notícias que mexem com ele.",
                  corpo, raiz="../", caminho=f"regioes/{r['slug']}.html", extra_css=CSS)


def pagina_pais(f: dict, r: dict, p: dict) -> str:
    ex = explicacao(f, r["nome"])
    nivel = config.nivel_de(p["valor"])
    lead = f"{p['valor']} de 100: {nivel['leitura'].lower()}."
    extra = (f'<p class="suave" style="margin:0 0 10px">{variacao(p["valor"], p.get("mes_anterior"))}</p>'
             f'<p style="margin:0">{html.escape(mais_pesa(p))}. Região: '
             f'<a href="../regioes/{r["slug"]}.html">{html.escape(r["nome"])} ({r["valor"]})</a>.</p>')
    linhas = "".join(f'<div class="sinal"><div><h3>{s["nome"]}</h3><p>{html.escape(s["frase"])}</p></div>'
                     f'<div><span class="pct" style="color:{config.nivel_de(s["pct"])["cor"]}">{s["pct"]}</span>'
                     f'{barra(s["pct"])}<span class="suave" style="font-size:13px">{s["comparacao"]}</span></div></div>'
                     for s in sinais_explicados(p))
    contexto = (ex.get("paises") or {}).get(p["nome"])
    bloco_contexto = (f'<section class="cartao"><h2 style="margin-top:0">O contexto</h2><p>{html.escape(contexto)}</p>'
                      f'<p class="suave" style="font-size:13px">Escrito pelo agente Correspondente a partir de notícias com fonte, '
                      f'conferido automaticamente. As notícias estão logo abaixo.</p></section>') if contexto else ""
    todas = noticias_da_regiao(f, r["nome"])
    noticias = [n for n in todas if p["nome"] in n.get("paises", [])]
    da_regiao = [n for n in todas if n not in noticias][:3]
    serie = f["paises"][p["nome"]] if f["paises"] is not None and p["nome"] in f["paises"] else None
    vizinhos = " ".join(f'<a class="tag" href="{v["slug"]}.html">{html.escape(v["nome"])} {v["valor"]}</a>'
                        for v in r["paises"] if v["nome"] != p["nome"] and v.get("valor") is not None)
    corpo = (f'<p class="trilha"><a href="../index.html">Início</a> › <a href="../regioes/{r["slug"]}.html">'
             f'{html.escape(r["nome"])}</a> › {html.escape(p["nome"])}</p>'
             + ficha(p["nome"], p["valor"], p["nivel"], p["cor"], lead, extra, "TERMÔMETRO DO PAÍS")
             + f'<section class="cartao"><h2 style="margin-top:0">Por que o termômetro está em {p["valor"]}</h2>'
               f'<p>{html.escape(por_que_automatico(p))} O termômetro é a média destes sinais:</p>{linhas}</section>'
             + bloco_contexto
             + noticias_secao(noticias, f"Notícias que mexem com {html.escape(ARTIGOS.get(p['nome'], '') + ' ' + p['nome']).strip()}", "../", mostrar_regiao=False)
             + noticias_secao(da_regiao, f"Na região: {html.escape(r['nome'])}", "../", mostrar_regiao=False)
             + historico_html(serie, p.get("picos", []), p["nome"], p["valor"])
             + (f'<section><h2>Outros países da região</h2><p class="meta" style="font-size:14px">{vizinhos}</p></section>'
                if vizinhos else "")
             + metodo_curto("../"))
    return pagina(f"{p['nome']}: termômetro de crise em {p['valor']} ({p['nivel']}) · {config.NOME}",
                  f"Por que o termômetro de crise {de(p['nome'])} está em {p['valor']} de 100: bolsa, sobe e desce, moeda e as notícias.",
                  corpo, raiz="../", caminho=f"paises/{p['slug']}.html", extra_css=CSS)


def observar_html(itens: list[dict]) -> str:
    if not itens:
        return ""
    def link(o: dict) -> str:
        if not o.get("url"):
            return ""
        return f' (<a href="{html.escape(o["url"])}" target="_blank" rel="noopener noreferrer">fonte</a>)'
    linhas = "".join(f'<li><strong>{data_curta(o["data"])}</strong> · {html.escape(o["evento"])}: '
                     f'{html.escape(o["por_que_importa"])}{link(o)}</li>' for o in itens)
    return f'<section class="cartao"><h2 style="margin-top:0">O que observar nos próximos dias</h2><ul>{linhas}</ul></section>'


def metodo_curto(raiz: str) -> str:
    return (f'<p class="suave" style="font-size:13px;margin-top:28px">Como funciona: cada sinal é comparado com a '
            f'história do próprio país (percentil 90 = mais tenso do que em 90% dos meses). O termômetro do país é a '
            f'média dos sinais; o da região, a média dos países. <a href="{raiz}metodologia.html#mundo">Metodologia completa</a>.</p>')


def pagina_ranking(f: dict) -> str:
    linhas = []
    todos = [(p, r) for r in f["mundo"].get("regioes", []) for p in r.get("paises", []) if p.get("valor") is not None]
    for i, (p, r) in enumerate(sorted(todos, key=lambda x: -x[0]["valor"]), 1):
        linhas.append(f'<tr><td class="r">{i}</td><td><a href="paises/{p["slug"]}.html">{html.escape(p["nome"])}</a>'
                      f'<br><a class="r" href="regioes/{r["slug"]}.html" style="font-weight:400">{html.escape(r["nome"])}</a></td>'
                      f'<td class="esconde" style="width:30%">{barra(p["valor"])}</td>'
                      f'<td class="num">{p["valor"]}</td><td>{chip(p["nivel"], p["cor"])}</td>'
                      f'<td class="r esconde">{variacao(p["valor"], p.get("mes_anterior"))}</td></tr>')
    corpo = (f'<section class="edicao" style="max-width:none"><h1>Todos os países, do mais tenso ao mais calmo</h1>'
             f'<p class="suave">Toque em um país para entender o porquê. Atualizado em {pd.Timestamp(f["data"]):%d/%m/%Y}.</p>'
             f'<table class="ranking"><tr><th>#</th><th>País</th><th class="esconde">Estresse</th>'
             f'<th style="text-align:right">Agora</th><th>Nível</th><th class="esconde">Mês passado</th></tr>'
             f'{"".join(linhas)}</table>{metodo_curto("")}</section>')
    return pagina(f"Ranking mundial do termômetro de crise · {config.NOME}",
                  "Os países do Termômetro de Crise, do mais tenso ao mais calmo, com o porquê de cada leitura.",
                  corpo, caminho="mundo.html", extra_css=CSS)


def whatsapp_html(texto: str) -> str:
    """Mostra o texto como ele aparece no WhatsApp (*negrito* e _itálico_)."""
    import re
    t = html.escape(texto)
    t = re.sub(r"\*([^*\n]+)\*", r"<strong>\1</strong>", t)
    return re.sub(r"(?<![\w/])_([^_\n]+)_(?!\w)", r"<em>\1</em>", t)


def pagina_panorama(f: dict) -> str:
    texto = f.get("panorama") or panorama.montar(f["mundo"], f.get("correspondente"), None, f["data"],
                                                 noticias=f.get("noticias"))
    dados = json.dumps(texto, ensure_ascii=False).replace("</", "<\\/")
    canal = (f'<a class="botao zap" href="{html.escape(config.WHATSAPP_URL)}" target="_blank" rel="noopener">'
             f'Entrar no canal do WhatsApp</a>' if config.WHATSAPP_URL else "")
    corpo = f"""<section class="edicao"><h1>Panorama do fim de tarde</h1>
<p class="suave">Todo dia útil, no fim da tarde (a partir das 18h30), o resumo do termômetro do mundo, das regiões e do Brasil,
com as notícias que mexeram com ele. Atualizado em {pd.Timestamp(f["data"]):%d/%m/%Y}.</p>
<div class="acoes" style="margin:16px 0">{canal}
<button class="botao" id="copiar" type="button">Copiar texto</button>
<a href="https://wa.me/?text={quote(texto)}" target="_blank" rel="noopener">Enviar pelo WhatsApp</a></div>
<div class="pano">{whatsapp_html(texto)}</div>
<script type="application/json" id="texto">{dados}</script>
<script>document.getElementById('copiar').onclick=function(){{var t=JSON.parse(document.getElementById('texto').textContent),b=this;
navigator.clipboard.writeText(t).then(function(){{b.textContent='Copiado!'}},function(){{b.textContent='Selecione e copie o texto abaixo'}})}};</script>
</section>"""
    return pagina(f"Panorama do fim de tarde · {config.NOME}",
                  "O resumo diário do termômetro de crise do mundo, das regiões e do Brasil.",
                  corpo, caminho="panorama.html", extra_css=CSS)


def gerar(saida: Path, f: dict) -> list[str]:
    """Grava as páginas e devolve os caminhos (para o mapa do site)."""
    caminhos = ["mundo.html", "panorama.html"]
    (saida / "regioes").mkdir(exist_ok=True)
    (saida / "paises").mkdir(exist_ok=True)
    for r in f["mundo"].get("regioes", []):
        if r.get("valor") is None:
            continue
        (saida / "regioes" / f"{r['slug']}.html").write_text(pagina_regiao(f, r))
        caminhos.append(f"regioes/{r['slug']}.html")
        for p in r.get("paises", []):
            if p.get("valor") is None:
                continue
            (saida / "paises" / f"{p['slug']}.html").write_text(pagina_pais(f, r, p))
            caminhos.append(f"paises/{p['slug']}.html")
    (saida / "mundo.html").write_text(pagina_ranking(f))
    (saida / "panorama.html").write_text(pagina_panorama(f))
    return caminhos
