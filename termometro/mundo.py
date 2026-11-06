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
    "Chile":          ("América Latina", None, ("yahoo", "CLP=X", False)),
    "Colômbia":       ("América Latina", None, ("yahoo", "COP=X", False)),
    "Peru":           ("América Latina", None, ("yahoo", "PEN=X", False)),
    "Paraguai":       ("América Latina", None, ("yahoo", "PYG=X", False)),
    "Uruguai":        ("América Latina", None, ("yahoo", "UYU=X", False)),
    "Alemanha":       ("Europa", "^GDAXI", ("fred", "DEXUSEU", True)),
    "França":         ("Europa", "^FCHI", ("fred", "DEXUSEU", True)),
    "Reino Unido":    ("Europa", "^FTSE", ("fred", "DEXUSUK", True)),
    "Itália":         ("Europa", "FTSEMIB.MI", ("fred", "DEXUSEU", True)),
    "Espanha":        ("Europa", "^IBEX", ("fred", "DEXUSEU", True)),
    "Portugal":       ("Europa", "PSI20.LS", ("fred", "DEXUSEU", True)),
    "Suíça":          ("Europa", "^SSMI", ("yahoo", "CHF=X", False)),
    "Rússia":         ("Europa", None, ("yahoo", "RUB=X", False)),
    "Turquia":        ("Oriente Médio", "XU100.IS", ("yahoo", "TRY=X", False)),
    "Israel":         ("Oriente Médio", "^TA125.TA", ("yahoo", "ILS=X", False)),
    "Egito":          ("Oriente Médio", None, ("yahoo", "EGP=X", False)),
    # O Yahoo não tem o histórico da Tadawul; o fundo MSCI Arábia Saudita (em dólar) faz o papel da bolsa,
    # e como o rial é atrelado ao dólar, o preço em dólar acompanha o preço local.
    "Arábia Saudita": ("Oriente Médio", "KSA", None),
    "África do Sul":  ("África", "^J203.JO", ("fred", "DEXSFUS", False)),
    "Nigéria":        ("África", None, ("yahoo", "NGN=X", False)),
    "Quênia":         ("África", None, ("yahoo", "KES=X", False)),
    "Marrocos":       ("África", None, ("yahoo", "MAD=X", False)),
    "Japão":          ("Ásia e Pacífico", "^N225", ("fred", "DEXJPUS", False)),
    "China":          ("Ásia e Pacífico", "000001.SS", ("fred", "DEXCHUS", False)),
    "Hong Kong":      ("Ásia e Pacífico", "^HSI", None),
    "Índia":          ("Ásia e Pacífico", "^NSEI", ("fred", "DEXINUS", False)),
    "Coreia do Sul":  ("Ásia e Pacífico", "^KS11", ("fred", "DEXKOUS", False)),
    "Austrália":      ("Ásia e Pacífico", "^AXJO", ("fred", "DEXUSAL", True)),
    "Indonésia":      ("Ásia e Pacífico", "^JKSE", ("yahoo", "IDR=X", False)),
    "Taiwan":         ("Ásia e Pacífico", "^TWII", ("yahoo", "TWD=X", False)),
    "Singapura":      ("Ásia e Pacífico", "^STI", ("yahoo", "SGD=X", False)),
}
REGIOES = ["América do Norte", "América Latina", "Europa", "Oriente Médio", "África", "Ásia e Pacífico"]

# Nomes para leigos, usados nas páginas de cada país
BOLSAS = {"EUA": "S&P 500", "Canadá": "S&P/TSX", "México": "IPC", "Brasil": "Ibovespa", "Argentina": "Merval",
          "Alemanha": "DAX", "França": "CAC 40", "Reino Unido": "FTSE 100", "Turquia": "BIST 100",
          "Israel": "TA-125", "África do Sul": "JSE All Share", "Japão": "Nikkei 225", "China": "Xangai Composto",
          "Hong Kong": "Hang Seng", "Índia": "Nifty 50", "Coreia do Sul": "Kospi", "Austrália": "ASX 200",
          "Itália": "FTSE MIB", "Espanha": "IBEX 35",
          "Portugal": "PSI", "Suíça": "SMI", "Arábia Saudita": "MSCI Arábia Saudita", "Indonésia": "Jakarta Composite",
          "Taiwan": "Taiex", "Singapura": "Straits Times"}
