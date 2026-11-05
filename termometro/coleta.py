"""Agente de coleta: baixa as séries públicas e grava uma cópia limpa.

Saída: <pasta>/<componente>.csv com as colunas data,valor e <pasta>/coleta.json
com a origem e a data do último dado de cada série.
"""

import io
import json
import os
from pathlib import Path

import pandas as pd
import requests

from . import config

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def baixar_historico(fonte: dict) -> pd.Series:
    resposta = requests.get(fonte["url"], timeout=60)
    resposta.raise_for_status()
    tabela = pd.read_csv(io.StringIO(resposta.text))
    datas = pd.to_datetime(tabela[fonte["data"]], format=fonte.get("formato"), errors="coerce")
    valores = pd.to_numeric(tabela[fonte["valor"]], errors="coerce")
    serie = pd.Series(valores.to_numpy(), index=datas)
    return serie[serie.index.notna()].dropna().sort_index()


def baixar_fred(serie_id: str, chave: str, inicio: pd.Timestamp) -> pd.Series:
    resposta = requests.get(FRED_URL, timeout=60, params={
        "series_id": serie_id, "api_key": chave, "file_type": "json",
        "observation_start": inicio.strftime("%Y-%m-%d"),
    })
    resposta.raise_for_status()
    pontos = {pd.Timestamp(o["date"]): float(o["value"])
              for o in resposta.json()["observations"] if o["value"] not in (".", "")}
    return pd.Series(pontos, dtype=float).sort_index()


def coletar(pasta: Path) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    chave_fred = os.environ.get("FRED_API_KEY", "").strip()
    relatorio = {}
    for nome, fonte in config.FONTES.items():
        serie = baixar_historico(fonte)
        if nome == "sp":
            serie = serie[serie > 0]
        origem = "datahub"
        if chave_fred and nome in config.FRED:
            try:
                inicio = (serie.index.max() - pd.DateOffset(months=13)).to_period("M").to_timestamp()
                recente = baixar_fred(config.FRED[nome], chave_fred, inicio)
                if len(recente):
                    corte = recente.index.min().to_period("M").to_timestamp()
                    serie = pd.concat([serie[serie.index < corte], recente[recente.index >= corte]])
                    origem = "datahub + FRED (diário)"
            except Exception as erro:  # o histórico continua valendo se o FRED falhar
                print(f"Aviso: FRED indisponível para {nome}: {erro}")
        serie.rename("valor").to_csv(pasta / f"{nome}.csv", index_label="data")
        relatorio[nome] = {"origem": origem, "ultimo_dado": serie.index.max().strftime("%Y-%m-%d"),
                           "observacoes": int(len(serie))}
        print(f"{nome:6s} {relatorio[nome]['ultimo_dado']}  {origem}")
    (pasta / "coleta.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=2))
    return relatorio
