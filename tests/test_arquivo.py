"""Testes do arquivo: panoramas por dia, notícias paginadas e edições paginadas."""

import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from termometro import arquivo, site  # noqa: E402


def noticia(i: int, dia: str, regiao: str = "Oriente Médio", paises=("Israel",)) -> dict:
    return {"titulo": f"Notícia {i} de {dia}", "resumo": f"Resumo {i} em {dia}.", "data": dia, "status": "fato confirmado",
            "regiao": regiao, "paises": list(paises), "mexe_em": ["moeda"], "direcao": "pressiona", "relevancia": 3,
            "fontes": [{"veiculo": "Reuters", "url": f"https://www.reuters.com/{i}", "confiavel": True}],
            "fonte_de_primeira_linha": True}


def montar_diario(pasta: Path, dias: list[str], por_dia: int) -> None:
    base = json.loads((RAIZ / "edicoes" / "2026-11-05" / "mundo.json").read_text())
    for k, dia in enumerate(dias):
        d = pasta / dia
        d.mkdir(parents=True)
        mundo = json.loads(json.dumps(base))
        mundo["mundo"]["valor"] = 50 + k
        (d / "mundo.json").write_text(json.dumps(mundo, ensure_ascii=False))
        noticias = [noticia(i, dia) for i in range(por_dia)]
        if dia >= "2026-11-03":
            noticias.append(noticia(99, "2026-11-03"))  # a 99 se repete todo dia
        (d / "correspondente.json").write_text(json.dumps({"regioes": {"Oriente Médio": {
            "resumo": "", "paises": {}, "noticias": noticias, "observar": []}}}, ensure_ascii=False))
        (d / "panorama.txt").write_text(f"*Panorama de {dia}*\n\n_Conteúdo educativo, com fonte em cada fato. Não é recomendação de investimento._")
    (pasta / "historico").mkdir()
    for nome in ("mundo_paises.csv", "mundo_regioes.csv"):
        shutil.copy(RAIZ / "edicoes" / "2026-11-05" / nome, pasta / "historico" / nome)


def test_arquivo_completo_e_sem_links_quebrados(tmp_path):
    dias = ["2026-10-30", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-07"]  # 07/11 é sábado
    montar_diario(tmp_path / "diario", dias, por_dia=9)
    edicoes = tmp_path / "edicoes"
    shutil.copytree(RAIZ / "edicoes" / "2026-11-05", edicoes / "2026-11-05")
    saida = tmp_path / "_site"
    site.gerar(edicoes, saida, tmp_path / "diario")

    # um panorama por dia útil, com dia anterior e seguinte; sábado não ganha página
    for dia in dias[:-1]:
        assert (saida / "panorama" / f"{dia}.html").exists()
    assert not (saida / "panorama" / "2026-11-07.html").exists()
    meio = (saida / "panorama" / "2026-11-04.html").read_text()
    assert 'href="2026-11-03.html"' in meio and 'href="2026-11-05.html"' in meio
    assert "Não reflete o mercado de hoje" in meio and "Panorama anterior" in meio
    assert "1 ponto acima do panorama anterior" in meio  # texto próprio de cada dia
    assert "Não reflete o mercado de hoje" not in (saida / "panorama" / "2026-11-05.html").read_text()
    assert "4 de novembro de 2026" in (saida / "panorama" / "index.html").read_text()

    # notícias: o mês em curso no endereço fixo, e outubro (mês fechado, 5 ou mais) em arquivo estável
    hub = (saida / "noticias" / "index.html").read_text()
    assert "Notícias de novembro de 2026" in hub and 'href="index-2026-10.html"' in hub
    pagina2 = (saida / "noticias" / "index-pagina-2.html").read_text()
    assert "Página 1 de 2" in hub and 'href="index-pagina-2.html"' in hub
    assert (hub + pagina2).count("Notícia 99 de 3/11") == 1  # a mesma notícia em vários dias aparece uma vez
    outubro = (saida / "noticias" / "index-2026-10.html").read_text()
    assert "Em outubro de 2026" in outubro and "Não reflete o mercado de hoje" in outubro
    assert (saida / "noticias" / "israel.html").exists() and not (saida / "noticias" / "brasil.html").exists()
    assert 'href="../noticias/israel.html"' in (saida / "paises" / "israel.html").read_text()
    assert 'href="panorama/index.html"' in (saida / "panorama.html").read_text()
    # mapa do site: arquivo mensal sim, páginas 2 em diante não
    mapa = (saida / "sitemap.xml").read_text() if (saida / "sitemap.xml").exists() else ""
    if mapa:
        assert "index-2026-10</loc>" in mapa and ".html</loc>" not in mapa and "pagina-2" not in mapa and "noticias/israel" not in mapa
    # páginas de arquivo sem a faixa de cotações (decisão do guardião de regras)
    assert 'class="faixa"' not in outubro and 'class="faixa"' not in meio
    assert (saida / "correcoes.html").exists()

    # nenhuma página com link interno quebrado
    for pagina in saida.rglob("*.html"):
        for href in re.findall(r'href="([^"#?]+\.html)"', pagina.read_text()):
            if not href.startswith("http"):
                alvo = saida / href.lstrip("/") if href.startswith("/") else pagina.parent / href  # "/x" = raiz
                assert alvo.resolve().exists(), f"{pagina.relative_to(saida)} → {href}"


def test_paginacao_numerada():
    nav = arquivo.paginacao(5, 9, lambda n: f"p{n}.html")
    assert 'aria-current="page">5<' in nav and 'href="p1.html"' in nav and 'href="p9.html"' in nav
    assert "Mais novas" in nav and "Mais antigas" in nav and nav.count("…") == 2
    assert arquivo.paginacao(1, 1, str) == ""


def test_privacidade_explica_o_adsense_so_quando_ele_entra(monkeypatch):
    from termometro import config, legal
    monkeypatch.setattr(config, "ADSENSE_CLIENT", "")
    assert "Hoje não usamos cookies de publicidade" in legal.privacidade() and "aboutads" not in legal.privacidade()
    monkeypatch.setattr(config, "ADSENSE_CLIENT", "ca-pub-0000000000000000")
    texto = " ".join(legal.privacidade().split())
    assert "Fornecedores terceiros, incluindo o Google" in texto and "adssettings.google.com" in texto
    assert "Hoje não usamos cookies de publicidade" not in texto


def test_endereco_publico_sem_html():
    from termometro import config
    base = config.SITE_URL
    assert config.url_publica("noticias/plantao/x.html") == f"{base}/noticias/plantao/x"
    assert config.url_publica("noticias/plantao/index.html") == f"{base}/noticias/plantao/"
    assert config.url_publica("index.html") == config.url_publica("") == f"{base}/"
    assert config.url_publica("noticias/plantao/x.png") == f"{base}/noticias/plantao/x.png"
