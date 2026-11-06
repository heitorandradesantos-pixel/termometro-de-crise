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
    (dia / "panorama.txt").write_text("x")
    return tmp_path / "diario"


def test_desligado_por_padrao_e_sem_configuracao(tmp_path, monkeypatch):
    for k in ("WHATSAPP_ENVIO", "ZAPI_INSTANCIA", "ZAPI_TOKEN", "ZAPI_CLIENT_TOKEN", "WHATSAPP_DESTINO"):
        monkeypatch.delenv(k, raising=False)
    assert "desligado" in whatsapp.fechamento(_dia(tmp_path), "2026-11-06", tmp_path / "t")
    monkeypatch.setenv("WHATSAPP_ENVIO", "sim")
    assert "sem configuração" in whatsapp.fechamento(tmp_path / "diario", "2026-11-06", tmp_path / "t")


def test_envia_card_com_legenda_uma_vez_e_teste_vai_para_outro_destino(tmp_path, monkeypatch):
    pedidos = []

    class Resposta:
        content = b"{}"

        def raise_for_status(self):
            pass

        def json(self):
            return {"messageId": "ABC"}

    def falso(metodo, url, json=None, timeout=0, headers=None):
        pedidos.append((metodo, url, json, headers))
        return Resposta()
    monkeypatch.setattr(whatsapp.requests, "request", falso)
    for k, v in {"ZAPI_INSTANCIA": "inst", "ZAPI_TOKEN": "tok", "ZAPI_CLIENT_TOKEN": "seg", "WHATSAPP_ENVIO": "teste",
                 "WHATSAPP_TESTE": "5511999999999", "WHATSAPP_DESTINO": "120363-group"}.items():
        monkeypatch.setenv(k, v)
    diario = _dia(tmp_path)
    assert "enviado" in whatsapp.fechamento(diario, "2026-11-06", tmp_path / "t")
    metodo, url, corpo, cabecalho = pedidos[-1]
    assert url == "https://api.z-api.io/instances/inst/token/tok/send-image" and cabecalho["Client-Token"] == "seg"
    assert corpo["phone"] == "5511999999999" and corpo["image"].startswith("data:image/png;base64,")
    assert "FECHAMENTO DO TERMÔMETRO" in corpo["caption"]
    assert "já foi enviado" in whatsapp.fechamento(diario, "2026-11-06", tmp_path / "t")  # reserva não repete
    monkeypatch.setenv("WHATSAPP_ENVIO", "sim")  # depois do teste, a comunidade recebe uma vez
    assert "enviado" in whatsapp.fechamento(diario, "2026-11-06", tmp_path / "t")
    assert pedidos[-1][2]["phone"] == "120363-group" and len(pedidos) == 2
