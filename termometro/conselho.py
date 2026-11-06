"""Conselho de monetização: os agentes conversam entre si e fecham um plano.

Rodada 1 (propostas): cada membro estuda o briefing, pesquisa o mercado brasileiro e propõe ideias com métrica,
custo, prazo e riscos, além de mudanças no site.
Rodada 2 (debate): cada membro lê as propostas de todos, diz com o que concorda, do que discorda e por quê, ajusta
a própria proposta e vota nas 3 melhores ideias. O guardião de regras libera, libera com cuidados ou veta cada uma.
Rodada 3 (decisão): o presidente do conselho monta o mapa de divergências e o plano por fases, respeitando os vetos,
com as mudanças no site, os experimentos, o sinal de alerta (tripwire) e os próximos passos para o dono do projeto.

Inspirado no protocolo "marketing council" (assentos com lentes diferentes, um dissidente obrigatório, mapa de
divergências e síntese), mas com papéis da nossa squad em vez de pessoas reais.
"""

import json
from pathlib import Path

from . import config, ia

MEMBROS = {
    "marketing": ("Analista de marketing", ["marketing"], 2),
    "comportamento": ("Analista de comportamento do lead", ["comportamento"], 1),
    "vendas": ("Vendedor especialista em produtos financeiros", ["vendas"], 2),
    "seo": ("Especialista em SEO", ["seo"], 2),
    "ux": ("Agente de UX", ["ux"], 0),
    "compliance": ("Guardião de regras", ["compliance"], 1),
}
DISSIDENTE = "comportamento"  # quem tem a obrigação de questionar o que estiver virando consenso fácil
FASES = ["0 a 30 dias", "1 a 3 meses", "3 a 6 meses", "6 a 12 meses"]

BASE = f"""Você é membro do conselho de monetização do "{config.NOME}". O conselho conversa em rodadas para decidir
a melhor forma de ganhar dinheiro com o projeto sem perder a confiança do leitor. Seja específico para ESTE projeto,
com números quando tiver fonte (diga a fonte) e estimativas marcadas como estimativas. Discorde quando discordar:
um conselho que concorda em tudo não serve. Escreva em português do Brasil, em frases curtas."""


def sistema(chave: str) -> str:
    nome, manuais, _ = MEMBROS[chave]
    extra = (" Seu papel extra: ser o dissidente. Aponte a fraqueza mais séria da ideia que estiver ganhando."
             if chave == DISSIDENTE else "")
    extra += (" Seu papel extra: para cada ideia, diga se está liberada, liberada com cuidados ou vetada, e por quê."
              if chave == "compliance" else "")
    return f"{BASE}\n\nSeu papel: {nome}.{extra}" + config.manual(*manuais)


PROPOSTA = {
    "name": "registrar_proposta",
    "description": "Registra a proposta deste membro na rodada 1.",
    "input_schema": {
        "type": "object",
        "properties": {
            "diagnostico": {"type": "string", "description": "O gargalo principal hoje, na sua visão (2 a 3 frases)"},
            "ideias": {"type": "array", "minItems": 2, "maxItems": 4, "items": {
                "type": "object",
                "properties": {"titulo": {"type": "string"}, "como_funciona": {"type": "string"},
                               "receita": {"type": "string", "description": "Como gera dinheiro e estimativa, com fonte"},
                               "custo_e_esforco": {"type": "string"}, "prazo": {"type": "string", "enum": FASES},
                               "metrica": {"type": "string"}, "riscos": {"type": "string"}},
                "required": ["titulo", "como_funciona", "receita", "prazo", "metrica", "riscos"]}},
            "mudancas_no_site": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
            "perguntas_para_o_conselho": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
        },
        "required": ["diagnostico", "ideias"],
    },
}