MOEDAS = {"Canadá": "dólar canadense", "México": "peso mexicano", "Brasil": "real", "Argentina": "peso argentino",
          "Alemanha": "euro", "França": "euro", "Reino Unido": "libra", "Turquia": "lira turca", "Israel": "shekel",
          "Egito": "libra egípcia", "África do Sul": "rand", "Nigéria": "naira", "Japão": "iene", "China": "yuan",
          "Índia": "rupia", "Coreia do Sul": "won", "Austrália": "dólar australiano", "Chile": "peso chileno",
          "Colômbia": "peso colombiano", "Peru": "sol", "Paraguai": "guarani", "Uruguai": "peso uruguaio",
          "Itália": "euro", "Espanha": "euro", "Portugal": "euro", "Suíça": "franco suíço", "Rússia": "rublo",
          "Quênia": "xelim queniano", "Marrocos": "dirham", "Indonésia": "rupia indonésia",
          "Taiwan": "dólar taiwanês", "Singapura": "dólar de Singapura"}

# Épocas conhecidas, para dar nome aos picos do histórico: (país, região ou "*", início, fim, rótulo)
EPOCAS = [
    ("*", "2008-09", "2009-06", "crise financeira global de 2008"),
    ("*", "2020-02", "2020-06", "pandemia de Covid"),
    ("*", "2011-08", "2011-12", "crise da dívida europeia"),
    ("*", "2015-08", "2016-02", "turbulência na China e queda das commodities"),
    ("*", "2025-04", "2025-04", "tarifaço dos EUA"),
    ("*", "2022-05", "2022-10", "alta global de juros e inflação"),
    ("EUA", "2001-09", "2002-10", "11 de setembro e fim da bolha da internet"),
    ("EUA", "2022-01", "2022-10", "inflação alta e subida de juros"),
    ("Europa", "2022-02", "2022-10", "guerra na Ucrânia e crise de energia"),
    ("Alemanha", "2022-02", "2022-10", "guerra na Ucrânia e crise de energia"),
    ("França", "2022-02", "2022-10", "guerra na Ucrânia e crise de energia"),
    ("Reino Unido", "2016-06", "2016-10", "Brexit"),
    ("Reino Unido", "2022-09", "2022-10", "crise do minipacote fiscal"),
    ("Brasil", "1998-08", "1999-03", "crise russa e desvalorização do real"),
    ("Brasil", "2002-05", "2002-12", "eleição de 2002"),
    ("Brasil", "2015-01", "2016-03", "recessão e crise política"),
    ("Brasil", "2017-05", "2017-05", "delação da JBS"),
    ("Brasil", "2024-11", "2024-12", "pacote fiscal e alta do dólar"),
    ("Argentina", "2001-06", "2002-12", "corralito e moratória"),
    ("Argentina", "2018-04", "2018-10", "crise cambial e acordo com o FMI"),
    ("Argentina", "2019-08", "2019-09", "choque após as primárias de 2019"),
    ("Argentina", "2023-08", "2023-12", "desvalorizações de 2023"),
    ("México", "2016-11", "2017-01", "eleição de Trump nos EUA"),
    ("México", "2024-06", "2024-08", "eleição e reforma judicial"),
    ("Turquia", "2018-05", "2018-10", "crise da lira de 2018"),
    ("Turquia", "2021-10", "2022-01", "queda da lira de 2021"),
    ("Turquia", "2025-03", "2025-04", "prisão do prefeito de Istambul"),
    ("Israel", "2000-09", "2000-12", "início da segunda intifada"),
    ("Israel", "2023-10", "2023-11", "guerra após o ataque de 7 de outubro"),
    ("Egito", "2016-11", "2016-12", "flutuação da libra egípcia"),
    ("Egito", "2022-03", "2023-01", "desvalorizações de 2022"),
    ("Egito", "2024-03", "2024-03", "desvalorização e acordo com o FMI"),
    ("Nigéria", "2016-06", "2016-08", "flexibilização do câmbio"),
    ("Nigéria", "2023-06", "2024-03", "unificação do câmbio e queda da naira"),
    ("África do Sul", "2015-12", "2016-01", "troca do ministro das Finanças"),
    ("China", "2015-06", "2016-02", "estouro da bolsa chinesa"),
    ("Japão", "2011-03", "2011-04", "terremoto e tsunami"),
    ("Japão", "2024-08", "2024-08", "desmonte das operações com o iene"),
    ("Coreia do Sul", "2024-12", "2025-01", "crise da lei marcial"),
    ("Índia", "2013-06", "2013-09", "fuga de capitais de 2013"),
    ("Rússia", "2014-11", "2015-01", "queda do rublo de 2014"),
    ("Rússia", "2022-02", "2022-04", "invasão da Ucrânia e sanções"),
    ("Suíça", "2015-01", "2015-02", "fim do piso do franco"),
    ("Espanha", "2012-05", "2012-08", "crise bancária espanhola"),
    ("Itália", "2011-07", "2011-12", "crise da dívida europeia"),
    ("Chile", "2019-10", "2019-12", "protestos de 2019"),
]

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
    for _ in range(1):  # o FRED às vezes não responde para os servidores do GitHub; não vale esperar muito
        try:
            r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": serie}, headers=UA,
                             timeout=12)
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


