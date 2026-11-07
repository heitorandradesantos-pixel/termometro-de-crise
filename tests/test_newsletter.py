"""Newsletter no Kit: formulário em todo bloco de inscrição, páginas próprias e a edição como e-mail."""

import json

import pandas as pd

from termometro import config, publicar, site


def test_bloco_tem_whatsapp_e_formulario_do_kit():
    b = site.bloco_celular("../")
    assert "Receber no WhatsApp" in b and 'action="/api/inscrever"' in b and 'name="email"' in b
    assert 'class="isca"' in b and "Termômetro da Semana" in b and '../privacidade.html' in b


def test_paginas_da_newsletter(tmp_path):
    assert site.paginas_newsletter(tmp_path, "2026-11-05") == ["newsletter/"]
    capa = (tmp_path / "newsletter" / "index.html").read_text()
    assert "O Termômetro da Semana" in capa and "../edicoes/2026-11-05.html" in capa and "data-news" in capa
    assert "Confirmar inscrição" in (tmp_path / "newsletter" / "obrigado.html").read_text()
    assert config.WHATSAPP_URL in (tmp_path / "newsletter" / "confirmado.html").read_text()


def test_quando_enviar_domingo_8h_ou_daqui_a_10_minutos():
    domingo = pd.Timestamp("2026-11-08 07:40", tz="America/Sao_Paulo")
    assert publicar.quando_enviar(domingo) == "2026-11-08T11:00:00Z"
    atrasado = pd.Timestamp("2026-11-08 09:00", tz="America/Sao_Paulo")
    assert publicar.quando_enviar(atrasado) == "2026-11-08T12:10:00Z"


def test_edicao_vira_email_do_kit_e_respeita_o_revisor(tmp_path, monkeypatch):
    pasta = tmp_path / "2026-11-08"
    pasta.mkdir()
    (pasta / "copy.json").write_text(json.dumps({"titulo_site": "A semana", "pre_cabecalho": "O resumo",
                                                 "assuntos_email": ["Assunto A", "Assunto B"], "assunto_escolhido": 1,
                                                 "descricao_seo": "x"}))
    (pasta / "edicao.md").write_text("# A semana\n\nO Brasil fechou em **64**.")
    (pasta / "revisao.json").write_text(json.dumps({"aprovado": True}))
    monkeypatch.setenv("KIT_ENVIO", "rascunho")
    corpo = publicar.email_kit(pasta)
    assert corpo["subject"] == "Assunto B" and corpo["preview_text"] == "O resumo" and corpo["send_at"] is None
    assert "<strong>64</strong>" in corpo["content"] and "não é recomendação" in corpo["content"].lower()
    assert config.WHATSAPP_URL in corpo["content"] and corpo["public"] is False
    enviados = []

    class R:
        status_code, text = 201, "{}"

    monkeypatch.setattr(publicar.requests, "post", lambda url, json=None, headers=None, timeout=0: enviados.append(
        (url, json, headers)) or R())
    monkeypatch.setenv("KIT_API_KEY", "chave-de-teste")
    assert publicar.newsletter_kit(pasta) and enviados[0][0] == publicar.KIT_API
    assert enviados[0][2]["X-Kit-Api-Key"] == "chave-de-teste"
    (pasta / "revisao.json").write_text(json.dumps({"aprovado": False}))
    assert not publicar.newsletter_kit(pasta)  # reprovada pelo Revisor não sai
