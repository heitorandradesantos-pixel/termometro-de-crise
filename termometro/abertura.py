"""Abertura do Termômetro: como o mundo amanheceu e como o Brasil abriu, todo dia útil logo depois que a B3 abre.

Vai para o grupo do WhatsApp junto com um card no estilo do Fechamento. Tudo sai das cotações do Yahoo Finance
(com a hora de cada uma) e do último fechamento do termômetro; o destaque é o artigo do Plantão da manhã, já
conferido. Sem a B3 aberta no dia (feriado), não há abertura.
"""

import json
from pathlib import Path

import pandas as pd
import requests

from . import config

UA = {"User-Agent": "Mozilla/5.0 (compatible; termometro-de-crise/1.0)"}
FUSO = "America/Sao_Paulo"
GRUPOS = [
    ("asia", "🌏", "Ásia", [("Nikkei", "^N225"), ("Hang Seng", "^HSI"), ("Xangai", "000001.SS")]),
    ("europa", "🌍", "Europa", [("DAX", "^GDAXI"), ("FTSE 100", "^FTSE"), ("Stoxx 50", "^STOXX50E")]),
    ("eua", "🇺🇸", "Nova York (futuros)", [("S&P 500", "ES=F"), ("Nasdaq", "NQ=F"), ("Dow Jones", "YM=F")]),
    ("materias", "🛢️", "Petróleo, ouro e bitcoin", [("Petróleo Brent", "BZ=F"), ("Ouro", "GC=F"), ("Bitcoin", "BTC-USD")]),
]
BRASIL = [("Ibovespa", "^BVSP"), ("Dólar", "BRL=X")]
VELHO = pd.Timedelta(hours=20)  # cotação mais velha que isso não entra (mercado fechado no dia)


def _num(v: float, casas: int = 0) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _var(v: float) -> str:
    return f"{'▲' if v > 0 else '▼' if v < 0 else ''}{_num(abs(v), 2)}%"


def cotacao(simbolo: str, buscar=requests.get, agora: pd.Timestamp | None = None) -> dict | None:
    r = buscar(f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}", headers=UA, timeout=30,
               params={"range": "1d", "interval": "5m"})
    r.raise_for_status()
    meta = r.json()["chart"]["result"][0]["meta"]
    ultimo, antes = meta.get("regularMarketPrice"), meta.get("chartPreviousClose") or meta.get("previousClose")
    if not ultimo or not antes or not meta.get("regularMarketTime"):
        return None
    fator = 0.01 if meta.get("currency") == "GBp" else 1
    periodo = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
    agora = (agora or pd.Timestamp.now(tz="UTC")).timestamp()
    return {"ultimo": ultimo * fator, "variacao_pct": (ultimo / antes - 1) * 100,
            "hora": pd.Timestamp(meta["regularMarketTime"], unit="s", tz="UTC").tz_convert(FUSO).isoformat(),
            "aberto": bool(periodo and periodo.get("start", 0) <= agora <= periodo.get("end", 0))}


def coletar(agora: pd.Timestamp | None = None, buscar=requests.get) -> dict:
    agora = agora or pd.Timestamp.now(tz=FUSO)
    saida, falhas = {}, {}
    for _, _, _, itens in GRUPOS + [("brasil", "", "", BRASIL)]:
        for nome, simbolo in itens:
            try:
                c = cotacao(simbolo, buscar, agora)
            except Exception as erro:  # noqa: BLE001 — um índice fora do ar não derruba a abertura
                falhas[nome] = str(erro)[:120]
                continue
            if c and agora - pd.Timestamp(c["hora"]) <= VELHO:
                saida[nome] = {**c, "simbolo": simbolo}
            else:
                falhas[nome] = "sem cotação recente"
    return {"quando": agora.isoformat(), "fonte": "Yahoo Finance", "itens": saida, "falhas": falhas}


def ultimo_fechamento(pasta_diario: Path, hoje: str) -> dict | None:
    dias = sorted(d for d in pasta_diario.iterdir() if d.is_dir() and d.name[:2] == "20" and d.name < hoje
                  and (d / "panorama.txt").exists() and (d / "mundo.json").exists()) if pasta_diario.exists() else []
    if not dias:
        return None
    m = json.loads((dias[-1] / "mundo.json").read_text())
    if (m.get("brasil") or {}).get("valor") is None:
        return None
    return {"data": dias[-1].name, "brasil": m["brasil"], "mundo": m.get("mundo") or {}}


