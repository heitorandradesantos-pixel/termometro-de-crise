"""Plantão: só publica notícia com fato de fonte conferida, recente e sem linguagem proibida."""

import json

import pandas as pd

from termometro import ia, plantao

AGORA = pd.Timestamp("2026-11-06 14:20")
LINKS = {"https://www.suno.com.br/noticias/fgc-alerta-golpes-acesso/", "https://sbtnews.sbt.com.br/noticia/fgc",
         "https://valor.globo.com/financas/fgc-dados"}


def _artigo(**troca):
    a = {"titulo": "FGC foi hackeado? O que se sabe sobre o acesso a dados", "descricao": "O FGC confirmou acesso indevido.",
         "palavra_chave": "fgc foi hackeado", "lead": "O FGC confirmou em 2026-11-05 acesso indevido a dados pessoais.",
         "o_que_se_sabe": [
             {"texto": "O FGC confirmou acesso indevido a dados pessoais.", "fonte_url": "https://valor.globo.com/financas/fgc-dados",
              "data": "2026-11-05", "veiculo": "Valor"},
             {"texto": "Os dados podem incluir nome, CPF, e-mail e data de nascimento.",
              "fonte_url": "https://www.suno.com.br/noticias/fgc-alerta-golpes-acesso/", "data": "2026-11-05"},
             {"texto": "O FGC diz não ter achado perda financeira.", "fonte_url": "https://sbtnews.sbt.com.br/noticia/fgc",
              "data": "2026-11-05"},
             {"texto": "Inventado sem fonte da busca.", "fonte_url": "https://blog-qualquer.com/x", "data": "2026-11-05"}],
         "o_que_nao_se_sabe": ["Se os dados foram copiados ainda está em investigação."],
         "o_que_muda_para_voce": ["Seu dinheiro garantido não foi afetado, segundo o FGC."],
         "como_se_proteger": ["O FGC não pede senha nem taxa e não chama por WhatsApp."], "linha_do_tempo": []}
    a.update(troca)
    return a


def test_conferencia_tira_fato_sem_link_da_busca_e_aprova_o_resto():
    r = plantao.conferir(_artigo(), LINKS, "2026-11-06")
    assert r["aprovado"] and len(r["artigo"]["o_que_se_sabe"]) == 3
    assert any("busca não devolveu" in p for p in r["problemas"])
    assert "5/11" in r["artigo"]["lead"]  # datas como o leitor fala


def test_conferencia_barra_pouco_fato_noticia_velha_e_recomendacao():
    assert not plantao.conferir(_artigo(o_que_se_sabe=_artigo()["o_que_se_sabe"][:2]), LINKS, "2026-11-06")["aprovado"]
    velho = [{**f, "data": "2026-10-01"} for f in _artigo()["o_que_se_sabe"][:3]]
    assert not plantao.conferir(_artigo(o_que_se_sabe=velho), LINKS, "2026-11-06")["aprovado"]
    ordem = _artigo(o_que_muda_para_voce=["Hora de vender suas ações de bancos."])
    assert any("linguagem" in p for p in plantao.conferir(ordem, LINKS, "2026-11-06")["problemas"])


def test_rodada_publica_uma_vez_e_nao_repete_assunto(tmp_path, monkeypatch):
    def falso(cliente, sistema, pedido, saida, buscas=0, max_tokens=0, links=None):
        if saida["name"] == "registrar_pauta_plantao":
            return {"assuntos": [{"assunto": "FGC confirma acesso indevido a dados de clientes",
                                  "busca_do_leitor": "fgc foi hackeado", "por_que_importa": "golpes", "fontes": []}]}
        links |= LINKS
        return _artigo()
    monkeypatch.setattr(ia, "estruturado", falso)
    gravados = plantao.rodar(tmp_path, AGORA, cliente=object())
    assert len(gravados) == 1 and json.loads(gravados[0].read_text())["slug"] == "fgc-foi-hackeado"
    assert plantao.rodar(tmp_path, AGORA + pd.Timedelta(hours=2), cliente=object()) == []  # mesmo assunto: não repete


def test_sem_assunto_aprovado_pede_uma_segunda_pauta_sem_o_recusado(tmp_path, monkeypatch):
    pautas = []

    def falso(cliente, sistema, pedido, saida, buscas=0, max_tokens=0, links=None):
        if saida["name"] == "registrar_pauta_plantao":
            pautas.append(pedido)
            if len(pautas) == 1:
                return {"assuntos": [{"assunto": "Liquidação da MW Pay", "busca_do_leitor": "mw pay liquidação",
                                      "fontes": []}]}
            return {"assuntos": [{"assunto": "FGC confirma acesso indevido a dados de clientes",
                                  "busca_do_leitor": "fgc foi hackeado", "fontes": []}]}
        links |= LINKS
        if "MW Pay" in pedido:
            return {**_artigo(), "o_que_se_sabe": _artigo()["o_que_se_sabe"][:1]}  # pouco fato: a conferência barra
        return _artigo()
    monkeypatch.setattr(ia, "estruturado", falso)
    gravados = plantao.rodar(tmp_path, AGORA, cliente=object(), turno="tarde")
    assert len(pautas) == 2 and "Liquidação da MW Pay" in pautas[1]  # a segunda pauta sabe o que foi recusado
    assert len(gravados) == 1 and json.loads(gravados[0].read_text())["slug"] == "fgc-foi-hackeado"


