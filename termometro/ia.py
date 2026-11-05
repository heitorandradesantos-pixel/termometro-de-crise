"""Conversa com o Claude (API da Anthropic) para os agentes Buscador, Redator e Copy.

Os agentes que precisam devolver dados estruturados usam uma "ferramenta de saída":
o Claude preenche um formulário com campos fixos (esquema JSON), e o programa lê
esse formulário em vez de tentar adivinhar o formato de um texto livre. Se o
formulário vier incompleto, o programa devolve o erro ao Claude e pede de novo.
"""

import json
import os

from . import config

BUSCA_WEB = {"type": "web_search_20250305", "name": "web_search"}
RODADAS = 8


def disponivel() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def novo_cliente():
    import anthropic

    return anthropic.Anthropic(max_retries=4)


def _normalizar(entrada) -> dict:
    """Às vezes listas chegam como texto JSON; converte de volta."""
    saida = {}
    for chave, valor in (entrada or {}).items():
        if isinstance(valor, str) and valor.strip()[:1] in ("[", "{"):
            try:
                valor = json.loads(valor)
            except ValueError:
                pass
        saida[chave] = valor
    return saida


def _faltando(entrada: dict, saida: dict) -> list[str]:
    esquema = saida["input_schema"]
    faltam = []
    for chave in esquema.get("required", []):
        regra, valor = esquema["properties"].get(chave, {}), entrada.get(chave)
        if regra.get("type") == "array":
            if not isinstance(valor, list) or len(valor) < regra.get("minItems", 0):
                faltam.append(chave)
        elif valor in (None, ""):
            faltam.append(chave)
    return faltam


def links_das_buscas(conteudo) -> set[str]:
    """Endereços que a busca na web devolveu de verdade (para conferir que nenhum link foi inventado)."""
    achados = set()
    for bloco in conteudo or []:
        if getattr(bloco, "type", None) != "web_search_tool_result":
            continue
        resultados = getattr(bloco, "content", None)
        for r in resultados if isinstance(resultados, list) else []:
            url = getattr(r, "url", None) or (r.get("url") if isinstance(r, dict) else None)
            if url:
                achados.add(url)
    return achados


def estruturado(cliente, sistema: str, pedido: str, saida: dict, buscas: int = 0, max_tokens: int = 8000,
                links: set | None = None) -> dict:
    """Roda o agente até ele preencher a ferramenta de saída por completo e devolve o que foi preenchido.

    Se `links` for um conjunto, ele recebe todos os endereços que as buscas na web devolveram."""
    nome = saida["name"]
    # Alguns modelos não aceitam forçar a ferramenta (tool_choice "tool"/"any"); por isso fica
    # sempre "auto", e o pedido diz com todas as letras para terminar chamando o formulário.
    escolha = obrigatoria = {"type": "auto"}
    ferramentas = ([{**BUSCA_WEB, "max_uses": buscas}] if buscas else []) + [saida]
    fim = f"Termine chamando a ferramenta {nome} uma única vez, com todos os campos obrigatórios."
    if isinstance(pedido, list):  # pedido com imagens (blocos de conteúdo), usado pelos agentes de UI e UX
        pedido = pedido + [{"type": "text", "text": fim}]
    else:
        pedido = f"{pedido}\n\n{fim}"
    mensagens = [{"role": "user", "content": pedido}]
    for rodada in range(1, RODADAS + 1):
        resposta = cliente.messages.create(model=config.MODELO_CLAUDE, max_tokens=max_tokens, system=sistema,
                                           messages=mensagens, tools=ferramentas, tool_choice=escolha)
        mensagens.append({"role": "assistant", "content": resposta.content})
        if links is not None:
            links |= links_das_buscas(resposta.content)
        pesquisas = sum(1 for b in resposta.content if b.type == "server_tool_use")
        bloco = next((b for b in resposta.content if b.type == "tool_use" and b.name == nome), None)
        print(f"  [{nome}] rodada {rodada}: parada={resposta.stop_reason}, buscas={pesquisas}, "
              f"formulário={'sim' if bloco else 'não'}")
        if bloco is not None:
            entrada = _normalizar(bloco.input)
            faltam = _faltando(entrada, saida)
            if not faltam:
                return entrada
            print(f"  [{nome}] formulário incompleto, faltou: {', '.join(faltam)}")
            aviso = (f"O registro veio incompleto (faltou: {', '.join(faltam)}). Chame {nome} de novo com todos "
                     "os campos obrigatórios preenchidos. Seja conciso nos textos para caber na resposta.")
            mensagens.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": bloco.id, "content": aviso, "is_error": True}]})
            escolha = obrigatoria
            continue
        if resposta.stop_reason == "pause_turn":  # a busca pausou no meio: continua de onde parou
            continue
        extra = " Seja conciso para caber na resposta." if resposta.stop_reason == "max_tokens" else ""
        mensagens.append({"role": "user", "content": f"Agora registre o resultado chamando a ferramenta {nome}.{extra}"})
        escolha = obrigatoria
    raise RuntimeError(f"O agente não preencheu {nome} por completo depois de {RODADAS} rodadas.")


def texto(cliente, sistema: str, pedido: str, max_tokens: int = 6000) -> str:
    resposta = cliente.messages.create(model=config.MODELO_CLAUDE, max_tokens=max_tokens, system=sistema,
                                       messages=[{"role": "user", "content": pedido}])
    print(f"  [texto] parada={resposta.stop_reason}")
    return "".join(b.text for b in resposta.content if b.type == "text")
