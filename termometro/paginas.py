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
from .site import bloco_celular, medidor_svg, pagina

C = config.CORES
FEMININAS = {"libra", "libra esterlina", "lira turca", "libra egípcia", "naira", "rupia", "rupia indonésia"}
NOMES_SINAIS = {"bolsa": "Queda da bolsa", "volatilidade": "Sobe e desce", "moeda": "Moeda"}
NA_FRASE = {"bolsa": "a queda da bolsa", "volatilidade": "o sobe e desce da bolsa", "moeda": "a moeda"}
COR_DIRECAO = {"pressiona": "#EE8A3C", "alivia": "#7CC3E0", "incerto": C["suave"]}
TEXTO_DIRECAO = {"pressiona": "aumenta a tensão", "alivia": "alivia", "incerto": "efeito incerto"}
ARTIGOS = {"EUA": "os", "Canadá": "o", "México": "o", "Brasil": "o", "Argentina": "a", "Alemanha": "a", "França": "a",
           "Reino Unido": "o", "Turquia": "a", "Israel": "", "Egito": "o", "África do Sul": "a", "Nigéria": "a",
           "Japão": "o", "China": "a", "Hong Kong": "", "Índia": "a", "Coreia do Sul": "a", "Austrália": "a",
           "América do Norte": "a", "América Latina": "a", "Europa": "a", "Oriente Médio": "o", "África": "a",
           "Ásia e Pacífico": "a", "Chile": "o", "Colômbia": "a", "Peru": "o", "Paraguai": "o", "Uruguai": "o",
           "Itália": "a", "Espanha": "a", "Portugal": "", "Suíça": "a", "Rússia": "a", "Arábia Saudita": "a",
           "Quênia": "o", "Marrocos": "o", "Indonésia": "a", "Taiwan": "", "Singapura": ""}


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
.trilha{font-size:13px;color:var(--suave);margin:20px 0 0}.trilha a{color:var(--suave);display:inline-block;padding:4px 0}
.ficha{display:grid;grid-template-columns:minmax(0,300px) minmax(0,1fr);gap:28px;align-items:center;padding:16px 0 8px}
.ficha .global{padding:16px}.ficha h1{font-size:34px;margin:0 0 8px}.ficha .lead{font-size:18px;margin:0 0 10px}
.chip{font-size:13px;font-weight:600;color:#0E141B;border-radius:6px;padding:2px 8px;white-space:nowrap}
.grade{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.grade2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.caixa{background:var(--painel);border-radius:14px;padding:16px;color:var(--texto);text-decoration:none;display:block}
a.caixa:hover{outline:1px solid #34485A}
.caixa h3{margin:0 0 6px;font-size:18px}.caixa p{margin:6px 0 0;font-size:14px;color:var(--suave)}
.mini{display:grid;grid-template-columns:104px 1fr 28px;gap:8px;align-items:center;font-size:13px;color:var(--suave);margin-top:6px}
.mini .barra,.mini .barra i{height:8px}
.mini .barra{min-width:0}
.sinal{display:grid;grid-template-columns:minmax(0,60ch) minmax(0,240px);gap:24px;padding:16px 0;border-bottom:1px solid var(--linha)}
.sinal:last-child{border-bottom:0}.sinal h3{margin:0 0 4px;font-size:18px}.sinal p{margin:0}
.sinal .pct{font:700 28px/1 'Space Grotesk',sans-serif}.sinal .barra{margin:8px 0 6px}
.noticia{border-left:4px solid var(--linha);padding:2px 0 2px 14px;margin:18px 0}
.noticia h3{font-size:17px;margin:4px 0}.noticia p{margin:4px 0;font-size:15px}
.meta{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:12px;color:var(--suave)}
.meta a{display:inline-block;padding:4px 0}
.mexe{font-size:13px;color:var(--suave);margin:6px 0}
.tag{border:1px solid var(--linha);border-radius:6px;padding:4px 8px;display:inline-block}
.fontes{font-size:13px}.fontes a{margin-right:10px;display:inline-block;padding:4px 2px;min-width:28px;text-align:center}
.hist svg{width:100%;height:auto;display:block}.hist .cel{display:none}
.picos{margin:10px 0 0;padding-left:20px}.picos li{margin:4px 0}
.ranking td{padding:10px 8px}.ranking a{color:var(--texto);text-decoration:none;font-weight:600;display:inline-block;padding:4px 0}
.ranking .r{color:var(--suave);font-size:13px}
.so-celular{display:none}
.pano{white-space:pre-wrap;background:#005C4B;color:#E9EDEF;border-radius:12px 12px 12px 2px;max-width:560px;padding:14px 16px 22px;position:relative;font:15px/1.55 'IBM Plex Sans',sans-serif}
.zap{background:#25D366;color:#0E141B}
.pano em{color:#D1D7DB}
.pano.trancado{padding-bottom:18px}.apagado{display:block;margin:14px 0 4px}.apagado span{display:block;height:10px;border-radius:5px;background:rgba(233,237,239,.2);margin:11px 0}.tranca{display:flex;flex-direction:column;gap:8px;align-items:flex-start;border-top:1px solid rgba(233,237,239,.25);padding-top:14px;margin-top:14px;white-space:normal}.tranca strong{font-size:17px}.tranca span{color:#D1D7DB;font-size:14px}.chega{padding-left:20px;line-height:1.6}.chega li{margin:6px 0}
.mapa-mundo svg{width:100%;height:auto;display:block}.mapa-mundo path{stroke:#0E141B;stroke-width:.7}
.mapa-mundo a:hover path,.mapa-mundo a:focus path{opacity:1;filter:brightness(1.15)}.terciario{background:none;border:1px solid var(--linha);color:var(--texto);border-radius:10px;padding:0 16px;
min-height:44px;font:inherit;cursor:pointer}
.legenda-faixas{font-size:12px;color:#A9B4C4;margin:6px 0 0;line-height:1.5}
.mapa-mundo .re{stroke:#3A4656;stroke-width:.6}
.mapa-mundo .pa{stroke:#EEF2F5;stroke-width:1.1}.mapa-mundo .br{stroke-width:2.4}.rot-mapa text{font:600 19px 'Space Grotesk',sans-serif;fill:#EEF2F5;
paint-order:stroke;stroke:#0E141B;stroke-width:5px;stroke-linejoin:round;pointer-events:none}
.comparar{display:grid;grid-template-columns:repeat(auto-fit,minmax(72px,1fr));gap:6px;margin-top:12px}
.comparar div{background:#121B25;border-radius:8px;padding:8px 4px;text-align:center;font-size:12px;color:var(--suave)}
.comparar strong{display:block;font:700 18px 'Space Grotesk',sans-serif;color:var(--texto)}
.educativo{font-size:12px;color:var(--suave);margin:10px 0 0}
.parcial{font-size:12px;color:var(--suave);white-space:nowrap;text-decoration:underline dotted;text-underline-offset:3px}
.sobe{color:#EE8A3C}.desce{color:#7CC3E0}
.bolso{background:#13202B;border:1px solid #23394A;border-radius:14px;padding:16px 18px;margin:16px 0}
.bolso h3{margin:0 0 8px;font-size:18px}.bolso ul{margin:0;padding-left:20px}.bolso li{margin:6px 0}
@media (max-width:760px){.ficha{grid-template-columns:1fr;gap:14px}.ficha h1{font-size:26px}.ficha .lead{font-size:16px}
.grade,.grade2{grid-template-columns:1fr}.sinal{grid-template-columns:1fr;gap:6px}.hist .desk{display:none}.hist .cel{display:block}
.rot-mapa{display:none}.comparar strong{font-size:16px}
.ranking .esconde{display:none}.so-celular{display:block}.ranking td{padding:8px 4px}.ranking td:nth-child(2){overflow-wrap:anywhere}}
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
    if d == 0:
        return f"Igual ao {texto} ({antes})"
    classe, seta, verbo = ("sobe", "▲", "subiu") if d > 0 else ("desce", "▼", "caiu")
    return f'<span class="{classe}">{seta} {verbo} {abs(d)}</span> em relação ao {texto} ({antes})'


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
    grade = "".join(f'<text x="{ml - 6}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="12" fill="{C["suave"]}">{v}</text>'
                    for v in (0, 20, 40, 60, 80, 100))
    anos = list(range(t0.year + 1, t1.year + 1))
    passo = next((p for p in (1, 2, 5, 10) if len(anos) / p <= (8 if largura > 500 else 4)), 20)
    marcos = "".join(f'<text x="{x(pd.Timestamp(a, 1, 1)):.1f}" y="{altura - 8}" text-anchor="middle" font-size="12" '
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
        tx = min(max(px, ml + 34), ml + w - 34)
        marcas += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="none" stroke="{C["texto"]}" stroke-width="1.5"/>'
                   f'<text x="{tx:.1f}" y="{max(py - 9, mt + 10):.1f}" text-anchor="middle" font-size="12" '
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


def fontes_unicas(fontes: list[dict], maximo: int = 3) -> list[dict]:
    vistos, saida = set(), []
    for f in fontes:
        nome = (f.get("veiculo") or "fonte").strip()
        if nome.lower() not in vistos:
            vistos.add(nome.lower())
            saida.append({**f, "veiculo": nome})
    return saida[:maximo]


def noticia_html(n: dict, raiz: str, mostrar_regiao: bool = True) -> str:
    direcao = n.get("direcao") or ""
    meta = [data_curta(n["data"])] if n.get("data") else []
    if mostrar_regiao and n.get("regiao") in motor.REGIOES:
        meta.append(f'<a href="{raiz}regioes/{motor.slug(n["regiao"])}.html">{html.escape(n["regiao"])}</a>')
    elif mostrar_regiao and n.get("regiao"):
        meta.append(html.escape(n["regiao"]))
    if n.get("status"):
        meta.append(html.escape(n["status"]))
    mexe = ""
    if n.get("mexe_em"):
        ponto = (f'<span style="color:{COR_DIRECAO[direcao]}" aria-hidden="true">●</span> '
                 if direcao in ("pressiona", "alivia") else "")
        mexe = (f'<p class="mexe">{ponto}Mexe em: {html.escape(", ".join(n["mexe_em"]))}'
                f'{" (" + TEXTO_DIRECAO.get(direcao, "") + ")" if direcao else ""}</p>')
    fontes = "".join(f'<a href="{html.escape(f["url"])}" target="_blank" rel="noopener noreferrer">'
                     f'{html.escape(f["veiculo"])}</a>' for f in fontes_unicas(n.get("fontes", [])))
    canal = (f'<p class="suave" style="font-size:14px">Como chega ao Brasil: {html.escape(n["canal_brasil"])}</p>'
             if n.get("canal_brasil") else "")
    return (f'<article class="noticia" style="border-left-color:{n.get("cor") or C["linha"]}">'
            f'<div class="meta">{" · ".join(meta)}</div>'
            f'<h3>{html.escape(n["titulo"])}</h3><p>{html.escape(n.get("resumo", ""))}</p>{canal}{mexe}'
            f'<div class="fontes">Fonte: {fontes}</div></article>')


def noticias_secao(noticias: list[dict], titulo: str, raiz: str, mostrar_regiao: bool = True, vazio: str = "") -> str:
    if not noticias:
        return (f'<section class="cartao"><h2 style="margin-top:0">{titulo}</h2><p class="suave">{vazio}</p></section>'
                if vazio else "")
    itens = "".join(noticia_html(n, raiz, mostrar_regiao) for n in noticias)
    return (f'<section class="cartao"><h2 style="margin-top:0">{titulo}</h2>{itens}'
            f'<p class="suave" style="font-size:13px">Cada notícia traz o status do fato (confirmado, ameaça, negociação…) '
            f'e o link da fonte. A borda tem a cor do nível da região; o ponto laranja indica que a notícia aumenta a '
            f'tensão, e o azul, que alivia.</p></section>')


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
            pico = (f" ({b['bolsa_pico']:,.0f} pontos, em {pd.Timestamp(b['bolsa_pico_dia']):%-d/%m})".replace(",", ".")
                    if b.get("bolsa_pico") and b.get("bolsa_pico_dia") else "")
            frase = f"A bolsa ({bolsa}) está {num(q)}% abaixo do ponto mais alto dos últimos 12 meses{pico}."
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
        texto = (f"O que mais pesa {em(nome)} é {NA_FRASE[tensos[0]['chave']]} (mais tenso que em {tensos[0]['pct']}% dos meses); "
                 f"os outros sinais estão mais perto do normal.")
    else:
        texto = (f"Nenhum sinal {de(nome)} está fora do normal: o mais alto é {NA_FRASE[sinais[0]['chave']]}, "
                 f"mais tenso que em {sinais[0]['pct']}% dos meses.")
    atreladas = {"EUA": "o dólar é a própria referência.", "Hong Kong": "o dólar de Hong Kong é atrelado ao dólar americano.",
                 "Arábia Saudita": "o rial saudita é atrelado ao dólar americano."}
    if "moeda" not in {x["chave"] for x in sinais} and p["nome"] in atreladas:
        texto += " A moeda não entra na conta: " + atreladas[p["nome"]]
    if "bolsa" not in {x["chave"] for x in sinais}:
        texto += " Sem um índice de bolsa com histórico confiável, a leitura usa só a moeda."
    return texto


def parcial(p: dict) -> str:
    """Selo quando o país tem menos de 3 sinais (ex.: Egito, só moeda)."""
    if p.get("nome") in ("EUA", "Hong Kong", "Arábia Saudita"):  # moeda fora por desenho (dólar ou moeda atrelada)
        return ""
    n = sum(1 for v in (p.get("sinais") or {}).values() if v is not None)
    return (f' <span class="parcial">só {n} de 3 sinais</span>' if 0 < n < 3 else "")


def incompleto(p: dict) -> bool:
    """Leitura com um único sinal (ex.: só a moeda): fica fora do topo do ranking, numa lista à parte."""
    if p.get("nome") in ("EUA", "Hong Kong", "Arábia Saudita"):
        return False
    return sum(1 for v in (p.get("sinais") or {}).values() if v is not None) == 1


def bolso_brasil(p: dict) -> str:
    """O que a leitura do Brasil muda no dia a dia, em termos gerais e educativos (sem recomendação)."""
    b, s = p.get("brutos") or {}, p.get("sinais") or {}
    itens = []
    v = b.get("moeda_variacao_3m_pct")
    if v is not None and abs(v) >= 1:
        if v > 0:
            itens.append(f"O dólar subiu {num(v)}% em 3 meses: viagem internacional, eletrônicos, remédios e outros produtos "
                         "importados tendem a ficar mais caros, e a conta pode chegar à inflação.")
        else:
            itens.append(f"O dólar caiu {num(abs(v))}% em 3 meses: importados e viagens tendem a pesar menos no bolso.")
    q = b.get("bolsa_queda_pct")
    if q is not None and q >= 5:
        itens.append(f"A bolsa está {num(q)}% abaixo do topo de 12 meses: fundos de ações e planos de previdência com parte "
                     "em ações podem mostrar saldo menor no extrato. Oscilação faz parte desse tipo de aplicação.")
    if (s.get("volatilidade") or 0) >= 70:
        itens.append("O sobe e desce da bolsa está acima do normal: o extrato de investimentos em ações pode variar mais "
                     "de um dia para o outro.")
    if not itens:
        itens.append("Os sinais do Brasil estão perto do normal: por enquanto, pouca pressão vinda do mercado sobre o dia a dia.")
    lista = "".join(f"<li>{html.escape(i)}</li>" for i in itens)
    return (f'<div class="bolso"><h3>O que isso muda no seu bolso</h3><ul>{lista}</ul>'
            f'<p class="educativo">Explicação geral e educativa. Não é recomendação de investimento.</p></div>')


def comparacoes(f: dict) -> list[tuple[str, int]]:
    """O mundo comparado com o mês passado, um ano atrás e o pior momento da série (o índice é mensal)."""
    m = (f.get("mundo") or {}).get("mundo") or {}
    saida = []
    if m.get("mes_anterior") is not None:
        saida.append(("Mês passado", m["mes_anterior"]))
    regioes = f.get("regioes")
    if regioes is not None and "Mundo (média das regiões)" in regioes:
        serie = regioes["Mundo (média das regiões)"].dropna()
        if len(serie) > 12:
            saida.append(("1 ano atrás", round(float(serie.iloc[-13]))))
        completas = regioes[[r for r in motor.REGIOES if r in regioes]].notna().all(axis=1)
        pico = regioes.loc[completas, "Mundo (média das regiões)"].dropna().iloc[:-1]  # só meses com as 6 regiões
        if len(pico) > 24:
            saida.append((f"Pior: {pico.idxmax():%Y} (série desde {pico.index[0]:%Y})", round(float(pico.max()))))
    return saida[:3]


def comparacoes_html(lista: list[tuple[str, int]]) -> str:
    if not lista:
        return ""
    itens = "".join(f'<div><strong style="color:{config.nivel_de(v)["cor"]}">{v}</strong>{html.escape(r)}</div>' for r, v in lista)
    return f'<div class="comparar" aria-label="Comparação com leituras anteriores">{itens}</div>'


MAPA = Path(__file__).resolve().parent / "mapa_mundo.json"
A2 = {"EUA": "US", "Canadá": "CA", "México": "MX", "Brasil": "BR", "Argentina": "AR", "Alemanha": "DE", "França": "FR",
      "Reino Unido": "GB", "Turquia": "TR", "Israel": "IL", "Egito": "EG", "África do Sul": "ZA", "Nigéria": "NG",
      "Japão": "JP", "China": "CN", "Hong Kong": "HK", "Índia": "IN", "Coreia do Sul": "KR", "Austrália": "AU",
      "Chile": "CL", "Colômbia": "CO", "Peru": "PE", "Paraguai": "PY", "Uruguai": "UY", "Itália": "IT", "Espanha": "ES",
      "Portugal": "PT", "Suíça": "CH", "Rússia": "RU", "Arábia Saudita": "SA", "Quênia": "KE", "Marrocos": "MA",
      "Indonésia": "ID", "Taiwan": "TW", "Singapura": "SG"}


SEM_LEITURA = "#2A3441"  # países que não medimos: cinza, com link para a região

# Países pequenos demais para aparecer no desenho do mapa: um ponto no lugar certo (coordenadas do próprio SVG).
PONTOS_NO_MAPA = {"HK": (777, 213), "SG": (752, 274)}


def mapa_svg(m: dict, raiz: str = "") -> str:
    """Mapa-múndi clicável: cada região na cor do seu nível; os países que medimos, na cor do próprio termômetro.
    Para teclado e leitor de tela, a lista de regiões logo abaixo faz o mesmo papel (o mapa fica fora do foco)."""
    if not MAPA.exists():
        return ""
    dados = json.loads(MAPA.read_text())
    regioes = {r["nome"]: r for r in m.get("regioes", []) if r.get("valor") is not None}
    medidos = {A2[p["nome"]]: p for r in regioes.values() for p in r["paises"] if p.get("valor") is not None and p["nome"] in A2}
    formas = []
    for c in dados["paises"]:
        r = regioes.get(c["regiao"])
        if r is None:
            continue
        if c["a2"] in medidos:
            p = medidos[c["a2"]]
            href, cor, classe = f"{raiz}paises/{p['slug']}.html", p["cor"], "pa"
            dica = f"{p['nome']}: {p['valor']}, {p['nivel']} (toque para entender)"
        else:
            href, cor, classe = f"{raiz}regioes/{r['slug']}.html", SEM_LEITURA, "re"
            dica = f"{c['nome']}: sem leitura própria. Região {r['nome']}: {r['valor']}, {r['nivel']}"
        if c["a2"] == "BR":
            classe += " br"
        formas.append(f'<a href="{href}" tabindex="-1"><path class="{classe}" d="{c["d"]}" fill="{cor}">'
                      f'<title>{html.escape(dica)}</title></path></a>')
    for a2, (px, py) in PONTOS_NO_MAPA.items():
        if a2 in medidos:
            p = medidos[a2]
            dica = html.escape(f"{p['nome']}: {p['valor']}, {p['nivel']} (toque para entender)")
            formas.append(f'<a href="{raiz}paises/{p["slug"]}.html" tabindex="-1"><circle class="pa ponto" cx="{px}" '
                          f'cy="{py}" r="4" fill="{p["cor"]}"><title>{dica}</title></circle></a>')
    rotulos = "".join(f'<text x="{x}" y="{y}" text-anchor="middle">{html.escape(nome)} {regioes[nome]["valor"]}</text>'
                      for nome, (x, y) in dados.get("rotulos", {}).items() if nome in regioes)
    return (f'<figure class="mapa-mundo" style="margin:0"><svg viewBox="0 0 {dados["largura"]} {dados["altura"]}" '
            f'aria-hidden="true" focusable="false">{"".join(formas)}'
            f'<g class="rot-mapa">{rotulos}</g></svg></figure>')


def jsonld(*itens: dict) -> str:
    return "".join(f'<script type="application/ld+json">{json.dumps(i, ensure_ascii=False)}</script>' for i in itens)


def migalhas(*passos: tuple[str, str]) -> dict:
    base = config.SITE_URL or ""
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": nome, "item": f"{base}/{caminho}"} for i, (nome, caminho) in enumerate(passos, 1)]}


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


def quando(f: dict) -> str:
    """'06/11/2026, parcial das 14h07 (o fechamento sai às 18h17)' ou '05/11/2026'."""
    dia = f"{pd.Timestamp(f['data']):%d/%m/%Y}"
    hora = ((f.get("mundo") or {}).get("parcial") or {}).get("hora")
    return f"{dia}, parcial das {hora} (o fechamento sai às 18h17)" if hora else dia


def fonte(pasta_edicao: Path, pasta_diario: Path) -> dict:
    """Escolhe os dados mais novos: a atualização diária, se for mais recente que a edição semanal."""
    f = {"data": pasta_edicao.name, "mundo": _json(pasta_edicao / "mundo.json") or {},
         "paises": _csv(pasta_edicao / "mundo_paises.csv"), "regioes": _csv(pasta_edicao / "mundo_regioes.csv"),
         "correspondente": None, "panorama": None, "dossie": _json(pasta_edicao / "pesquisa.json") or {}}
    dias = dias_do_diario(pasta_diario)
    if dias and dias[-1].name >= pasta_edicao.name:
        d = dias[-1]
        hist = pasta_diario / "historico"
        # numa leitura parcial (11h, 14h) ainda não há notícias nem panorama do dia: valem as do último fechamento
        com_noticias = next((x for x in reversed(dias) if (x / "correspondente.json").exists()), None)
        com_panorama = next((x for x in reversed(dias) if (x / "panorama.txt").exists()), None)
        com_acoes = next((x for x in reversed(dias) if (x / "acoes.json").exists()), None)
        f["acoes"] = _json(com_acoes / "acoes.json") if com_acoes else None
        f.update(data=d.name, mundo=_json(d / "mundo.json"),
                 paises=_csv(hist / "mundo_paises.csv"), regioes=_csv(hist / "mundo_regioes.csv"),
                 correspondente=_json(com_noticias / "correspondente.json") if com_noticias else None,
                 panorama=(com_panorama / "panorama.txt").read_text() if com_panorama else None,
                 data_panorama=com_panorama.name if com_panorama else None)
    membros = {r["nome"]: [p["nome"] for p in r.get("paises", [])] for r in f["mundo"].get("regioes", [])}
    for r in ((f.get("correspondente") or {}).get("regioes") or {}).values():
        r["resumo"] = corr.datas_br(r.get("resumo", ""))
        r["paises"] = {k: corr.datas_br(x) for k, x in (r.get("paises") or {}).items()}
        for n in r.get("noticias", []):
            n["titulo"], n["resumo"] = corr.datas_br(n["titulo"]), corr.datas_br(n.get("resumo", ""))
            if not n.get("paises"):  # país citado no texto, mesmo que o agente não tenha marcado
                n["paises"] = corr.citados(f"{n['titulo']} {n['resumo']}", membros.get(n.get("regiao"), []))
    if f["correspondente"] and corr.todas_as_noticias(f["correspondente"]):
        f["noticias"] = corr.todas_as_noticias(f["correspondente"])
    else:
        f["noticias"] = corr.noticias_do_dossie(f["dossie"], membros)
    # completa o que os arquivos antigos não tinham (endereço da página, picos e a cor atual de cada faixa)
    def recolorir(item: dict | None) -> None:
        if item and item.get("valor") is not None:
            item["cor"] = config.nivel_de(item["valor"])["cor"]
    recolorir(f["mundo"].get("mundo"))
    recolorir(f["mundo"].get("brasil"))
    for r in f["mundo"].get("regioes", []):
        recolorir(r)
        for p in r.get("paises", []):
            recolorir(p)
    for r in f["mundo"].get("regioes", []):
        r.setdefault("slug", motor.slug(r["nome"]))
        if "picos" not in r and f["regioes"] is not None and r["nome"] in f["regioes"]:
            r["picos"] = motor.picos(f["regioes"][r["nome"]], r["nome"])
        for p in r.get("paises", []):
            p.setdefault("slug", motor.slug(p["nome"]))
            if "picos" not in p and f["paises"] is not None and p["nome"] in f["paises"]:
                p["picos"] = motor.picos(f["paises"][p["nome"]], p["nome"], r["nome"])
    # cor do nível da região em cada notícia (borda do cartão) e leituras anteriores do mundo (comparações)
    cores = {r["nome"]: r.get("cor") for r in f["mundo"].get("regioes", [])}
    listas = [f["noticias"]] + [r.get("noticias", []) for r in ((f.get("correspondente") or {}).get("regioes") or {}).values()]
    for lista in listas:
        for n in lista:
            n["cor"] = cores.get(n.get("regiao"))
    f["dias_anteriores"] = []
    for d in dias_do_diario(pasta_diario):
        if d.name < f["data"]:
            valor = ((_json(d / "mundo.json") or {}).get("mundo") or {}).get("valor")
            if valor is not None:
                f["dias_anteriores"].append((d.name, valor))
    return f


def explicacao(f: dict, regiao: str) -> dict:
    return ((f.get("correspondente") or {}).get("regioes") or {}).get(regiao) or {}


def noticias_da_regiao(f: dict, regiao: str) -> list[dict]:
    """As notícias da própria região (a lista geral da página inicial tira as repetidas entre regiões)."""
    if f.get("correspondente") and corr.todas_as_noticias(f["correspondente"]):
        return explicacao(f, regiao).get("noticias", [])
    return [n for n in f["noticias"] if n.get("regiao") == regiao]


# ---------------------------------------------------------------- páginas
def legenda_faixas() -> str:
    return ('<p class="legenda-faixas">' + " · ".join(f'{n["nome"]} {n["min"]}–{n["max"]}' for n in config.NIVEIS) + "</p>")


def ficha(nome: str, valor, nivel: str, cor: str, lead: str, extra: str, rotulo: str, raiz: str = "../",
          ancora: str = "mundo") -> str:
    return (f'<section class="ficha"><div class="global"><span class="rotulo">{rotulo}</span>{medidor_svg(valor, cor)}'
            f'<div class="valor">{valor}</div><div class="nivel" style="color:{cor}">{nivel.upper()}</div>{legenda_faixas()}'
            f'<p class="educativo">Indicador educativo: mostra o que já aconteceu, não prevê nem recomenda. '
            f'<a href="{raiz}metodologia.html#{ancora}">Como calculamos</a></p></div>'
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
                       f'{minis}{("<p>" + parcial(p).strip() + "</p>") if parcial(p) else ""}<p>{html.escape(curto)}</p>'
                       f'<p style="color:#7CC3E0">Entender {html.escape(com_artigo(p["nome"]))}</p></a>')
    noticias = noticias_da_regiao(f, r["nome"])
    serie = f["regioes"][r["nome"]] if f["regioes"] is not None and r["nome"] in f["regioes"] else None
    corpo = (f'<p class="trilha"><a href="../index.html">Início</a> › {html.escape(r["nome"])}</p>'
             + ficha(r["nome"], r["valor"], r["nivel"], r["cor"], lead, extra, "Termômetro da região", ancora="regiao")
             + (f'<section><h2>{html.escape(sujeito(ordenados[0]["nome"])[0])} {"são" if sujeito(ordenados[0]["nome"])[1] == "estão" else "é"} '
                f'o país mais tenso da região: {ordenados[0]["valor"]}</h2><div class="grade">{"".join(cartoes)}</div></section>'
                if ordenados else "")
             + noticias_secao(noticias, "Notícias que mexem com o termômetro", "../", mostrar_regiao=False,
                              vazio="Nenhuma notícia conferida com fonte nos últimos dias para esta região.")
             + link_arquivo(f, r["slug"], f"Ver todas as notícias {de(r['nome'])}")
             + historico_html(serie, r.get("picos", []), r["nome"], r["valor"])
             + observar_html(ex.get("observar", []))
             + compartilhar(f"Termômetro de crise {de(r['nome'])}: {r['valor']} de 100 ({r['nivel']})", f"regioes/{r['slug']}.html")
             + bloco_celular("../")
             + metodo_curto("../"))
    corpo += jsonld(migalhas(("Início", ""), (r["nome"], f"regioes/{r['slug']}.html")))
    return pagina(f"Risco de crise {em(r['nome'])}: termômetro em {r['valor']} ({r['nivel']})",
                  f"Por que o risco de crise {em(r['nome'])} está em {r['valor']} de 100, país por país, com as notícias "
                  f"que mexem com o termômetro. Atualizado todo dia útil.",
                  corpo, raiz="../", caminho=f"regioes/{r['slug']}.html", extra_css=CSS)


def pagina_pais(f: dict, r: dict, p: dict) -> str:
    ex = explicacao(f, r["nome"])
    nivel = config.nivel_de(p["valor"])
    lead = f"{p['valor']} de 100: {nivel['leitura'].lower()}."
    extra = (f'<p class="suave" style="margin:0 0 10px">{variacao(p["valor"], p.get("mes_anterior"))}{parcial(p)}</p>'
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
    da_regiao = [n for n in todas if n not in noticias][:3]  # regra pública: mesmo país, depois a região, até 3
    serie = f["paises"][p["nome"]] if f["paises"] is not None and p["nome"] in f["paises"] else None
    vizinhos = " ".join(f'<a class="tag" href="{v["slug"]}.html">{html.escape(v["nome"])} {v["valor"]}</a>'
                        for v in r["paises"] if v["nome"] != p["nome"] and v.get("valor") is not None)
    corpo = (f'<p class="trilha"><a href="../index.html">Início</a> › <a href="../regioes/{r["slug"]}.html">'
             f'{html.escape(r["nome"])}</a> › {html.escape(p["nome"])}</p>'
             + ficha(p["nome"], p["valor"], p["nivel"], p["cor"], lead, extra, "Termômetro do país", ancora="pais")
             + f'<section class="cartao"><h2 style="margin-top:0">Por que o termômetro está em {p["valor"]}</h2>'
               f'<p>{html.escape(por_que_automatico(p))} O termômetro é a média destes sinais:</p>{linhas}</section>'
             + (bolso_brasil(p) if p["nome"] == "Brasil" else "")
             + bloco_contexto
             + noticias_secao(noticias, f"Notícias que mexem com {html.escape(ARTIGOS.get(p['nome'], '') + ' ' + p['nome']).strip()}", "../", mostrar_regiao=False)
             + link_arquivo(f, p["slug"], f"Ver todas as notícias {de(p['nome'])}")
             + noticias_secao(da_regiao, "Leia também", "../", mostrar_regiao=False)
             + historico_html(serie, p.get("picos", []), p["nome"], p["valor"])
             + (f'<section><h2>Outros países da região</h2><p class="meta" style="font-size:14px">{vizinhos}</p></section>'
                if vizinhos else "")
             + compartilhar(f"Termômetro de crise {de(p['nome'])}: {p['valor']} de 100 ({p['nivel']})", f"paises/{p['slug']}.html")
             + bloco_celular("../")
             + metodo_curto("../"))
    corpo += jsonld(migalhas(("Início", ""), (r["nome"], f"regioes/{r['slug']}.html"), (p["nome"], f"paises/{p['slug']}.html")))
    return pagina(f"Risco de crise {em(p['nome'])} hoje: termômetro em {p['valor']} ({p['nivel']})",
                  f"Por que o risco de crise {em(p['nome'])} está em {p['valor']} de 100: bolsa, moeda, sobe e desce e as "
                  f"notícias que mexem com o termômetro. Atualizado todo dia útil.",
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


def link_arquivo(f: dict, slug: str, texto: str) -> str:
    if slug not in f.get("com_arquivo", set()):
        return ""
    return f'<p style="margin:-8px 0 20px"><a class="contorno" href="../noticias/{slug}.html">{html.escape(texto)}</a></p>'


def compartilhar(titulo: str, caminho: str) -> str:
    url = f"{config.SITE_URL or 'https://termometrodecrise.com'}/{caminho}"
    texto = quote(f"{titulo}: {url}")
    return (f'<p class="meta" style="font-size:14px;margin-top:20px">Compartilhar: '
            f'<a href="https://wa.me/?text={texto}" target="_blank" rel="noopener">WhatsApp</a> · '
            f'<a href="https://t.me/share/url?url={quote(url)}&text={quote(titulo)}" target="_blank" rel="noopener">Telegram</a> · '
            f'<a href="https://twitter.com/intent/tweet?url={quote(url)}&text={quote(titulo)}" target="_blank" rel="noopener">X</a></p>')


def metodo_curto(raiz: str) -> str:
    return (f'<p class="suave" style="font-size:13px;margin-top:28px">Como funciona: cada sinal é comparado com a '
            f'história do próprio país (percentil 90 = mais tenso do que em 90% dos meses). O termômetro do país é a '
            f'média dos sinais; o da região, a média dos países. <a href="{raiz}metodologia.html#mundo">Metodologia completa</a>.</p>')


def mudanca(agora, antes) -> str:
    """Mudança no mês em formato curto: '▲ 3 (89)'."""
    if agora is None or antes is None:
        return ""
    d = agora - antes
    if d == 0:
        return f"= ({antes})"
    classe, seta, verbo = ("sobe", "▲", "subiu") if d > 0 else ("desce", "▼", "caiu")
    return (f'<span class="{classe}"><span aria-hidden="true">{seta}</span><span class="sr">{verbo} </span>{abs(d)}</span> '
            f'<span class="suave">({antes})</span>')


def _tabela_ranking(itens: list, inicio: int = 1) -> str:
    linhas = []
    for i, (p, r) in enumerate(itens, inicio):
        linhas.append(f'<tr><td class="r">{i}</td><td><a href="paises/{p["slug"]}.html">{html.escape(p["nome"])}</a>{parcial(p)}'
                      f'<br><a class="r" href="regioes/{r["slug"]}.html" style="font-weight:400">{html.escape(r["nome"])}</a>'
                      f'<div class="so-celular" style="margin-top:6px">{barra(p["valor"])}</div></td>'
                      f'<td class="esconde" style="width:30%">{barra(p["valor"])}</td>'
                      f'<td class="num">{p["valor"]}</td><td>{chip(p["nivel"], p["cor"])}</td>'
                      f'<td class="r esconde">{mudanca(p["valor"], p.get("mes_anterior"))}</td></tr>')
    return (f'<table class="ranking"><tr><th>#</th><th>País</th><th class="esconde">Estresse</th>'
            f'<th style="text-align:right">Agora</th><th>Nível</th><th class="esconde">Mudança no mês</th></tr>'
            f'{"".join(linhas)}</table>')


def pagina_ranking(f: dict) -> str:
    todos = sorted(((p, r) for r in f["mundo"].get("regioes", []) for p in r.get("paises", []) if p.get("valor") is not None),
                   key=lambda x: -x[0]["valor"])
    completos = [x for x in todos if not incompleto(x[0])]
    incompletos = [x for x in todos if incompleto(x[0])]
    destaque = ""
    for pos, (p, r) in enumerate(completos, 1):
        if p["nome"] == "Brasil":
            destaque = (f'<p class="cartao" style="padding:14px 18px;margin:12px 0 20px">🇧🇷 <a href="paises/brasil.html"><strong>'
                        f'Brasil: {p["valor"]}</strong></a> {chip(p["nivel"], p["cor"])} · {pos}º de {len(completos)} '
                        f'países com leitura completa</p>')
    corpo = (f'<section class="edicao" style="max-width:none"><h1>Todos os países, do mais tenso ao mais calmo</h1>'
             f'<p class="suave">Toque em um país para entender o porquê. Atualizado em {quando(f)}.</p>'
             f'{destaque}{_tabela_ranking(completos)}')
    if incompletos:
        corpo += (f'<h2 id="incompleta">Leitura incompleta</h2><p class="suave">Estes países são medidos só pela moeda, '
                  f'porque a fonte de dados não tem o histórico da bolsa. Com um único sinal, a leitura é menos confiável, '
                  f'por isso eles ficam fora da lista principal.</p>{_tabela_ranking(incompletos)}')
    corpo += f'{metodo_curto("")}</section>'
    return pagina(f"Ranking mundial do termômetro de crise · {config.NOME}",
                  "Os países do Termômetro de Crise, do mais tenso ao mais calmo, com o porquê de cada leitura.",
                  corpo, caminho="mundo.html", extra_css=CSS)


def whatsapp_html(texto: str) -> str:
    """Mostra o texto como ele aparece no WhatsApp (*negrito* e _itálico_)."""
    import re
    t = html.escape(texto)
    t = re.sub(r"\*([^*\n]+)\*", r"<strong>\1</strong>", t)
    return re.sub(r"(?<![\w/])_([^_\n]+)_(?!\w)", r"<em>\1</em>", t)


def previa_trancada(texto: str) -> str:
    """Só o começo da mensagem (o cabeçalho e o mundo, que já estão no site); o resto fica apagado, com o convite.
    O panorama completo é do grupo do WhatsApp: é o motivo para entrar."""
    linhas = texto.splitlines()
    topo = "\n".join(linhas[:4]).rstrip()
    larguras = [92, 64, 80, 71, 88, 58, 76, 84, 49, 69]
    apagado = "".join(f'<span style="width:{w}%"></span>' for w in larguras)
    destino = html.escape(config.WHATSAPP_URL)
    return (f'<div class="pano trancado">{whatsapp_html(topo)}<span class="apagado" aria-hidden="true">{apagado}</span>'
            f'<div class="tranca"><strong>O panorama completo chega no grupo</strong>'
            f'<span>Regiões, Brasil, Banco Central e as notícias que mexeram com o termômetro.</span>'
            f'<a class="acao" href="{destino}" target="_blank" rel="noopener">Entrar no grupo do WhatsApp</a></div></div>')


def pagina_panorama(f: dict) -> str:
    texto = f.get("panorama") or panorama.montar(f["mundo"], f.get("correspondente"), None, f["data"],
                                                 noticias=f.get("noticias"))
    destino = html.escape(config.WHATSAPP_URL)
    dia = pd.Timestamp(f.get("data_panorama") or f["data"])
    corpo = f"""<section class="edicao"><h1>Panorama do fim de tarde, no grupo do WhatsApp</h1>
<p class="suave">Todo dia útil, depois do fechamento (a partir das 18h30), o grupo recebe o card do Fechamento do Termômetro,
o balanço do Ibovespa e do dólar e o panorama do mundo, das regiões e do Brasil, com as notícias que mexeram com o termômetro.
Para ler em 30 segundos.</p>
<div class="acoes" style="margin:16px 0"><a class="acao" href="{destino}" target="_blank" rel="noopener">Entrar no grupo do WhatsApp</a></div>
<small class="suave" style="display:block;margin-bottom:22px">Grátis. Um envio por dia útil. Sem recomendação de investimento.
Sai quando quiser.</small>
<p class="rotulo" style="margin:18px 0 8px">O panorama de {dia:%d/%m}</p>
{previa_trancada(texto)}
<h2 style="margin-top:32px">O que chega no grupo</h2>
<ul class="chega">
<li><strong>O card do fechamento:</strong> o termômetro do Brasil e do mundo, o Ibovespa e o dólar do dia, com o porquê.</li>
<li><strong>O panorama:</strong> as seis regiões, o Brasil sinal por sinal, os números do Banco Central e as três notícias do dia.</li>
<li><strong>Com fonte em cada fato:</strong> o mesmo método do site, sem palpite e sem recomendação de investimento.</li>
</ul>
{'<p style="margin-top:20px"><a class="contorno" href="panorama/index.html">Os números de cada dia</a></p>' if f.get("tem_arquivo_panorama") else ""}
</section>"""
    return pagina(f"Panorama do fim de tarde no WhatsApp · {config.NOME}",
                  "Todo dia útil, o card do fechamento e o panorama do mundo, das regiões e do Brasil, no grupo do WhatsApp "
                  "do Termômetro de Crise. Grátis.",
                  corpo, caminho="panorama.html", extra_css=CSS,
                  imagem=(f.get("fechamento") or {}).get("imagem", ""))


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
