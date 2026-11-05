"""Agente redator: escreve a edição semanal a partir dos números e do dossiê do Buscador.

O Redator não pesquisa: ele só usa os fatos e links que o Buscador registrou.
Sem ANTHROPIC_API_KEY, monta a parte de dados e marca o resto como PENDENTE
(o Revisor então bloqueia a publicação).
"""

import json

import pandas as pd

from . import config, ia
from .grafico import mes_curto

SECOES = ["## O Termômetro da semana", "## Os 3 riscos no radar", "## Uma lição da história",
          "## O que acompanhar nos próximos 7 dias"]

SISTEMA = f"""Você é o Redator da newsletter "{config.NOME}", escrita em português do Brasil para
leitores que querem entender riscos globais e o efeito deles no próprio dinheiro.

Regras que não podem ser quebradas:
1. Use somente os números do bloco DADOS e somente os fatos e links do bloco DOSSIÊ.
   Não acrescente fatos, números ou links que não estejam lá.
2. Nunca recomende comprar, vender ou manter um ativo. Não cite códigos de ações nem fundos.
   Pode explicar mecanismos e riscos de classes de ativos (juros, dólar, ouro, ações) de forma educativa.
3. Mantenha o status de cada fato como o dossiê registrou: ameaça é ameaça, hipótese é hipótese.
4. Tom frio, claro e politicamente neutro. Sem sensacionalismo, sem promessa de lucro.
5. Analogias históricas mostram semelhanças e diferenças; nunca provam que o futuro vai se repetir.
6. Frases curtas. Explique termos técnicos na primeira vez que aparecerem.

Formato em Markdown, exatamente estas seções e nesta ordem:
{chr(10).join(SECOES)}
- "O Termômetro da semana": 2 parágrafos curtos com o valor, o nível, o mês da leitura e o que mais mexeu.
- "Os 3 riscos no radar": 3 itens numerados, escolhidos entre os eventos mais relevantes do dossiê
  (de preferência de regiões diferentes). Cada um: título em negrito, 2 a 4 frases, o canal até o
  Brasil e o link da fonte no formato [veículo](url).
- "Uma lição da história": um episódio comparável a um dos riscos, com semelhanças e diferenças.
- "O que acompanhar nos próximos 7 dias": 3 a 5 itens da agenda do dossiê, com data e link quando houver.
Não escreva título nem aviso legal: o programa acrescenta os dois. Entre 500 e 900 palavras."""


def _dados(dados: dict) -> str:
    comps = "\n".join(
        f"- {c['nome']} ({c['descricao']}): percentil {c['percentil']} de 100"
        + ("" if c["variacao_mes"] is None else f", {c['variacao_mes']:+d} no mês")
        for c in dados["componentes"])
    picos = ", ".join(f"{k}: {v['valor']} ({mes_curto(v['mes'])})" for k, v in dados["picos_historicos"].items())
    return (f"Leitura: {mes_curto(dados['referencia'])} (a mais recente com dados completos)\n"
            f"Termômetro: {dados['valor']} de 100, nível {dados['nivel']}: {dados['leitura']}\n"
            f"Mês anterior: {dados['mes_anterior']['valor']} ({dados['mes_anterior']['nivel']})\n"
            f"Componentes:\n{comps}\nPicos históricos: {picos}")


def _com_claude(dados: dict, dossie: dict, data_edicao: str, cliente) -> str:
    enxuto = {"eventos": [{k: ev[k] for k in ("titulo", "regiao", "status", "data", "resumo", "canal_brasil",
                                               "relevancia", "fontes")} for ev in dossie["eventos"][:8]],
              "agenda": dossie["agenda"][:6], "observacoes": dossie.get("observacoes", "")}
    pedido = (f"Data da edição: {data_edicao}\n\nDADOS\n{_dados(dados)}\n\n"
              f"DOSSIÊ\n{json.dumps(enxuto, ensure_ascii=False, indent=1)}")
    corpo = ia.texto(cliente, SISTEMA, pedido)
    inicio = corpo.find(SECOES[0])  # descarta qualquer frase solta antes da primeira seção
    return corpo[inicio:] if inicio >= 0 else corpo


def _sem_ia(dados: dict) -> str:
    variacao = dados["valor"] - dados["mes_anterior"]["valor"]
    movidos = sorted((c for c in dados["componentes"] if c["variacao_mes"] is not None),
                     key=lambda c: abs(c["variacao_mes"]), reverse=True)[:2]
    mexeu = " e ".join(f"{c['nome'].lower()} ({c['variacao_mes']:+d} pontos de percentil)" for c in movidos)
    pendente = "PENDENTE: escrito pelos agentes Buscador e Redator quando o segredo ANTHROPIC_API_KEY existir."
    return (f"{SECOES[0]}\n\nO Termômetro de Crise marcou **{dados['valor']}** em {mes_curto(dados['referencia'])}, "
            f"nível **{dados['nivel']}**: {dados['leitura'][0].lower() + dados['leitura'][1:]}. No mês anterior estava em "
            f"{dados['mes_anterior']['valor']} ({dados['mes_anterior']['nivel']}), {variacao:+d} pontos.\n\n"
            f"O que mais mexeu: {mexeu}.\n\n{SECOES[1]}\n\n{pendente}\n\n{SECOES[2]}\n\n{pendente}\n\n"
            f"{SECOES[3]}\n\n{pendente}")


def escrever(dados: dict, dossie: dict, data_edicao: str, cliente=None) -> tuple[str, str]:
    """Devolve (edição completa em Markdown, modo usado)."""
    if dossie.get("eventos") and (cliente or ia.disponivel()):
        corpo = _com_claude(dados, dossie, data_edicao, cliente or ia.novo_cliente())
        modo = f"claude ({config.MODELO_CLAUDE})"
    else:
        corpo, modo = _sem_ia(dados), "sem IA (só dados)"
    dia = pd.Timestamp(data_edicao)
    titulo = f"# {config.NOME}: {dados['valor']}, {dados['nivel']} — edição de {dia:%d/%m/%Y}"
    rodape = (f"*Leitura de {mes_curto(dados['referencia'])}, a mais recente com dados completos. Método aberto: "
              f"5 indicadores públicos, cada um comparado com o próprio histórico desde 1990.*\n\n---\n\n*{config.AVISO}*")
    return f"{titulo}\n\n{corpo.strip()}\n\n{rodape}\n", modo
