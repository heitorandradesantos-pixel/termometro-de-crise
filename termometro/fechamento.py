"""Fechamento do Termômetro: o card do fim do dia (imagem 1080x1350) e o texto do balanço que vai junto.

Inspirado no ritual do "fechamento" diário dos perfis de mercado: todo dia útil, à mesma hora, o mesmo
desenho. Aqui tudo sai de números já conferidos (motor, Yahoo Finance, Banco Central) e das manchetes
que o Correspondente validou com fonte; nada é escrito à mão nem pela IA na hora de montar o card.

Fica em panorama/fechamento-AAAA-MM-DD.png e na página do Panorama, com botão para baixar e para copiar
o texto (WhatsApp, Instagram).
"""

import json
import math
import textwrap
from pathlib import Path

import pandas as pd

from . import config
from .correspondente import todas_as_noticias

MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]


def _num(v: float, casas: int = 0) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _var(v: float) -> str:
    return f"{'▲' if v > 0 else '▼' if v < 0 else ''}{_num(abs(v), 2)}%"


def _primeira_frase(texto: str, limite: int = 150) -> str:
    frases = [f.strip() for f in texto.replace("...", ".").split(". ") if f.strip()]
    saida = ""
    for f in frases:
        candidato = (saida + " " + f.rstrip(".") + ".").strip()
        if len(candidato) > limite:
            break
        saida = candidato
    return saida or (texto[: limite - 1].rstrip() + "…" if texto else "")


def _motivo(noticias: list[dict], sinal: str) -> str:
    """O porquê do dia, do resumo conferido da notícia do Brasil que mais mexeu nesse sinal (bolsa ou moeda)."""
    for n in noticias:
        if "Brasil" in n.get("paises", []) and sinal in n.get("mexe_em", []):
            return _primeira_frase(n.get("resumo") or n["titulo"])
    return ""


def dados(dia: str, pasta_dia: Path) -> dict | None:
    """Junta o que o card precisa, a partir dos arquivos do dia. None se faltar o essencial."""
    arq = pasta_dia / "mundo.json"
    if not arq.exists():
        return None
    m = json.loads(arq.read_text())
    cot = {c["nome"]: c for c in m.get("cotacoes", [])}
    ibov, dolar = cot.get("Ibovespa"), cot.get("Dólar")
    b, w = m.get("brasil") or {}, m.get("mundo") or {}
    if not ibov or not dolar or b.get("valor") is None:
        return None
    if dolar.get("serie") != "extra_dolar":  # dólar do mercado no dia (BRL=X); a série do FRED sai em outro horário
        return None
    brutos = next((p.get("brutos", {}) for r in m.get("regioes", []) for p in r.get("paises", [])
                   if p["nome"] == "Brasil"), {})
    corr = json.loads((pasta_dia / "correspondente.json").read_text()) if (pasta_dia / "correspondente.json").exists() else None
    bc = json.loads((pasta_dia / "bcb.json").read_text()) if (pasta_dia / "bcb.json").exists() else {}
    noticias = todas_as_noticias(corr)
    return {"data": dia, "brasil": b, "mundo": w, "ibov": ibov, "dolar": dolar,
            "queda": brutos.get("bolsa_queda_pct"), "pico": brutos.get("bolsa_pico"), "pico_dia": brutos.get("bolsa_pico_dia"),
            "selic": (bc.get("selic") or {}).get("valor"), "ptax": (bc.get("ptax") or {}).get("valor"),
            "motivo_bolsa": _motivo(noticias, "bolsa"), "motivo_dolar": _motivo(noticias, "moeda")}


def legenda(d: dict) -> str:
    """O texto do balanço que acompanha o card (WhatsApp e Instagram)."""
    dia = pd.Timestamp(d["data"])
    i, u = d["ibov"], d["dolar"]
    linhas = [f"🌡️ FECHAMENTO DO TERMÔMETRO · {dia:%d/%m}", "",
              f"🇧🇷 Brasil em {d['brasil']['valor']} ({d['brasil']['nivel']}) · 🌍 Mundo em {d['mundo']['valor']} "
              f"({d['mundo']['nivel']})", "",
              f"📉 Ibovespa: {_num(i['ultimo'])} pontos ({_var(i['variacao_pct'])})"
              + (f", {_num(d['queda'], 1)}% abaixo do recorde de {pd.Timestamp(d['pico_dia']):%d/%m}"
                 if d.get("queda") and d["queda"] >= 5 and d.get("pico_dia") else "")]
    if d["motivo_bolsa"]:
        linhas.append(f"Por quê: {d['motivo_bolsa']}")
    linhas.append(f"💵 Dólar: R$ {_num(u['ultimo'], 2)} ({_var(u['variacao_pct'])})")
    if d["motivo_dolar"] and d["motivo_dolar"] != d["motivo_bolsa"]:
        linhas.append(f"Por quê: {d['motivo_dolar']}")
    if d.get("selic"):
        linhas.append(f"🏦 Selic {_num(d['selic'], 2)}%" + (f" · PTAX R$ {_num(d['ptax'], 4)}" if d.get("ptax") else "")
                      + " (Banco Central)")
    linhas += ["", f"O porquê de cada número, com as fontes: {config.SITE_URL}/panorama.html",
               "Conteúdo educativo, feito com IA e conferido por regras automáticas. Não é recomendação de investimento."]
    return "\n".join(linhas)


