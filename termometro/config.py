"""Configurações do Termômetro de Crise.

Tudo o que você pode querer ajustar fica aqui: fontes de dados, pesos,
faixas, cores, textos fixos e o modelo de IA. O resto do código lê daqui.
"""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- dados
# Histórico longo: espelhos públicos do datahub.io no GitHub (sem chave).
_DATAHUB = "https://raw.githubusercontent.com/datasets"
FONTES = {
    "vix":   {"url": f"{_DATAHUB}/finance-vix/main/data/vix-daily.csv",        "data": "DATE", "valor": "CLOSE"},
    "brent": {"url": f"{_DATAHUB}/oil-prices/main/data/brent-daily.csv",        "data": "Date", "valor": "Price"},
    "juros": {"url": f"{_DATAHUB}/bond-yields-us-10y/main/data/monthly.csv",    "data": "Date", "valor": "Rate"},
    "sp":    {"url": f"{_DATAHUB}/s-and-p-500/main/data/data.csv",              "data": "Date", "valor": "SP500"},
    "ouro":  {"url": f"{_DATAHUB}/gold-prices/main/data/monthly.csv",           "data": "Date", "valor": "Price", "formato": "%Y-%m"},
}

# Dados recentes diários pelo FRED (Fed de St. Louis). Opcional: só é usado
# quando existe o segredo FRED_API_KEY (a chave é grátis).
FRED = {"vix": "VIXCLS", "brent": "DCOILBRENTEU", "juros": "DGS10", "sp": "SP500"}

# ---------------------------------------------------------------- método
INICIO_REFERENCIA = "1990-01-01"   # percentil contra todo o histórico desde 1990
MINIMO_MESES = 120                 # 10 anos de histórico antes do primeiro cálculo
MINIMO_COMPONENTES = 4             # só publica com pelo menos 4 dos 5 componentes

COMPONENTES = {
    "energia":      {"nome": "Energia",      "peso": 15, "descricao": "Distância do Brent até a média de 12 meses, em qualquer direção"},
    "juros":        {"nome": "Juros longos", "peso": 15, "descricao": "Variação do juro de 10 anos dos EUA em 3 meses, em qualquer direção"},
    "volatilidade": {"nome": "Volatilidade", "peso": 15, "descricao": "VIX, média do mês"},
    "acoes":        {"nome": "Ações",        "peso": 10, "descricao": "Queda do S&P 500 desde a máxima de 12 meses"},
    "ouro":         {"nome": "Porto seguro", "peso": 10, "descricao": "Variação do ouro em 3 meses, em qualquer direção"},
}

NIVEIS = [
    {"nome": "Calmaria", "min": 0,  "max": 20,  "cor": "#3B82C4", "leitura": "Risco abaixo do normal; atenção a excessos de otimismo"},
    {"nome": "Atenção",  "min": 21, "max": 40,  "cor": "#7CC3E0", "leitura": "Tensões localizadas, ainda sem contágio entre mercados"},
    {"nome": "Alerta",   "min": 41, "max": 60,  "cor": "#F2C14E", "leitura": "Dois ou mais componentes estressados ao mesmo tempo"},
    {"nome": "Tensão",   "min": 61, "max": 80,  "cor": "#EE8A3C", "leitura": "Estresse amplo: hora de revisar proteções"},
    {"nome": "Crise",    "min": 81, "max": 100, "cor": "#D9483B", "leitura": "Contágio entre mercados: liquidez e preservação em primeiro lugar"},
]


def nivel_de(valor: float) -> dict:
    for n in NIVEIS:
        if round(valor) <= n["max"]:
            return n
    return NIVEIS[-1]


# ---------------------------------------------------------------- marca
NOME = "Termômetro de Crise"
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")   # ex.: https://termometrodecrise.com.br
DOMINIO = os.environ.get("DOMINIO", "")                  # ex.: termometrodecrise.com.br (gera o CNAME)
ADSENSE_CLIENT = os.environ.get("ADSENSE_CLIENT", "")    # ex.: ca-pub-1234567890 (só depois de aprovado)
NEWSLETTER_URL = os.environ.get("NEWSLETTER_URL", "")    # página de inscrição (ex.: a do beehiiv)

CORES = {"fundo": "#0E141B", "painel": "#1A2430", "linha": "#22303C", "texto": "#EEF2F5", "suave": "#9AA7B2"}

AVISO = ("Conteúdo educativo e informativo. Não é recomendação de compra ou venda de nenhum ativo "
         "nem considera a sua situação financeira. Decisões de investimento são suas; se precisar, "
         "procure um profissional certificado.")

# ---------------------------------------------------------------- pesquisa
REGIOES = ["Europa e Eurásia", "Oriente Médio", "Ásia e Pacífico", "África", "Américas", "Global"]
STATUS_FATO = ["fato confirmado", "operação em curso", "ameaça ou declaração", "negociação", "hipótese ou cenário"]

# Fontes de primeira linha. Outras podem aparecer, mas o Revisor avisa quando um
# risco se apoia só em fonte fora desta lista.
FONTES_CONFIAVEIS = [
    "reuters.com", "apnews.com", "ft.com", "bloomberg.com", "wsj.com", "economist.com", "nikkei.com",
    "bbc.com", "bbc.co.uk", "dw.com", "lemonde.fr", "elpais.com", "nytimes.com", "washingtonpost.com",
    "valor.globo.com", "folha.uol.com.br", "estadao.com.br", "g1.globo.com", "agenciabrasil.ebc.com.br",
    "bcb.gov.br", "gov.br", "ibge.gov.br", "federalreserve.gov", "ecb.europa.eu", "bankofengland.co.uk",
    "boj.or.jp", "imf.org", "worldbank.org", "bis.org", "oecd.org", "wto.org", "iea.org", "eia.gov",
    "opec.org", "un.org", "unhcr.org", "acleddata.com", "crisisgroup.org", "cfr.org", "sipri.org",
    "iiss.org", "csis.org", "chathamhouse.org", "nato.int", "europa.eu", "whitehouse.gov", "state.gov",
    "treasury.gov", "defense.gov", "kremlin.ru", "mid.ru", "fmprc.gov.cn", "gov.uk",
]

# ---------------------------------------------------------------- IA
# "or" porque o GitHub manda a variável vazia quando ela não foi criada
MODELO_CLAUDE = os.environ.get("MODELO_CLAUDE") or "claude-sonnet-5-5"
BUSCAS_MAXIMAS = int(os.environ.get("BUSCAS_MAXIMAS") or "12")  # buscas na web por edição (Buscador)
# "sim" = publica sozinho quando o Revisor aprova; qualquer outra coisa = pede sua aprovação.
AUTOMATICO = os.environ.get("AUTOMATICO", "").strip().lower() == "sim"
