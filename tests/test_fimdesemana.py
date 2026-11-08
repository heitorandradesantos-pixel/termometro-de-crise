import json

import pandas as pd
import pytest

from termometro import fimdesemana as fds


class Resposta:
    def __init__(self, dados):
        self.dados = dados

    def raise_for_status(self):
        pass

    def json(self):
        return self.dados


def yahoo_falso(url, headers=None, timeout=None, params=None):
    """Preço sobe 1 por período: diário para commodities, por hora para cripto (até domingo 08/11)."""
    horario = params["interval"] == "1h"
    fim = pd.Timestamp("2026-11-08 18:00", tz="UTC") if horario else pd.Timestamp("2026-11-06 21:00", tz="UTC")
    passos = pd.date_range(end=fim, periods=24 * 14 if horario else 30, freq="h" if horario else "D")
    precos = [100 + i * (0.01 if horario else 1) for i in range(len(passos))]
    return Resposta({"chart": {"result": [{"timestamp": [int(t.timestamp()) for t in passos],
                                           "indicators": {"quote": [{"close": precos}]}}]}})


@pytest.fixture
def diario(tmp_path):
    for dia, mundo, brasil in (("2026-11-05", 55, 63), ("2026-11-06", 58, 64), ("2026-11-13", 61, 62)):
        (tmp_path / dia).mkdir()
        (tmp_path / dia / "mundo.json").write_text(json.dumps({
            "mundo": {"valor": mundo, "nivel": "Alerta"}, "brasil": {"valor": brasil, "nivel": "Tensão"}}))
    (tmp_path / "plantao").mkdir()
    (tmp_path / "plantao" / "2026-11-15-o-que-esperar-do-mercado-essa-semana.json").write_text(json.dumps({
        "slug": "o-que-esperar-do-mercado-essa-semana", "turno": "manha", "titulo": "O que esperar", "lead": "",
        "o_que_se_sabe": [{"texto": "O Ibovespa fechou a sexta em alta.", "data": "2026-11-13"},
                          {"texto": "O IBGE divulga o IPCA de outubro na terça (17/11). Outra frase.", "data": "2026-11-17"},
                          {"texto": "O Fed fala na quarta.", "data": "2026-11-18"}],
        "linha_do_tempo": [{"texto": "Primeiro pregão da semana.", "data": "2026-11-16"},
                           {"texto": "O IBGE divulga o IPCA de outubro na terça.", "data": "2026-11-17"}]}))
    (tmp_path / "plantao" / "2026-11-12-nvidia.json").write_text(json.dumps({
        "slug": "nvidia", "titulo": "Nvidia e os chips", "lead": "A Nvidia anunciou chips novos na quarta (11/11).",
        "o_que_se_sabe": []}))
    return tmp_path


def test_termometro_da_semana_compara_com_uma_semana_antes(diario):
    t = fds.termometro_semana(diario, "2026-11-15")
    assert t["data"] == "2026-11-13" and t["antes"]["data"] == "2026-11-06"
    bloco = fds.bloco_termometro(t)
    assert "61 de 100" in bloco and "▲3 (era 58 em 06/11)" in bloco and "Brasil: 62 (Tensão), ▼2" in bloco


def test_variacao_de_7_dias_com_corte_no_domingo_ao_meio_dia():
    corte = pd.Timestamp("2026-11-08 12:00", tz="America/Sao_Paulo")
    v = fds.variacao_7d("BTC-USD", corte, yahoo_falso)
    assert v["quando"].startswith("2026-11-08T12:00") and v["variacao_pct"] > 0
    ouro = fds.variacao_7d("GC=F", corte, yahoo_falso)
    assert ouro["variacao_pct"] == pytest.approx((129 / 122 - 1) * 100)


def test_mensagem_com_e_sem_numeros(diario):
    sem = fds.montar(diario, "2026-11-15", numeros=False, buscar=yahoo_falso)
    assert "O IBGE divulga o IPCA de outubro na terça (17/11)." in sem["texto"] and "Outra frase" not in sem["texto"]
    assert "fechou a sexta" not in sem["texto"] and "Primeiro pregão" not in sem["texto"]
    assert sem["texto"].count("IPCA") == 1 and "O Fed fala na quarta." in sem["texto"]
    assert "Commodities" not in sem["texto"] and "Bitcoin" not in sem["texto"]
    assert "🤖" in sem["texto"] and "newsletter" in sem["texto"] and not sem["proibido"]
    com = fds.montar(diario, "2026-11-15", numeros=True, buscar=yahoo_falso)
    assert "Petróleo Brent ▲" in com["texto"] and "Bitcoin ▲" in com["texto"] and com["texto"].count("Fonte: Yahoo Finance") == 2


def test_previa_vai_para_o_proprio_numero_e_so_no_domingo(diario, tmp_path, monkeypatch):
    monkeypatch.setenv("FDS_MODO", "previa")
    saida = tmp_path / "_fds"
    assert "não é domingo" in fds.preparar(diario, "2026-11-14", saida, buscar=yahoo_falso)
    assert "prévia" in fds.preparar(diario, "2026-11-15", saida, buscar=yahoo_falso)
    envio = json.loads((saida / "envio.json").read_text())
    assert envio["modo"] == "teste" and envio["tipo"] == "fimdesemana" and "PRÉVIA" in envio["textos"][0]
    assert "Bitcoin" in envio["textos"][1]  # na prévia, os números aparecem para o Heitor decidir
    monkeypatch.delenv("FDS_MODO")  # padrão: grupo, com os números
    monkeypatch.setenv("WHATSAPP_ENVIO", "nao")
    assert "desligado" in fds.preparar(diario, "2026-11-15", tmp_path / "_off", buscar=yahoo_falso)
    monkeypatch.setenv("WHATSAPP_ENVIO", "sim")
    monkeypatch.delenv("FDS_NUMEROS", raising=False)
    fds.preparar(diario, "2026-11-15", saida, buscar=yahoo_falso)
    envio = json.loads((saida / "envio.json").read_text())
    assert envio["modo"] == "sim" and len(envio["textos"]) == 1 and "Bitcoin" in envio["textos"][0]
    monkeypatch.setenv("FDS_NUMEROS", "nao")
    fds.preparar(diario, "2026-11-15", saida, buscar=yahoo_falso)
    assert "Bitcoin" not in json.loads((saida / "envio.json").read_text())["textos"][0]
