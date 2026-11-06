"""Agente de arte: gera o gráfico histórico e o card para redes sociais (PNG)."""

import math
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle, Wedge  # noqa: E402

from . import config  # noqa: E402

C = config.CORES
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def mes_curto(ref: str) -> str:
    ano, mes = ref.split("-")
    return f"{MESES[int(mes) - 1]}/{ano[2:]}"


def _fonte() -> str:
    nomes = {f.name for f in font_manager.fontManager.ttflist}
    return next((n for n in ("Inter", "IBM Plex Sans", "DejaVu Sans") if n in nomes), "sans-serif")


CURTOS = {"Bolha .com": ".com", "Crise de 2008": "2008", "Covid": "Covid", "Choque de 2022": "2022"}


def historico(resultado: pd.DataFrame, dados: dict, caminho: Path, mobile: bool = False) -> None:
    """Gráfico do índice desde o início. mobile=True gera a versão em pé, com letras maiores."""
    L = (dict(tam=(5.4, 6.4), eixo=[0.1, 0.08, 0.64, 0.75], fs=11, pico=10.5, titulo=17, sub=11, passo=8,
              titulo_y=0.945, sub_y=0.875, rodape=False, topo=112)
         if mobile else
         dict(tam=(10, 5.8), eixo=[0.065, 0.14, 0.82, 0.68], fs=9.5, pico=9, titulo=17, sub=10.5, passo=4,
              titulo_y=0.93, sub_y=0.875, rodape=True, topo=118))
    plt.rcParams.update({"font.family": _fonte()})
    serie = resultado["termometro"]
    topo = L["topo"]
    fig = plt.figure(figsize=L["tam"], dpi=200, facecolor=C["fundo"])
    ax = fig.add_axes(L["eixo"], facecolor=C["fundo"])

    for n in config.NIVEIS:
        baixo, alto = (0 if n["min"] == 0 else n["min"] - 1), n["max"]
        ax.axhspan(baixo, alto, color=n["cor"], alpha=0.14, lw=0)
        ax.add_patch(Rectangle((1.008, baixo / topo), 0.01 if mobile else 0.007, (alto - baixo) / topo,
                               transform=ax.transAxes, color=n["cor"], clip_on=False, lw=0))
        ax.text(1.04 if mobile else 1.022, (baixo + alto) / 2 / topo, n["nome"], transform=ax.transAxes,
                va="center", color=C["suave"], fontsize=L["fs"])

    ax.plot(serie.index, serie.values, color=C["texto"], lw=1.4 if mobile else 1.5,
            solid_joinstyle="round", solid_capstyle="round")

    picos = sorted(dados["picos_historicos"].items(), key=lambda kv: kv[1]["mes"])
    for i, (nome, pico) in enumerate(picos):
        x = pd.Timestamp(pico["mes"] + "-01")
        # picos vizinhos (menos de 3 anos) abrem para lados opostos, para os rótulos não se tocarem;
        # o primeiro pico abre para a direita quando está colado no começo do eixo
        perto_antes = i > 0 and (x - pd.Timestamp(picos[i - 1][1]["mes"] + "-01")).days < 1100
        perto_depois = i < len(picos) - 1 and (pd.Timestamp(picos[i + 1][1]["mes"] + "-01") - x).days < 1100
        no_comeco = (x - serie.index[0]).days < 1100
        if perto_antes or no_comeco:
            lado, dx = "left", 3
        elif perto_depois:
            lado, dx = "right", -3
        else:
            lado, dx = "center", 0
        rotulo = f"{CURTOS.get(nome, nome)}\n{pico['valor']}" if mobile else f"{nome}: {pico['valor']}"
        ax.annotate(rotulo, xy=(x, pico["valor"]), xytext=(dx, 6), textcoords="offset points", ha=lado,
                    va="bottom", color=C["texto"], fontsize=L["pico"], linespacing=1.15)

    fim_x, fim_y = serie.index[-1], serie.iloc[-1]
    ax.plot([fim_x], [fim_y], "o", ms=8, color=dados["cor"], mec=C["fundo"], mew=2, zorder=5)
    ax.annotate(f"{dados['valor']}\n{mes_curto(dados['referencia'])}", xy=(fim_x, fim_y), xytext=(8, 0),
                textcoords="offset points", ha="left", va="center", color=C["texto"], fontsize=L["fs"],
                weight="semibold", linespacing=1.2)

    ax.set_ylim(0, topo)
    ax.set_xlim(serie.index[0], serie.index[-1] + pd.DateOffset(months=60 if mobile else 28))
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    anos = range(serie.index[0].year + 1, serie.index[-1].year + 1, L["passo"])
    ax.set_xticks([pd.Timestamp(f"{a}-01-01") for a in anos], [str(a) for a in anos])
    ax.tick_params(colors=C["suave"], labelsize=L["fs"], length=0, pad=6)
    for lado in ax.spines.values():
        lado.set_visible(False)

    inicio, fim = serie.index[0].year, serie.index[-1].year
    x0 = L["eixo"][0] - (0.04 if mobile else 0)
    fig.text(x0, L["titulo_y"], f"Índice dos mercados globais, {inicio}–{fim}", color=C["texto"], fontsize=L["titulo"],
             weight="semibold")
    subtitulo = ("Índice mensal de estresse dos mercados,\nde 0 a 100. Cada faixa de cor é um nível." if mobile else
                 "Índice mensal de estresse dos mercados, de 0 a 100. Cada faixa de cor é um nível.")
    fig.text(x0, L["sub_y"], subtitulo, color=C["suave"], fontsize=L["sub"], linespacing=1.35)
    if L["rodape"]:
        fig.text(0.065, 0.04, "Fontes: VIX, petróleo Brent, juro de 10 anos dos EUA, S&P 500 e ouro (datahub.io e FRED). "
                 "Teste histórico; não é recomendação de investimento.", color=C["suave"], fontsize=8.5)
    fig.savefig(caminho, facecolor=C["fundo"])
    plt.close(fig)


