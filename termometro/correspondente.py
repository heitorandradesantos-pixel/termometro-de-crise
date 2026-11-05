"""Agente Correspondente: explica, região por região, por que cada termômetro está onde está.

Para cada uma das 6 regiões, o Claude recebe os números do motor mundial (país por país),
pesquisa os últimos dias na web e registra:
- um resumo de por que a região está nesse nível;
- um "por que" curto para cada país, ligando os sinais (bolsa, sobe e desce, moeda) aos fatos;
- as notícias que mexem com o termômetro, cada uma com status, sinal afetado e fonte.

Depois o programa confere tudo: só ficam links que a busca devolveu de verdade, datas recentes,
países da região e textos sem recomendação, promessa ou alarmismo. O que não passa é descartado,
e a página do país usa a explicação automática feita só com os números.
"""

import re

import pandas as pd

from . import config, ia
from .buscador import confiavel, dominio
from .revisor import linguagem_proibida

SINAIS = ["bolsa", "sobe e desce", "moeda", "energia", "juros", "comércio"]
DIRECOES = ["pressiona", "alivia", "incerto"]
LIMITES = {"resumo": 360, "por_que": 480, "titulo": 110, "resumo_noticia": 320}
JANELA_DIAS = 10

SISTEMA = f"""Você é o agente Correspondente do "{config.NOME}", um site que mede o estresse dos mercados
de cada país e explica isso para leitores brasileiros leigos.

Cada país tem um termômetro de 0 a 100 feito de três sinais, todos comparados com a história do próprio país:
- bolsa: quanto o índice principal está abaixo do topo dos últimos 12 meses;
- sobe e desce: quanto a bolsa oscila por dia neste mês;
- moeda: quanto a moeda mudou contra o dólar em 3 meses, para qualquer lado.
Faixas: Calmaria 0–20, Atenção 21–40, Alerta 41–60, Tensão 61–80, Crise 81–100.

Sua tarefa: pesquisar os últimos dias e explicar por que os termômetros da região estão onde estão.
Regras:
1. Só fatos com fonte. Prefira Reuters, AP, FT, Bloomberg, bancos centrais, FMI, governos e veículos locais
   de referência. Nunca registre rumor como fato; use o status certo: {', '.join(config.STATUS_FATO)}.
2. Ligue cada notícia ao sinal que ela mexe ({', '.join(SINAIS)}) e diga se ela pressiona (aumenta a tensão),
   alivia ou é incerta.
3. Se nenhum fato explica um sinal, diga isso com clareza ("as notícias não mostram uma causa única").
   Não invente causa. Use só números que estão nos dados recebidos ou nas fontes.
4. Linguagem simples, frases curtas, sem jargão. Nada de previsão, recomendação de investimento,
   promessa de ganho ou alarmismo. Neutralidade política: descreva o que governos e partidos fizeram,
   sem opinar.
5. Datas reais do acontecimento, no formato AAAA-MM-DD.
Ao terminar, chame a ferramenta registrar_regiao uma única vez."""


def ferramenta(paises: list[str]) -> dict:
    return {
        "name": "registrar_regiao",
        "description": "Registra a explicação da região, de cada país e as notícias que mexem com o termômetro.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resumo": {"type": "string", "description": "Por que a região está nesse nível hoje. 2 ou 3 frases."},
                "paises": {"type": "array", "minItems": 1, "items": {
                    "type": "object",
                    "properties": {"nome": {"type": "string", "enum": paises},
                                   "por_que": {"type": "string", "description": "2 a 3 frases ligando os sinais aos fatos"}},
                    "required": ["nome", "por_que"]}},
                "noticias": {"type": "array", "minItems": 1, "maxItems": 6, "items": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string", "description": "Manchete factual, até 100 caracteres"},
                        "resumo": {"type": "string", "description": "1 ou 2 frases, só fatos"},
                        "data": {"type": "string", "description": "AAAA-MM-DD do acontecimento"},
                        "status": {"type": "string", "enum": config.STATUS_FATO},
                        "paises": {"type": "array", "items": {"type": "string", "enum": paises}},
                        "mexe_em": {"type": "array", "minItems": 1, "items": {"type": "string", "enum": SINAIS}},
                        "direcao": {"type": "string", "enum": DIRECOES},
                        "relevancia": {"type": "integer", "minimum": 1, "maximum": 5},
                        "fontes": {"type": "array", "minItems": 1, "items": {
                            "type": "object",
                            "properties": {"veiculo": {"type": "string"}, "url": {"type": "string"},
                                           "data": {"type": "string"}},
                            "required": ["veiculo", "url"]}},
                    },
                    "required": ["titulo", "resumo", "data", "status", "mexe_em", "direcao", "relevancia", "fontes"]}},
                "observar": {"type": "array", "maxItems": 4, "items": {
                    "type": "object",
                    "properties": {"data": {"type": "string"}, "evento": {"type": "string"},
                                   "por_que_importa": {"type": "string"}, "url": {"type": "string"}},
                    "required": ["data", "evento", "por_que_importa"]}},
            },
            "required": ["resumo", "paises", "noticias"],
        },
    }


