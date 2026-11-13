"""Roteirista: roteiro de Reel só com números do material, gancho forte, tamanho de 30 a 45 s."""

import json

from termometro import estrategista, ia, roteirista

MATERIAL = ("🌡️ FECHAMENTO DO TERMÔMETRO · 06/11\n\n🇧🇷 Brasil em 64 (Tensão) · 🌍 Mundo em 58 (Alerta)\n\n"
            "📈 Ibovespa: 168.501 pontos (▲1,39%)\nPor quê: investidores reagiram ao corte de juros nos EUA.\n"
            "💵 Dólar: R$ 5,51 (▲0,85%)\n🏦 Selic 13,75% · PTAX R$ 5,5013 (Banco Central)")
NOTA_BOA = {"especifico": 2, "tensao": 2, "espectador": 1, "rapido": 2, "verdadeiro": 2}


def _bruto(falas=None, gancho="O Ibovespa subiu 1,39% hoje, e o motivo está nos Estados Unidos.", nota=None):
    falas = falas or [
        "A bolsa brasileira fechou em 168.501 pontos.",
        "Quem puxou foi o corte de juros nos Estados Unidos.",
        "Mas tem um detalhe que pouca gente viu: o dólar também subiu.",
        "Ele fechou em R$ 5,51, alta de 0,85%.",
        "O termômetro do Brasil está em 64, na faixa de Tensão.",
        "Antes de mexer no dinheiro, olhe com calma o seu prazo e a sua reserva.",
        "Quem tem dívida em dólar sente primeiro, então vale conferir a fatura.",
    ]
    return {"ganchos": [{"formula": "número + porquê", "texto": gancho, "na_tela": "Ibovespa *+1,39%*",
                         "nota": nota or NOTA_BOA}] * 3,
            "gancho_escolhido": 0, "falas": falas, "retomada": 2,
            "engajamento": "E aí, o dólar ainda sobe mais? Comenta SIM ou NÃO.",
            "na_tela": [{"fala": 0, "texto": "168.501 pontos", "fonte": "Yahoo Finance"},
                        {"fala": 3, "texto": "R$ 5,51", "fonte": "Yahoo Finance"}],
            "rua": {"gancho": "O Ibovespa subiu 1,39% hoje.", "topicos": [
                "Fechou em 168.501 pontos, segundo o Yahoo Finance.", "O dólar subiu 0,85%, para R$ 5,51.",
                "Antes de mexer no dinheiro, olhe o seu prazo."]},
            "formato": "rua", "por_que_formato": "Notícia do dia.",
            "busca": "ibovespa hoje", "legenda": "Ibovespa hoje: a bolsa subiu 1,39%.\\n\\nE o dólar também.",
            "hashtags": ["ibovespa", "#dólar", "mercadofinanceiro"]}


def test_roteiro_bom_passa_e_termina_com_engajamento_e_bordao():
    r = roteirista.montar(_bruto())
    assert r["linhas"][-2] == "E aí, o dólar ainda sobe mais? Comenta SIM ou NÃO."
    assert roteirista.ASSINATURA not in r["linhas"] and roteirista.FECHO not in r["linhas"]  # vão para a tela final
    assert r["linhas"][-1] == roteirista.BORDAO == "Sem alarde. Eu sou só o termômetro!"
    assert roteirista.conferir(r, MATERIAL) == []
    assert 34 <= r["segundos"] <= 46 and r["retomada"] == 3
    assert roteirista.AVISO_LEGENDA in r["legenda"] and r["legenda"].endswith("#ibovespa #dolar #mercadofinanceiro")
    assert "1,39%.\n\nE o dólar" in r["legenda"]  # quebra de linha escrita como texto vira quebra de verdade
    assert r["na_tela"][0]["texto"] == "Ibovespa *+1,39%*" and r["na_tela"][1]["fala"] == 1


def test_numero_inventado_vicio_e_recomendacao_reprovam():
    falas = _bruto()["falas"][:6] + ["O Ibovespa pode chegar a 180.000 pontos, vale ressaltar."]
    problemas = roteirista.conferir(roteirista.montar(_bruto(falas=falas)), MATERIAL)
    assert any("180.000" in p for p in problemas)  # número que não está no material
    assert any("vícios" in p for p in problemas)
    falas = _bruto()["falas"][:6] + ["É hora de comprar ações da Petrobras."]
    assert any("proibida" in p for p in roteirista.conferir(roteirista.montar(_bruto(falas=falas)), MATERIAL))