# Só para a faixa do topo: (arquivo, símbolo no Yahoo)
EXTRAS = {"extra_dow_jones": "^DJI", "extra_nasdaq": "^IXIC", "extra_bitcoin": "BTC-USD",
          "extra_petroleo": "BZ=F", "extra_ouro": "GC=F"}


def yahoo_recente(simbolo: str, dias: int = 40) -> pd.Series:
    agora = int(pd.Timestamp.now(tz="UTC").timestamp())
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}", headers=UA, timeout=30,
                     params={"period1": agora - dias * 86400, "period2": agora, "interval": "1d"})
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    datas = pd.to_datetime(res["timestamp"], unit="s").normalize()
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=datas, dtype=float)
    return s[s > 0].dropna().groupby(level=0).last().sort_index()


def coletar_extras(pasta: Path, relatorio: dict) -> None:
    for nome, simbolo in EXTRAS.items():
        try:
            yahoo_recente(simbolo).rename("valor").to_csv(pasta / f"{nome}.csv", index_label="data")
            relatorio[nome] = "ok"
        except Exception as erro:  # a faixa só perde um item; o termômetro não depende disso
            relatorio[nome] = f"faixa sem {simbolo}: {type(erro).__name__}"


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
    coletar_extras(pasta, relatorio)
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


def brutos_do_pais(pasta: Path, pais: str, sinais: pd.DataFrame) -> dict:
    """Os mesmos sinais em unidades que um leigo entende, para explicar a leitura do país."""
    saida = {}
    if "bolsa" in sinais and sinais["bolsa"].notna().any():
        d = pd.read_csv(pasta / f"{arquivo(pais)}_bolsa.csv", parse_dates=["data"]).set_index("data")["valor"]
        saida["bolsa_queda_pct"] = round(100 * float(sinais["bolsa"].dropna().iloc[-1]), 1)
        saida["bolsa_ultimo_dia"] = d.index[-1].strftime("%Y-%m-%d")
    if "volatilidade" in sinais and sinais["volatilidade"].notna().any():
        anual = float(sinais["volatilidade"].dropna().iloc[-1])
        saida["oscilacao_diaria_pct"] = round(100 * anual / math.sqrt(252), 2)  # quanto a bolsa anda num dia típico
    moeda_csv = pasta / f"{arquivo(pais)}_moeda.csv"
    if moeda_csv.exists():
        m = pd.read_csv(moeda_csv, parse_dates=["data"]).set_index("data")["valor"]
        variacao = m.resample("MS").mean().pct_change(3, fill_method=None).dropna()
        if not variacao.empty:  # positivo = moeda local mais fraca (mais moeda por dólar)
            saida["moeda_variacao_3m_pct"] = round(100 * float(variacao.iloc[-1]), 1)
            saida["moeda_ultimo_dia"] = m.index[-1].strftime("%Y-%m-%d")
    saida["desde"] = {k: int(s.first_valid_index().year) for k, s in sinais.items() if s.notna().any()}
    return saida


def picos(serie: pd.Series, quem: str, regiao: str | None = None, n: int = 3, minimo: float = 61) -> list[dict]:
    """Os n meses mais tensos do passado (um por episódio, separados por 12 meses), com o nome da época."""
    s = serie.dropna()
    if s.empty:
        return []
    passado = s[s.index <= s.index[-1] - pd.DateOffset(months=6)]  # o agora não conta como "já foi pior"
    escolhidos = []
    for mes, valor in passado.sort_values(ascending=False).items():
        if valor < minimo or len(escolhidos) == n:
            break
        if all(abs((mes - outro).days) > 365 for outro, _ in escolhidos):
            escolhidos.append((mes, valor))
    saida = []
    for mes, valor in sorted(escolhidos, key=lambda x: -x[1]):
        chave = mes.strftime("%Y-%m")
        rotulo = next((r for q, ini, fim, r in EPOCAS if q == quem and ini <= chave <= fim), None) or \
            next((r for q, ini, fim, r in EPOCAS if q == regiao and ini <= chave <= fim), None) or \
            next((r for q, ini, fim, r in EPOCAS if q == "*" and ini <= chave <= fim), None)
        saida.append({"mes": chave, "valor": round(float(valor)), "epoca": rotulo})
    return saida


