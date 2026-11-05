"""Agente revisor: confere a edição antes de qualquer publicação.

Regras que BLOQUEIAM (a edição vai para sua aprovação manual):
aviso legal, seções completas, nada pendente, número certo do Termômetro,
nenhuma linguagem de recomendação ou promessa, e todo link saído do dossiê do Buscador.
Regras que só AVISAM: fonte fora da lista de primeira linha, peças de copy trocadas.
"""

import re

from . import config

PROIBIDAS = [
    (r"\brecomend(o|amos)\b|\bnossa recomendação\b", "recomendação direta", re.I),
    (r"\bcomprem?\b(?! de)", "ordem de compra", re.I),
    (r"\bvendam?\s+(já|agora|tudo|suas?|seus?)\b", "ordem de venda", re.I),
    (r"\bhora de (comprar|vender)\b", "ordem de compra ou venda", re.I),
    (r"\b(invista|aposte|aplique)\s+(em|no|na|nos|nas)\b", "ordem de investimento", re.I),
    (r"\bpreço[- ]alvo\b", "preço-alvo", re.I),
    (r"\blucro (certo|garantido|fácil)\b|\bganho garantido\b|\brentabilidade garantida\b", "promessa de lucro", re.I),
    (r"\b(colapso iminente|vai quebrar|vai despencar|fim do mundo|apocalipse)\b", "alarmismo", re.I),
    (r"\b[A-Z]{4}(3|4|5|6|11)\b", "código de ação da B3", 0),
    (r"\$[A-Z]{1,5}\b", "código de ação dos EUA", 0),
]

LINK = re.compile(r"https?://[^\s)\]>\"']+")

# Linguagem simples (manual de redação): jargão que precisa de tradução na mesma frase
JARGAO = ["spread", "yield", "hawkish", "dovish", "drawdown", "carry trade", "hedge", "rally", "sell-off",
          "curva de juros", "risco-país", "volatilidade implícita", "treasuries", "bear market", "bull market"]
FRASE_LONGA = 35  # palavras


def frases_longas(texto: str) -> list[str]:
    """Frases do corpo com mais de FRASE_LONGA palavras (sem contar títulos, listas de links e o aviso)."""
    limpo = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto.replace(config.AVISO, ""))
    linhas = [l for l in limpo.splitlines() if l.strip() and not l.lstrip().startswith(("#", "|", "---", "*"))]
    frases = re.split(r"(?<=[.!?])\s+", " ".join(linhas))
    return [f for f in frases if len(re.findall(r"\w+", f)) > FRASE_LONGA]


def jargao_sem_traducao(texto: str) -> list[str]:
    """Termos técnicos que aparecem sem explicação por perto (vírgula, parênteses ou travessão logo depois)."""
    achados = []
    for termo in JARGAO:
        for m in re.finditer(rf"\b{re.escape(termo)}\b", texto, re.I):
            depois = texto[m.end():m.end() + 3]
            if not re.match(r"\s*[,(—–-]", depois):
                achados.append(termo)
                break
    return achados


def linguagem_proibida(texto: str) -> list[str]:
    texto = texto.replace(config.AVISO, "")
    return sorted({rotulo for padrao, rotulo, flags in PROIBIDAS if re.search(padrao, texto, flags)})


def links(texto: str) -> list[str]:
    return [u.rstrip(".,;:") for u in LINK.findall(texto)]


def secoes(texto: str) -> dict[str, str]:
    partes, atual = {}, None
    for linha in texto.splitlines():
        if linha.startswith("## "):
            atual = linha.strip()
            partes[atual] = ""
        elif atual:
            partes[atual] += linha + "\n"
    return partes


