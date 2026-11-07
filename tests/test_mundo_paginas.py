"""Testes do termômetro por país: motor, Correspondente, panorama do WhatsApp e páginas clicáveis.

Rodam sem internet e sem chave de IA: os dados dos países são sintéticos e o Claude é simulado.
"""

import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import rodar  # noqa: E402
from termometro import correspondente, ia, mundo, paginas, panorama, site  # noqa: E402

DATA = "2026-11-05"
BUSCADOS = ["https://www.reuters.com/world/middle-east/x", "https://apnews.com/article/y", "https://www.ft.com/z"]


def serie(semente: int, inicio: str = "2000-01-03", choque: str | None = None) -> pd.Series:
    rng = np.random.default_rng(semente)
    dias = pd.bdate_range(inicio, DATA)
    passos = rng.normal(0.0003, 0.01, len(dias))
    if choque:  # um tombo forte para o histórico ter um pico
        i = dias.get_indexer([pd.Timestamp(choque)], method="nearest")[0]
        passos[i:i + 40] -= 0.012
    return pd.Series(100 * np.exp(np.cumsum(passos)), index=dias)


@pytest.fixture(scope="module")
def dados_mundo(tmp_path_factory) -> Path:
    pasta = tmp_path_factory.mktemp("dados") / "mundo"
    pasta.mkdir()
    arquivos = {"eua_bolsa": serie(1, choque="2008-09-15"), "brasil_bolsa": serie(2, choque="2008-09-15"),
                "brasil_moeda": serie(3, "2003-12-01"), "israel_bolsa": serie(4, choque="2008-09-15"),
                "israel_moeda": serie(5), "egito_moeda": serie(6, choque="2016-11-01"),
                "turquia_bolsa": serie(7), "turquia_moeda": serie(8, choque="2018-06-01")}
    for nome, s in arquivos.items():
        s.rename("valor").to_csv(pasta / f"{nome}.csv", index_label="data")
    (pasta / "coleta_mundo.json").write_text(json.dumps({k: "ok" for k in arquivos}))
    return pasta


@pytest.fixture(scope="module")
def resultado(dados_mundo, tmp_path_factory) -> dict:
    return mundo.rodar(dados_mundo, tmp_path_factory.mktemp("saida"))


def regiao(resultado: dict, nome: str) -> dict:
    return next(r for r in resultado["regioes"] if r["nome"] == nome)


# ---------------------------------------------------------------- motor
def test_motor_explica_em_numeros_simples(resultado):
    brasil = next(p for p in regiao(resultado, "América Latina")["paises"] if p["nome"] == "Brasil")
    b = brasil["brutos"]
    assert brasil["slug"] == "brasil" and brasil["bolsa_nome"] == "Ibovespa" and brasil["moeda_nome"] == "real"
    assert 0 <= b["bolsa_queda_pct"] < 100 and b["oscilacao_diaria_pct"] > 0
    assert "moeda_variacao_3m_pct" in b and b["desde"]["moeda"] == 2004
    assert not any(k.startswith("_") for k in resultado["brasil"]["sinais"])


def test_picos_tem_nome_da_epoca(resultado):
    eua = regiao(resultado, "América do Norte")["paises"][0]
    assert eua["picos"], "o tombo de 2008 deveria aparecer como pico"
    assert any(p["epoca"] == "crise financeira global de 2008" for p in eua["picos"])
    meses = [pd.Timestamp(p["mes"]) for p in eua["picos"]]
    assert all(abs((a - b).days) > 365 for i, a in enumerate(meses) for b in meses[i + 1:])


# ---------------------------------------------------------------- Correspondente
def bloco_busca():
    return SimpleNamespace(type="web_search_tool_result",
                           content=[SimpleNamespace(type="web_search_result", url=u) for u in BUSCADOS])


