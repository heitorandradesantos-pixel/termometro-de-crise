"""Envio automático ao WhatsApp: desligado por padrão, teste antes, nunca duas vezes."""

import json

from termometro import whatsapp


def _dia(tmp_path):
    dia = tmp_path / "diario" / "2026-11-06"
    dia.mkdir(parents=True)
    m = {"brasil": {"valor": 65, "nivel": "Tensão", "cor": "#EE8A3C"}, "mundo": {"valor": 57, "nivel": "Alerta", "cor": "#F2C14E"},
         "regioes": [], "cotacoes": [{"nome": "Ibovespa", "ultimo": 168773.0, "variacao_pct": 1.55, "serie": "brasil_bolsa"},
                                     {"nome": "Dólar", "ultimo": 5.49, "variacao_pct": 0.6, "serie": "extra_dolar"}]}
    (dia / "mundo.json").write_text(json.dumps(m))
    (dia / "panorama.txt").write_text("*TERMÔMETRO DE CRISE · Panorama*\n\nMundo em 57")
    return tmp_path / "diario"


def test_modo_vem_da_variavel_ou_do_arquivo(tmp_path, monkeypatch):
    monkeypatch.setattr(whatsapp, "ARQ_MODO", tmp_path / "modo.txt")
    monkeypatch.delenv("WHATSAPP_ENVIO", raising=False)
    assert whatsapp.modo() == "nao"  # sem nada, não envia
    (tmp_path / "modo.txt").write_text("sim\n")
    assert whatsapp.modo() == "sim"
    monkeypatch.setenv("WHATSAPP_ENVIO", "teste")
    assert whatsapp.modo() == "teste"
    monkeypatch.setenv("WHATSAPP_ENVIO", "qualquer")
    assert whatsapp.modo() == "nao"


def test_prepara_card_balanco_e_panorama_e_nunca_repete(tmp_path, monkeypatch):
    monkeypatch.setenv("WHATSAPP_ENVIO", "sim")
    diario, pasta = _dia(tmp_path), tmp_path / "envio"
    assert "pronto" in whatsapp.preparar(diario, "2026-11-06", pasta)
    envio = json.loads((pasta / "envio.json").read_text())
    assert envio["modo"] == "sim" and envio["imagem"].endswith("fechamento-2026-11-06.png")
    assert "FECHAMENTO DO TERMÔMETRO" in envio["legenda"] and envio["textos"][0].startswith("*TERMÔMETRO")
    (pasta / "envio.json.resultado.json").write_text(json.dumps({"ok": True, "ids": ["A", "B"]}))
    assert "enviado (sim)" in whatsapp.concluir(diario, pasta)
    assert "já foi enviado" in whatsapp.preparar(diario, "2026-11-06", pasta)  # a reserva não repete
    assert "pronto" in whatsapp.preparar(diario, "2026-11-06", pasta, teste=True)  # o teste sempre pode


def test_falha_fica_registrada_mas_nao_bloqueia_nova_tentativa(tmp_path, monkeypatch):
    monkeypatch.setenv("WHATSAPP_ENVIO", "sim")
    diario, pasta = _dia(tmp_path), tmp_path / "envio"
    whatsapp.preparar(diario, "2026-11-06", pasta)
    assert "falhou" in whatsapp.concluir(diario, pasta)  # sem resultado: o envio não aconteceu
    assert json.loads((diario / "2026-11-06" / "whatsapp.json").read_text())[0]["ok"] is False
    assert "pronto" in whatsapp.preparar(diario, "2026-11-06", pasta)


def test_desligado_nao_prepara_nada(tmp_path, monkeypatch):
    monkeypatch.setenv("WHATSAPP_ENVIO", "nao")
    assert "desligado" in whatsapp.preparar(_dia(tmp_path), "2026-11-06", tmp_path / "envio")
    assert not (tmp_path / "envio").exists()
