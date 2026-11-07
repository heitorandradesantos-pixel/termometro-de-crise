"""Roteirista: roteiro de Reel só com números do material, gancho forte, tamanho de 45 a 60 s."""

import json

from termometro import ia, roteirista

MATERIAL = ("🌡️ FECHAMENTO DO TERMÔMETRO · 06/11\n\n🇧🇷 Brasil em 64 (Tensão) · 🌍 Mundo em 58 (Alerta)\n\n"
            "📈 Ibovespa: 168.501 pontos (▲1,39%)\nPor quê: investidores reagiram ao corte de juros nos EUA.\n"
            "💵 Dólar: R$ 5,51 (▲0,85%)\n🏦 Selic 13,75% · PTAX R$ 5,5013 (Banco Central)")
NOTA_BOA = {"especifico": 2, "tensao": 2, "espectador": 1, "rapido": 2, "verdadeiro": 2}


def _bruto(falas=None, gancho="O Ibovespa subiu 1,39% hoje, e o motivo está nos Estados Unidos.", nota=None):
    falas = falas or [
        "A bolsa brasileira fechou em 168.501 pontos.",
        "Quem puxou foi o corte de juros nos Estados Unidos.",
        "Juro mais baixo lá fora deixa o dinheiro mais disposto a correr risco aqui.",
        "Mas tem um detalhe que pouca gente viu: o dólar também subiu.",
        "Ele fechou em R$ 5,51, alta de 0,85%.",
        "Normalmente, bolsa e dólar andam em direções opostas.",
        "Hoje andaram juntos, e isso mostra que o mercado ainda está desconfiado.",
        "O termômetro do Brasil está em 64, na faixa de Tensão.",
        "O do mundo está em 58, em Alerta.",
        "Amanhã o foco volta para a inflação de outubro.",
    ]
    return {"ganchos": [{"formula": "número + porquê", "texto": gancho, "na_tela": "Ibovespa *+1,39%*",
                         "nota": nota or NOTA_BOA}] * 3,
            "gancho_escolhido": 0, "falas": falas, "retomada": 3,
            "na_tela": [{"fala": 0, "texto": "168.501 pontos", "fonte": "Yahoo Finance"},
                        {"fala": 4, "texto": "R$ 5,51", "fonte": "Yahoo Finance"}],
            "busca": "ibovespa hoje", "legenda": "Ibovespa hoje: a bolsa subiu 1,39%.\\n\\nE o dólar também.",
            "hashtags": ["ibovespa", "#dólar", "mercadofinanceiro"]}


def test_roteiro_bom_passa_e_ganha_assinatura_fecho_e_aviso():
    r = roteirista.montar(_bruto())
    assert r["linhas"][1] == roteirista.ASSINATURA and r["linhas"][-2] == roteirista.FECHO
    assert roteirista.conferir(r, MATERIAL) == []
    assert 42 <= r["segundos"] <= 64 and r["retomada"] == 5
    assert roteirista.AVISO_LEGENDA in r["legenda"] and r["legenda"].endswith("#ibovespa #dolar #mercadofinanceiro")
    assert "1,39%.\n\nE o dólar" in r["legenda"]  # quebra de linha escrita como texto vira quebra de verdade
    assert r["na_tela"][0]["texto"] == "Ibovespa *+1,39%*" and r["na_tela"][1]["fala"] == 2


def test_numero_inventado_vicio_e_recomendacao_reprovam():
    falas = _bruto()["falas"][:9] + ["O Ibovespa pode chegar a 180.000 pontos, vale ressaltar."]
    problemas = roteirista.conferir(roteirista.montar(_bruto(falas=falas)), MATERIAL)
    assert any("180.000" in p for p in problemas)  # número que não está no material
    assert any("vícios" in p for p in problemas)
    falas = _bruto()["falas"][:9] + ["É hora de comprar ações da Petrobras."]
    assert any("proibida" in p for p in roteirista.conferir(roteirista.montar(_bruto(falas=falas)), MATERIAL))


def test_gancho_fraco_e_roteiro_curto_reprovam():
    fraco = {"especifico": 1, "tensao": 0, "espectador": 1, "rapido": 2, "verdadeiro": 2}
    problemas = roteirista.conferir(roteirista.montar(_bruto(nota=fraco, falas=["A bolsa subiu hoje."] * 5)), MATERIAL)
    assert any("gancho fraco" in p for p in problemas) and any("tamanho" in p for p in problemas)


def test_segunda_versao_quando_a_primeira_reprova(tmp_path, monkeypatch):
    pedidos = []

    def falso(cliente, sistema, pedido, saida, buscas=0, max_tokens=0, links=None):
        pedidos.append(pedido)
        if len(pedidos) == 1:
            return _bruto(falas=_bruto()["falas"][:9] + ["O índice pode ir a 200.000 pontos."])
        return _bruto()
    monkeypatch.setattr(ia, "estruturado", falso)
    pasta = tmp_path / "envio"
    pasta.mkdir()
    (pasta / "envio.json").write_text(json.dumps({"dia": "2026-11-06", "tipo": "fechamento", "legenda": MATERIAL,
                                                   "textos": []}))
    gravados = roteirista.rodar(tmp_path / "diario", "fechamento", pasta, cliente=object())
    r = json.loads(gravados[0].read_text())
    assert r["aprovado"] and r["tentativas"] == 2 and "200.000" in pedidos[1]  # a correção diz o que errou
    assert gravados[0].name == "fechamento.json" and r["persona"] == roteirista.PERSONA


def test_explica_roteiriza_cada_artigo_do_dia_uma_vez(tmp_path, monkeypatch):
    artigo = {"titulo": "Reforma tributária vai ser adiada?", "slug": "reforma-tributaria-adiada",
              "lead": "Até 6 de novembro, a reforma não foi adiada.",
              "o_que_se_sabe": [{"texto": "O TCU aprovou 11,3% como alíquota de referência da CBS em 2027.",
                                 "veiculo": "Correio Braziliense"}]}
    (tmp_path / "plantao").mkdir()
    (tmp_path / "plantao" / "2026-11-06-reforma-tributaria-adiada.json").write_text(json.dumps(artigo))
    material = roteirista.material_artigo(artigo)
    assert "11,3%" in material and "Correio Braziliense" in material
    monkeypatch.setattr(ia, "estruturado", lambda *a, **k: _bruto())
    assert len(roteirista.rodar(tmp_path, "explica", dia="2026-11-06", cliente=object())) == 1
    assert roteirista.rodar(tmp_path, "explica", dia="2026-11-06", cliente=object()) == []  # já tem roteiro
