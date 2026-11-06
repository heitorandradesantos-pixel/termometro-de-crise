"""Panorama v2 (consulta #17): Banco Central, marco do termômetro e conferências."""

import json

import pytest

from termometro import bcb, panorama


def _mundo(brasil=("Tensão", 61), mundo=("Alerta", 59)):
    return {"mundo": {"valor": mundo[1], "nivel": mundo[0]},
            "brasil": {"valor": brasil[1], "nivel": brasil[0], "sinais": {"bolsa": 70, "volatilidade": 43, "moeda": 68}},
            "regioes": [{"nome": "Europa", "valor": 51, "nivel": "Alerta"},
                        {"nome": "Oriente Médio", "valor": 76, "nivel": "Tensão"}]}


BC = {"fonte": bcb.FONTE, "falhas": {}, "selic": {"data": "2026-11-05", "valor": 14.25},
      "ptax": {"data": "2026-11-04", "valor": 5.4587},
      "focus_ipca": {"valor": 4.1, "data": "2026-10-31", "ano": 2027},
      "focus_selic": {"valor": 12.25, "data": "2026-10-31", "ano": 2027}}


def test_linha_do_banco_central_com_data_quando_nao_e_de_hoje():
    linha = bcb.linha(BC, "2026-11-05")
    assert "Selic 14,25%" in linha and "Dólar PTAX R$ 5,4587 (de 04/11)" in linha
    assert "Focus para 2027: inflação 4,10%, Selic no fim do ano 12,25%" in linha
    assert bcb.linha({"falhas": {"selic": "erro"}}, "2026-11-05") == "🏦 Banco Central: sem dado hoje"
    assert bcb.ano_do_focus("2026-11-05") == 2027 and bcb.ano_do_focus("2026-05-05") == 2026


def test_coletar_le_os_formatos_oficiais_e_registra_falhas(monkeypatch):
    class Resposta:
        def __init__(self, dados):
            self.dados = dados

        def raise_for_status(self):
            pass

        def json(self):
            return self.dados

    def falso_get(url, params=None, **_):
        if "sgs.432" in url:
            return Resposta([{"data": "05/11/2026", "valor": "14.25"}])
        if "sgs.1/" in url:
            raise ConnectionError("fora do ar")
        indicador = "IPCA" if "'IPCA'" in params["$filter"] else "Selic"
        return Resposta({"value": [{"Indicador": indicador, "Data": "2026-10-31", "DataReferencia": "2027",
                                    "Mediana": 4.1 if indicador == "IPCA" else 12.25}]})

    monkeypatch.setattr(bcb.requests, "get", falso_get)
    bc = bcb.coletar("2026-11-05")
    assert bc["selic"] == {"data": "2026-11-05", "valor": 14.25}
    assert "ptax" not in bc and "ptax" in bc["falhas"]
    assert bc["focus_ipca"]["valor"] == 4.1 and bc["focus_selic"]["ano"] == 2027
    texto = panorama.montar(_mundo(), None, None, "2026-11-05", noticias=[], bc=bc)
    assert "Selic 14,25%" in texto and "PTAX" not in texto  # o que falhou some do texto


def test_marco_mudanca_de_faixa_sequencia_e_limite_por_semana():
    ontem = {**_mundo(brasil=("Alerta", 58)), "_data": "2026-11-04"}
    assert panorama.marco(_mundo(), [ontem]) == "📍 O Brasil mudou de faixa: de Alerta para Tensão."
    iguais = [{**_mundo(), "_data": d} for d in ("2026-11-02", "2026-11-03", "2026-11-04")]
    assert panorama.marco(_mundo(), iguais) == "📍 O Brasil está há 4 dias úteis seguidos em Tensão."
    assert panorama.marco(_mundo(), iguais[-1:]) == ""  # 2 dias ainda não é marco
    assert panorama.marco(_mundo(), [ontem], ["📍 a", "📍 b", "📍 c"]) == ""  # já teve 3 na semana
    assert panorama.marco(_mundo(), []) == ""


def test_checar_pega_numero_do_banco_central_errado_e_marco_inventado():
    texto = panorama.montar(_mundo(), None, None, "2026-11-05", noticias=[], bc=BC,
                            destaque="📍 O Brasil mudou de faixa: de Alerta para Tensão.")
    assert panorama.checar(texto, _mundo(), BC)["aprovado"]
    outro = {**BC, "selic": {"data": "2026-11-05", "valor": 15.0}}
    assert "Selic diferente do Banco Central" in panorama.checar(texto, _mundo(), outro)["problemas"]
    inventado = texto.replace("📍 O Brasil mudou de faixa: de Alerta para Tensão.", "📍 Hora de comprar ações!")
    assert not panorama.checar(inventado, _mundo(), BC)["aprovado"]


@pytest.mark.parametrize("n_noticias", [0, 3])
def test_panorama_cabe_no_limite_e_traz_link_unico_e_aviso(n_noticias):
    noticias = [{"titulo": "Manchete longa " * 6, "regiao": "Europa"} for _ in range(n_noticias)]
    texto = panorama.montar(_mundo(), None, None, "2026-11-05", noticias=noticias, bc=BC)
    assert len(texto) <= panorama.LIMITE
    assert texto.count("https://") == 1 and panorama.AVISO_CURTO in texto
    assert texto.startswith("*TERMÔMETRO DE CRISE · Panorama de qui, 05/11*")
    json.dumps(texto)  # vai para o JSON do diário sem problema