def destaque(pasta_diario: Path, hoje: str) -> dict | None:
    """O artigo do Plantão publicado hoje (o da manhã é o contexto do mercado)."""
    pasta = pasta_diario / "plantao"
    artigos = [json.loads(a.read_text()) for a in sorted(pasta.glob(f"{hoje}-*.json"))] if pasta.exists() else []
    artigos = [a for a in artigos if a.get("titulo") and a.get("slug")]
    if not artigos:
        return None
    a = min(artigos, key=lambda x: x.get("publicado_em") or "")
    return {"titulo": a["titulo"], "url": f"{config.SITE_URL}/noticias/plantao/{a['slug']}.html"}


def montar(cot: dict, fechamento: dict | None, art: dict | None) -> str | None:
    """O texto da abertura. None quando a B3 não abriu hoje (feriado ou fim de semana)."""
    itens = cot["itens"]
    agora = pd.Timestamp(cot["quando"])
    ibov = itens.get("Ibovespa")
    if not ibov or pd.Timestamp(ibov["hora"]).date() != agora.date():
        return None
    dias = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    linhas = [f"*TERMÔMETRO DE CRISE · Abertura de {dias[agora.weekday()]}, {agora:%d/%m}*",
              "_Como o mundo amanheceu e como o Brasil abriu_", ""]
    for chave, emoji, titulo, lista in GRUPOS:
        partes = []
        for nome, _ in lista:
            c = itens.get(nome)
            if not c:
                continue
            if chave == "materias":
                preco = _num(c["ultimo"], 0 if c["ultimo"] >= 1000 else 2)
                partes.append(f"{nome} US$ {preco} ({_var(c['variacao_pct'])})")
            else:
                partes.append(f"{nome} {_var(c['variacao_pct'])}")
        if not partes:
            continue
        estado = ""
        if chave in ("asia", "europa"):
            abertos = [itens[n]["aberto"] for n, _ in lista if n in itens]
            estado = " (agora)" if any(abertos) else " (fechamento)"
        linhas += [f"{emoji} *{titulo}{estado}*", " · ".join(partes), ""]
    hora = pd.Timestamp(ibov["hora"])
    rotulo = "na abertura" if hora.hour < 11 else "agora"
    linhas.append(f"🇧🇷 *Brasil {rotulo} ({hora:%Hh%M})*")
    linhas.append(f"{'📈' if ibov['variacao_pct'] > 0 else '📉'} Ibovespa: {_num(ibov['ultimo'])} pontos "
                  f"({_var(ibov['variacao_pct'])})")
    if itens.get("Dólar"):
        u = itens["Dólar"]
        linhas.append(f"💵 Dólar: R$ {_num(u['ultimo'], 2)} ({_var(u['variacao_pct'])})")
    if fechamento:
        b, w = fechamento["brasil"], fechamento["mundo"]
        linhas += ["", f"🌡️ No último fechamento ({pd.Timestamp(fechamento['data']):%d/%m}): Brasil em {b['valor']} "
                       f"({b['nivel']}) · Mundo em {w.get('valor')} ({w.get('nivel')})"]
    if art:
        linhas += ["", "📰 *Destaque da manhã*", art["titulo"], art["url"]]
    linhas += ["", "_Conteúdo educativo, com fonte em cada fato. Não é recomendação de investimento._",
               "_Cotações: Yahoo Finance._"]
    return "\n".join(linhas)


