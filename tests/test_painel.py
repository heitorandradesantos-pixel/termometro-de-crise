import json

import pandas as pd
import pytest
from cryptography.exceptions import InvalidTag

from termometro import painel


class Resposta:
    def __init__(self, corpo, status=200):
        self.corpo, self.status_code = corpo, status

    def json(self):
        return self.corpo


def graph_falso(chamadas=None):
    """Uma conta com 3 posts (um Reel forte, um fraco e um carrossel), em duas páginas, e uma métrica que não existe."""
    midias = [
        {"id": "r1", "caption": "Selic mantida: o que muda no cartão\n#selic", "media_type": "VIDEO",
         "media_product_type": "REELS", "permalink": "https://instagram.com/reel/r1", "timestamp": "2026-11-08T12:00:00+0000",
         "thumbnail_url": "https://cdn/r1.jpg", "like_count": 40, "comments_count": 6},
        {"id": "r2", "caption": "Dólar hoje", "media_type": "VIDEO", "media_product_type": "REELS",
         "permalink": "https://instagram.com/reel/r2", "timestamp": "2026-11-07T12:00:00+0000"},
        {"id": "c1", "caption": "Carrossel do FGC", "media_type": "CAROUSEL_ALBUM", "media_product_type": "FEED",
         "permalink": "https://instagram.com/p/c1", "timestamp": "2026-10-01T12:00:00+0000", "media_url": "https://cdn/c1.jpg"},
    ]
    numeros = {"r1": {"views": 5000, "reach": 3000, "saved": 60, "shares": 90, "comments": 6, "likes": 40,
                      "total_interactions": 196, "ig_reels_avg_watch_time": 12400},
               "r2": {"views": 900, "reach": 800, "saved": 2, "shares": 1, "comments": 0, "likes": 10,
                      "total_interactions": 13, "ig_reels_avg_watch_time": 3100},
               "c1": {"views": 400, "reach": 350, "saved": 9, "shares": 3, "comments": 1, "likes": 20,
                      "total_interactions": 33, "profile_visits": 4}}

    def buscar(url, params=None, timeout=None):
        if chamadas is not None:
            chamadas.append(url)
        if url.endswith("/17841"):
            return Resposta({"username": "termometrodecrise", "followers_count": 120, "media_count": 3})
        if url.endswith("/17841/media"):
            return Resposta({"data": midias[:2], "paging": {"next": "https://graph/pagina2"}})
        if url == "https://graph/pagina2":
            return Resposta({"data": midias[2:]})
        mid = url.split("/")[-2]
        pedidas = params["metric"].split(",")
        if "follows" in pedidas:  # a API não tem essa métrica para este post
            return Resposta({"error": {"message": "metric follows not supported", "code": 100}}, 400)
        return Resposta({"data": [{"name": m, "values": [{"value": numeros[mid][m]}]}
                                  for m in pedidas if m in numeros[mid]]})
    return buscar


@pytest.fixture(autouse=True)
def limpo(monkeypatch):
    painel._INVALIDAS.clear()
    monkeypatch.setenv("IG_TOKEN", "t")
    monkeypatch.setenv("IG_USER_ID", "17841")
    monkeypatch.setenv("PAINEL_SENHA", "senha-forte-de-teste")


def test_cofre_abre_so_com_a_senha_certa():
    texto = painel.cifrar({"a": 1, "nome": "Termômetro"}, "certa")
    assert "Termômetro" not in texto and painel.decifrar(texto, "certa") == {"a": 1, "nome": "Termômetro"}
    with pytest.raises(InvalidTag):
        painel.decifrar(texto, "errada")


def test_rodar_le_metricas_calcula_forca_e_guarda_criptografado(tmp_path):
    arq = tmp_path / "painel" / "dados.enc"
    msg = painel.rodar(arq, buscar=graph_falso(), agora="2026-11-09T09:11-03:00")
    assert "3 post(s)" in msg and "120 seguidores" in msg and "follows" in msg
    assert "Selic" not in arq.read_text()  # nada legível no repositório
    dados, sal = painel.ler("senha-forte-de-teste", arq)
    r1 = next(p for p in dados["posts"] if p["id"] == "r1")
    assert r1["forca"] == round((2 * 90 + 60 + 6) / 3000 * 100, 1) and r1["tempo_medio"] == 12.4
    assert r1["data"] == "2026-11-08T12:00:00+00:00" and r1["serie"] == [["2026-11-09T09:11-03:00", 5000]]
    c1 = next(p for p in dados["posts"] if p["id"] == "c1")
    assert c1["views"] == 400 and c1["capa"] == "https://cdn/c1.jpg"
    assert dados["seguidores"] == [{"t": "2026-11-09T09:11-03:00", "n": 120}]
    # segunda leitura no mesmo horário não duplica; em outro horário, entra na série e o sal continua o mesmo
    painel.rodar(arq, buscar=graph_falso(), agora="2026-11-09T09:40-03:00")
    painel.rodar(arq, buscar=graph_falso(), agora="2026-11-09T13:11-03:00")
    dados2, sal2 = painel.ler("senha-forte-de-teste", arq)
    assert len(dados2["seguidores"]) == 2 and sal2 == sal
    assert len(next(p for p in dados2["posts"] if p["id"] == "r1")["serie"]) == 2


