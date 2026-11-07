"""Estúdio: página de trabalho dos vídeos, fora do Google, com o prompt de cada cena pronto para copiar."""

import json

from termometro import estudio, roteirista


def _roteiro(aprovado=True):
    cenas = [{"tipo": "apresentadora" if i in (0, 5) else "imagem", "fala": f"Fala {i} com US$ 6,3 bilhões em 7/11.",
              "visual": "a trading floor", "na_tela": "Tela", "transicao": "camera pushes in", "inicio_s": i * 8}
             for i in range(6)]
    return {"aprovado": aprovado, "problemas": [] if aprovado else ["tamanho"], "segundos": 47,
            "gancho": {"texto": "O dólar subiu."}, "legenda": "Dólar hoje.\n\n#dolar", "na_tela": [{"texto": "R$ 5,51"}],
            "cenas": cenas, "cenas_ok": True, "linhas": ["O dólar subiu."]}


def test_estudio_lista_os_dias_e_cada_cena_tem_prompt_sem_entrar_no_google(tmp_path):
    diario = tmp_path / "diario"
    (diario / "2026-11-07" / "roteiros").mkdir(parents=True)
    (diario / "plantao").mkdir()
    (diario / "plantao" / "2026-11-07-pix.json").write_text(json.dumps({"titulo": "Pix caiu: o que se sabe"}))
    (diario / "2026-11-07" / "roteiros" / "explica-pix.json").write_text(json.dumps(_roteiro()))
    (diario / "2026-11-07" / "roteiros" / "fechamento.json").write_text(json.dumps(_roteiro(aprovado=False)))
    caminhos = estudio.gerar(tmp_path / "site", diario)
    assert caminhos == ["estudio/2026-11-07.html"]
    pagina = (tmp_path / "site" / "estudio" / "2026-11-07.html").read_text()
    assert 'content="noindex,nofollow"' in pagina and "Explica: Pix caiu: o que se sabe" in pagina
    assert pagina.count("Copiar prompt da cena") == 6 and "reprovado" in pagina
    assert "6,3 bilhões de dólares em 7 de novembro" in pagina  # a voz lê sem símbolo
    assert "Photorealistic studio portrait" in pagina
    assert "2026-11-07.html" in (tmp_path / "site" / "estudio" / "index.html").read_text()


def test_fala_para_a_voz_sem_simbolos():
    assert roteirista.falado("O dólar a R$ 5,51 e a Selic em 13,75% nos EUA, em 7/11.") == \
        "O dólar a 5,51 reais e a Selic em 13,75 por cento nos Estados Unidos, em 7 de novembro."
    assert roteirista.falado("Roubo de US$ 6,3 bilhões.") == "Roubo de 6,3 bilhões de dólares."