def test_paginas_e_mapa_de_noticias(tmp_path):
    a = plantao.conferir(_artigo(), LINKS, "2026-11-06")["artigo"]
    a.update(slug="fgc-foi-hackeado", publicado_em=AGORA.isoformat(), atualizado_em=AGORA.isoformat(), assunto="FGC")
    (tmp_path / "plantao").mkdir()
    (tmp_path / "plantao" / "2026-11-06-fgc-foi-hackeado.json").write_text(json.dumps(a))
    caminhos, artigos = plantao.paginas(tmp_path / "_site", tmp_path)
    assert caminhos == ["noticias/plantao/index.html", "noticias/plantao/fgc-foi-hackeado.html"]
    pagina = (tmp_path / "_site" / caminhos[1]).read_text()
    for trecho in ["O que se sabe", "O que ainda não se sabe", "Como se proteger", '"@type": "NewsArticle"', "Valor",
                   "PLANTÃO", "Publicado em 06/11/2026 às 14h20"]:
        assert trecho in pagina, trecho
    mapa = plantao.sitemap_noticias(artigos, AGORA + pd.Timedelta(hours=3))
    assert "<news:title>FGC foi hackeado?" in mapa and "/fgc-foi-hackeado</loc>" in mapa
    assert "fgc-foi-hackeado" not in plantao.sitemap_noticias(artigos, AGORA + pd.Timedelta(days=3))


def test_limite_de_artigos_por_dia(tmp_path, monkeypatch):
    chamadas = []
    monkeypatch.setattr(ia, "estruturado", lambda *a, **k: chamadas.append(1) or {"assuntos": []})
    (tmp_path / "plantao").mkdir()
    for i in range(plantao.MAXIMO_POR_DIA):
        (tmp_path / "plantao" / f"2026-11-06-a{i}.json").write_text(json.dumps(
            {"titulo": f"Assunto {i}", "palavra_chave": f"assunto {i}", "publicado_em": f"2026-11-06T0{i}:00:00"}))
    assert plantao.rodar(tmp_path, AGORA, cliente=object()) == [] and chamadas == []  # nem chama a IA


def test_artigo_tem_imagem_para_google_e_whatsapp(tmp_path):
    a = plantao.conferir(_artigo(), LINKS, "2026-11-06")["artigo"]
    a.update(slug="fgc-foi-hackeado", publicado_em=AGORA.isoformat(), atualizado_em=AGORA.isoformat(), assunto="FGC")
    (tmp_path / "plantao").mkdir()
    (tmp_path / "plantao" / "2026-11-06-fgc-foi-hackeado.json").write_text(json.dumps(a))
    plantao.paginas(tmp_path / "_site", tmp_path)
    assert (tmp_path / "_site" / "noticias" / "plantao" / "fgc-foi-hackeado.png").stat().st_size > 10000
    pagina = (tmp_path / "_site" / "noticias" / "plantao" / "fgc-foi-hackeado.html").read_text()
    assert 'property="og:image"' in pagina and '"image": ["https://' in pagina


