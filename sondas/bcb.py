"""Testa os dados oficiais do Banco Central (Selic, PTAX e Focus) e mostra a linha do panorama (usado pelo robô)."""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from termometro import bcb  # noqa: E402

hoje = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
dados = bcb.coletar(hoje)
print(json.dumps(dados, ensure_ascii=False, indent=1))
print("\n" + bcb.linha(dados, hoje))