def registro_oriente_medio() -> dict:
    return {
        "resumo": "Israel e Egito puxam a região: a moeda dos dois mudou forte em 3 meses.",
        "paises": [{"nome": "Israel", "por_que": "A bolsa caiu e o shekel oscilou com a guerra."},
                   {"nome": "Egito", "por_que": "Compre libras agora."},  # linguagem proibida: deve sair
                   {"nome": "Brasil", "por_que": "fora da região"}],
        "noticias": [
            {"titulo": "Catar medeia conversa entre EUA e Irã", "resumo": "Fato com fonte.", "data": "2026-11-04",
             "status": "negociação", "paises": ["Israel", "Brasil"], "mexe_em": ["moeda", "energia"],
             "direcao": "alivia", "relevancia": 5, "fontes": [{"veiculo": "Reuters", "url": BUSCADOS[0] + "/"}]},
            {"titulo": "Link inventado", "resumo": "x", "data": "2026-11-04", "status": "fato confirmado",
             "mexe_em": ["bolsa"], "direcao": "pressiona", "relevancia": 4,
             "fontes": [{"veiculo": "Blog", "url": "https://inventado.com/a"}]},
            {"titulo": "Notícia velha", "resumo": "x", "data": "2026-09-01", "status": "fato confirmado",
             "mexe_em": ["bolsa"], "direcao": "pressiona", "relevancia": 4,
             "fontes": [{"veiculo": "AP", "url": BUSCADOS[1]}]},
        ],
        "observar": [{"data": "2026-11-10", "evento": "Reunião em Abu Dhabi", "por_que_importa": "Pode mexer no petróleo.",
                      "url": BUSCADOS[2]}],
    }


class ClaudeCorrespondente:
    def __init__(self):
        self.messages = SimpleNamespace(create=self._create)
        self.chamadas = 0

    def _create(self, **kw):
        self.chamadas += 1
        assert kw["tools"][0]["type"] == "web_search_20250305"
        entrada = registro_oriente_medio()
        return SimpleNamespace(stop_reason="tool_use", content=[
            bloco_busca(), SimpleNamespace(type="tool_use", id="t1", name="registrar_regiao", input=entrada)])


def test_ia_guarda_os_links_das_buscas():
    assert ia.links_das_buscas([bloco_busca(), SimpleNamespace(type="text", text="oi")]) == set(BUSCADOS)


def test_correspondente_confere_links_datas_e_linguagem(resultado):
    r = regiao(resultado, "Oriente Médio")
    v = correspondente.validar(registro_oriente_medio(), r, DATA, set(BUSCADOS))
    assert [n["titulo"] for n in v["noticias"]] == ["Catar medeia conversa entre EUA e Irã"]
    n = v["noticias"][0]
    assert n["paises"] == ["Israel"] and n["fonte_de_primeira_linha"] and n["regiao"] == "Oriente Médio"
    assert set(v["paises"]) == {"Israel"}, "texto com ordem de compra e país de fora da região saem"
    motivos = " ".join(d["motivo"] for d in v["descartados"])
    assert "busca não devolveu" in motivos and "fora da janela" in motivos and "linguagem" in motivos
    assert v["observar"][0]["url"] == BUSCADOS[2]


def test_correspondente_roda_todas_as_regioes(resultado):
    claude = ClaudeCorrespondente()
    saida = correspondente.pesquisar(resultado, DATA, claude)
    com_dados = [r for r in resultado["regioes"] if r.get("valor") is not None]
    assert claude.chamadas == len(com_dados)
    assert saida["regioes"]["Oriente Médio"]["noticias"]


# ---------------------------------------------------------------- panorama
def test_panorama_bate_com_o_motor_e_tem_aviso(resultado):
    anterior = json.loads(json.dumps(resultado))
    anterior["mundo"]["valor"] -= 3
    anterior["_data"] = "2026-11-04"
    corr = {"regioes": {"Oriente Médio": {"noticias": correspondente.validar(
        registro_oriente_medio(), regiao(resultado, "Oriente Médio"), DATA, set(BUSCADOS))["noticias"]}}}
    texto = panorama.montar(resultado, corr, anterior, DATA)
    assert "▲3 desde 04/11" in texto and "Catar medeia" in texto
    assert panorama.checar(texto, resultado)["aprovado"]
    assert len(texto) <= panorama.LIMITE
    assert not panorama.checar(texto.replace(panorama.AVISO_CURTO, ""), resultado)["aprovado"]


# ---------------------------------------------------------------- páginas
def explicacoes_brasil(resultado):
    brasil = next(p for p in regiao(resultado, "América Latina")["paises"] if p["nome"] == "Brasil")
    return paginas.sinais_explicados(brasil), paginas.por_que_automatico(brasil)