def test_turnos_manha_tarde_noite_e_atualizacao_no_mesmo_endereco(tmp_path, monkeypatch):
    assert [plantao.turno_de(pd.Timestamp(f"2026-11-06 {h}:13")) for h in (9, 13, 18)] == ["manha", "tarde", "noite"]
    pautas = {"manha": {"assunto": "Ibovespa hoje: o que o mercado olha", "busca_do_leitor": "ibovespa hoje"},
              "tarde": {"assunto": "FGC confirma acesso indevido a dados de clientes", "busca_do_leitor": "fgc foi hackeado"}}

    def falso(cliente, sistema, pedido, saida, buscas=0, max_tokens=0, links=None):
        if saida["name"] == "registrar_pauta_plantao":
            turno = "manha" if "Turno da manhã" in pedido else ("tarde" if "Turno da tarde" in pedido else "noite")
            item = pautas.get(turno) or {"assunto": "FGC: novidade", "busca_do_leitor": "fgc",
                                          "atualizar_slug": "fgc-foi-hackeado"}
            return {"assuntos": [{**item, "por_que_importa": "x", "fontes": []}]}
        links |= LINKS
        if "ATUALIZAÇÃO" in pedido:
            return _artigo(lead="Nesta noite (6/11), o FGC informou o número de afetados.")
        if "ibovespa hoje" in pedido:
            return _artigo(titulo="Ibovespa hoje: o que o mercado olha nesta sexta (6/11)", palavra_chave="ibovespa hoje")
        return _artigo()
    monkeypatch.setattr(ia, "estruturado", falso)
    manha = plantao.rodar(tmp_path, pd.Timestamp("2026-11-06 09:13"), cliente=object())
    assert len(manha) == 1 and json.loads(manha[0].read_text())["turno"] == "manha"
    assert plantao.rodar(tmp_path, pd.Timestamp("2026-11-06 09:40"), cliente=object()) == []  # turno já publicou
    tarde = plantao.rodar(tmp_path, pd.Timestamp("2026-11-06 13:13"), cliente=object())
    assert json.loads(tarde[0].read_text())["slug"] == "fgc-foi-hackeado"
    noite = plantao.rodar(tmp_path, pd.Timestamp("2026-11-06 18:43"), cliente=object())
    a = json.loads(noite[0].read_text())
    assert noite[0] == tarde[0] and a["publicado_em"].endswith("13:13:00") and a["atualizado_em"].endswith("18:43:00")
    assert a["lead"].startswith("Nesta noite") and len(list((tmp_path / "plantao").glob("*.json"))) == 2


def test_card_do_fechamento_e_texto_do_balanco(tmp_path):
    from termometro import fechamento
    dia = tmp_path / "diario" / "2026-11-06"
    dia.mkdir(parents=True)
    m = {"brasil": {"valor": 65, "nivel": "Tensão", "cor": "#EE8A3C"}, "mundo": {"valor": 57, "nivel": "Alerta", "cor": "#F2C14E"},
         "regioes": [{"nome": "América Latina", "paises": [{"nome": "Brasil", "brutos": {
             "bolsa_queda_pct": 19.3, "bolsa_pico": 209067.0, "bolsa_pico_dia": "2026-10-09"}}]}],
         "cotacoes": [{"nome": "Ibovespa", "ultimo": 168773.0, "variacao_pct": 1.55, "serie": "brasil_bolsa"},
                      {"nome": "Dólar", "ultimo": 5.4912, "variacao_pct": 0.6, "serie": "extra_dolar"}]}
    (dia / "mundo.json").write_text(json.dumps(m))
    (dia / "bcb.json").write_text(json.dumps({"selic": {"valor": 13.75, "data": "2026-11-06"}}))
    fc = fechamento.gerar(tmp_path / "_site", tmp_path / "diario", "2026-11-06")
    assert (tmp_path / "_site" / fc["imagem"]).stat().st_size > 20000
    for trecho in ["FECHAMENTO DO TERMÔMETRO · 06/11", "Brasil em 65 (Tensão)", "Ibovespa: 168.773 pontos (▲1,55%)",
                   "19,3% abaixo do recorde de 09/10", "Dólar: R$ 5,49 (▲0,60%)", "Selic 13,75%", "Não é recomendação"]:
        assert trecho in fc["legenda"], trecho
    m["cotacoes"][1]["serie"] = "brasil_moeda"  # dólar do FRED (outro horário): sem card, para não contradizer o dia
    (dia / "mundo.json").write_text(json.dumps(m))
    assert fechamento.gerar(tmp_path / "_site2", tmp_path / "diario", "2026-11-06") is None


def test_cinco_turnos_pelo_horario():
    import pandas as pd

    from termometro import plantao as pl
    horas = {9: "manha", 11: "meio", 13: "tarde", 16: "viral", 18: "noite"}
    for h, turno in horas.items():
        assert pl.turno_de(pd.Timestamp(f"2026-11-09 {h:02d}:30", tz="America/Sao_Paulo")) == turno
    assert set(pl.TURNOS) == set(horas.values()) and pl.MAXIMO_POR_DIA == 5


def test_domingo_de_manha_e_a_agenda_da_semana():
    from termometro import plantao as pl
    assert pl.instrucao("manha", "2026-11-15") == pl.DOMINGO_MANHA
    assert pl.instrucao("manha", "2026-11-16") == pl.TURNOS["manha"] and pl.instrucao("tarde", "2026-11-15") == pl.TURNOS["tarde"]


def test_pauta_das_referencias_nao_repete_assunto(tmp_path, monkeypatch):
    import inspect

    from termometro import plantao as pl
    assert "sugerido" in inspect.signature(pl.rodar).parameters
    fonte = inspect.getsource(pl.rodar)
    assert "sugerido or (not tema" in fonte
