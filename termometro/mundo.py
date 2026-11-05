"""Termômetro Mundial: um termômetro por país e por região (protótipo v1).

Para cada país, três sinais de estresse, todos mensais:
- Bolsa: queda do índice principal desde a máxima de 12 meses;
- Sobe e desce: volatilidade realizada da bolsa no mês (a partir dos fechamentos diários);
- Moeda: variação da moeda contra o dólar em 3 meses, em qualquer direção.
Cada sinal vira o percentil do próprio histórico do país (sem olhar o futuro), o
termômetro do país é a média dos sinais disponíveis e o da região é a média dos países.

Fontes: Yahoo Finance (bolsas e algumas moedas) e FRED (câmbio). Antes de cobrar por
acesso ou exibir anúncios em escala, trocar por fonte com licença comercial (ver README).
"""

import io
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import config

UA = {"User-Agent": "termometro-de-crise/1.0"}
MINIMO_MESES = 60  # 5 anos de histórico do país antes da primeira leitura

# país: (região, índice no Yahoo, (fonte da moeda, código, inverter?))
# "inverter" = a série vem como dólares por moeda local (euro, libra, dólar australiano).
PAISES = {
    "EUA":            ("América do Norte", "^GSPC", None),
    "Canadá":         ("América do Norte", "^GSPTSE", ("fred", "DEXCAUS", False)),
    "México":         ("América Latina", "^MXX", ("fred", "DEXMXUS", False)),
    "Brasil":         ("América Latina", "^BVSP", ("fred", "DEXBZUS", False)),
    "Argentina":      ("América Latina", "^MERV", ("yahoo", "ARS=X", False)),
    "Alemanha":       ("Europa", "^GDAXI", ("fred", "DEXUSEU", True)),
    "França":         ("Europa", "^FCHI", ("fred", "DEXUSEU", True)),
    "Reino Unido":    ("Europa", "^FTSE", ("fred", "DEXUSUK", True)),
    "Turquia":        ("Oriente Médio", "XU100.IS", ("yahoo", "TRY=X", False)),
    "Israel":         ("Oriente Médio", "^TA125.TA", ("yahoo", "ILS=X", False)),
    "Egito":          ("Oriente Médio", None, ("yahoo", "EGP=X", False)),
    "África do Sul":  ("África", "^J203.JO", ("fred", "DEXSFUS", False)),
    "Nigéria":        ("África", None, ("yahoo", "NGN=X", False)),
    "Japão":          ("Ásia e Pacífico", "^N225", ("fred", "DEXJPUS", False)),
    "China":          ("Ásia e Pacífico", "000001.SS", ("fred", "DEXCHUS", False)),
    "Hong Kong":      ("Ásia e Pacífico", "^HSI", None),
    "Índia":          ("Ásia e Pacífico", "^NSEI", ("fred", "DEXINUS", False)),
    "Coreia do Sul":  ("Ásia e Pacífico", "^KS11", ("fred", "DEXKOUS", False)),
    "Austrália":      ("Ásia e Pacífico", "^AXJO", ("fred", "DEXUSAL", True)),
}
REGIOES = ["América do Norte", "América Latina", "Europa", "Oriente Médio", "África", "Ásia e Pacífico"]

# Episódios para o teste histórico: (rótulo, país ou região, início, fim)
EPISODIOS = [
    ("Brasil, eleição de 2002", "Brasil", "2002-06", "2002-12"),
    ("Brasil, 2008", "Brasil", "2008-09", "2009-03"),
    ("Brasil, recessão de 2015", "Brasil", "2015-08", "2016-01"),
    ("Brasil, Covid", "Brasil", "2020-02", "2020-05"),
    ("Argentina, 2001", "Argentina", "2001-06", "2002-06"),
    ("Argentina, 2018", "Argentina", "2018-04", "2018-10"),
    ("Turquia, 2018", "Turquia", "2018-05", "2018-10"),
    ("Turquia, 2021", "Turquia", "2021-10", "2022-01"),
    ("China, 2015", "China", "2015-06", "2016-02"),
    ("Europa, 2011", "Europa", "2011-07", "2011-12"),
    ("América Latina, 2008", "América Latina", "2008-09", "2009-03"),
    ("Ásia e Pacífico, 2008", "Ásia e Pacífico", "2008-09", "2009-03"),
    ("Oriente Médio, 2008", "Oriente Médio", "2008-09", "2009-03"),
    ("África, Covid", "África", "2020-02", "2020-05"),
    ("Brasil, ano calmo de 2019", "Brasil", "2019-01", "2019-12"),
    ("Europa, ano calmo de 2017", "Europa", "2017-01", "2017-12"),
]