def test_explicacao_automatica_em_portugues_correto(resultado):
    sinais, texto = explicacoes_brasil(resultado)
    assert {s["chave"] for s in sinais} == {"bolsa", "volatilidade", "moeda"}
    assert any("Ibovespa" in s["frase"] for s in sinais) and any("real" in s["frase"] for s in sinais)
    assert "desde 2004" in next(s["comparacao"] for s in sinais if s["chave"] == "moeda")
    assert texto.startswith(("O Brasil está", "O que mais pesa no Brasil", "Nenhum sinal do Brasil"))
    assert paginas.de("EUA") == "dos EUA" and paginas.em("Israel") == "em Israel" and paginas.sujeito("EUA") == ("Os EUA", "estão")


def test_site_com_atualizacao_diaria_tem_paginas_clicaveis(tmp_path, dados_mundo, monkeypatch):
    # uma edição semanal antiga e uma atualização diária mais nova: o site usa a diária
    edicoes = tmp_path / "edicoes"
    origem = RAIZ / "edicoes" / "2026-11-05"
    destino = edicoes / "2026-11-05"
    destino.mkdir(parents=True)
    for arq in origem.iterdir():
        (destino / arq.name).write_bytes(arq.read_bytes())
    monkeypatch.setattr(rodar, "DIARIO", tmp_path / "diario")
    monkeypatch.setattr(ia, "disponivel", lambda: True)
    monkeypatch.setattr(ia, "novo_cliente", lambda: ClaudeCorrespondente())
    pasta = rodar.diario(dados_mundo.parent, "2026-11-06", coletar=False)
    assert (pasta / "panorama.txt").exists() and json.loads((pasta / "revisao.json").read_text())["aprovado"]

    saida = tmp_path / "_site"
    site.gerar(edicoes, saida, tmp_path / "diario")
    inicio = (saida / "index.html").read_text()
    assert 'href="regioes/oriente-medio.html"' in inicio and 'href="paises/israel.html"' in inicio
    assert "O que está mexendo no termômetro" in inicio and "Catar medeia" in inicio
    assert "atualizada em 06/11/2026" in inicio and "mapa-mundo" in inicio and "Fechamento de" in inicio
    israel = (saida / "paises" / "israel.html").read_text()
    for trecho in ["Por que o termômetro está em", "O contexto", "Catar medeia", BUSCADOS[0], "Já foi pior?",
                   "<svg", "../regioes/oriente-medio.html"]:
        assert trecho in israel, trecho
    assert (saida / "regioes" / "oriente-medio.html").exists() and (saida / "mundo.html").exists()
    pano = (saida / "panorama.html").read_text()
    # o panorama completo é do grupo: no site fica só o começo e o convite para entrar
    assert "Entrar no grupo do WhatsApp" in pano and "chat.whatsapp.com" in pano
    assert "Copiar texto" not in pano and "wa.me/?text=" not in pano and "O que mexeu com o termômetro" not in pano
    # nenhum link interno quebrado
    paginas_geradas = list(saida.rglob("*.html"))
    for arquivo in paginas_geradas:
        for href in re.findall(r'href="([^"#]+\.html)"', arquivo.read_text()):
            if not href.startswith("http"):
                alvo = saida / href.lstrip("/") if href.startswith("/") else arquivo.parent / href  # "/x" = raiz
                assert alvo.resolve().exists(), f"{arquivo.name} → {href}"


def test_todo_pais_do_motor_aparece_no_mapa():
    """Cada país medido precisa de código no mapa, artigo para as frases e um desenho (ou ponto) para ser pintado."""
    import json
    from termometro import mundo, paginas
    desenhos = {c["a2"] for c in json.loads(paginas.MAPA.read_text())["paises"]} | set(paginas.PONTOS_NO_MAPA)
    for pais in mundo.PAISES:
        assert pais in paginas.A2 and pais in paginas.ARTIGOS, pais
        assert paginas.A2[pais] in desenhos, pais


