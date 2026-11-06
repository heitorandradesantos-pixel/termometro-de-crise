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
    assert "<news:title>FGC foi hackeado?" in mapa and "fgc-foi-hackeado.html" in mapa
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
