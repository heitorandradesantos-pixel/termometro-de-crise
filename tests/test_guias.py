from termometro import guias, site


def test_guias_longos_com_fonte_e_sem_promessa():
    gs = guias.todos()
    assert len(gs) >= 4
    for g in gs:
        assert g["titulo"] and g["descricao"] and g["data"] and g["fontes"]
        assert guias.palavras(g) >= 900, g["slug"]
        texto = " ".join(g["corpo"]).lower()
        for proibido in ("garantido", "100% seguro", "sem risco", "recomendamos comprar", "#cambio"):
            assert proibido not in texto, (g["slug"], proibido)
        html = guias.pagina_guia(g, gs)
        assert "<h2" in html and "Não é recomendação de investimento" in html


def test_paginas_automaticas_ficam_fora_do_google():
    assert site.automatica("noticias/plantao/x.html") and site.automatica("panorama/2026-11-05.html")
    assert not site.automatica("guias/inflacao.html") and not site.automatica("panorama/index.html")
