"""Testes dos agentes. Rodam sem internet e sem chave de IA (o Claude é simulado).

    python -m pytest -q
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from termometro import buscador, config, copywriter, ia, redator, revisor  # noqa: E402

DADOS = {
    "referencia": "2026-09", "valor": 59, "valor_exato": 59.2, "nivel": "Alerta", "cor": "#F2C14E",
    "leitura": "Dois ou mais componentes estressados ao mesmo tempo",
    "mes_anterior": {"referencia": "2026-08", "valor": 38, "nivel": "Atenção"},
    "componentes": [
        {"chave": "energia", "nome": "Energia", "descricao": "x", "peso": 15, "percentil": 91, "variacao_mes": 40},
        {"chave": "juros", "nome": "Juros longos", "descricao": "x", "peso": 15, "percentil": 76, "variacao_mes": 39},
        {"chave": "volatilidade", "nome": "Volatilidade", "descricao": "x", "peso": 15, "percentil": 36, "variacao_mes": 4},
        {"chave": "acoes", "nome": "Ações", "descricao": "x", "peso": 10, "percentil": 53, "variacao_mes": 31},
        {"chave": "ouro", "nome": "Porto seguro", "descricao": "x", "peso": 10, "percentil": 27, "variacao_mes": -21},
    ],
    "componentes_ausentes": ["Crédito"],
    "picos_historicos": {"Bolha .com": {"valor": 89, "mes": "2001-10"}, "Crise de 2008": {"valor": 96, "mes": "2009-02"},
                         "Covid": {"valor": 94, "mes": "2020-04"}, "Choque de 2022": {"valor": 88, "mes": "2022-06"}},
}

URLS = ["https://www.reuters.com/a", "https://apnews.com/b", "https://www.ft.com/c", "https://www.bcb.gov.br/d"]
DOSSIE = {
    "eventos": [{"titulo": f"Evento {i}", "regiao": "Global", "status": "fato confirmado", "data": "2026-11-05",
                 "resumo": "r", "canal_brasil": "c", "relevancia": 5 - i,
                 "fontes": [{"veiculo": "V", "url": URLS[i], "confiavel": True}]} for i in range(3)],
    "agenda": [{"data": "2026-11-10", "evento": "Copom", "por_que_importa": "juros", "url": URLS[3]}],
}


def edicao_boa(extra: str = "") -> str:
    riscos = "\n".join(f"{i + 1}. **Risco {i + 1}.** Texto do risco. [Fonte]({URLS[i]})" for i in range(3))
    enchimento = " ".join(["palavra"] * 450)
    corpo = (f"{redator.SECOES[0]}\n\nO Termômetro marcou **59** de 100, nível Alerta. {extra}\n\n"
             f"{redator.SECOES[1]}\n\n{riscos}\n\n{redator.SECOES[2]}\n\n{enchimento}\n\n"
             f"{redator.SECOES[3]}\n\n- 10/11: Copom ([BC]({URLS[3]}))")
    return f"# Título\n\n{corpo}\n\n---\n\n*{config.AVISO}*\n"


def revisar(texto: str, copy: dict | None = None) -> dict:
    copy = copy or {**copywriter.padrao(DADOS, "2026-11-08"), "ajustes": []}
    return revisor.checar(texto, DADOS, DOSSIE, copy)


def falhas(r: dict) -> set[str]:
    return {c["regra"] for c in r["checagens"] if not c["ok"] and c["bloqueia"]}


# ---------------------------------------------------------------- Revisor
def test_revisor_aprova_edicao_correta():
    r = revisar(edicao_boa())
    assert r["aprovado"], falhas(r)


def test_revisor_bloqueia_recomendacao():
    for frase in ["Recomendo reduzir ações.", "Compre ouro agora.", "Hora de vender dólar.", "Invista em PETR4 já."]:
        assert "Sem recomendação, promessa ou alarmismo" in falhas(revisar(edicao_boa(frase))), frase


def test_revisor_aceita_vocabulario_neutro():
    texto = edicao_boa("A venda de títulos pelo Tesouro e a compra de dólares pelo BC mexeram com o câmbio.")
    assert revisar(texto)["aprovado"]


def test_revisor_bloqueia_link_inventado():
    texto = edicao_boa("Veja [aqui](https://site-inventado.com/x).")
    assert "Todo link veio da pesquisa do Buscador" in falhas(revisar(texto))


def test_revisor_bloqueia_numero_errado():
    assert "Número e nível do Termômetro corretos" in falhas(revisar(edicao_boa("Antes estava em 71 de 100.")))


def test_revisor_bloqueia_sem_aviso_e_pendente():
    texto = edicao_boa().replace(config.AVISO, "") + "\nPENDENTE"
    assert {"Aviso legal presente", "Nada pendente"} <= falhas(revisar(texto))


# ---------------------------------------------------------------- Buscador
def test_buscador_filtra_dossie():
    bruto = {"eventos": [
        {"titulo": "Sem fonte", "data": "2026-11-05", "fontes": [{"veiculo": "X", "url": "ftp://x"}]},
        {"titulo": "Velho", "data": "2026-09-01", "relevancia": 5, "fontes": [{"veiculo": "R", "url": URLS[0]}]},
        {"titulo": "Bom", "data": "2026-11-04", "relevancia": 3, "fontes": [{"veiculo": "R", "url": URLS[0]}]},
        {"titulo": "bom", "data": "2026-11-04", "relevancia": 3, "fontes": [{"veiculo": "R", "url": URLS[1]}]},
        {"titulo": "Blog", "data": "2026-11-04", "relevancia": 4, "fontes": [{"veiculo": "B", "url": "https://blog.xyz/a"}]},
    ], "agenda": []}
    limpo = buscador.validar(bruto, "2026-11-08")
    assert [e["titulo"] for e in limpo["eventos"]] == ["Blog", "Bom"]
    assert not limpo["eventos"][0]["fonte_de_primeira_linha"] and limpo["eventos"][1]["fonte_de_primeira_linha"]
    assert len(limpo["descartados"]) == 3


def test_fontes_confiaveis_reconhece_subdominios():
    assert buscador.confiavel("https://www.reuters.com/x") and buscador.confiavel("https://valor.globo.com/x")
    assert not buscador.confiavel("https://reuters.com.golpe.io/x")


# ---------------------------------------------------------------- Copy
def test_copy_troca_so_a_peca_ruim():
    reserva = copywriter.padrao(DADOS, "2026-11-08")
    peca = {**reserva, "assuntos_email": ["Assunto curto", "Outro assunto", "Terceiro"], "assunto_escolhido": 1,
            "post_x": "Lucro garantido com o Termômetro! " * 3, "titulo_site": "Título bom e claro do site"}
    final, ajustes = copywriter.validar(peca, reserva)
    assert final["assunto_escolhido"] == 1 and final["titulo_site"] == "Título bom e claro do site"
    assert final["post_x"] == reserva["post_x"] and any("post_x" in a for a in ajustes)


def test_copy_padrao_respeita_limites():
    reserva = copywriter.padrao(DADOS, "2026-11-08")
    _, ajustes = copywriter.validar(reserva, reserva)
    assert not ajustes, ajustes


# ---------------------------------------------------------------- conversa com o Claude (simulada)
class ClaudeFalso:
    """Imita a API: primeiro pausa a busca (pause_turn), depois preenche o formulário de saída."""

    def __init__(self, saida: dict):
        self.saida, self.chamadas = saida, []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.chamadas.append({**kw, "n_mensagens": len(kw["messages"])})  # tamanho no momento da chamada
        if len(self.chamadas) == 1:
            return SimpleNamespace(stop_reason="pause_turn", content=[SimpleNamespace(type="server_tool_use")])
        nome = kw["tools"][-1]["name"]
        return SimpleNamespace(stop_reason="tool_use",
                               content=[SimpleNamespace(type="tool_use", name=nome, input=self.saida)])


def test_buscador_com_claude_simulado_continua_apos_pausa():
    cliente = ClaudeFalso({"eventos": DOSSIE["eventos"], "agenda": DOSSIE["agenda"]})
    dossie = buscador.pesquisar(DADOS, "2026-11-08", cliente)
    assert len(dossie["eventos"]) == 3 and len(cliente.chamadas) == 2
    assert cliente.chamadas[0]["tools"][0]["type"] == "web_search_20250305"
    assert cliente.chamadas[1]["n_mensagens"] == 2  # o turno pausado foi devolvido como estava


def test_estruturado_pede_formulario_quando_o_agente_esquece():
    class Esquecido(ClaudeFalso):
        def _create(self, **kw):
            self.chamadas.append(kw)
            if kw["tool_choice"]["type"] == "auto":
                return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="pronto")])
            return SimpleNamespace(stop_reason="tool_use", content=[
                SimpleNamespace(type="tool_use", name=buscador.FERRAMENTA["name"], input={"ok": 1})])

    saida = ia.estruturado(Esquecido({}), "s", "p", buscador.FERRAMENTA, buscas=3)
    assert saida == {"ok": 1}


def test_ciclo_completo_simulado_passa_no_revisor():
    texto_claude = edicao_boa().split("\n\n", 1)[1].split("\n\n---")[0]

    class Redator:
        messages = SimpleNamespace(create=lambda **kw: SimpleNamespace(
            stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Aqui vai:\n\n" + texto_claude)]))

    texto, modo = redator.escrever(DADOS, DOSSIE, "2026-11-08", Redator())
    assert texto.startswith("# Termômetro de Crise: 59, Alerta") and "Aqui vai" not in texto
    copy = copywriter.escrever(DADOS, texto, "2026-11-08", ClaudeFalso(copywriter.padrao(DADOS, "2026-11-08")))
    resultado = revisor.checar(texto, DADOS, DOSSIE, copy)
    assert resultado["aprovado"], json.dumps(resultado, ensure_ascii=False)