def slug(nome: str) -> str:
    return arquivo(nome).replace("_", "-").replace("(", "").replace(")", "")


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
        detalhes[pais]["_brutos"] = brutos_do_pais(pasta, pais, sinais)
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
    def pais(p: str, regiao: str) -> dict:
        det = dict(detalhes.get(p, {}))
        brutos = det.pop("_brutos", {})
        return {"nome": p, "slug": slug(p), **(leitura(por_pais[p]) or {"valor": None}), "sinais": det,
                "brutos": brutos, "bolsa_nome": BOLSAS.get(p), "moeda_nome": MOEDAS.get(p),
                "picos": picos(por_pais[p], p, regiao)}
    regioes = []
    for regiao in REGIOES:
        membros = [p for p, (r, _, _) in PAISES.items() if r == regiao and p in por_pais]
        regioes.append({"nome": regiao, "slug": slug(regiao), **(leitura(por_regiao[regiao]) or {"valor": None}),
                        "picos": picos(por_regiao[regiao], regiao),
                        "paises": [pais(p, regiao) for p in membros]})
    brasil = leitura(por_pais["Brasil"]) if "Brasil" in por_pais else None
    sinais_brasil = {k: v for k, v in detalhes.get("Brasil", {}).items() if not k.startswith("_")}
    return {"regioes": regioes, "brasil": {**(brasil or {}), "sinais": sinais_brasil},
            "mundo": leitura(por_regiao["Mundo (média das regiões)"])}


def teste_historico(por_pais: pd.DataFrame, por_regiao: pd.DataFrame) -> list[dict]:
    tabela = pd.concat([por_pais, por_regiao], axis=1)
    linhas = []
    for rotulo, quem, ini, fim in EPISODIOS:
        trecho = tabela.loc[ini:fim, quem].dropna() if quem in tabela else pd.Series(dtype=float)
        linhas.append({"episodio": rotulo, "maximo": None if trecho.empty else round(float(trecho.max())),
                       "mes": None if trecho.empty else trecho.idxmax().strftime("%Y-%m")})
    return linhas


# Faixa de mercados: (rótulo, arquivo, tipo). "brl" = preço em reais calculado a partir das moedas contra o dólar.
FAIXA = [("Ibovespa", "brasil_bolsa", "pontos"), ("Dólar", "brasil_moeda", "brl"), ("Euro", "euro", "brl"),
         ("Dow Jones", "extra_dow_jones", "pontos"), ("S&P 500", "eua_bolsa", "pontos"), ("Nasdaq", "extra_nasdaq", "pontos"),
         ("Bitcoin", "extra_bitcoin", "usd"), ("Petróleo Brent", "extra_petroleo", "usd"), ("Ouro", "extra_ouro", "usd"),
         ("DAX", "alemanha_bolsa", "pontos"), ("Nikkei", "japao_bolsa", "pontos"), ("Merval", "argentina_bolsa", "pontos")]


def cotacoes(pasta: Path) -> list[dict]:
    """Último fechamento e variação do dia de alguns mercados, para a faixa do topo do site."""
    def serie(nome: str) -> pd.Series | None:
        caminho = pasta / f"{nome}.csv"
        if not caminho.exists():
            return None
        return pd.read_csv(caminho, parse_dates=["data"]).set_index("data")["valor"].dropna()
    saida = []
    for rotulo, nome, tipo in FAIXA:
        if nome == "euro":  # euro em reais = (reais por dólar) / (euros por dólar)
            brl, eur = serie("brasil_moeda"), serie("alemanha_moeda")
            s = (brl / eur).dropna() if brl is not None and eur is not None else None
        else:
            s = serie(nome)
        if s is None or len(s) < 2:
            continue
        ultimo, anterior = float(s.iloc[-1]), float(s.iloc[-2])
        saida.append({"nome": rotulo, "ultimo": round(ultimo, 4 if tipo in ("brl", "usd") else 2), "tipo": tipo,
                      "variacao_pct": round(100 * (ultimo / anterior - 1), 2), "data": s.index[-1].strftime("%Y-%m-%d")})
    return saida


def rodar(pasta_dados: Path, pasta_saida: Path) -> dict:
    pasta_saida.mkdir(parents=True, exist_ok=True)
    por_pais, por_regiao, detalhes = calcular(pasta_dados)
    por_pais.to_csv(pasta_saida / "mundo_paises.csv")
    por_regiao.to_csv(pasta_saida / "mundo_regioes.csv")
    dados = {**resumo(por_pais, por_regiao, detalhes), "cotacoes": cotacoes(pasta_dados),
             "teste_historico": teste_historico(por_pais, por_regiao)}
    (pasta_saida / "mundo.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1))
    return dados
