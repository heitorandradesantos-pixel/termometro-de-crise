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
        noticias = [noticia(i, dia) for i in range(por_dia)] + [noticia(99, "2026-11-03")]  # a 99 se repete todo dia
        (d / "correspondente.json").write_text(json.dumps({"regioes": {"Oriente Médio": {
            "resumo": "", "paises": {}, "noticias": noticias, "observar": []}}}, ensure_ascii=False))
        (d / "panorama.txt").write_text(f"*Panorama de {dia}*\n\n_Conteúdo educativo. Não é recomendação de investimento._")
    (pasta / "historico").mkdir()
    for nome in ("mundo_paises.csv", "mundo_regioes.csv"):
        shutil.copy(RAIZ / "edicoes" / "2026-11-05" / nome, pasta / "historico" / nome)


def test_arquivo_completo_e_sem_links_quebrados(tmp_path):
    dias = ["2026-11-03", "2026-11-04", "2026-11-05"]
    montar_diario(tmp_path / "diario", dias, por_dia=9)
    edicoes = tmp_path / "edicoes"
    shutil.copytree(RAIZ / "edicoes" / "2026-11-05", edicoes / "2026-11-05")
    saida = tmp_path / "_site"
    site.gerar(edicoes, saida, tmp_path / "diario")

    # um panorama por dia, com dia anterior e seguinte, e o calendário
    for dia in dias:
        assert (saida / "panorama" / f"{dia}.html").exists()
    meio = (saida / "panorama" / "2026-11-04.html").read_text()
    assert 'href="2026-11-03.html"' in meio and 'href="2026-11-05.html"' in meio
    assert "Novembro de 2026" in (saida / "panorama" / "index.html").read_text()

    # 3 dias × 9 + 1 repetida = 28 notícias: duas páginas, sem repetir a notícia 99
    hub = (saida / "noticias" / "index.html").read_text()
    assert "28 notícias guardadas" in hub and 'href="pagina-2.html"' in hub
    todas = hub + (saida / "noticias" / "pagina-2.html").read_text()
    assert todas.count("Notícia 99 de 3/11") == 1  # datas viram padrão brasileiro
    assert (saida / "noticias" / "israel.html").exists() and not (saida / "noticias" / "brasil.html").exists()
    assert 'href="../noticias/israel.html"' in (saida / "paises" / "israel.html").read_text()
    assert 'href="panorama/index.html"' in (saida / "panorama.html").read_text()

    # nenhuma página com link interno quebrado
    for pagina in saida.rglob("*.html"):
        for href in re.findall(r'href="([^"#?]+\.html)"', pagina.read_text()):
            if not href.startswith("http"):
                assert (pagina.parent / href).resolve().exists(), f"{pagina.relative_to(saida)} → {href}"


def test_paginacao_numerada():
    nav = arquivo.paginacao(5, 9, lambda n: f"p{n}.html")
    assert 'aria-current="page">5<' in nav and 'href="p1.html"' in nav and 'href="p9.html"' in nav
    assert "Mais novas" in nav and "Mais antigas" in nav and nav.count("…") == 2
    assert arquivo.paginacao(1, 1, str) == ""