def card(dados: dict, data_edicao: str, caminho: Path, chamada: str = "Receba o Termômetro todo domingo · link na bio") -> None:
    """Post 1080x1350 (4:5) no mesmo desenho do canvas de identidade visual."""
    fonte = _fonte()
    plt.rcParams.update({"font.family": fonte})
    W, H = 1080, 1350
    fig = plt.figure(figsize=(W / 200, H / 200), dpi=200, facecolor=C["fundo"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    pt = 72 / 200  # 1 pixel do desenho em pontos tipográficos
    y = lambda topo: H - topo  # noqa: E731  (coordenada do desenho, de cima para baixo)

    ax.text(80, y(100), "TERMÔMETRO DE CRISE", color=C["texto"], fontsize=26 * pt, weight="semibold", va="center")
    dia = pd.Timestamp(data_edicao)
    ax.text(W - 80, y(100), f"Semana de {dia:%d/%m/%Y}", color=C["suave"], fontsize=22 * pt, va="center", ha="right")

    s = 860 / 600
    cx, cy, r, larg = 110 + 300 * s, y(192 + 300 * s), 230 * s, 40 * s
    for i, n in enumerate(config.NIVEIS):
        t2, t1 = 180 - 36 * i - 1.07, 180 - 36 * (i + 1) + 1.07
        ax.add_patch(Wedge((cx, cy), r + larg / 2, t1, t2, width=larg, color=n["cor"], lw=0))
    for valor, (tx, ty) in zip(range(0, 101, 20), [(18, 305), (72, 139), (213, 37), (387, 37), (528, 139), (582, 305)]):
        ax.text(110 + tx * s, y(192 + ty * s), str(valor), color=C["suave"], fontsize=14 * s * pt, ha="center", va="baseline")
    ang = math.radians(180 - 1.8 * dados["valor"])
    ax.plot([cx, cx + 190 * s * math.cos(ang)], [cy, cy + 190 * s * math.sin(ang)],
            color=C["texto"], lw=6 * s * pt, solid_capstyle="round")
    ax.add_patch(Circle((cx + r * math.cos(ang), cy + r * math.sin(ang)), 13 * s, fc=dados["cor"],
                        ec=C["fundo"], lw=4 * s * pt, zorder=4))
    ax.add_patch(Circle((cx, cy), 14 * s, color=C["texto"], lw=0, zorder=4))
    ax.add_patch(Circle((cx, cy), 6 * s, color=C["fundo"], lw=0, zorder=5))

    ax.text(W / 2, y(655), str(dados["valor"]), color=C["texto"], fontsize=220 * pt, weight="bold", ha="center", va="top")
    ax.text(W / 2, y(905), dados["nivel"].upper(), color=dados["cor"], fontsize=40 * pt, weight="semibold",
            ha="center", va="top")
    leitura = "\n".join(textwrap.wrap(dados["leitura"], 34))
    ax.text(W / 2, y(985), leitura, color=C["texto"], fontsize=36 * pt, ha="center", va="top", linespacing=1.3)

    ax.add_patch(FancyBboxPatch((80, y(1236)), W - 160, 84, boxstyle="round,pad=0,rounding_size=16",
                                color=C["painel"], lw=0))
    ax.text(W / 2, y(1194), chamada, color=C["texto"],
            fontsize=30 * pt, weight="semibold", ha="center", va="center")
    ax.text(W / 2, y(1272), f"Leitura de {mes_curto(dados['referencia'])} · dados públicos · não é recomendação de investimento",
            color=C["suave"], fontsize=18 * pt, ha="center", va="center")
    fig.savefig(caminho, facecolor=C["fundo"])
    plt.close(fig)
