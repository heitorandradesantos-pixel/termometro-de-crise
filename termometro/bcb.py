"""Dados oficiais do Banco Central do Brasil: Selic, dólar PTAX e expectativas do Focus.

São dados abertos, grátis e com fonte citável (api.bcb.gov.br e olinda.bcb.gov.br). Cada número
sai com a própria data, para o panorama nunca dizer "hoje" sobre um dado de outro dia. Se uma
série falhar, ela simplesmente fica de fora e o panorama escreve "sem dado hoje".
"""

import pandas as pd
import requests

SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados/ultimos/{}"
FOCUS = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
UA = {"User-Agent": "termometro-de-crise/1.0 (+https://termometrodecrise.com)"}
SERIES = {"selic": 432, "ptax": 1}  # meta Selic (% ao ano) e dólar PTAX de venda (R$)
FONTE = "Banco Central do Brasil (SGS e Focus)"


def sgs(serie: int, n: int = 1) -> list[dict]:
    r = requests.get(SGS.format(serie, n), params={"formato": "json"}, headers=UA, timeout=20)
    r.raise_for_status()
    return [{"data": pd.to_datetime(x["data"], dayfirst=True).strftime("%Y-%m-%d"), "valor": float(x["valor"])}
            for x in r.json()]


def ano_do_focus(data: str) -> int:
    """No último trimestre, a expectativa que ainda informa é a do ano seguinte."""
    d = pd.Timestamp(data)
    return d.year + 1 if d.month >= 10 else d.year


def focus(indicador: str, ano: int) -> dict:
    params = {"$filter": f"Indicador eq '{indicador}' and DataReferencia eq '{ano}' and baseCalculo eq 0",
              "$orderby": "Data desc", "$top": 1, "$format": "json", "$select": "Indicador,Data,DataReferencia,Mediana"}
    r = requests.get(FOCUS, params=params, headers=UA, timeout=25)
    r.raise_for_status()
    linhas = r.json().get("value", [])
    if not linhas:
        raise RuntimeError(f"Focus sem {indicador} para {ano}")
    return {"valor": float(linhas[0]["Mediana"]), "data": linhas[0]["Data"][:10], "ano": ano}


def coletar(data: str) -> dict:
    """Busca tudo o que der; o que falhar fica registrado em "falhas" e some do texto."""
    saida: dict = {"fonte": FONTE, "falhas": {}}
    for nome, serie in SERIES.items():
        try:
            saida[nome] = sgs(serie)[-1]
        except Exception as erro:  # noqa: BLE001 — dado oficial que falha vira "sem dado hoje"
            saida["falhas"][nome] = str(erro)[:160]
    ano = ano_do_focus(data)
    for nome, indicador in (("focus_ipca", "IPCA"), ("focus_selic", "Selic")):
        try:
            saida[nome] = focus(indicador, ano)
        except Exception as erro:  # noqa: BLE001
            saida["falhas"][nome] = str(erro)[:160]
    return saida


def _num(v: float, casas: int = 2) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def linha(bc: dict | None, data: str) -> str:
    """'Banco Central: Selic 15,00% · Dólar PTAX R$ 5,4587 · Focus 2027: inflação 4,10%, Selic 12,25%'."""
    if not bc:
        return ""
    def quando(item: dict) -> str:  # só mostra a data quando não é a do panorama
        return "" if item["data"] == data else f" (de {pd.Timestamp(item['data']):%d/%m})"
    partes = []
    if bc.get("selic"):
        partes.append(f"Selic {_num(bc['selic']['valor'])}%")
    if bc.get("ptax"):
        partes.append(f"Dólar PTAX R$ {_num(bc['ptax']['valor'], 4)}{quando(bc['ptax'])}")
    fi, fs = bc.get("focus_ipca"), bc.get("focus_selic")
    if fi or fs:
        ano = (fi or fs)["ano"]
        itens = ([f"inflação {_num(fi['valor'])}%"] if fi else []) + ([f"Selic no fim do ano {_num(fs['valor'])}%"] if fs else [])
        partes.append(f"Focus para {ano}: " + ", ".join(itens))
    return ("🏦 Banco Central: " + " · ".join(partes)) if partes else "🏦 Banco Central: sem dado hoje"
