"""Testa símbolos do Yahoo antes de entrarem no motor: mostra de quando a quando há dados (usado pelo robô do GitHub).

Uso: SIMBOLOS="^IPSA,ECH,KSA" python sondas/simbolos.py
"""

import os
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from termometro.mundo import UA  # noqa: E402

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
AGORA = int(pd.Timestamp.now(tz="UTC").timestamp())
JANELAS = {"desde 1980": {"period1": 315532800, "period2": AGORA, "interval": "1d"},
           "desde 2005": {"period1": 1104537600, "period2": AGORA, "interval": "1d"},
           "range=max": {"range": "max", "interval": "1d"}}

for simbolo in [s.strip() for s in os.environ.get("SIMBOLOS", "").split(",") if s.strip()]:
    for nome, params in JANELAS.items():
        try:
            r = requests.get(URL.format(simbolo), headers=UA, params=params, timeout=40)
            r.raise_for_status()
            res = r.json()["chart"]["result"][0]
            datas = pd.to_datetime(res.get("timestamp", []), unit="s")
            fechamentos = pd.Series(res["indicators"]["quote"][0].get("close", []), dtype=float).dropna()
            meta = res.get("meta", {})
            print(f"{simbolo:14s} {nome:11s} {len(fechamentos):6d} pontos  {datas.min():%Y-%m-%d} a {datas.max():%Y-%m-%d}"
                  f"  {meta.get('currency', '')} {meta.get('longName') or meta.get('shortName') or ''}" if len(datas)
                  else f"{simbolo:14s} {nome:11s} sem pontos")
        except Exception as erro:  # noqa: BLE001 — a sonda só relata
            print(f"{simbolo:14s} {nome:11s} FALHOU: {str(erro)[:90]}")