# ---------------------------------------------------------------- números em palavras
def _num(x: float, casas: int = 1) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def descrever_pais(p: dict) -> str:
    """Uma linha com os números do país, no jeito que o leitor vai ver na página."""
    s, b = p.get("sinais", {}), p.get("brutos", {})
    partes = []
    if s.get("bolsa") is not None:
        extra = f", {p.get('bolsa_nome') or 'índice'} {_num(b['bolsa_queda_pct'])}% abaixo do topo de 12 meses" \
            if b.get("bolsa_queda_pct") is not None else ""
        partes.append(f"bolsa {s['bolsa']}{extra}")
    if s.get("volatilidade") is not None:
        extra = f", cerca de {_num(b['oscilacao_diaria_pct'])}% por dia" if b.get("oscilacao_diaria_pct") is not None else ""
        partes.append(f"sobe e desce {s['volatilidade']}{extra}")
    if s.get("moeda") is not None:
        v = b.get("moeda_variacao_3m_pct")
        extra = "" if v is None else (f", {p.get('moeda_nome') or 'moeda'} {'perdeu' if v > 0 else 'ganhou'} "
                                      f"{_num(abs(v))}% contra o dólar em 3 meses")
        partes.append(f"moeda {s['moeda']}{extra}")
    variacao = "" if p.get("mes_anterior") is None else f", mês anterior {p['mes_anterior']}"
    return f"- {p['nome']}: {p.get('valor')} ({p.get('nivel')}{variacao}). Sinais em percentil: " + "; ".join(partes)


def pedido(regiao: dict, data: str) -> str:
    linhas = "\n".join(descrever_pais(p) for p in regiao["paises"] if p.get("valor") is not None)
    return (f"Data de hoje: {data}. Região: {regiao['nome']}, termômetro {regiao.get('valor')} ({regiao.get('nivel')}), "
            f"mês anterior {regiao.get('mes_anterior')}.\n\nPaíses (percentil 90 = mais tenso do que em 90% dos meses "
            f"da história do país):\n{linhas}\n\nPesquise os últimos 7 dias e explique por que cada país está nesse nível. "
            "Se um país está calmo, diga o que sustenta a calma. Registre as notícias que mais mexem com esses termômetros.")


# ---------------------------------------------------------------- conferência
def _limpo(url: str) -> str:
    return re.sub(r"[#?].*$", "", url.strip()).rstrip("/").replace("://www.", "://").lower()


def _cortar(texto: str, limite: int) -> str:
    texto = " ".join(str(texto or "").split())
    if len(texto) <= limite:
        return texto
    corte = texto[:limite]
    fim = max(corte.rfind(". "), corte.rfind("! "), corte.rfind("? "))
    return corte[: fim + 1] if fim > limite * 0.5 else corte.rsplit(" ", 1)[0] + "…"