def card(d: dict, caminho: Path) -> None:
    from .grafico import C, FancyBboxPatch, Rectangle, Wedge, _fonte, plt
    plt.rcParams.update({"font.family": _fonte()})
    W, H = 1080, 1350
    fig = plt.figure(figsize=(W / 200, H / 200), dpi=200, facecolor=C["fundo"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    pt = 72 / 200
    y = lambda topo: H - topo  # noqa: E731
    dia = pd.Timestamp(d["data"])

    ax.text(W / 2, y(110), "FECHAMENTO DO TERMÔMETRO", color="#F2C14E", fontsize=50 * pt, weight="bold", ha="center",
            va="center")
    ax.add_patch(FancyBboxPatch((W / 2 - 150, y(205)), 300, 58, boxstyle="round,pad=0,rounding_size=8",
                                color=C["texto"], lw=0))
    ax.text(W / 2, y(176), f"{dia:%d}.{MESES[dia.month - 1]}.{dia:%Y}", color=C["fundo"], fontsize=32 * pt, weight="bold",
            ha="center", va="center")

    # dois medidores: Brasil e mundo
    for k, (quem, rot) in enumerate([("brasil", "BRASIL"), ("mundo", "MUNDO")]):
        v = d[quem]
        cx, cy, r, larg = 285 + k * 510, y(430), 150, 30
        for i, n in enumerate(config.NIVEIS):
            t2, t1 = 180 - 36 * i - 1.2, 180 - 36 * (i + 1) + 1.2
            ax.add_patch(Wedge((cx, cy), r + larg / 2, t1, t2, width=larg, color=n["cor"], lw=0, alpha=1 if n["nome"] == v["nivel"] else .35))
        ang = math.radians(180 - 1.8 * v["valor"])
        ax.plot([cx, cx + 118 * math.cos(ang)], [cy, cy + 118 * math.sin(ang)], color=C["texto"], lw=5 * pt * 2,
                solid_capstyle="round")
        ax.text(cx, y(470), str(v["valor"]), color=C["texto"], fontsize=96 * pt, weight="bold", ha="center", va="top")
        ax.text(cx, y(585), f"{rot} · {v['nivel'].upper()}", color=v["cor"], fontsize=30 * pt, weight="semibold",
                ha="center", va="top")

    def bloco(topo: int, titulo: str, valor: str, variacao: float, texto: str):
        ax.add_patch(FancyBboxPatch((70, y(topo + 270)), W - 140, 270, boxstyle="round,pad=0,rounding_size=18",
                                    color=C["painel"], lw=0))
        ax.text(110, y(topo + 52), titulo, color=C["texto"], fontsize=40 * pt, weight="bold", va="center")
        cor = "#7EC8E3" if variacao < 0 else ("#F28C38" if variacao > 0 else C["suave"])
        ax.text(W - 110, y(topo + 52), _var(variacao), color=cor, fontsize=44 * pt, weight="bold", ha="right", va="center")
        ax.text(W - 110, y(topo + 112), valor, color=C["texto"], fontsize=34 * pt, ha="right", va="center")
        if texto:
            ax.text(110, y(topo + 150), "\n".join(textwrap.wrap(texto, 48)[:3]), color=C["suave"], fontsize=25 * pt,
                    va="top", linespacing=1.3)

    i, u = d["ibov"], d["dolar"]
    extra = (f"{_num(d['queda'], 1)}% abaixo do recorde de {_num(d['pico'])} pontos ({pd.Timestamp(d['pico_dia']):%d/%m}). "
             if d.get("queda") and d["queda"] >= 5 and d.get("pico") else "")
    bloco(660, "IBOVESPA", f"{_num(i['ultimo'])} pts", i["variacao_pct"], extra + (d["motivo_bolsa"] or ""))
    juros = (f"Selic {_num(d['selic'], 2)}% ao ano (Banco Central). " if d.get("selic") else "")
    motivo_dolar = d["motivo_dolar"] if d["motivo_dolar"] != d["motivo_bolsa"] else ""
    bloco(950, "DÓLAR", f"R$ {_num(u['ultimo'], 2)}", u["variacao_pct"], juros + motivo_dolar)

    ax.add_patch(Rectangle((70, y(1262)), W - 140, 2, color=C["linha"], lw=0))
    ax.text(70, y(1300), "TERMÔMETRO DE CRISE", color=C["texto"], fontsize=28 * pt, weight="semibold", va="center")
    ax.text(W - 70, y(1300), "termometrodecrise.com · não é recomendação", color=C["suave"], fontsize=22 * pt,
            ha="right", va="center")
    fig.savefig(caminho, facecolor=C["fundo"])
    plt.close(fig)


def gerar(saida: Path, pasta_diario: Path, dia: str | None) -> dict | None:
    """Gera o card do último fechamento. Devolve {"imagem", "legenda", "data"} ou None."""
    if not dia:
        return None
    d = dados(dia, pasta_diario / dia)
    if not d:
        return None
    (saida / "panorama").mkdir(parents=True, exist_ok=True)
    nome = f"panorama/fechamento-{dia}.png"
    try:
        card(d, saida / nome)
    except Exception as erro:  # noqa: BLE001 — sem card, o panorama sai do mesmo jeito
        print(f"Card do fechamento falhou: {erro}")
        return None
    return {"imagem": nome, "legenda": legenda(d), "data": dia}
