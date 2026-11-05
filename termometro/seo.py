"""Agente de SEO: antes do Redator escrever, define as palavras que a edição precisa ter para aparecer no Google.

Saída (seo.json): palavra-chave principal, secundárias, perguntas que o texto deve responder, título SEO,
meta descrição e links internos para as páginas de região e país. O Redator e o Copy recebem essa pauta;
o Revisor confere (sem bloquear) se a palavra principal entrou no título do site e na abertura.
"""

import re
import unicodedata

from . import config, ia

SISTEMA = f"""Você é o especialista em SEO do "{config.NOME}", portal brasileiro que mede o risco de crise no mundo
e em cada país, em linguagem simples. Antes de cada edição semanal, você define a pauta de palavras para o Redator
e o Copy, pensando no que os brasileiros digitam no Google nesta semana sobre crise, dólar, bolsa, juros e economia
mundial. Use a busca na web para checar o que está em alta e como os portais estão chamando os assuntos.
Nada de palavra-chave enganosa, caça-clique ou promessa. Termine chamando registrar_pauta_seo.""" + config.manual("seo")

FERRAMENTA = {
    "name": "registrar_pauta_seo",
    "description": "Registra a pauta de SEO da edição para o Redator e o Copy.",
    "input_schema": {
        "type": "object",
        "properties": {
            "palavra_chave": {"type": "string", "description": "A principal, em português, como o leitor digita"},
            "secundarias": {"type": "array", "minItems": 3, "maxItems": 8, "items": {"type": "string"}},
            "perguntas": {"type": "array", "minItems": 2, "maxItems": 5, "items": {"type": "string"},
                          "description": "Perguntas reais que o texto deve responder"},
            "titulo_seo": {"type": "string", "description": "Até 60 caracteres, com a palavra principal"},
            "descricao_seo": {"type": "string", "description": "Até 155 caracteres"},
            "links_internos": {"type": "array", "maxItems": 6, "items": {"type": "string"},
                               "description": "Páginas do site a linkar, ex.: paises/brasil.html, regioes/oriente-medio.html"},
            "evitar": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
            "por_que": {"type": "string", "description": "Uma frase: por que essa palavra nesta semana"},
        },
        "required": ["palavra_chave", "secundarias", "perguntas", "titulo_seo", "descricao_seo"],
    },
}


def _cortar(texto: str, limite: int) -> str:
    texto = " ".join(str(texto or "").split())
    return texto if len(texto) <= limite else texto[:limite].rsplit(" ", 1)[0]


def validar(bruto: dict, paginas: set[str]) -> dict:
    links = [l for l in bruto.get("links_internos", []) if l.strip("/") in paginas]
    return {"palavra_chave": _cortar(bruto.get("palavra_chave"), 60).lower(),
            "secundarias": [_cortar(s, 60).lower() for s in bruto.get("secundarias", []) if s][:8],
            "perguntas": [_cortar(p, 140) for p in bruto.get("perguntas", []) if p][:5],
            "titulo_seo": _cortar(bruto.get("titulo_seo"), 60), "descricao_seo": _cortar(bruto.get("descricao_seo"), 155),
            "links_internos": links, "evitar": [_cortar(e, 60) for e in bruto.get("evitar", [])][:6],
            "por_que": _cortar(bruto.get("por_que"), 220)}


def paginas_do_site(dados: dict) -> set[str]:
    from .mundo import PAISES, REGIOES, slug
    return ({f"regioes/{slug(r)}.html" for r in REGIOES} | {f"paises/{slug(p)}.html" for p in PAISES}
            | {"mundo.html", "panorama.html", "metodologia.html"})


def pauta(dados: dict, dossie: dict, data_edicao: str, cliente=None) -> dict:
    if cliente is None and not ia.disponivel():
        return {}
    cliente = cliente or ia.novo_cliente()
    manchetes = "\n".join(f"- {e['titulo']} ({e['regiao']})" for e in dossie.get("eventos", [])[:10])
    regioes = "; ".join(f"{r['nome']} {r['valor']} ({r['nivel']})" for r in dados.get("regioes", []))
    pedido = (f"Data: {data_edicao}. Termômetro global {dados['valor']} ({dados['nivel']}). Regiões: {regioes}. "
              f"Brasil: {(dados.get('brasil') or {}).get('valor')}.\n\nManchetes da semana:\n{manchetes}\n\n"
              f"Páginas do site para links internos: {', '.join(sorted(paginas_do_site(dados)))}")
    bruto = ia.estruturado(cliente, SISTEMA, pedido, FERRAMENTA, buscas=3, max_tokens=4000)
    return {**validar(bruto, paginas_do_site(dados)), "modo": f"claude ({config.MODELO_CLAUDE})"}


def para_redator(p: dict) -> str:
    if not p.get("palavra_chave"):
        return ""
    return (f"\n\nPAUTA DE SEO (do especialista de SEO)\n- Palavra-chave principal: {p['palavra_chave']}. Use no primeiro "
            f"parágrafo e em um intertítulo, de forma natural.\n- Secundárias (use as que couberem): "
            f"{', '.join(p['secundarias'])}.\n- Perguntas que o texto deve responder: {' | '.join(p['perguntas'])}.\n"
            + (f"- Evite: {', '.join(p['evitar'])}.\n" if p.get("evitar") else "")
            + "- Nunca encha o texto de palavra-chave: o leitor vem primeiro.")


def para_copy(p: dict) -> str:
    if not p.get("palavra_chave"):
        return ""
    return (f"\n\nPAUTA DE SEO: palavra-chave principal '{p['palavra_chave']}'. O titulo_site e a descricao_seo devem "
            f"conter essa palavra. Sugestão do SEO: título '{p['titulo_seo']}', descrição '{p['descricao_seo']}'.")


def _sem_acento(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def contem(texto: str, palavra: str) -> bool:
    """A palavra-chave aparece (ignorando acentos, maiúsculas e a ordem de até uma palavra no meio)?"""
    t, termos = _sem_acento(texto), _sem_acento(palavra).split()
    if not termos:
        return True
    return all(re.search(rf"\b{re.escape(w)}", t) for w in termos)