def validar(bruto: dict, regiao: dict, data: str, buscados: set | None) -> dict:
    """Confere o que o Claude registrou. `buscados` = links que a busca devolveu (None = não conferir)."""
    hoje = pd.Timestamp(data)
    membros = {p["nome"] for p in regiao["paises"]}
    permitidos = None if buscados is None else {_limpo(u) for u in buscados}
    descartes, noticias, vistos = [], [], set()

    def texto_ok(onde: str, texto: str) -> bool:
        proibido = linguagem_proibida(texto)
        if proibido:
            descartes.append({"onde": onde, "motivo": "linguagem: " + ", ".join(proibido)})
        return not proibido

    for n in bruto.get("noticias", []):
        titulo = _cortar(n.get("titulo"), LIMITES["titulo"])
        fontes = []
        for f in n.get("fontes", []):
            url = str(f.get("url", ""))
            if not url.startswith("https://"):
                continue
            if permitidos is not None and _limpo(url) not in permitidos:
                descartes.append({"onde": titulo, "motivo": f"link que a busca não devolveu: {url}"})
                continue
            fontes.append({"veiculo": f.get("veiculo") or dominio(url), "url": url, "data": f.get("data"),
                           "confiavel": confiavel(url)})
        quando = pd.to_datetime(n.get("data"), errors="coerce")
        if not fontes:
            descartes.append({"onde": titulo, "motivo": "sem fonte conferida"})
        elif pd.isna(quando) or quando < hoje - pd.Timedelta(days=JANELA_DIAS) or quando > hoje + pd.Timedelta(days=1):
            descartes.append({"onde": titulo, "motivo": f"data fora da janela ({n.get('data')})"})
        elif titulo.lower() in vistos:
            descartes.append({"onde": titulo, "motivo": "repetida"})
        elif texto_ok(titulo, f"{titulo} {n.get('resumo', '')}"):
            vistos.add(titulo.lower())
            noticias.append({
                "titulo": titulo, "resumo": _cortar(n.get("resumo"), LIMITES["resumo_noticia"]),
                "data": quando.strftime("%Y-%m-%d"), "status": n.get("status") if n.get("status") in config.STATUS_FATO
                else "hipótese ou cenário", "regiao": regiao["nome"],
                "paises": [p for p in n.get("paises", []) if p in membros],
                "mexe_em": [s for s in n.get("mexe_em", []) if s in SINAIS] or ["bolsa"],
                "direcao": n.get("direcao") if n.get("direcao") in DIRECOES else "incerto",
                "relevancia": int(n.get("relevancia") or 1), "fontes": fontes,
                "fonte_de_primeira_linha": any(f["confiavel"] for f in fontes)})
    noticias.sort(key=lambda n: (n["relevancia"], n["fonte_de_primeira_linha"], n["data"]), reverse=True)

    paises = {}
    for p in bruto.get("paises", []):
        nome, texto = p.get("nome"), _cortar(p.get("por_que"), LIMITES["por_que"])
        if nome in membros and texto and texto_ok(nome, texto):
            paises[nome] = texto
    resumo = _cortar(bruto.get("resumo"), LIMITES["resumo"])
    if resumo and not texto_ok("resumo da região", resumo):
        resumo = ""
    observar = []
    for o in bruto.get("observar", []):
        url = str(o.get("url") or "")
        if url and (not url.startswith("https://") or (permitidos is not None and _limpo(url) not in permitidos)):
            url = ""
        if pd.notna(pd.to_datetime(o.get("data"), errors="coerce")) and texto_ok("observar", f"{o.get('evento')} {o.get('por_que_importa')}"):
            observar.append({"data": o["data"], "evento": _cortar(o.get("evento"), 120),
                             "por_que_importa": _cortar(o.get("por_que_importa"), 220), "url": url})
    observar.sort(key=lambda o: o["data"])
    return {"resumo": resumo, "paises": paises, "noticias": noticias, "observar": observar, "descartados": descartes}


