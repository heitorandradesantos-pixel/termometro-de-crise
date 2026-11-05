"""Teste histórico do motor: roda com os dados baixados pelo Coletor.

    DADOS_DIR=dados python -m pytest -q tests/test_motor.py

Se uma mudança no método fizer 2008 ou a Covid saírem da faixa Crise, ou um ano
calmo entrar nela, o teste falha e a edição não é gerada.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from termometro import motor  # noqa: E402

PASTA = Path(os.environ.get("DADOS_DIR", "dados"))
pytestmark = pytest.mark.skipif(not (PASTA / "vix.csv").exists(), reason="sem dados baixados")


@pytest.fixture(scope="module")
def indice():
    return motor.calcular(motor.componentes_brutos(motor.carregar(PASTA)))["termometro"]


@pytest.mark.parametrize("inicio,fim", [("2008-09", "2009-03"), ("2020-02", "2020-05")])
def test_crises_chegam_a_faixa_crise(indice, inicio, fim):
    assert indice.loc[inicio:fim].max() > 80


@pytest.mark.parametrize("ano", ["2005", "2017", "2019", "2021"])
def test_anos_calmos_ficam_fora_da_faixa_crise(indice, ano):
    assert indice.loc[ano].max() <= 80


def test_indice_entre_0_e_100(indice):
    assert indice.between(0, 100).all()