def checar(texto: str, dados: dict, dossie: dict, copy: dict) -> dict:
    from .buscador import confiavel, urls
    from .redator import SECOES

    checagens = []

    def regra(nome: str, ok: bool, detalhe: str = "", bloqueia: bool = True):
        checagens.append({"regra": nome, "ok": bool(ok), "detalhe": detalhe, "bloqueia": bloqueia})

    corpo = texto.split("\n---\n")[0]
    partes = secoes(texto)
    posicoes = [texto.find(s) for s in SECOES]
    regra("Aviso legal presente", config.AVISO in texto)
    regra("Seções completas e na ordem", all(p >= 0 for p in posicoes) and posicoes == sorted(posicoes),
          "faltando: " + ", ".join(s[3:] for s, p in zip(SECOES, posicoes) if p < 0))
    regra("Nada pendente", "PENDENTE" not in texto, "a edição ainda tem trechos PENDENTE")

    abertura = partes.get(SECOES[0], "")
    valores_validos = {dados["valor"], dados["mes_anterior"]["valor"],
                       *(p["valor"] for p in dados["picos_historicos"].values()),
                       *(c["percentil"] for c in dados["componentes"] if c["percentil"] is not None),
                       *(r["valor"] for r in dados.get("regioes", [])),
                       *([dados["brasil"]["valor"]] if dados.get("brasil") else [])}
    citados = {int(n) for n in re.findall(r"\b(\d{1,3})\s*(?:de 100|/100)", corpo)}
    regra("Número e nível do Termômetro corretos",
          re.search(rf"\b{dados['valor']}\b", abertura) and dados["nivel"].lower() in abertura.lower()
          and citados <= valores_validos,
          f"no texto: {sorted(citados)}; válidos: {sorted(valores_validos)}")

    proibidas = linguagem_proibida(texto)
    regra("Sem recomendação, promessa ou alarmismo", not proibidas, ", ".join(proibidas))

    do_texto = set(links(corpo))
    do_dossie = urls(dossie)
    inventados = sorted(do_texto - do_dossie)
    regra("Todo link veio da pesquisa do Buscador", not inventados, "fora do dossiê: " + ", ".join(inventados))
    regra("Cada risco com fonte", len(links(partes.get(SECOES[1], ""))) >= 3, "menos de 3 links nos riscos")

    palavras = len(re.findall(r"\w+", corpo))
    regra("Tamanho entre 400 e 1.300 palavras", 400 <= palavras <= 1300, f"{palavras} palavras")

    pecas = " ".join(str(v) for k, v in copy.items() if k not in ("modo", "ajustes"))
    proibidas_copy = linguagem_proibida(pecas)
    regra("Copy sem linguagem proibida", not proibidas_copy, ", ".join(proibidas_copy))

    fracas = sorted({u for u in do_texto if not confiavel(u)})
    regra("Fontes de primeira linha", not fracas, "conferir: " + ", ".join(fracas), bloqueia=False)
    regra("Copy sem ajustes automáticos", not copy.get("ajustes"), "; ".join(copy.get("ajustes", [])), bloqueia=False)
    longas = frases_longas(corpo)
    regra("Frases curtas (linguagem simples)", len(longas) <= 2,
          f"{len(longas)} frases com mais de {FRASE_LONGA} palavras; a primeira: {longas[0][:120]}…" if longas else "",
          bloqueia=False)
    pauta = dados.get("seo") or {}
    if pauta.get("palavra_chave"):
        from .seo import contem
        lugares = {"título do site": contem(copy.get("titulo_site", ""), pauta["palavra_chave"]),
                   "abertura": contem(abertura, pauta["palavra_chave"])}
        regra("SEO: palavra-chave no título e na abertura", all(lugares.values()),
              f"'{pauta['palavra_chave']}' faltou em: " + ", ".join(k for k, v in lugares.items() if not v), bloqueia=False)
    jargao = jargao_sem_traducao(corpo)
    regra("Jargão traduzido", not jargao, "explicar: " + ", ".join(jargao), bloqueia=False)
    if dossie.get("descartados"):
        regra("Dossiê sem descartes", False, f"{len(dossie['descartados'])} eventos descartados pelo filtro", bloqueia=False)

    aprovado = all(c["ok"] for c in checagens if c["bloqueia"])
    return {"aprovado": aprovado, "palavras": palavras, "checagens": checagens}
