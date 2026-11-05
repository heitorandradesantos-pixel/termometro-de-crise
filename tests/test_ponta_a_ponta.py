"""Ensaio geral: roda o programa inteiro com dados reais e um Claude simulado.

    DADOS_DIR=dados python -m pytest -q tests/test_ponta_a_ponta.py
"""

import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import rodar  # noqa: E402
from termometro import copywriter, ia, redator, site  # noqa: E402

from test_agentes import DOSSIE, URLS  # noqa: E402

PASTA = Path(os.environ.get("DADOS_DIR", "dados"))
pytestmark = pytest.mark.skipif(not (PASTA / "vix.csv").exists(), reason="sem dados baixados")


class ClaudeEnsaio:
    """Responde como cada agente responderia, conforme as ferramentas que recebe."""

    def __init__(self):
        self.messages = SimpleNamespace(create=self._create)
        self.agentes = []

    def _create(self, **kw):
        nomes = [t.get("name") for t in kw.get("tools", [])]
        pedido = kw["messages"][0]["content"]
        if "registrar_dossie" in nomes:
            self.agentes.append("Buscador")
            return self._ferramenta("registrar_dossie", {"eventos": DOSSIE["eventos"], "agenda": DOSSIE["agenda"]})
        if "registrar_copy" in nomes:
            self.agentes.append("Copy")
            valor = int(re.search(r"Termômetro: (\d+)", pedido).group(1))
            nivel = re.search(r"nível (\w+)", pedido).group(1)
            dados = {"valor": valor, "nivel": nivel, "referencia": "2026-09", "leitura": "Leitura",
                     "picos_historicos": {"Crise de 2008": {"valor": 96}, "Covid": {"valor": 94}}}
            return self._ferramenta("registrar_copy", copywriter.padrao(dados, "2026-11-08"))
        self.agentes.append("Redator")
        valor, nivel = re.search(r"Termômetro: (\d+) de 100, nível (\w+)", pedido).groups()
        riscos = "\n".join(f"{i + 1}. **Risco {i + 1}.** Fato e canal até o Brasil. [Fonte]({URLS[i]})" for i in range(3))
        texto = (f"{redator.SECOES[0]}\n\nO Termômetro marcou **{valor}** de 100, nível {nivel}.\n\n"
                 f"{redator.SECOES[1]}\n\n{riscos}\n\n{redator.SECOES[2]}\n\n{' '.join(['história'] * 450)}\n\n"
                 f"{redator.SECOES[3]}\n\n- 10/11: Copom ([BC]({URLS[3]}))")
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=texto)])

    @staticmethod
    def _ferramenta(nome, entrada):
        return SimpleNamespace(stop_reason="tool_use", content=[SimpleNamespace(type="tool_use", name=nome, input=entrada)])


def test_edicao_completa_sai_aprovada_e_vira_site(tmp_path, monkeypatch):
    claude = ClaudeEnsaio()
    monkeypatch.setattr(rodar, "EDICOES", tmp_path / "edicoes")
    monkeypatch.setattr(ia, "disponivel", lambda: True)
    monkeypatch.setattr(ia, "novo_cliente", lambda: claude)
    monkeypatch.setattr(rodar.mundo, "coletar", lambda pasta: None)  # sem internet no teste

    pasta = rodar.gerar(PASTA, "2026-11-08", coletar=False)

    revisao = json.loads((pasta / "revisao.json").read_text())
    assert revisao["aprovado"], [c for c in revisao["checagens"] if not c["ok"]]
    assert claude.agentes == ["Buscador", "Redator", "Copy"]
    for arquivo in ("edicao.md", "copy.json", "pesquisa.json", "redes.md", "card.png", "historico.png",
                    "historico_celular.png", "resumo_pr.md"):
        assert (pasta / arquivo).exists(), arquivo

    site.gerar(tmp_path / "edicoes", tmp_path / "_site")
    pagina = (tmp_path / "_site" / "index.html").read_text()
    assert "TERMÔMETRO GLOBAL" in pagina and (tmp_path / "_site" / "edicoes" / "2026-11-08.html").exists()
