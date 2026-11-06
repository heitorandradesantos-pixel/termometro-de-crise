"""Abertura do Termômetro: como o mundo amanheceu e como o Brasil abriu."""

import json

import pandas as pd

from termometro import abertura, whatsapp

AGORA = pd.Timestamp("2026-11-09 10:20", tz="America/Sao_Paulo")


def _buscar(fechados=(), sem=(), horas_fechado=8):
    def buscar(url, headers=None, timeout=0, params=None):
        simbolo = url.rsplit("/", 1)[1]

        class R:
            def raise_for_status(self):
                if simbolo in sem:
                    raise ConnectionError("fora do ar")

            def json(self):
                hora = AGORA - pd.Timedelta(hours=horas_fechado if simbolo in fechados else 0, minutes=15)
                inicio = AGORA.timestamp() - (99999 if simbolo in fechados else 3600)
                preco = {"^BVSP": 169000.0, "BRL=X": 5.48, "BZ=F": 64.2, "GC=F": 4010.0, "BTC-USD": 101200.0}.get(simbolo, 100.0)
                return {"chart": {"result": [{"meta": {
                    "regularMarketPrice": preco, "chartPreviousClose": preco / 1.01, "currency": "USD",
                    "regularMarketTime": int(hora.timestamp()),
                    "currentTradingPeriod": {"regular": {"start": inicio, "end": inicio + 7200}}}}]}}
        return R()
    return buscar


def test_texto_da_abertura_com_asia_fechada_europa_aberta_e_destaque(tmp_path):
    diario = tmp_path / "diario"
    (diario / "2026-11-06").mkdir(parents=True)
    (diario / "2026-11-06" / "panorama.txt").write_text("x")
    (diario / "2026-11-06" / "mundo.json").write_text(json.dumps(
        {"brasil": {"valor": 64, "nivel": "Tensão"}, "mundo": {"valor": 58, "nivel": "Alerta"}}))
    (diario / "plantao").mkdir()
    (diario / "plantao" / "2026-11-09-dolar-abre.json").write_text(json.dumps(
        {"titulo": "Dólar abre a semana em alta", "slug": "dolar-abre", "publicado_em": "2026-11-09T09:20:00"}))
    cot = abertura.coletar(AGORA, _buscar(fechados={"^N225", "^HSI", "000001.SS"}, sem={"^FTSE"}))
    assert "FTSE 100" in cot["falhas"]  # um índice fora do ar não derruba a abertura
    texto = abertura.montar(cot, abertura.ultimo_fechamento(diario, "2026-11-09"), abertura.destaque(diario, "2026-11-09"))
    assert texto.startswith("*TERMÔMETRO DE CRISE · Abertura de seg, 09/11*")
    assert "*Ásia (fechamento)*" in texto and "*Europa (agora)*" in texto and "FTSE" not in texto
    assert "Ibovespa: 169.000 pontos (▲1,00%)" in texto and "Dólar: R$ 5,48" in texto
    assert "Brasil na abertura (10h05)" in texto and "Petróleo Brent US$ 64,20" in texto and "Bitcoin US$ 101.200" in texto
    assert "No último fechamento (06/11): Brasil em 64 (Tensão)" in texto
    assert "Dólar abre a semana em alta" in texto and "/noticias/plantao/dolar-abre.html" in texto
    assert len(texto) <= whatsapp.LEGENDA_MAXIMA  # cabe inteiro na legenda do card


def test_sem_b3_no_dia_nao_tem_abertura(tmp_path):
    cot = abertura.coletar(AGORA, _buscar(fechados={"^BVSP"}, horas_fechado=65))  # sexta
    assert "Ibovespa" not in cot["itens"] and abertura.montar(cot, None, None) is None


def test_card_e_envio_da_abertura(tmp_path, monkeypatch):
    monkeypatch.setenv("WHATSAPP_ENVIO", "sim")
    real = abertura.coletar
    monkeypatch.setattr(abertura, "coletar", lambda agora=None, buscar=None: real(AGORA, _buscar()))
    monkeypatch.setattr(whatsapp.pd.Timestamp, "now", classmethod(lambda cls, tz=None: AGORA))
    diario, pasta = tmp_path / "diario", tmp_path / "envio"
    assert "pronta para enviar (sim)" in whatsapp.preparar(diario, "", pasta, tipo="abertura")
    envio = json.loads((pasta / "envio.json").read_text())
    assert envio["tipo"] == "abertura" and envio["dia"] == "2026-11-09" and envio["imagem"].endswith(".png")
    assert envio["legenda"].startswith("*TERMÔMETRO DE CRISE · Abertura") and envio["textos"] == []
    (pasta / "envio.json.resultado.json").write_text(json.dumps({"ok": True, "ids": ["A"]}))
    assert "enviado (sim)" in whatsapp.concluir(diario, pasta)
    assert "já foi enviada" in whatsapp.preparar(diario, "", pasta, tipo="abertura")  # a reserva não repete