def pesquisar(mundo: dict, data: str, cliente=None) -> dict:
    """Roda o Correspondente nas 6 regiões. Sem chave de IA, devolve vazio (as páginas usam só os números)."""
    if cliente is None and not ia.disponivel():
        return {"regioes": {}, "modo": "sem IA"}
    cliente = cliente or ia.novo_cliente()
    saida = {}
    for regiao in mundo.get("regioes", []):
        if regiao.get("valor") is None:
            continue
        print(f"  Correspondente: {regiao['nome']}")
        buscados: set = set()
        try:
            bruto = ia.estruturado(cliente, SISTEMA, pedido(regiao, data),
                                   ferramenta([p["nome"] for p in regiao["paises"]]),
                                   buscas=config.BUSCAS_POR_REGIAO, max_tokens=8000, links=buscados)
        except Exception as erro:  # uma região com problema não derruba as outras
            print(f"  {regiao['nome']}: falhou ({erro})")
            saida[regiao["nome"]] = {"resumo": "", "paises": {}, "noticias": [], "observar": [],
                                     "descartados": [{"onde": regiao["nome"], "motivo": f"falhou: {str(erro)[:200]}"}]}
            continue
        saida[regiao["nome"]] = validar(bruto, regiao, data, buscados)
        r = saida[regiao["nome"]]
        print(f"    {len(r['noticias'])} notícias, {len(r['paises'])} países explicados, {len(r['descartados'])} descartes")
    return {"regioes": saida, "modo": f"claude ({config.MODELO_CLAUDE})"}


def todas_as_noticias(correspondente: dict) -> list[dict]:
    lista = [n for r in (correspondente or {}).get("regioes", {}).values() for n in r.get("noticias", [])]
    vistos, saida = set(), []  # a mesma notícia pode aparecer em duas regiões; na lista geral entra uma vez
    for n in sorted(lista, key=lambda n: (n["relevancia"], n["fonte_de_primeira_linha"], n["data"]), reverse=True):
        chave = n["titulo"].strip().lower()
        if chave not in vistos:
            vistos.add(chave)
            saida.append(n)
    return saida


# ---------------------------------------------------------------- reserva: o dossiê semanal do Buscador
_REGIAO_DO_BUSCADOR = {"Europa e Eurásia": "Europa", "Oriente Médio": "Oriente Médio",
                       "Ásia e Pacífico": "Ásia e Pacífico", "África": "África"}
_APELIDOS = {"EUA": ["EUA", "Estados Unidos", "Fed", "Treasury", "Trump", "Casa Branca", "Wall Street"],
             "Brasil": ["Brasil", "Lula", "Copom", "Selic", "Ibovespa", "B3"],
             "Argentina": ["Argentina", "Milei"], "México": ["México", "Sheinbaum"],
             "Reino Unido": ["Reino Unido", "Bank of England", "libra"], "China": ["China", "chinês", "chinesa", "Pequim"],
             "Japão": ["Japão", "iene", "BoJ"], "Israel": ["Israel", "israelense"], "Turquia": ["Turquia", "lira"],
             "Egito": ["Egito"], "Alemanha": ["Alemanha", "alemã"], "França": ["França", "francês", "francesa"]}


def noticias_do_dossie(dossie: dict, paises_por_regiao: dict[str, list[str]]) -> list[dict]:
    """Converte os eventos do Buscador (semanal) para o formato das notícias, enquanto não há Correspondente."""
    saida = []
    for ev in (dossie or {}).get("eventos", []):
        texto = f"{ev.get('titulo', '')} {ev.get('resumo', '')}"
        citados = [p for regiao in paises_por_regiao.values() for p in regiao
                   if any(re.search(rf"\b{re.escape(a)}\b", texto) for a in _APELIDOS.get(p, [p]))]
        regiao = _REGIAO_DO_BUSCADOR.get(ev.get("regiao"))
        if ev.get("regiao") == "Américas":
            latinos = set(paises_por_regiao.get("América Latina", []))
            regiao = "América Latina" if any(p in latinos for p in citados) else "América do Norte"
        regiao = regiao or "Global"
        saida.append({"titulo": ev.get("titulo", ""), "resumo": ev.get("resumo", ""), "data": ev.get("data", ""),
                      "status": ev.get("status", ""), "regiao": regiao,
                      "paises": [p for p in citados if p in paises_por_regiao.get(regiao, [])],
                      "mexe_em": [], "direcao": "", "relevancia": ev.get("relevancia", 1),
                      "canal_brasil": ev.get("canal_brasil", ""), "fontes": ev.get("fontes", []),
                      "fonte_de_primeira_linha": ev.get("fonte_de_primeira_linha", False)})
    return saida
