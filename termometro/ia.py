"""Conversa com o Claude (API da Anthropic) para os agentes Buscador, Redator e Copy.

Os agentes que precisam devolver dados estruturados usam uma "ferramenta de saída":
o Claude preenche um formulário com campos fixos (esquema JSON), e o programa lê
esse formulário em vez de tentar adivinhar o formato de um texto livre.
"""

import os

from . import config

BUSCA_WEB = {"type": "web_search_20250305", "name": "web_search"}


def disponivel() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def novo_cliente():
    import anthropic

    return anthropic.Anthropic(max_retries=4)


def estruturado(cliente, sistema: str, pedido: str, saida: dict, buscas: int = 0, max_tokens: int = 8000) -> dict:
    """Roda o agente até ele preencher a ferramenta de saída e devolve o que foi preenchido."""
    ferramentas = ([{**BUSCA_WEB, "max_uses": buscas}] if buscas else []) + [saida]
    escolha = {"type": "auto"} if buscas else {"type": "tool", "name": saida["name"]}
    mensagens = [{"role": "user", "content": pedido}]
    for _ in range(8):
        resposta = cliente.messages.create(model=config.MODELO_CLAUDE, max_tokens=max_tokens, system=sistema,
                                           messages=mensagens, tools=ferramentas, tool_choice=escolha)
        mensagens.append({"role": "assistant", "content": resposta.content})
        for bloco in resposta.content:
            if bloco.type == "tool_use" and bloco.name == saida["name"]:
                return bloco.input
        if resposta.stop_reason == "pause_turn":  # a busca pausou no meio: continua de onde parou
            continue
        mensagens.append({"role": "user", "content": f"Agora registre o resultado chamando a ferramenta {saida['name']}."})
        escolha = {"type": "tool", "name": saida["name"]}
    raise RuntimeError(f"O agente não preencheu {saida['name']} depois de 8 rodadas.")


def texto(cliente, sistema: str, pedido: str, max_tokens: int = 6000) -> str:
    resposta = cliente.messages.create(model=config.MODELO_CLAUDE, max_tokens=max_tokens, system=sistema,
                                       messages=[{"role": "user", "content": pedido}])
    return "".join(b.text for b in resposta.content if b.type == "text")