DEBATE = {
    "name": "registrar_debate",
    "description": "Registra a posição deste membro na rodada 2, depois de ler todas as propostas.",
    "input_schema": {
        "type": "object",
        "properties": {
            "concordo": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "discordo": {"type": "array", "maxItems": 4, "items": {
                "type": "object", "properties": {"de_quem": {"type": "string"}, "ponto": {"type": "string"},
                                                 "por_que": {"type": "string"}},
                "required": ["de_quem", "ponto", "por_que"]}},
            "parecer_de_regras": {"type": "array", "maxItems": 10, "items": {
                "type": "object", "properties": {"ideia": {"type": "string"},
                                                 "situacao": {"type": "string", "enum": ["liberada", "com cuidados", "vetada"]},
                                                 "motivo": {"type": "string"}},
                "required": ["ideia", "situacao", "motivo"]},
                "description": "Só o guardião de regras preenche"},
            "proposta_ajustada": {"type": "string"},
            "voto": {"type": "array", "minItems": 1, "maxItems": 3, "items": {"type": "string"},
                     "description": "Títulos das 3 melhores ideias, de qualquer membro"},
        },
        "required": ["concordo", "discordo", "proposta_ajustada", "voto"],
    },
}

DECISAO = {
    "name": "registrar_decisao",
    "description": "Registra a decisão do conselho.",
    "input_schema": {
        "type": "object",
        "properties": {
            "resumo": {"type": "string", "description": "A decisão em 3 a 4 frases"},
            "divergencias": {"type": "array", "minItems": 1, "maxItems": 4, "items": {
                "type": "object", "properties": {"conflito": {"type": "string"}, "troca": {"type": "string"},
                                                 "o_que_decide": {"type": "string"}},
                "required": ["conflito", "troca", "o_que_decide"]}},
            "plano": {"type": "array", "minItems": 3, "maxItems": 10, "items": {
                "type": "object", "properties": {"fase": {"type": "string", "enum": FASES},
                                                 "iniciativa": {"type": "string"}, "responsavel": {"type": "string"},
                                                 "metrica": {"type": "string"}, "meta": {"type": "string"}},
                "required": ["fase", "iniciativa", "responsavel", "metrica", "meta"]}},
            "mudancas_no_site": {"type": "array", "minItems": 1, "maxItems": 10, "items": {
                "type": "object", "properties": {"prioridade": {"type": "integer", "minimum": 1, "maximum": 3},
                                                 "mudanca": {"type": "string"}, "por_que": {"type": "string"},
                                                 "agente": {"type": "string"}},
                "required": ["prioridade", "mudanca", "por_que"]}},
            "experimentos": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
            "vetos_respeitados": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
            "precisa_de_advogado": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
            "tripwire": {"type": "string", "description": "O sinal que mostra que o plano está errado"},
            "proximos_passos_do_dono": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string"}},
        },
        "required": ["resumo", "divergencias", "plano", "mudancas_no_site", "tripwire", "proximos_passos_do_dono"],
    },
}

PRESIDENTE = (f"{BASE}\n\nSeu papel: presidente do conselho. Você não traz ideia própria: lê as propostas e o debate, "
              "monta o mapa de divergências (qual é a troca por trás de cada conflito e que dado resolveria) e decide o "
              "plano que melhor serve a um projeto no começo, com pouca verba e um dono sem experiência técnica. "
              "Ideias vetadas pelo guardião de regras ficam fora. Toda iniciativa tem métrica e meta.")


def briefing(raiz: Path) -> str:
    """O que o conselho precisa saber do projeto, montado a partir dos arquivos do próprio repositório."""
    def ler(caminho: Path, limite: int = 2500) -> str:
        return caminho.read_text()[:limite] if caminho.exists() else ""
    ultima_design = sorted((raiz / "design").glob("*/relatorio.md")) if (raiz / "design").exists() else []
    contexto = ler(raiz / "termometro" / "manuais" / "contexto_do_projeto.md", 6000)
    return (f"{contexto}\n\n" + (f"ÚLTIMO RELATÓRIO DA SQUAD DE DESIGN (trecho)\n{ler(ultima_design[-1])}\n" if ultima_design else ""))