def test_gancho_fraco_e_roteiro_curto_reprovam():
    fraco = {"especifico": 1, "tensao": 0, "espectador": 1, "rapido": 2, "verdadeiro": 2}
    problemas = roteirista.conferir(roteirista.montar(_bruto(nota=fraco, falas=["A bolsa subiu hoje."] * 5)), MATERIAL)
    assert any("gancho fraco" in p for p in problemas) and any("tamanho" in p for p in problemas)


def test_segunda_versao_quando_a_primeira_reprova(tmp_path, monkeypatch):
    pedidos = []

    def falso(cliente, sistema, pedido, saida, buscas=0, max_tokens=0, links=None):
        if saida["name"] == "registrar_roteiro":
            pedidos.append(pedido)
        if len(pedidos) == 1:
            return _bruto(falas=_bruto()["falas"][:6] + ["O índice pode ir a 200.000 pontos."])
        if saida["name"] == "registrar_apoios":
            return {"apoios": []}  # as imagens de apoio falham: o roteiro continua valendo
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
    monkeypatch.setattr(ia, "estruturado", lambda c, s, p, saida, **k: _bruto() if saida["name"] == "registrar_roteiro"
                        else {"apoios": []})
    assert len(roteirista.rodar(tmp_path, "explica", dia="2026-11-06", cliente=object())) == 1
    assert roteirista.rodar(tmp_path, "explica", dia="2026-11-06", cliente=object()) == []  # já tem roteiro


def test_imagens_de_apoio_teleprompter_e_pacote_do_whatsapp(monkeypatch):
    r = roteirista.montar(_bruto())
    bons = [{"fala": 3, "visual": "Vertical 9:16, 6 seconds. a trading floor with glowing screens"},
            {"fala": 5, "visual": "a dollar bill on a desk, 6 seconds"}]
    monkeypatch.setattr(ia, "estruturado", lambda *a, **k: {"apoios": bons})
    d = roteirista.apoiar(object(), r)
    assert d["apoios_ok"] and [a["fala"] for a in d["apoios"]] == [3, 5]
    assert d["apoios"][0]["texto_da_fala"] == r["linhas"][3] and "No people in focus" in d["apoios"][0]["prompt_flow"]
    assert d["apoios"][0]["prompt_flow"].startswith("Vertical 9:16 video") and "A trading floor" in d["apoios"][0]["prompt_flow"]
    ruins = [{"fala": 0, "visual": "a screen showing 168.501"}]
    problemas = roteirista.conferir_apoios(ruins, r)
    assert any("fora do corpo" in p for p in problemas) and any("número dentro" in p for p in problemas)
    assert any("de 2 a 3" in p for p in problemas)
    r = {**r, **d}
    assert roteirista.teleprompter(r).split("\n\n") == r["linhas"] and r["linhas"][-1] == roteirista.BORDAO
    msgs = roteirista.pacote_whatsapp(r, "Ibovespa hoje")
    assert len(msgs) == 6 and msgs[1] == roteirista.teleprompter(r) and "🎬 ROTEIRO: Ibovespa hoje" in msgs[0]
    assert "Formato sugerido: RUA" in msgs[0] and "VERSÃO RUA" in msgs[2] and "• O dólar subiu 0,85%" in msgs[2]
    assert "fala 4" in msgs[3] and msgs[4] == r["legenda"] and roteirista.AVISO_LEGENDA in msgs[4]
    assert "FIM DO ROTEIRO" in msgs[5]
    varios = roteirista.pacote_whatsapp(r, "Ibovespa hoje", 2, 3)
    assert "ROTEIRO 2 de 3" in varios[0] and "FIM DO ROTEIRO 2 de 3" in varios[-1] and "Dicas" not in varios[0]
    ruim = roteirista.montar({**_bruto(), "rua": {"gancho": "O dólar vai a R$ 7.", "topicos": ["Só um."]}})
    problemas = roteirista.conferir(ruim, MATERIAL)
    assert any("versão rua incompleta" in p for p in problemas)
    assert {"6", "9"} <= roteirista.permitidos("Seis das nove cadeiras")


