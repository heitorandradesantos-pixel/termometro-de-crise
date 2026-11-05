"""Agente analista: calcula o Termômetro de Crise (0 a 100) a partir dos dados coletados.

Método (v1):
- cada componente vira o percentil do próprio histórico desde 1990 (quanto maior, mais estresse);
- energia, juros e ouro contam choques nos dois sentidos, porque em crises de liquidez
  (2008, 2020) petróleo e ouro despencam, e isso também é estresse;
- o índice é a média ponderada dos percentis; os pesos ausentes são redistribuídos.
Teste histórico (dados mensais 1999–2026): 2008 chegou a 96, Covid a 94, 2022 a 88;
nenhum ano calmo (2005, 2017, 2019, 2021) entrou na faixa Crise.
"""

import json
from pathlib import Path

import pandas as pd

from . import config


def mensal(serie: pd.Series) -> pd.Series:
    return serie.dropna().sort_index().resample("MS").mean()


def carregar(pasta: Path) -> dict:
    series = {}
    for nome in config.FONTES:
        tabela = pd.read_csv(pasta / f"{nome}.csv", parse_dates=["data"]).set_index("data")["valor"]
        series[nome] = mensal(pd.to_numeric(tabela, errors="coerce"))
    return series


def componentes_brutos(d: dict) -> pd.DataFrame:
    return pd.DataFrame({
        "energia": (d["brent"] / d["brent"].rolling(12).mean() - 1).abs(),
        "juros": (d["juros"] - d["juros"].shift(3)).abs(),
        "volatilidade": d["vix"],
        "acoes": 1 - d["sp"] / d["sp"].rolling(12, min_periods=1).max(),
        "ouro": d["ouro"].pct_change(3, fill_method=None).abs(),
    })


def percentil_historico(serie: pd.Series) -> pd.Series:
    """Percentil (0–100) de cada mês contra todo o histórico desde 1990 até ele (sem olhar o futuro)."""
    serie = serie.loc[config.INICIO_REFERENCIA:]
    saida = []
    for i, x in enumerate(serie.to_numpy()):
        janela = serie.iloc[: i + 1].dropna()
        if pd.isna(x) or len(janela) < config.MINIMO_MESES:
            saida.append(float("nan"))
            continue
        saida.append(100 * ((janela < x).mean() + (janela == x).mean() / 2))
    return pd.Series(saida, index=serie.index)


def calcular(brutos: pd.DataFrame) -> pd.DataFrame:
    pct = brutos.apply(percentil_historico)
    pesos = pd.Series({k: v["peso"] for k, v in config.COMPONENTES.items()})
    presentes = pct.notna()
    valor = (pct.fillna(0) * pesos).sum(axis=1) / (presentes * pesos).sum(axis=1)
    valor = valor.where(presentes.sum(axis=1) >= config.MINIMO_COMPONENTES)
    resultado = pct.add_prefix("pct_")
    resultado["termometro"] = valor.round(1)
    resultado = resultado.dropna(subset=["termometro"])
    resultado["nivel"] = resultado["termometro"].map(lambda v: config.nivel_de(v)["nome"])
    return resultado


def resumo(resultado: pd.DataFrame, coleta: dict | None = None) -> dict:
    """Dados da leitura mais recente, no formato que o redator, o site e o card usam."""
    atual, anterior = resultado.iloc[-1], resultado.iloc[-2]
    nivel = config.nivel_de(atual["termometro"])
    componentes = []
    for chave, info in config.COMPONENTES.items():
        p, p0 = atual[f"pct_{chave}"], anterior[f"pct_{chave}"]
        componentes.append({
            "chave": chave, "nome": info["nome"], "descricao": info["descricao"], "peso": info["peso"],
            "percentil": None if pd.isna(p) else round(float(p)),
            "variacao_mes": None if pd.isna(p) or pd.isna(p0) else round(float(p - p0)),
        })
    def pico(inicio, fim):
        trecho = resultado.loc[inicio:fim, "termometro"]
        return {"valor": round(float(trecho.max())), "mes": trecho.idxmax().strftime("%Y-%m")}
    return {
        "referencia": resultado.index[-1].strftime("%Y-%m"),
        "valor": round(float(atual["termometro"])),
        "valor_exato": float(atual["termometro"]),
        "nivel": nivel["nome"], "cor": nivel["cor"], "leitura": nivel["leitura"],
        "mes_anterior": {"referencia": resultado.index[-2].strftime("%Y-%m"),
                         "valor": round(float(anterior["termometro"])), "nivel": anterior["nivel"]},
        "componentes": componentes,
        "componentes_ausentes": ["Crédito (spread corporativo)", "Dólar global", "Conflitos (ACLED)"],
        "picos_historicos": {"Bolha .com": pico("2000-01", "2003-12"), "Crise de 2008": pico("2008-01", "2009-12"),
                             "Covid": pico("2020-01", "2020-12"), "Choque de 2022": pico("2022-01", "2022-12")},
        "coleta": coleta or {},
    }


def rodar(pasta_dados: Path, pasta_saida: Path) -> tuple[pd.DataFrame, dict]:
    pasta_saida.mkdir(parents=True, exist_ok=True)
    resultado = calcular(componentes_brutos(carregar(pasta_dados)))
    coleta_json = pasta_dados / "coleta.json"
    coleta = json.loads(coleta_json.read_text()) if coleta_json.exists() else {}
    dados = resumo(resultado, coleta)
    resultado.to_csv(pasta_saida / "termometro_mensal.csv", float_format="%.1f")
    (pasta_saida / "atual.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2))
    print(f"Termômetro {dados['referencia']}: {dados['valor']} ({dados['nivel']})")
    return resultado, dados