def _campos(item, *nomes: str, sep: str = " | ") -> str:
    """Junta campos de um item do formulário; se o modelo devolveu texto solto em vez de objeto, usa o texto."""
    if isinstance(item, dict):
        return sep.join(str(item.get(n, "")) for n in nomes if item.get(n))
    return str(item)


def _lista(x) -> list:
    return x if isinstance(x, list) else ([x] if x else [])


def _texto_propostas(propostas: dict) -> str:
    partes = []
    for chave, p in propostas.items():
        ideias = "\n".join("  - " + _campos(i, "titulo", "prazo", "como_funciona", "receita", "metrica", "riscos")
                           for i in _lista(p.get("ideias")))
        partes.append(f"[{MEMBROS[chave][0]}]\nDiagnóstico: {p.get('diagnostico', '')}\nIdeias:\n{ideias}\n"
                      f"Mudanças no site: {'; '.join(map(str, _lista(p.get('mudancas_no_site'))))}")
    return "\n\n".join(partes)


def _texto_debate(debate: dict) -> str:
    partes = []
    for chave, d in debate.items():
        discordo = "; ".join(_campos(x, "de_quem", "ponto", "por_que", sep=": ") for x in _lista(d.get("discordo")))
        regras = "; ".join(_campos(x, "ideia", "situacao", "motivo", sep=": ") for x in _lista(d.get("parecer_de_regras")))
        partes.append(f"[{MEMBROS[chave][0]}]\nConcordo: {'; '.join(map(str, _lista(d.get('concordo'))))}\n"
                      f"Discordo: {discordo}\n" + (f"Parecer de regras: {regras}\n" if regras else "")
                      + f"Proposta ajustada: {d.get('proposta_ajustada', '')}\n"
                      f"Voto: {', '.join(map(str, _lista(d.get('voto'))))}")
    return "\n\n".join(partes)


def tema() -> str:
    """Pergunta do dono para uma consulta ao time (vazio = reunião de monetização de sempre)."""
    import os
    return os.environ.get("PERGUNTA_CONSELHO", "").strip()


def reunir(raiz: Path, cliente) -> dict:
    contexto = briefing(raiz)
    if tema():
        contexto += (f"\n\nTEMA DESTA REUNIÃO (pergunta do dono): {tema()}\nNesta reunião, as 'ideias' são as suas "
                     "recomendações sobre esse tema, e 'receita' é o impacto esperado (audiência, confiança, conversão ou "
                     "receita). Diga também o que mudaria na proposta e o que não faria.")
    propostas, debate = {}, {}
    for chave, (nome, _, buscas) in MEMBROS.items():
        print(f"  Rodada 1: {nome}")
        try:
            propostas[chave] = ia.estruturado(cliente, sistema(chave), f"BRIEFING DO PROJETO\n{contexto}\n\n"
                                              "Rodada 1: faça a sua proposta.", PROPOSTA, buscas=buscas, max_tokens=9000)
        except Exception as erro:  # um membro com problema não derruba o conselho
            print(f"    {nome} ficou de fora: {erro}")
    todas = _texto_propostas(propostas)
    for chave in propostas:
        print(f"  Rodada 2: {MEMBROS[chave][0]}")
        try:
            debate[chave] = ia.estruturado(cliente, sistema(chave), f"BRIEFING DO PROJETO\n{contexto}\n\nPROPOSTAS DA "
                                           f"RODADA 1\n{todas}\n\nRodada 2: debata.", DEBATE, max_tokens=5000)
        except Exception as erro:
            print(f"    {MEMBROS[chave][0]} não debateu: {erro}")
    print("  Rodada 3: presidente do conselho")
    decisao = ia.estruturado(cliente, PRESIDENTE, f"BRIEFING DO PROJETO\n{contexto}\n\nPROPOSTAS\n{todas}\n\nDEBATE\n"
                             f"{_texto_debate(debate)}\n\nRodada 3: decida. Seja direto: frases curtas em cada campo.",
                             DECISAO, max_tokens=14000)
    return {"propostas": propostas, "debate": debate, "decisao": decisao}


