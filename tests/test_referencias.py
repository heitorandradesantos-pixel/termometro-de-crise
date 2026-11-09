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
    monkeypatch.setattr(ref, "PERFIS", ("pablospyer", "falecomrian", "shimoncomunica"))
    manual = tmp_path / "referencias.md"
    manual.write_text("# Referências\n\n" + ref.MARCA_DIARIO + "\n- 2026-11-01 · nota antiga\n")
    monkeypatch.setattr(ref, "ARQ_MANUAL", manual)
    monkeypatch.setattr(ref.atualizar_manual, "__defaults__", (manual,))
    vistos_transcritos = []

    def analisar_falso(cliente, perfil, legenda, transcricao, titulos):
        vistos_transcritos.append(transcricao)
        pauta = "O que se sabe sobre o novo imposto do Pix" if perfil == "pablospyer" else ""
        return {"tema": f"Tema de {perfil}", "gancho": "Pergunta de bolso.", "tecnicas": ["print da fonte"],
                "formato": "selfie, 40 s", "pauta": pauta, "ja_coberto": False, "relevancia": "alta"}

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


def test_no_maximo_duas_pautas_por_dia(tmp_path, monkeypatch):
    monkeypatch.setenv("IG_TOKEN", "t")
    monkeypatch.setenv("IG_USER_ID", "1")
    monkeypatch.setattr(ref, "atualizar_manual", lambda notas: None)
    hoje = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
    pasta = tmp_path / "ref"
    pasta.mkdir()
    (pasta / "vistos.json").write_text(json.dumps({"a": {"pauta_enviada": hoje}}))
    monkeypatch.setattr(ref, "analisar", lambda c, perfil, *a: {"tema": "t", "pauta": f"Pauta de {perfil}", "ja_coberto": False,
                                                              "relevancia": "alta"})
    (tmp_path / "plantao").mkdir()
    r = ref.rodar(tmp_path, pasta, cliente=object(), buscar=graph_falso, transcritor=lambda v: "")
    assert len(r["pautas"]) == 1  # já tinha ido 1 hoje; o teto é 2


def test_sem_pauta_vira_vazio():
    for texto in ("Sem pauta: material insuficiente.", "(vazio: sem conteúdo)", "Nenhuma: vídeo atemporal", "-",
                  "SEM PAUTA", "  "):
        assert ref.limpar_pauta(texto) == ""
    assert ref.limpar_pauta("O que se sabe sobre o boletim Focus") == "O que se sabe sobre o boletim Focus"


def test_ideias_de_reels_vao_para_o_whatsapp_uma_vez(tmp_path, monkeypatch):
    from termometro import whatsapp
    hoje = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
    pasta = tmp_path / "referencias"
    pasta.mkdir()
    (pasta / "vistos.json").write_text(json.dumps({
        "a": {"perfil": "pablospyer", "dia": hoje, "ideia_reel": "Quanto o Focus prevê para a inflação e o que muda no seu boleto."},
        "b": {"perfil": "falecomrian", "dia": hoje, "ideia_reel": ""},
        "c": {"perfil": "shimoncomunica", "dia": "2020-01-01", "ideia_reel": "velha"}}))
    saida = tmp_path / "_ideias"
    assert "1 ideia" in whatsapp.preparar_ideias(tmp_path, saida)
    envio = json.loads((saida / "envio.json").read_text())
    assert envio["modo"] == "teste" and "Focus" in envio["textos"][0] and envio["ideias"] == ["a"]
    (saida / "envio.json.resultado.json").write_text(json.dumps({"ok": True}))
    assert "1 enviada" in whatsapp.concluir(tmp_path, saida)
    assert "Nenhuma ideia" in whatsapp.preparar_ideias(tmp_path, saida)


def test_so_relevancia_alta_vira_artigo(tmp_path, monkeypatch):
    monkeypatch.setenv("IG_TOKEN", "t")
    monkeypatch.setenv("IG_USER_ID", "1")
    monkeypatch.setattr(ref, "atualizar_manual", lambda notas: None)
    (tmp_path / "plantao").mkdir()
    respostas = {"pablospyer": "alta", "falecomrian": "media", "shimoncomunica": "baixa"}
    monkeypatch.setattr(ref, "analisar", lambda c, perfil, *a: {
        "tema": "t", "pauta": f"O que se sabe sobre {perfil}", "ja_coberto": False, "relevancia": respostas[perfil],
        "ideia_reel": f"Ideia de {perfil}"})
    r = ref.rodar(tmp_path, tmp_path / "ref", cliente=object(), buscar=graph_falso, transcritor=lambda v: "fala")
    assert r["pautas"] == ["O que se sabe sobre pablospyer"]
    assert len(ref.ideias_pendentes(tmp_path / "ref")) == 3


def test_resumo_de_ideias_tira_repetida_e_nao_serve(tmp_path):
    from termometro import whatsapp
    pasta = tmp_path / "referencias"
    pasta.mkdir()
    hoje = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
    (pasta / "vistos.json").write_text(json.dumps({
        "a": {"perfil": "falecomrian", "dia": hoje,
              "ideia_reel": "Se o seu banco quebrar, o que o FGC cobre por CPF e por instituição."},
        "b": {"perfil": "pablospyer", "dia": hoje,
              "ideia_reel": "O que o FGC cobre por CPF e por instituição quando um banco digital quebra."},
        "c": {"perfil": "shimoncomunica", "dia": hoje, "ideia_reel": "Não serve como está: é opinião política."},
        "d": {"perfil": "pablospyer", "dia": hoje, "ideia_reel": "Selic mantida: o que muda na parcela do cartão."}}))
    saida = tmp_path / "_ideias"
    assert "2 ideia" in whatsapp.preparar_ideias(tmp_path, saida)
    envio = json.loads((saida / "envio.json").read_text())
    assert sorted(envio["ideias"]) == ["a", "d"] and "Não serve" not in envio["textos"][0]
    vistos = json.loads((pasta / "vistos.json").read_text())
    assert vistos["b"].get("ideia_enviada") and vistos["c"].get("ideia_enviada")  # descartadas não voltam amanhã
