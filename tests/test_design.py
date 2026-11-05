"""Testes da squad de design (agentes de UI e UX) e dos manuais de especialista."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from termometro import buscador, config, copywriter, correspondente, design, redator, revisor  # noqa: E402


def medidas(**extra) -> dict:
    base = {"rolagem_horizontal": False, "alvos_total": 10, "alvos_pequenos": 0, "exemplos_alvos": [],
            "menor_fonte": 13, "textos_menores_que_12px": 0, "exemplos_fonte": [], "contraste_falhas": 0,
            "exemplos_contraste": [], "h1": 1, "titulos_pulados": 0, "imagens_sem_alt": 0, "graficos_sem_rotulo": 0,
            "idioma": "pt-BR", "titulo": "x", "tem_descricao": True, "link_para_pular": True, "nova_aba_sem_aviso": 0,
            "numero_sem_rolar": True, "peso_kb": 100, "elementos": 200, "primeiro_tab": {"foco": "Pular", "visivel": True},
            "telas": []}
    return {**base, **extra}


def auditoria(**problemas) -> dict:
    a = {"paginas": {"Início": {"caminho": "index.html", "celular": medidas(**problemas), "computador": medidas()}},
         "links_quebrados": [], "axe": False}
    a["regras"] = design.regras(a)
    return a


def test_manuais_entram_nos_agentes():
    for modulo, trecho in ((buscador, "Leitura lateral"), (correspondente, "Linguagem simples"),
                           (redator, "Pirâmide invertida"), (copywriter, "Botões dizem exatamente")):
        assert "<manual_do_especialista>" in modulo.SISTEMA and trecho in modulo.SISTEMA, modulo.__name__
    assert "WCAG" in design.PAPEIS["ui"] and "Nielsen" in design.PAPEIS["ux"]


def test_regras_objetivas_apontam_problemas():
    ok = auditoria()
    assert all(r["ok"] for r in ok["regras"])
    ruim = auditoria(rolagem_horizontal=True, alvos_pequenos=2, exemplos_alvos=["Menu (40×16)"], contraste_falhas=1,
                     exemplos_contraste=["Crise (4.35:1)"], h1=2, link_para_pular=False, numero_sem_rolar=False)
    falhas = {r["regra"]: r["detalhe"] for r in ruim["regras"] if not r["ok"]}
    assert "Sem rolagem horizontal" in falhas and "Menu (40×16)" in falhas["Alvos de toque com pelo menos 24×24px"]
    assert "Crise (4.35:1)" in falhas["Contraste de texto WCAG AA"]
    assert {"Exatamente um h1 por página", "Link para pular ao conteúdo",
            "Número do termômetro visível sem rolar (celular)"} <= set(falhas)


def test_validacao_e_relatorio_dos_agentes():
    bruto = {"notas": {"hierarquia": 12, "tipografia": 7}, "pontos_fortes": ["Medidor claro"],
             "achados": [{"pagina": "Início", "tela": "celular", "severidade": 2, "principio": "Hierarquia",
                          "problema": "Muitos blocos", "sugestao": "Cortar a tabela", "esforco": "pequeno"},
                         {"pagina": "Inexistente", "tela": "tablet", "severidade": 9, "principio": "Contraste",
                          "problema": "Selo vermelho", "sugestao": "Clarear para #E5554A", "esforco": "enorme"},
                         {"pagina": "Início", "problema": "", "sugestao": ""}],
             "primeiro_passo": "Clarear o selo"}
    av = design.validar(bruto, "ui", ["Início"])
    assert av["notas"]["hierarquia"] == 10 and av["notas"]["cor_e_contraste"] == 0
    assert [x["severidade"] for x in av["achados"]] == [4, 2]
    assert av["achados"][0]["pagina"] == "Geral" and av["achados"][0]["esforco"] == "médio"
    texto = design.relatorio("2026-11-09", auditoria(), av, None)
    assert "Plano da semana" in texto and "Clarear para #E5554A" in texto and "Agente de UI" in texto
    assert "Checagens objetivas" in texto


def test_agente_recebe_os_prints(tmp_path):
    prints = tmp_path / "prints"
    prints.mkdir()
    (prints / "index_celular_1.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    a = auditoria(telas=["index_celular_1.jpg"])
    recebido = {}

    def criar(**kw):
        recebido.update(kw)
        entrada = {"notas": {k: 8 for k in design.DIMENSOES["ux"]}, "pontos_fortes": ["ok"],
                   "achados": [{"pagina": "Início", "tela": "celular", "severidade": 3, "principio": "Clareza",
                                "problema": f"p{i}", "sugestao": "s", "esforco": "pequeno"} for i in range(3)],
                   "primeiro_passo": "x"}
        return SimpleNamespace(stop_reason="tool_use", content=[
            SimpleNamespace(type="tool_use", id="t", name="registrar_avaliacao", input=entrada)])
    av = design.avaliar(a, tmp_path, "ux", SimpleNamespace(messages=SimpleNamespace(create=criar)))
    conteudo = recebido["messages"][0]["content"]
    assert any(b.get("type") == "image" for b in conteudo) and av["nota_geral"] == 8.0
    assert "Nielsen" in recebido["system"]


def test_revisor_avisa_jargao_e_frase_longa():
    assert revisor.jargao_sem_traducao("O spread abriu. O yield, rendimento do título, caiu.") == ["spread"]
    assert len(revisor.frases_longas("Curta. " + " ".join(["palavra"] * 40) + ".")) == 1


def test_auditoria_de_verdade_num_site_pequeno(tmp_path):
    pytest.importorskip("playwright.sync_api")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>T</title>'
        '<meta name="viewport" content="width=device-width"><meta name="description" content="d"></head>'
        '<body style="background:#0E141B;color:#EEF2F5"><a href="#c">Pular para o conteúdo</a>'
        '<main id="c"><h1>Termômetro</h1><div class="valor" style="font-size:40px">59</div>'
        '<p>Texto <a href="mundo.html">quebrado</a></p></main></body></html>')
    try:
        a = design.auditar(site, tmp_path / "saida")
    except Exception as erro:  # sem navegador instalado nesta máquina
        pytest.skip(f"navegador indisponível: {erro}")
    m = a["paginas"]["Início"]["celular"]
    assert m["h1"] == 1 and m["link_para_pular"] and m["numero_sem_rolar"] and not m["rolagem_horizontal"]
    assert (tmp_path / "saida" / "prints" / "index_celular.png").exists()
    assert a["links_quebrados"] == ["index.html → mundo.html"]
    assert not next(r for r in a["regras"] if r["regra"] == "Sem links internos quebrados")["ok"]


def test_datas_no_padrao_brasileiro():
    assert correspondente.datas_br("Em 2026-11-05 o Ibovespa caiu; em 2026-10-28, também.") == \
        "Em 5/11 o Ibovespa caiu; em 28/10, também."
