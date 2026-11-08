from datetime import date, datetime
from zoneinfo import ZoneInfo

from termometro import bolsas as b


def faixa(chave, dia):
    p = b.pregao(chave, date.fromisoformat(dia))
    return None if p is None else b.faixa_brasilia(p)


def test_b3_e_nova_york_mudam_com_o_horario_de_verao_dos_eua():
    assert faixa("b3", "2026-10-30") == "10h às 17h" and faixa("nyse", "2026-10-30") == "10h30 às 17h"
    assert faixa("b3", "2026-11-03") == "10h às 18h" and faixa("nyse", "2026-11-03") == "11h30 às 18h"
    # março de 2027: os EUA entram no horário de verão no domingo, 14/03
    assert faixa("nyse", "2027-03-12") == "11h30 às 18h" and faixa("nyse", "2027-03-15") == "10h30 às 17h"


def test_feriados_e_pregao_curto_dos_calendarios_oficiais():
    assert faixa("b3", "2026-11-20") == ""  # Consciência Negra
    assert faixa("nyse", "2026-11-20") == "11h30 às 18h"
    assert faixa("nyse", "2026-11-26") == ""  # Ação de Graças
    assert faixa("nyse", "2026-11-27") == "11h30 às 15h"  # fecha às 13h em Nova York
    assert faixa("b3", "2026-12-24") == "" and faixa("b3", "2026-12-31") == ""
    assert faixa("b3", "2026-11-07") == ""  # sábado


def test_fora_do_calendario_some_o_selo_mas_fica_o_horario_regular():
    assert b.pregao("b3", date(2027, 1, 4)) is None
    assert b.faixa_brasilia(b.regular("b3", date(2027, 1, 4))) == "10h às 18h"


def test_asia_atravessa_a_meia_noite_e_tadawul_e_de_domingo_a_quinta():
    assert faixa("toquio", "2026-11-09") == "21h às 23h30 e 0h30 às 3h30"
    assert faixa("tadawul", "2026-11-08") == "4h às 9h"  # domingo tem pregão em Riad
    assert faixa("tadawul", "2026-11-13") == ""  # sexta não tem
    assert faixa("lse", "2026-11-09") == "5h às 13h30"


def test_janela_do_relogio_e_dados_da_pagina():
    hoje = date(2026, 11, 8)
    dados = b.dados_js(hoje)
    assert set(dados) == set(b.POR_CHAVE) and "pregao" in dados["b3"] and "pregao" not in dados["lse"]
    ny = dados["nyse"]["pregao"]
    abre = datetime.fromtimestamp(ny[0][0] / 1000, ZoneInfo("America/New_York"))
    assert (abre.hour, abre.minute) == (9, 30) and "2026-11-26" in dados["nyse"]["feriados"]


def test_paginas_gravadas_e_linha_dos_paises(tmp_path):
    def pagina(titulo, descricao, corpo, **kw):
        return f"<title>{titulo}</title>{corpo}"
    caminhos = b.gerar(tmp_path, pagina, hoje=date(2026, 11, 8))
    assert caminhos[0] == "horario-bolsas/index.html"
    hub = (tmp_path / "horario-bolsas" / "index.html").read_text()
    assert "Bolsa de Tóquio" in hub and "11h30 às 18h" in hub and 'data-selo="b3"' in hub and "FAQPage" in hub
    assert 'data-selo="lse"' not in hub  # sem calendário oficial, sem selo
    assert "Últimos" not in hub and "cotação" not in hub.lower().replace("sem cotação", "")
    assert "Feriados e dias especiais" in (tmp_path / "horario-bolsas" / "b3.html").read_text()
    linha = b.linha_pais("Japão", "../", date(2026, 11, 8))
    assert "Asia/Tokyo" in linha and "21h às 23h30" in linha
    assert "Santiago" in b.linha_pais("Chile", "../") and b.linha_pais("Atlântida", "../") == ""