# ---------------------------------------------------------------- coleta
# Mesma moeda no Yahoo, na mesma direção da série do FRED (reserva se o FRED não responder)
YAHOO_RESERVA = {"DEXCAUS": "CAD=X", "DEXMXUS": "MXN=X", "DEXBZUS": "BRL=X", "DEXUSEU": "EURUSD=X",
                 "DEXUSUK": "GBPUSD=X", "DEXSFUS": "ZAR=X", "DEXJPUS": "JPY=X", "DEXCHUS": "CNY=X",
                 "DEXINUS": "INR=X", "DEXKOUS": "KRW=X", "DEXUSAL": "AUDUSD=X"}


def yahoo_diario(simbolo: str) -> pd.Series:
    # Com range=max o Yahoo devolve pontos espaçados; com datas explícitas devolve todos os dias.
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}", headers=UA, timeout=60,
                     params={"period1": 315532800, "period2": int(pd.Timestamp.now(tz="UTC").timestamp()),
                             "interval": "1d"})
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    datas = pd.to_datetime(res["timestamp"], unit="s").normalize()
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=datas, dtype=float)
    return s[s > 0].dropna().groupby(level=0).last().sort_index()


def fred_diario(serie: str) -> pd.Series:
    """FRED com duas tentativas curtas; se não responder, usa a mesma moeda no Yahoo."""
    for _ in range(2):
        try:
            r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": serie}, headers=UA,
                             timeout=25)
            r.raise_for_status()
            break
        except requests.RequestException as erro:
            print(f"  FRED {serie} não respondeu ({type(erro).__name__})")
    else:
        if serie in YAHOO_RESERVA:
            print(f"  usando {YAHOO_RESERVA[serie]} do Yahoo no lugar de {serie}")
            return yahoo_diario(YAHOO_RESERVA[serie])
        raise RuntimeError(f"FRED {serie} indisponível e sem reserva")
    t = pd.read_csv(io.StringIO(r.text))
    s = pd.to_numeric(t.iloc[:, 1], errors="coerce").set_axis(pd.to_datetime(t.iloc[:, 0]))
    return s[s > 0].dropna().sort_index()


