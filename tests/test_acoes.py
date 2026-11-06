"""Página Cotações: lista editorial, formatação e páginas."""

import json

from termometro import acoes, mundo


def _falsos(data="2026-11-06"):
    itens = {}
    for i, a in enumerate(acoes.simbolos()):
        moeda = {"brasil": "BRL", "eua": "USD", "europa": "EUR", "asia": "JPY"}[a["bolsa"]]
        itens[a["simbolo"]] = {"ultimo": 100.0 + i, "dia_pct": -0.82 if i % 2 else 1.1, "mes_pct": 4.0,
                               "linha": [90, 95, 92, 100.0 + i], "data": data if i else "2026-11-05", "moeda": moeda}
    return {"data": data, "fonte": "Yahoo Finance", "itens": itens, "falhas": {}}


def test_lista_editorial_tem_60_acoes_sem_repeticao_e_paises_conhecidos():
    todas = acoes.simbolos()
    assert len(todas) == 60 and len({a["simbolo"] for a in todas}) == 60
    for b in acoes.lista()["bolsas"]:
        assert list(b["setores"]) == ["Tecnologia", "Infraestrutura", "Commodities"]
        assert all(len(v) == 5 for v in b["setores"].values())
    fora = {a["pais"] for a in todas} - set(mundo.PAISES)
    assert fora == {"Holanda", "Finlândia"}  # sem termômetro próprio: ligam à região Europa


def test_formatos_de_preco_variacao_e_linha():
    assert acoes.preco(38.2, "BRL") == "R$ 38,20" and acoes.preco(98500, "KRW") == "₩ 98.500"
    assert acoes.preco(27.15, "GBP") == "£ 27,15" and acoes.preco(3420, "JPY") == "¥ 3.420"
    assert "caiu" in acoes.variacao(-0.82) and "▼" in acoes.variacao(-0.82) and "—" in acoes.variacao(None)
    svg = acoes.linha_svg([1, 2, 3], 4.0)
    assert 'aria-label="subiu 4% em 30 dias"' in svg and "<polyline" in svg
    assert acoes.ticker("PETR4.SA") == "PETR4" and acoes.ticker("NVDA") == "NVDA"


def test_paginas_de_cotacoes(tmp_path):
    m = json.loads((acoes.config.RAIZ / "diario" / "2026-11-05" / "mundo.json").read_text())
    feitas = acoes.paginas(tmp_path, _falsos(), m)
    assert feitas == ["cotacoes/index.html", "cotacoes/eua.html", "cotacoes/europa.html", "cotacoes/asia.html"]
    br = (tmp_path / "cotacoes" / "index.html").read_text()
    for trecho in ["Cotações: Brasil", "Petrobras", "PETR4", "Preços de fechamento de 06/11/2026 · fonte: Yahoo Finance",
                   'aria-current="page"', "Não é recomendação", "último pregão 05/11", "Termômetro Brasil", "?bolsa="]:
        assert trecho in br, trecho
    vazia = acoes.paginas(tmp_path / "vazio", None, m)
    assert len(vazia) == 4 and "Sem cotações guardadas" in (tmp_path / "vazio" / "cotacoes" / "eua.html").read_text()