def card(cot: dict, caminho: Path) -> None:
    """Card 1080x1350 no estilo do Fechamento: o Brasil em destaque e o mundo em linhas."""
    from .grafico import C, FancyBboxPatch, Rectangle, _fonte, plt
    plt.rcParams.update({"font.family": _fonte()})
    W, H = 1080, 1350
    fig = plt.figure(figsize=(W / 200, H / 200), dpi=200, facecolor=C["fundo"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    pt = 72 / 200
    y = lambda topo: H - topo  # noqa: E731
    agora = pd.Timestamp(cot["quando"])
    meses = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
    cor_de = lambda v: "#7EC8E3" if v < 0 else ("#F28C38" if v > 0 else C["suave"])  # noqa: E731
    itens = cot["itens"]

    ax.text(W / 2, y(110), "ABERTURA DO TERMÔMETRO", color="#F2C14E", fontsize=50 * pt, weight="bold", ha="center",
            va="center")
    ax.add_patch(FancyBboxPatch((W / 2 - 150, y(205)), 300, 58, boxstyle="round,pad=0,rounding_size=8",
                                color=C["texto"], lw=0))
    ax.text(W / 2, y(176), f"{agora:%d}.{meses[agora.month - 1]}.{agora:%Y}", color=C["fundo"], fontsize=32 * pt,
            weight="bold", ha="center", va="center")

    for k, (nome, rotulo, fmt) in enumerate([("Ibovespa", "IBOVESPA", lambda v: f"{_num(v)} pts"),
                                              ("Dólar", "DÓLAR", lambda v: f"R$ {_num(v, 2)}")]):
        c = itens.get(nome)
        x0 = 70 + k * 480
        ax.add_patch(FancyBboxPatch((x0, y(500)), 460, 240, boxstyle="round,pad=0,rounding_size=18",
                                    color=C["painel"], lw=0))
        ax.text(x0 + 36, y(316), rotulo, color=C["texto"], fontsize=36 * pt, weight="bold", va="center")
        if c:
            ax.text(x0 + 36, y(396), _var(c["variacao_pct"]), color=cor_de(c["variacao_pct"]), fontsize=52 * pt,
                    weight="bold", va="center")
            ax.text(x0 + 36, y(458), fmt(c["ultimo"]), color=C["suave"], fontsize=30 * pt, va="center")
    if itens.get("Ibovespa"):
        hora = pd.Timestamp(itens["Ibovespa"]["hora"])
        ax.text(W / 2, y(540), f"Brasil às {hora:%Hh%M} · cotações do Yahoo Finance", color=C["suave"],
                fontsize=22 * pt, ha="center", va="center")

    topo = 590
    for chave, _, titulo, lista in GRUPOS:
        presentes = [(n, itens[n]) for n, _ in lista if n in itens]
        if not presentes:
            continue
        ax.add_patch(FancyBboxPatch((70, y(topo + 140)), W - 140, 140, boxstyle="round,pad=0,rounding_size=16",
                                    color=C["painel"], lw=0))
        ax.text(106, y(topo + 36), titulo.upper(), color=C["suave"], fontsize=22 * pt, weight="semibold", va="center")
        largura = (W - 212) / 3
        for i, (nome, c) in enumerate(presentes):
            x = 106 + i * largura
            ax.text(x, y(topo + 80), nome, color=C["texto"], fontsize=26 * pt, va="center")
            ax.text(x, y(topo + 116), _var(c["variacao_pct"]), color=cor_de(c["variacao_pct"]), fontsize=30 * pt,
                    weight="bold", va="center")
        topo += 158

    ax.add_patch(Rectangle((70, y(1262)), W - 140, 2, color=C["linha"], lw=0))
    ax.text(70, y(1300), "TERMÔMETRO DE CRISE", color=C["texto"], fontsize=28 * pt, weight="semibold", va="center")
    ax.text(W - 70, y(1300), "termometrodecrise.com · não é recomendação", color=C["suave"], fontsize=22 * pt,
            ha="right", va="center")
    fig.savefig(caminho, facecolor=C["fundo"])
    plt.close(fig)


def gerar(pasta_diario: Path, pasta_saida: Path, agora: pd.Timestamp | None = None, buscar=requests.get) -> dict | None:
    """Coleta, monta o texto e o card. None quando não há abertura hoje."""
    cot = coletar(agora, buscar)
    hoje = pd.Timestamp(cot["quando"]).strftime("%Y-%m-%d")
    texto = montar(cot, ultimo_fechamento(pasta_diario, hoje), destaque(pasta_diario, hoje))
    if not texto:
        return None
    pasta_saida.mkdir(parents=True, exist_ok=True)
    imagem = pasta_saida / f"abertura-{hoje}.png"
    try:
        card(cot, imagem)
    except Exception as erro:  # noqa: BLE001 — sem card, o texto vai sozinho
        print(f"Card da abertura falhou: {erro}")
        imagem = None
    return {"dia": hoje, "texto": texto, "imagem": str(imagem.resolve()) if imagem else "", "cotacoes": cot}
