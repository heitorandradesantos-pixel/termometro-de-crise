"""Sonda: testa quais fontes de dados mundiais respondem de dentro do robô do GitHub.

Não muda nada no site. Só imprime, para cada fonte, se respondeu, desde quando tem
histórico e qual o último dado. Roda com: python sondas/fontes_mundiais.py
"""

import io
import json
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

UA = {"User-Agent": "termometro-de-crise/1.0 (+https://github.com/heitorandradesantos-pixel/termometro-de-crise)"}

# Bolsas por país (Yahoo Finance, gráfico diário)
BOLSAS = {
    "EUA": "^GSPC", "Canadá": "^GSPTSE", "Brasil": "^BVSP", "México": "^MXX", "Argentina": "^MERV",
    "Chile": "^IPSA", "Alemanha": "^GDAXI", "França": "^FCHI", "Reino Unido": "^FTSE", "Zona do euro": "^STOXX50E",
    "Japão": "^N225", "China": "000001.SS", "Hong Kong": "^HSI", "Índia": "^NSEI", "Coreia do Sul": "^KS11",
    "Austrália": "^AXJO", "Arábia Saudita": "^TASI.SR", "Israel": "^TA125.TA", "Turquia": "XU100.IS",
    "África do Sul": "^J203.JO", "Egito": "^CASE30", "Nigéria": "^NGSE",
}
# Moedas contra o dólar (FRED, CSV público sem chave)
MOEDAS_FRED = {
    "Real": "DEXBZUS", "Peso mexicano": "DEXMXUS", "Euro": "DEXUSEU", "Libra": "DEXUSUK", "Iene": "DEXJPUS",
    "Yuan": "DEXCHUS", "Rupia": "DEXINUS", "Won": "DEXKOUS", "Rand": "DEXSFUS", "Dólar canadense": "DEXCAUS",
    "Dólar global (índice)": "DTWEXBGS", "Crédito EUA (BAA-10a)": "BAA10Y", "High yield EUA": "BAMLH0A0HYM2",
}
# Moedas de emergentes sem série no FRED (Yahoo)
MOEDAS_YAHOO = {"Peso argentino": "ARS=X", "Lira turca": "TRY=X", "Naira": "NGN=X", "Libra egípcia": "EGP=X",
                "Shekel": "ILS=X", "Rial saudita": "SAR=X"}


def yahoo(simbolo: str) -> pd.Series:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}"
    r = requests.get(url, params={"range": "max", "interval": "1mo"}, headers=UA, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    datas = pd.to_datetime(res["timestamp"], unit="s")
    return pd.Series(res["indicators"]["quote"][0]["close"], index=datas).dropna()


def fred_csv(serie: str) -> pd.Series:
    r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": serie}, headers=UA, timeout=30)
    r.raise_for_status()
    t = pd.read_csv(io.StringIO(r.text))
    return pd.to_numeric(t.iloc[:, 1], errors="coerce").set_axis(pd.to_datetime(t.iloc[:, 0])).dropna()


def stooq(simbolo: str) -> pd.Series:
    r = requests.get("https://stooq.com/q/d/l/", params={"s": simbolo, "i": "m"}, headers=UA, timeout=30)
    r.raise_for_status()
    t = pd.read_csv(io.StringIO(r.text))
    return t.set_index(pd.to_datetime(t["Date"]))["Close"].dropna()


def bcb(codigo: int) -> pd.Series:
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/24"
    r = requests.get(url, params={"formato": "json"}, headers=UA, timeout=30)
    r.raise_for_status()
    t = pd.DataFrame(r.json())
    return pd.to_numeric(t["valor"]).set_axis(pd.to_datetime(t["data"], dayfirst=True))


def gdelt(pais_fips: str) -> pd.Series:
    consulta = f"(war OR attack OR missile OR sanctions OR coup OR protest) sourcecountry:{pais_fips}"
    r = requests.get("https://api.gdeltproject.org/api/v2/doc/doc", headers=UA, timeout=60,
                     params={"query": consulta, "mode": "timelinevol", "timespan": "120m", "format": "json"})
    r.raise_for_status()
    pontos = r.json()["timeline"][0]["data"]
    return pd.Series({pd.Timestamp(p["date"][:8]): p["value"] for p in pontos})


def testar(rotulo: str, funcao, *args) -> dict:
    try:
        s = funcao(*args)
        info = {"ok": len(s) > 0, "inicio": str(s.index.min())[:10], "fim": str(s.index.max())[:10], "pontos": len(s)}
    except Exception as erro:  # a sonda só registra
        info = {"ok": False, "erro": f"{type(erro).__name__}: {str(erro)[:120]}"}
    marca = "OK  " if info["ok"] else "FALHOU"
    detalhe = f"{info.get('inicio')} → {info.get('fim')} ({info.get('pontos')} pontos)" if info["ok"] else info["erro"]
    print(f"{marca} {rotulo:38s} {detalhe}")
    return {"fonte": rotulo, **info}


def main() -> None:
    resultados = []
    print("== Bolsas (Yahoo)")
    resultados += [testar(f"Yahoo {p} {s}", yahoo, s) for p, s in BOLSAS.items()]
    print("== Moedas e crédito (FRED, sem chave)")
    resultados += [testar(f"FRED {n} {s}", fred_csv, s) for n, s in MOEDAS_FRED.items()]
    print("== Moedas (Yahoo)")
    resultados += [testar(f"Yahoo {n} {s}", yahoo, s) for n, s in MOEDAS_YAHOO.items()]
    print("== Alternativas")
    resultados += [testar("Stooq Ibovespa ^bvp", stooq, "^bvp"), testar("Stooq DAX ^dax", stooq, "^dax")]
    print("== Brasil (Banco Central, SGS)")
    resultados += [testar("BCB Selic meta 432", bcb, 432), testar("BCB dólar PTAX 1", bcb, 1),
                   testar("BCB IPCA 433", bcb, 433)]
    print("== Tensão geopolítica (GDELT)")
    resultados += [testar(f"GDELT {p}", gdelt, p) for p in ("US", "BR", "IS", "UP", "CH", "IR")]
    ok = sum(r["ok"] for r in resultados)
    print(f"\n{ok} de {len(resultados)} fontes responderam ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)")
    with open("sondas/resultado.json", "w") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