def test_estrategista_de_marca_pede_nova_versao_quando_a_nota_e_baixa(monkeypatch):
    chamadas = []

    def falso(cliente, sistema, pedido, saida, **k):
        chamadas.append(saida["name"])
        if saida["name"] == "registrar_avaliacao":
            if chamadas.count("registrar_avaliacao") == 1:
                return {"notas": {"persona": 0, "arquetipo": 1, "temperamentos": 1, "gatilhos": 2, "voz": 1},
                        "sugestoes": ["O gancho fala do mercado, não do bolso de quem assiste."], "veredito": "frio"}
            return {"notas": {k: 2 for k in ("persona", "arquetipo", "temperamentos", "gatilhos", "voz")},
                    "sugestoes": [], "veredito": "fala com o público"}
        if saida["name"] == "registrar_apoios":
            return {"apoios": []}
        if saida["name"] == "registrar_avaliacao_viral":
            return {"notas": {}, "sugestoes": [], "veredito": "para o dedo"}
        if chamadas.count("registrar_roteiro") == 2:
            assert "estrategista de marca, nota 5/10" in pedido and "bolso de quem assiste" in pedido
        return _bruto()
    monkeypatch.setattr(ia, "estruturado", falso)
    r = roteirista.escrever(object(), "fechamento", MATERIAL)
    assert r["aprovado"] and r["tentativas"] == 2 and r["marca"]["nota"] == 10 and estrategista.NOTA_MINIMA == 8
    assert chamadas.count("registrar_roteiro") == 2


def test_prints_da_fonte_para_a_edicao():
    artigo = {"o_que_se_sabe": [
        {"texto": "O Focus trouxe 1,20% para o PIB de 2027. Antes, era 1,31%.", "fonte_url": "https://a.com/focus",
         "veiculo": "InfoMoney", "confiavel": True},
        {"texto": "Outro fato do mesmo link.", "fonte_url": "https://a.com/focus", "veiculo": "InfoMoney"},
        {"texto": "Fato duvidoso.", "fonte_url": "https://b.com/x", "veiculo": "Blog", "confiavel": False},
        {"texto": "O Copom manteve a Selic.", "fonte_url": "https://bcb.gov.br/copom", "veiculo": "Banco Central"}]}
    prints = roteirista.prints_artigo(artigo)
    assert [p["veiculo"] for p in prints] == ["InfoMoney", "Banco Central"]
    assert prints[0]["destaque"] == "O Focus trouxe 1,20% para o PIB de 2027."
    r = {**roteirista.montar(_bruto()), "prints": prints}
    edicao = roteirista.pacote_whatsapp(r, "PIB")[-3]
    assert "Prints da fonte" in edicao and "https://bcb.gov.br/copom" in edicao


def test_especialista_em_viralizacao_pede_nova_versao_quando_a_nota_e_baixa(monkeypatch):
    chamadas = []

    def falso(cliente, sistema, pedido, saida, **k):
        chamadas.append(saida["name"])
        if saida["name"] == "registrar_avaliacao":
            return {"notas": {}, "sugestoes": [], "veredito": "fala com o público"}
        if saida["name"] == "registrar_avaliacao_viral":
            if chamadas.count("registrar_avaliacao_viral") == 1:
                return {"notas": {"gancho": 0, "pagamento": 1, "retencao": 1, "envio": 1, "conversa": 1},
                        "sugestoes": ["O gancho não abre lacuna no bolso de quem assiste."], "veredito": "morno"}
            return {"notas": {}, "sugestoes": [], "veredito": "para o dedo"}
        if saida["name"] == "registrar_apoios":
            return {"apoios": []}
        if chamadas.count("registrar_roteiro") == 2:
            assert "especialista em viralização, nota 4/10" in pedido and "lacuna" in pedido
        return _bruto()
    monkeypatch.setattr(ia, "estruturado", falso)
    r = roteirista.escrever(object(), "fechamento", MATERIAL)
    assert r["aprovado"] and r["tentativas"] == 2 and r["viral"]["nota"] == 10
    assert any("🔥 Especialista em viralização: 10/10" in m for m in roteirista.pacote_whatsapp(r, "Teste"))


def test_sem_frase_de_engajamento_entra_o_convite_do_grupo():
    b = _bruto(); b.pop("engajamento")
    r = roteirista.montar(b)
    assert r["linhas"][-2] == roteirista.CHAMADAS["grupo"] and "Comenta GRUPO" in r["linhas"][-2]
