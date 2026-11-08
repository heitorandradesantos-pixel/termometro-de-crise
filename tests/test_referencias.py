import json

import pandas as pd

from termometro import referencias as ref


class Resposta:
    def __init__(self, dados=None, conteudo=b""):
        self.dados, self.content = dados, conteudo

    def raise_for_status(self):
        pass

    def json(self):
        return self.dados


def graph_falso(url, params=None, timeout=None):
    if "graph.facebook.com" not in url:
        return Resposta(conteudo=b"video")
    agora = pd.Timestamp.now(tz="UTC")
    perfil = params["fields"].split("username(")[1].split(")")[0]
    media = [{"id": f"{perfil}-1", "caption": "Legenda que não pode ir para o repositório", "media_type": "VIDEO",
              "permalink": f"https://www.instagram.com/reel/{perfil}1/", "timestamp": agora.strftime("%Y-%m-%dT%H:%M:%S+0000"),
              "media_url": "https://video.exemplo/1.mp4"},
             {"id": f"{perfil}-velho", "caption": "velho", "media_type": "IMAGE", "permalink": "x",
              "timestamp": (agora - pd.Timedelta(days=9)).strftime("%Y-%m-%dT%H:%M:%S+0000")}]
    return Resposta({"business_discovery": {"media": {"data": media}}})


def test_sem_token_nao_faz_nada(tmp_path, monkeypatch):
    monkeypatch.delenv("IG_TOKEN", raising=False)
    assert ref.rodar(tmp_path, tmp_path / "ref", cliente=object()) == {"notas": [], "pautas": []}


def test_analisa_os_reels_novos_sem_guardar_o_texto_do_criador(tmp_path, monkeypatch):
    monkeypatch.setenv("IG_TOKEN", "t")
    monkeypatch.setenv("IG_USER_ID", "1")
    manual = tmp_path / "referencias.md"
    manual.write_text("# Referências\n\n" + ref.MARCA_DIARIO + "\n- 2026-11-01 · nota antiga\n")
    monkeypatch.setattr(ref, "ARQ_MANUAL", manual)
    monkeypatch.setattr(ref.atualizar_manual, "__defaults__", (manual,))
    vistos_transcritos = []

    def analisar_falso(cliente, perfil, legenda, transcricao, titulos):
        vistos_transcritos.append(transcricao)
        pauta = "O que se sabe sobre o novo imposto do Pix" if perfil == "pablospyer" else ""
        return {"tema": f"Tema de {perfil}", "gancho": "Pergunta de bolso.", "tecnicas": ["print da fonte"],
                "formato": "selfie, 40 s", "pauta": pauta, "ja_coberto": False}

    monkeypatch.setattr(ref, "analisar", analisar_falso)
    (tmp_path / "plantao").mkdir()
    r = ref.rodar(tmp_path, tmp_path / "ref", cliente=object(), buscar=graph_falso, transcritor=lambda v: "fala transcrita")
    assert len(r["notas"]) == 3 and r["pautas"] == ["O que se sabe sobre o novo imposto do Pix"]
    assert vistos_transcritos == ["fala transcrita"] * 3 and "Tema de shimoncomunica" in manual.read_text()
    texto = manual.read_text()
    assert "Tema de pablospyer" in texto and "nota antiga" in texto and "Legenda que não pode" not in texto
    vistos = (tmp_path / "ref" / "vistos.json").read_text()
    assert "pablospyer-1" in vistos and "Legenda" not in vistos and "fala transcrita" not in vistos
    # rodando de novo, nada se repete
    r2 = ref.rodar(tmp_path, tmp_path / "ref", cliente=object(), buscar=graph_falso, transcritor=lambda v: "")
    assert r2 == {"notas": [], "pautas": []}


def test_diario_guarda_so_as_ultimas_notas(tmp_path):
    manual = tmp_path / "m.md"
    ref.atualizar_manual([f"- nota {i}" for i in range(20)], manual)
    linhas = [li for li in manual.read_text().splitlines() if li.startswith("- ")]
    assert len(linhas) == ref.MAX_NOTAS and linhas[0] == "- nota 0"


def test_manual_de_referencias_entra_no_roteirista_e_no_copy():
    from termometro import copywriter, estrategista, roteirista
    assert "Diário de referências" in roteirista.SISTEMA and "Diário de referências" in copywriter.SISTEMA
    assert "Diário de referências" in estrategista.SISTEMA
    assert json.dumps(ref.ferramenta())  # o formulário é JSON válido


def test_no_maximo_tres_pautas_por_dia(tmp_path, monkeypatch):
    monkeypatch.setenv("IG_TOKEN", "t")
    monkeypatch.setenv("IG_USER_ID", "1")
    monkeypatch.setattr(ref, "atualizar_manual", lambda notas: None)
    hoje = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
    pasta = tmp_path / "ref"
    pasta.mkdir()
    (pasta / "vistos.json").write_text(json.dumps({"a": {"pauta_enviada": hoje}, "b": {"pauta_enviada": hoje}}))
    monkeypatch.setattr(ref, "analisar", lambda c, perfil, *a: {"tema": "t", "pauta": f"Pauta de {perfil}", "ja_coberto": False})
    (tmp_path / "plantao").mkdir()
    r = ref.rodar(tmp_path, pasta, cliente=object(), buscar=graph_falso, transcritor=lambda v: "")
    assert len(r["pautas"]) == 1  # já tinham ido 2 hoje
