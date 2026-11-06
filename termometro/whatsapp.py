"""Envio automático para a comunidade do WhatsApp (pela Z-API, que liga um número de WhatsApp por QR code).

A API oficial do WhatsApp (Cloud API da Meta) só manda para grupos de até 8 pessoas e não posta em comunidade
nem em canal; por isso o envio usa um serviço que conecta um número como o WhatsApp Web. Recomendação: um
número só da marca (não o pessoal), que seja administrador da comunidade, e no máximo poucos envios por dia.

Configuração (o dono cria a conta e grava os segredos no GitHub; ninguém cola chave no chat):
- segredos ZAPI_INSTANCIA, ZAPI_TOKEN e ZAPI_CLIENT_TOKEN (painel da Z-API);
- variável WHATSAPP_ENVIO: "nao" (padrão, não envia), "teste" (manda para WHATSAPP_TESTE) ou "sim" (comunidade);
- variável WHATSAPP_DESTINO: o grupo de avisos da comunidade ("123...-group"); o robô "WhatsApp" lista os grupos;
- variável WHATSAPP_TESTE: o número (5511999999999) ou grupo que recebe os testes.

Cada envio fica registrado em diario/AAAA-MM-DD/whatsapp.json, para um horário de reserva nunca mandar duas vezes.
"""

import base64
import json
import os
from pathlib import Path

import pandas as pd
import requests

BASE = "https://api.z-api.io/instances/{instancia}/token/{token}"


def configurado() -> bool:
    return all(os.environ.get(k) for k in ("ZAPI_INSTANCIA", "ZAPI_TOKEN", "ZAPI_CLIENT_TOKEN"))


def modo() -> str:
    m = (os.environ.get("WHATSAPP_ENVIO") or "nao").strip().lower()
    return m if m in ("nao", "teste", "sim") else "nao"


def destino() -> str:
    return (os.environ.get("WHATSAPP_TESTE") if modo() == "teste" else os.environ.get("WHATSAPP_DESTINO")) or ""


def _chamar(metodo: str, caminho: str, corpo: dict | None = None) -> dict:
    url = BASE.format(instancia=os.environ["ZAPI_INSTANCIA"], token=os.environ["ZAPI_TOKEN"]) + caminho
    r = requests.request(metodo, url, json=corpo, timeout=60,
                         headers={"Client-Token": os.environ["ZAPI_CLIENT_TOKEN"], "Content-Type": "application/json"})
    r.raise_for_status()
    return r.json() if r.content else {}


def enviar_imagem(para: str, imagem: Path, legenda: str) -> dict:
    conteudo = "data:image/png;base64," + base64.b64encode(imagem.read_bytes()).decode()
    return _chamar("POST", "/send-image", {"phone": para, "image": conteudo, "caption": legenda})


def enviar_texto(para: str, texto: str) -> dict:
    return _chamar("POST", "/send-text", {"phone": para, "message": texto})


def grupos() -> list[dict]:
    """Os grupos e comunidades do número conectado, para achar o grupo de avisos (o robô imprime a lista)."""
    saida = []
    try:
        for c in _chamar("GET", "/chats") or []:
            if c.get("isGroup"):
                saida.append({"comunidade": "", "grupo": c.get("name"), "phone": c.get("phone"), "avisos": False})
    except Exception as erro:  # noqa: BLE001
        print(f"Lista de conversas falhou: {erro}")
    for c in _chamar("GET", "/communities") or []:
        meta = _chamar("GET", f"/communities-metadata/{c.get('id')}")
        for g in meta.get("subGroups", []):
            saida.append({"comunidade": meta.get("name"), "grupo": g.get("name"), "phone": g.get("phone"),
                          "avisos": bool(g.get("isGroupAnnouncement"))})
    return saida


def ja_enviado(pasta_dia: Path, o_que: str) -> bool:
    arq = pasta_dia / "whatsapp.json"
    return arq.exists() and any(e.get("o_que") == o_que and e.get("modo") == modo()
                                for e in json.loads(arq.read_text()))


def registrar(pasta_dia: Path, o_que: str, resposta: dict) -> None:
    arq = pasta_dia / "whatsapp.json"
    lista = json.loads(arq.read_text()) if arq.exists() else []
    lista.append({"o_que": o_que, "modo": modo(), "quando": pd.Timestamp.now(tz="America/Sao_Paulo").isoformat(),
                  "id": resposta.get("messageId") or resposta.get("id")})
    arq.write_text(json.dumps(lista, ensure_ascii=False, indent=1))


def fechamento(pasta_diario: Path, dia: str, pasta_trabalho: Path) -> str:
    """Manda o card do Fechamento do Termômetro com o texto do balanço. Devolve o que aconteceu, em uma frase."""
    from . import fechamento as fch
    if modo() == "nao":
        return "Envio ao WhatsApp desligado (variável WHATSAPP_ENVIO)."
    if not configurado() or not destino():
        return "Envio ao WhatsApp sem configuração (segredos da Z-API ou destino)."
    pasta_dia = pasta_diario / dia
    if ja_enviado(pasta_dia, "fechamento"):
        return f"O fechamento de {dia} já foi enviado ({modo()})."
    gerado = fch.gerar(pasta_trabalho, pasta_diario, dia)
    if not gerado:
        return f"Sem card do fechamento de {dia}: nada enviado."
    resposta = enviar_imagem(destino(), pasta_trabalho / gerado["imagem"], gerado["legenda"])
    registrar(pasta_dia, "fechamento", resposta)
    return f"Fechamento de {dia} enviado ao WhatsApp ({modo()})."