def test_sem_segredos_nao_faz_nada(monkeypatch, tmp_path):
    monkeypatch.delenv("PAINEL_SENHA")
    assert "faltam" in painel.rodar(tmp_path / "x.enc", buscar=graph_falso())
    assert not (tmp_path / "x.enc").exists()


def test_candidatos_e_ranking_da_semana(tmp_path):
    arq = tmp_path / "dados.enc"
    painel.rodar(arq, buscar=graph_falso(), agora="2026-11-09T09:11-03:00")
    dados, _ = painel.ler("senha-forte-de-teste", arq)
    top, confiavel = painel.candidatos(dados["posts"])
    assert [p["id"] for p in top][:2] == ["r1", "c1"] and confiavel
    texto = painel.ranking(dados, agora=pd.Timestamp("2026-11-09T09:30", tz="America/Sao_Paulo"))
    assert "1. Selic mantida: o que muda no cartão" in texto and "c1" not in texto  # o carrossel é de outubro
    assert "Ainda é cedo" not in texto and "painel/" in texto
    pouco = painel.candidatos(dados["posts"], minimo=10_000)
    assert pouco[1] is False and pouco[0]  # ninguém passou do mínimo: mostra assim mesmo, avisando


def test_pagina_do_painel_fora_do_google(tmp_path):
    arq = tmp_path / "dados.enc"
    arq.write_text(painel.cifrar({"posts": []}, "x"))
    painel.gerar(tmp_path / "site", arq)
    pagina = (tmp_path / "site" / "painel" / "index.html").read_text()
    assert 'name="robots" content="noindex, nofollow"' in pagina and "raw.githubusercontent.com" in pagina
    assert "__FONTE__" not in pagina and f"const ITER = {painel.ITERACOES};" in pagina
    assert (tmp_path / "site" / "painel" / "dados.enc").exists()
    assert "X-Robots-Tag: noindex" in (tmp_path / "site" / "_headers").read_text()
    produto = (tmp_path / "site" / "metricas" / "index.html").read_text()
    assert "Descubra qual post seu vale impulsionar" in produto and "__" not in produto.replace("__proto__", "")
    assert "sem ligação com a Meta" in produto
    demo_produto = (tmp_path / "site" / "metricas" / "demo" / "index.html").read_text()
    assert "TERMÔMETRO" not in demo_produto and "--fundo:#F5F8FC" in demo_produto and "__MARCA__" not in demo_produto
    assert "/metricas/*" in (tmp_path / "site" / "_headers").read_text()
    vitrine = (tmp_path / "site" / "painel" / "demo" / "index.html").read_text()
    assert "/*__DEMO__*/null" not in vitrine and '"usuario": "seuperfil"' in vitrine and "__ITER__" not in vitrine


def test_demo_tem_numeros_estaveis_e_recentes():
    hoje = pd.Timestamp("2026-11-09T10:00", tz="America/Sao_Paulo")
    a, b = painel.demo(hoje), painel.demo(hoje)
    assert a == b and len(a["posts"]) == len(painel.DEMO_TITULOS)
    assert all(p["forca"] is not None for p in a["posts"]) and painel.candidatos(a["posts"])[1]


def test_ranking_vai_para_o_whatsapp(tmp_path, monkeypatch):
    from termometro import whatsapp
    arq = tmp_path / "dados.enc"
    painel.rodar(arq, buscar=graph_falso(), agora="2026-11-09T09:11-03:00")
    monkeypatch.setattr(painel, "ARQ", arq)
    saida = tmp_path / "_ranking"
    assert "pronto" in whatsapp.preparar_ranking(saida)
    envio = json.loads((saida / "envio.json").read_text())
    assert envio["modo"] == "teste" and envio["tipo"] == "ranking" and "RANKING DA SEMANA" in envio["textos"][0]
    (saida / "envio.json.resultado.json").write_text(json.dumps({"ok": True}))
    assert "enviado" in whatsapp.concluir(tmp_path, saida)