def coletar(pasta: Path) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    relatorio = {}
    for pais, (_, indice, moeda) in PAISES.items():
        for tipo, buscar in (("bolsa", indice and (lambda i=indice: yahoo_diario(i))),
                             ("moeda", moeda and (lambda m=moeda: (fred_diario if m[0] == "fred" else yahoo_diario)(m[1])))):
            if not buscar:
                continue
            try:
                s = buscar()
                if tipo == "moeda" and moeda[2]:
                    s = 1 / s  # sempre moeda local por dólar: subir = moeda local mais fraca
                s.rename("valor").to_csv(pasta / f"{arquivo(pais)}_{tipo}.csv", index_label="data")
                relatorio[f"{pais} {tipo}"] = f"{s.index.min():%Y-%m} a {s.index.max():%Y-%m-%d} ({len(s)})"
            except Exception as erro:  # um país sem dado não derruba os outros
                relatorio[f"{pais} {tipo}"] = f"FALHOU: {erro}"
            print(f"{pais:15s} {tipo:6s} {relatorio[f'{pais} {tipo}']}")
    (pasta / "coleta_mundo.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=1))
    return relatorio


def arquivo(pais: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", pais).encode("ascii", "ignore").decode().lower().replace(" ", "_")


# ---------------------------------------------------------------- cálculo
def percentil(serie: pd.Series) -> pd.Series:
    valores, saida = serie.to_numpy(), []
    for i, x in enumerate(valores):
        janela = serie.iloc[: i + 1].dropna()
        if pd.isna(x) or len(janela) < MINIMO_MESES:
            saida.append(np.nan)
        else:
            saida.append(100 * ((janela < x).mean() + (janela == x).mean() / 2))
    return pd.Series(saida, index=serie.index)


def sinais_do_pais(pasta: Path, pais: str) -> pd.DataFrame:
    sinais = {}
    bolsa_csv = pasta / f"{arquivo(pais)}_bolsa.csv"
    if bolsa_csv.exists():
        d = pd.read_csv(bolsa_csv, parse_dates=["data"]).set_index("data")["valor"]
        mensal = d.resample("MS").last()
        sinais["bolsa"] = 1 - mensal / mensal.rolling(12, min_periods=1).max()
        retornos = np.log(d).diff()
        sinais["volatilidade"] = retornos.resample("MS").std() * math.sqrt(252)
    moeda_csv = pasta / f"{arquivo(pais)}_moeda.csv"
    if moeda_csv.exists():
        m = pd.read_csv(moeda_csv, parse_dates=["data"]).set_index("data")["valor"].resample("MS").mean()
        sinais["moeda"] = m.pct_change(3, fill_method=None).abs()
    return pd.DataFrame(sinais)


def calcular(pasta: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Devolve (termômetro por país, por região, detalhes do mês mais recente)."""
    paises, detalhes = {}, {}
    for pais in PAISES:
        sinais = sinais_do_pais(pasta, pais)
        if sinais.empty:
            continue
        pct = sinais.apply(percentil)
        paises[pais] = pct.mean(axis=1, skipna=True).where(pct.notna().sum(axis=1) >= 1)
        ultimo = pct.dropna(how="all").iloc[-1] if pct.dropna(how="all").shape[0] else pd.Series(dtype=float)
        detalhes[pais] = {k: (None if pd.isna(v) else round(float(v))) for k, v in ultimo.items()}
    por_pais = pd.DataFrame(paises).sort_index()
    regioes = {}
    for regiao in REGIOES:
        membros = [p for p, (r, _, _) in PAISES.items() if r == regiao and p in por_pais]
        bloco = por_pais[membros]
        regioes[regiao] = bloco.mean(axis=1, skipna=True).where(bloco.notna().sum(axis=1) >= min(2, len(membros)))
    por_regiao = pd.DataFrame(regioes)
    por_regiao["Mundo (média das regiões)"] = por_regiao[REGIOES].mean(axis=1, skipna=True)
    return por_pais.round(1), por_regiao.round(1), detalhes


def resumo(por_pais: pd.DataFrame, por_regiao: pd.DataFrame, detalhes: dict) -> dict:
    def leitura(serie: pd.Series) -> dict | None:
        s = serie.dropna()
        if s.empty:
            return None
        nivel = config.nivel_de(s.iloc[-1])
        return {"valor": round(float(s.iloc[-1])), "nivel": nivel["nome"], "cor": nivel["cor"],
                "referencia": s.index[-1].strftime("%Y-%m"),
                "mes_anterior": round(float(s.iloc[-2])) if len(s) > 1 else None}
    regioes = []
    for regiao in REGIOES:
        membros = [p for p, (r, _, _) in PAISES.items() if r == regiao and p in por_pais]
        regioes.append({"nome": regiao, **(leitura(por_regiao[regiao]) or {"valor": None}),
                        "paises": [{"nome": p, **(leitura(por_pais[p]) or {"valor": None}), "sinais": detalhes.get(p, {})}
                                   for p in membros]})
    brasil = leitura(por_pais["Brasil"]) if "Brasil" in por_pais else None
    return {"regioes": regioes, "brasil": {**(brasil or {}), "sinais": detalhes.get("Brasil", {})},
            "mundo": leitura(por_regiao["Mundo (média das regiões)"])}


def teste_historico(por_pais: pd.DataFrame, por_regiao: pd.DataFrame) -> list[dict]:
    tabela = pd.concat([por_pais, por_regiao], axis=1)
    linhas = []
    for rotulo, quem, ini, fim in EPISODIOS:
        trecho = tabela.loc[ini:fim, quem].dropna() if quem in tabela else pd.Series(dtype=float)
        linhas.append({"episodio": rotulo, "maximo": None if trecho.empty else round(float(trecho.max())),
                       "mes": None if trecho.empty else trecho.idxmax().strftime("%Y-%m")})
    return linhas


def rodar(pasta_dados: Path, pasta_saida: Path) -> dict:
    pasta_saida.mkdir(parents=True, exist_ok=True)
    por_pais, por_regiao, detalhes = calcular(pasta_dados)
    por_pais.to_csv(pasta_saida / "mundo_paises.csv")
    por_regiao.to_csv(pasta_saida / "mundo_regioes.csv")
    dados = {**resumo(por_pais, por_regiao, detalhes), "teste_historico": teste_historico(por_pais, por_regiao)}
    (pasta_saida / "mundo.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1))
    return dados
