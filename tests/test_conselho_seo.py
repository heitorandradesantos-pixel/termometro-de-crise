"""Testes do conselho de monetização e do agente de SEO (Claude simulado, sem internet)."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from termometro import conselho, seo  # noqa: E402


class ClaudeConselho:
    def __init__(self):
        self.messages = SimpleNamespace(create=self._create)
        self.chamadas = []

    def _create(self, **kw):
        nome = next(t["name"] for t in kw["tools"] if t.get("name", "").startswith("registrar_"))
        self.chamadas.append((nome, kw["system"][:80]))
        if nome == "registrar_proposta":
            entrada = {"diagnostico": "Falta tráfego.", "ideias": [
                {"titulo": "Curso de educação financeira", "como_funciona": "Curso curto", "receita": "estimativa",
                 "prazo": "3 a 6 meses", "metrica": "vendas", "riscos": "confiança"},
                {"titulo": "Afiliado de corretora com recomendação", "como_funciona": "indicar ações", "receita": "CPA",
                 "prazo": "0 a 30 dias", "metrica": "cadastros", "riscos": "regulatório"}],
                "mudancas_no_site": ["Botão do WhatsApp no topo"]}
        elif nome == "registrar_debate":
            entrada = {"concordo": ["Curso"], "discordo": [{"de_quem": "Vendas", "ponto": "afiliado", "por_que": "CVM"}],
                       "parecer_de_regras": [{"ideia": "Afiliado de corretora com recomendação", "situacao": "vetada",
                                              "motivo": "recomendação exige registro"}],
                       "proposta_ajustada": "Começar pela audiência", "voto": ["Curso de educação financeira"]}
        else:
            entrada = {"resumo": "Primeiro audiência, depois curso.",
                       "divergencias": [{"conflito": "Alcance x profundidade", "troca": "volume ou confiança",
                                         "o_que_decide": "retenção em 30 dias"}],
                       "plano": [{"fase": "0 a 30 dias", "iniciativa": "Canal do WhatsApp", "responsavel": "Marketing",
                                  "metrica": "seguidores", "meta": "500"},
                                 {"fase": "3 a 6 meses", "iniciativa": "Curso", "responsavel": "Vendas",
                                  "metrica": "vendas", "meta": "50"},
                                 {"fase": "1 a 3 meses", "iniciativa": "SEO de países", "responsavel": "SEO",
                                  "metrica": "visitas", "meta": "5 mil"}],
                       "mudancas_no_site": [{"prioridade": 1, "mudanca": "Botão do canal no topo", "por_que": "hábito"}],
                       "vetos_respeitados": ["Afiliado com recomendação"], "tripwire": "Retenção abaixo de 20%",
                       "proximos_passos_do_dono": ["Criar o canal no WhatsApp"]}
        return SimpleNamespace(stop_reason="tool_use", content=[
            SimpleNamespace(type="tool_use", id="t", name=nome, input=entrada)])


def test_conselho_conversa_em_tres_rodadas_e_respeita_vetos(tmp_path):
    claude = ClaudeConselho()
    r = conselho.rodar(RAIZ, tmp_path / "ata", "2026-11-05", claude)
    nomes = [n for n, _ in claude.chamadas]
    membros = len(conselho.MEMBROS)
    assert nomes == ["registrar_proposta"] * membros + ["registrar_debate"] * membros + ["registrar_decisao"]
    ata = (tmp_path / "ata" / "ata.md").read_text()
    for trecho in ["Conselho de monetização: ata de 2026-11-05", "| 0 a 30 dias | Canal do WhatsApp",
                   "Botão do canal no topo", "Vetos do guardião de regras", "Criar o canal no WhatsApp", "tripwire"]:
        assert trecho in ata, trecho
    # o plano sai em ordem de fase
    assert ata.index("0 a 30 dias") < ata.index("1 a 3 meses") < ata.index("3 a 6 meses")
    assert json.loads((tmp_path / "ata" / "conselho.json").read_text())["decisao"]["tripwire"]


def test_cada_membro_recebe_o_proprio_manual():
    assert "Manual do guardião de regras" in conselho.sistema("compliance") and "vetada" in conselho.sistema("compliance")
    assert "dissidente" in conselho.sistema(conselho.DISSIDENTE)
    assert "Manual do vendedor" in conselho.sistema("vendas") and "Manual do especialista em SEO" in conselho.sistema("seo")
    assert "Contexto do projeto" in conselho.briefing(RAIZ)


def test_pauta_de_seo_validada_e_entregue():
    paginas = seo.paginas_do_site({})
    p = seo.validar({"palavra_chave": "Risco de Crise", "secundarias": ["Dólar hoje", "Ibovespa"],
                     "perguntas": ["Vai ter crise?"], "titulo_seo": "x" * 80, "descricao_seo": "y",
                     "links_internos": ["paises/brasil.html", "paises/atlantida.html"]}, paginas)
    assert p["palavra_chave"] == "risco de crise" and p["links_internos"] == ["paises/brasil.html"]
    assert len(p["titulo_seo"]) <= 60
    assert "Palavra-chave principal: risco de crise" in seo.para_redator(p) and "risco de crise" in seo.para_copy(p)
    assert seo.contem("O risco de uma crise no Brasil", "risco de crise") and not seo.contem("Dólar sobe", "risco de crise")