def ata(data: str, r: dict) -> str:
    d = r["decisao"]
    titulo = f"Consulta ao time: {tema()[:80]}" if tema() else "Conselho de monetização"
    linhas = [f"# {titulo} (ata de {data})", "",
              "_Conversa entre os agentes da squad (marketing, comportamento do lead, vendas, SEO, UX e guardião de "
              "regras), com decisão do presidente do conselho. É uma recomendação para você decidir, não uma ordem._", "",
              "## Decisão", "", str(d.get("resumo", "")), "", "## Plano", "", "| Fase | Iniciativa | Responsável | Métrica | Meta |",
              "|---|---|---|---|---|"]
    def campo(x, nome, padrao=""):
        return x.get(nome, padrao) if isinstance(x, dict) else (str(x) if nome in ("iniciativa", "mudanca", "conflito") else padrao)
    plano = [x for x in _lista(d.get("plano"))]
    linhas += [f"| {campo(p, 'fase')} | {campo(p, 'iniciativa')} | {campo(p, 'responsavel')} | {campo(p, 'metrica')} | "
               f"{campo(p, 'meta')} |" for p in sorted(plano, key=lambda p: FASES.index(campo(p, 'fase'))
                                                      if campo(p, 'fase') in FASES else 9)]
    linhas += ["", "## Mudanças no site (para a squad aplicar)", ""]
    mudancas = sorted(_lista(d.get("mudancas_no_site")), key=lambda m: str(campo(m, "prioridade", 9)))
    linhas += [f"{i}. **[P{campo(m, 'prioridade', '?')}] {campo(m, 'mudanca')}**: {campo(m, 'por_que')}"
               + (f" _(agente: {campo(m, 'agente')})_" if campo(m, "agente") else "") for i, m in enumerate(mudancas, 1)]
    linhas += ["", "## Onde o conselho discordou", ""]
    linhas += [f"- **{campo(x, 'conflito')}.** A troca: {campo(x, 'troca')}. O que decide: {campo(x, 'o_que_decide')}."
               for x in _lista(d.get("divergencias"))]
    for chave, titulo_secao in (("experimentos", "Experimentos"), ("vetos_respeitados", "Vetos do guardião de regras"),
                                ("precisa_de_advogado", "Validar com advogado antes de ir ao ar")):
        if d.get(chave):
            linhas += ["", f"## {titulo_secao}", ""] + [f"- {_campos(e, *(e.keys() if isinstance(e, dict) else ()))}"
                                                        for e in _lista(d[chave])]
    linhas += ["", f"**Sinal de alerta (tripwire):** {d.get('tripwire', '')}", "", "## Próximos passos para você", ""]
    linhas += [f"- [ ] {_campos(x, *(x.keys() if isinstance(x, dict) else ()))}" for x in _lista(d.get("proximos_passos_do_dono"))]
    linhas += ["", "_A conversa completa (propostas e debate de cada agente) vai no primeiro comentário._"]
    return "\n".join(linhas) + "\n"


def conversa(data: str, r: dict) -> str:
    texto = (f"# Conselho de {data}: a conversa completa\n\n## Rodada 1: propostas\n\n"
             + _texto_propostas(r["propostas"]).replace("\n", "\n\n")
             + "\n\n## Rodada 2: debate\n\n" + _texto_debate(r["debate"]).replace("\n", "\n\n"))
    return texto[:60000]  # limite de tamanho de comentário do GitHub


def rodar(raiz: Path, pasta: Path, data: str, cliente=None) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    cliente = cliente or ia.novo_cliente()
    r = reunir(raiz, cliente)
    (pasta / "conselho.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
    texto = ata(data, r)
    (pasta / "ata.md").write_text(texto[:60000])
    (pasta / "conversa.md").write_text(conversa(data, r))
    return {**r, "ata": texto}
