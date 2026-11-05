"""Agente buscador: pesquisa a semana no mundo e monta o dossiê com fontes.

Saída (pesquisa.json): eventos com região, status do fato, canal até o Brasil e
fontes com link; agenda dos próximos dias. O Redator só escreve a partir daqui,
e o Revisor confere que todo link do texto saiu deste dossiê.
"""

from urllib.parse import urlparse

import pandas as pd

from . import config, ia
from .grafico import mes_curto

SISTEMA = f"""Você é o agente Buscador do "{config.NOME}", um serviço de inteligência geopolítica e
econômica para leitores brasileiros. Sua única tarefa é pesquisar e registrar fatos com fonte;
você não escreve a newsletter.

Como trabalhar:
1. Varra as seis frentes: {', '.join(config.REGIOES)}. Nenhuma região fica de fora só por ter
   menos cobertura na imprensa. Inclua guerras, insurgências, sanções, disputas comerciais,
   decisões de bancos centrais, choques de energia e alimentos, eleições e crises fiscais.
2. Priorize fontes de primeira linha (Reuters, AP, FT, Bloomberg, bancos centrais, FMI, ACLED,
   International Crisis Group, governos). Confirme fatos controversos em duas fontes.
3. Classifique cada evento com um status: {', '.join(config.STATUS_FATO)}.
   Nunca registre rumor como fato confirmado.
4. Considere a data do acontecimento, não só a data da publicação.
5. Para cada evento, explique o canal até o Brasil (câmbio, Selic, inflação, exportações,
   agronegócio, energia) sem recomendar ativos.
6. Registre também a agenda dos próximos 7 dias (bancos centrais, inflação, eleições,
   prazos diplomáticos) com link oficial sempre que possível.
Ao terminar, chame a ferramenta registrar_dossie uma única vez com tudo."""
SISTEMA += config.manual('pesquisa')

FERRAMENTA = {
    "name": "registrar_dossie",
    "description": "Registra o dossiê da semana com eventos verificados e a agenda.",
    "input_schema": {
        "type": "object",
        "properties": {
            "eventos": {"type": "array", "minItems": 3, "maxItems": 12, "items": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string", "description": "Manchete factual, até 90 caracteres"},
                    "regiao": {"type": "string", "enum": config.REGIOES},
                    "status": {"type": "string", "enum": config.STATUS_FATO},
                    "data": {"type": "string", "description": "Data do acontecimento, AAAA-MM-DD"},
                    "resumo": {"type": "string", "description": "2 a 4 frases, só fatos"},
                    "canal_brasil": {"type": "string", "description": "Como isso pode chegar ao Brasil"},
                    "relevancia": {"type": "integer", "minimum": 1, "maximum": 5},
                    "fontes": {"type": "array", "minItems": 1, "items": {
                        "type": "object",
                        "properties": {"veiculo": {"type": "string"}, "url": {"type": "string"},
                                       "data": {"type": "string"}},
                        "required": ["veiculo", "url"]}},
                },
                "required": ["titulo", "regiao", "status", "data", "resumo", "canal_brasil", "relevancia", "fontes"]}},
            "agenda": {"type": "array", "maxItems": 8, "items": {
                "type": "object",
                "properties": {"data": {"type": "string"}, "evento": {"type": "string"},
                               "por_que_importa": {"type": "string"}, "url": {"type": "string"}},
                "required": ["data", "evento", "por_que_importa"]}},
            "regioes_sem_novidade": {"type": "array", "items": {"type": "string"}},
            "observacoes": {"type": "string", "description": "Divergências entre fontes e pontos incertos"},
        },
        "required": ["eventos", "agenda"],
    },
}


def dominio(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def confiavel(url: str) -> bool:
    host = dominio(url)
    return any(host == d or host.endswith("." + d) for d in config.FONTES_CONFIAVEIS)


def validar(dossie: dict, data_edicao: str) -> dict:
    """Limpa o dossiê: tira fontes sem link válido, eventos velhos e repetidos; ordena por relevância."""
    hoje = pd.Timestamp(data_edicao)
    vistos, eventos, descartes = set(), [], []
    for ev in dossie.get("eventos", []):
        fontes = [f for f in ev.get("fontes", []) if str(f.get("url", "")).startswith("https://")]
        quando = pd.to_datetime(ev.get("data"), errors="coerce")
        chave = ev.get("titulo", "").strip().lower()
        if not fontes:
            descartes.append({"titulo": ev.get("titulo"), "motivo": "sem link de fonte"})
        elif pd.notna(quando) and (quando < hoje - pd.Timedelta(days=14) or quando > hoje + pd.Timedelta(days=1)):
            descartes.append({"titulo": ev.get("titulo"), "motivo": f"data fora da semana ({ev.get('data')})"})
        elif chave in vistos:
            descartes.append({"titulo": ev.get("titulo"), "motivo": "repetido"})
        else:
            vistos.add(chave)
            for f in fontes:
                f["confiavel"] = confiavel(f["url"])
            eventos.append({**ev, "fontes": fontes, "fonte_de_primeira_linha": any(f["confiavel"] for f in fontes)})
    eventos.sort(key=lambda e: (e.get("relevancia", 0), e["fonte_de_primeira_linha"]), reverse=True)
    agenda = [a for a in dossie.get("agenda", []) if pd.notna(pd.to_datetime(a.get("data"), errors="coerce"))]
    agenda.sort(key=lambda a: a["data"])
    return {**dossie, "eventos": eventos, "agenda": agenda, "descartados": descartes}


def urls(dossie: dict) -> set[str]:
    todas = {f["url"] for ev in dossie.get("eventos", []) for f in ev.get("fontes", [])}
    return todas | {a["url"] for a in dossie.get("agenda", []) if a.get("url")}


def pesquisar(dados: dict, data_edicao: str, cliente=None) -> dict:
    if cliente is None and not ia.disponivel():
        return {"eventos": [], "agenda": [], "descartados": [], "modo": "sem IA"}
    cliente = cliente or ia.novo_cliente()
    pedido = (f"Data de hoje: {data_edicao}. Pesquise o que aconteceu nos últimos 7 dias.\n"
              f"Contexto: o Termômetro de Crise está em {dados['valor']} de 100 ({dados['nivel']}), "
              f"leitura de {mes_curto(dados['referencia'])}. Componentes em percentil: "
              + ", ".join(f"{c['nome']} {c['percentil']}" for c in dados["componentes"]) + ".")
    bruto = ia.estruturado(cliente, SISTEMA, pedido, FERRAMENTA, buscas=config.BUSCAS_MAXIMAS, max_tokens=16000)
    return {**validar(bruto, data_edicao), "modo": f"claude ({config.MODELO_CLAUDE})"}