def test_correcoes_da_squad_ranking_faixa_e_mapa():
    from termometro import paginas, site
    so_moeda = {"nome": "Marrocos", "sinais": {"moeda": 85}}
    assert paginas.incompleto(so_moeda) and "só 1 de 3 sinais" in paginas.parcial(so_moeda)
    assert not paginas.incompleto({"nome": "Arábia Saudita", "sinais": {"bolsa": 74, "volatilidade": 76}})
    assert "▲" in paginas.mudanca(61, 58) and "(58)" in paginas.mudanca(61, 58) and paginas.mudanca(61, None) == ""
    faixa = site.faixa_mercados([{"nome": "Ibovespa", "ultimo": 166191.4, "tipo": "pontos", "variacao_pct": -0.82,
                                  "data": "2026-11-05"}])
    assert "Fechamento de 05/11 · fonte: Yahoo Finance" in faixa and '<span class="sr">caiu </span>' in faixa
    assert "Sem leitura" not in paginas.legenda_faixas() and "Crise 81–100" in paginas.legenda_faixas()


def test_leitura_parcial_do_meio_do_dia_mantem_noticias_e_panorama(tmp_path, dados_mundo, monkeypatch):
    edicoes = tmp_path / "edicoes"
    destino = edicoes / "2026-11-05"
    destino.mkdir(parents=True)
    for arq in (RAIZ / "edicoes" / "2026-11-05").iterdir():
        (destino / arq.name).write_bytes(arq.read_bytes())
    monkeypatch.setattr(rodar, "DIARIO", tmp_path / "diario")
    monkeypatch.setattr(ia, "disponivel", lambda: True)
    monkeypatch.setattr(ia, "novo_cliente", lambda: ClaudeCorrespondente())
    rodar.diario(dados_mundo.parent, "2026-11-06", coletar=False)
    assert rodar.parcial(dados_mundo.parent, "2026-11-06", "14h07", coletar=False) is None  # dia já fechado
    pasta = rodar.parcial(dados_mundo.parent, "2026-11-09", "14h07", coletar=False)
    assert json.loads((pasta / "mundo.json").read_text())["parcial"] == {"hora": "14h07"}
    assert rodar.parcial(dados_mundo.parent, "2026-11-09", "14h37", coletar=False) is None  # reserva: já saiu
    assert not (pasta / "panorama.txt").exists() and not (pasta / "correspondente.json").exists()
    saida = tmp_path / "_site"
    site.gerar(edicoes, saida, tmp_path / "diario")
    inicio = (saida / "index.html").read_text()
    assert "09/11/2026, parcial das 14h07" in inicio and "Parcial das 14h07 · fonte" in inicio
    assert "Catar medeia" in inicio  # as notícias do último fechamento continuam
    assert "O panorama de 06/11" in (saida / "panorama.html").read_text()  # a prévia é a do último fechamento
    assert "/api/cotacoes" in inicio  # a faixa se atualiza sozinha no navegador


def test_faixa_tira_cotacao_parada_ha_dias():
    from termometro import site
    faixa = site.faixa_mercados([
        {"nome": "Ibovespa", "ultimo": 166191.4, "tipo": "pontos", "variacao_pct": -0.82, "data": "2026-11-05"},
        {"nome": "Merval", "ultimo": 2848945.2, "tipo": "pontos", "variacao_pct": -0.35, "data": "2026-10-16"}])
    assert "Ibovespa" in faixa and 'data-c="Merval"' not in faixa


def test_queda_da_bolsa_conta_o_pico_diario_e_nao_so_o_fim_de_mes(tmp_path):
    # como o Ibovespa em 2026: sobe até um recorde no meio do mês e despenca antes do fim do mês
    datas = pd.bdate_range("2026-08-03", "2026-11-05")
    valores = pd.Series(170.0, index=datas)
    valores[(datas >= "2026-10-05") & (datas <= "2026-10-08")] = 206.9
    valores[datas > "2026-10-08"] = 166.2
    pd.DataFrame({"data": datas, "valor": valores.values}).to_csv(tmp_path / f"{mundo.arquivo('Brasil')}_bolsa.csv",
                                                                  index=False)
    sinais = mundo.sinais_do_pais(tmp_path, "Brasil")
    assert round(100 * sinais["bolsa"].iloc[-1], 1) == 19.7  # antes, com fins de mês, dava 2,2%
    brutos = mundo.brutos_do_pais(tmp_path, "Brasil", sinais)
    assert brutos["bolsa_pico"] == 206.9 and brutos["bolsa_pico_dia"] == "2026-10-05"
