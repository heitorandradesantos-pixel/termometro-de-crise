"""Agente publicador: manda a edição aprovada para o beehiiv.

Precisa dos segredos BEEHIIV_API_KEY e BEEHIIV_PUBLICATION_ID (plano com acesso à API de posts).
BEEHIIV_ENVIO=rascunho (padrão) cria um rascunho para você conferir no beehiiv;
BEEHIIV_ENVIO=enviar publica e envia aos assinantes na hora.
"""

import json
import os
from pathlib import Path

import markdown
import requests

from . import config

API = "https://api.beehiiv.com/v2/publications/{pub}/posts"


def montar(pasta: Path) -> dict:
    copy = json.loads((pasta / "copy.json").read_text())
    texto = (pasta / "edicao.md").read_text().split("\n", 1)[1]  # o título vira o título do post
    corpo = markdown.markdown(texto, extensions=["extra", "sane_lists"])
    card = f"{config.SITE_URL}/edicoes/{pasta.name}/card.png" if config.SITE_URL else ""
    if card:
        corpo = f'<p><img src="{card}" alt="Termômetro de Crise da semana" width="540"></p>{corpo}'
    assunto = copy["assuntos_email"][copy["assunto_escolhido"]]
    post = {
        "title": copy["titulo_site"], "subtitle": copy["pre_cabecalho"], "body_content": corpo,
        "status": "confirmed" if os.environ.get("BEEHIIV_ENVIO", "rascunho") == "enviar" else "draft",
        "email_settings": {"email_subject_line": assunto, "email_preview_text": copy["pre_cabecalho"]},
        "seo_settings": {"default_title": copy["titulo_site"], "default_description": copy["descricao_seo"]},
    }
    if card:
        post["thumbnail_image_url"] = card
    return post


def newsletter(pasta: Path) -> bool:
    chave = os.environ.get("BEEHIIV_API_KEY", "").strip()
    pub = os.environ.get("BEEHIIV_PUBLICATION_ID", "").strip()
    if not (chave and pub):
        print("beehiiv não configurado: envio pulado (a edição continua no site).")
        return False
    revisao = json.loads((pasta / "revisao.json").read_text())
    if not revisao["aprovado"] and os.environ.get("PUBLICAR_MESMO_ASSIM") != "sim":
        print("O Revisor não aprovou esta edição; envio pulado. Corrija ou use PUBLICAR_MESMO_ASSIM=sim.")
        return False
    post = montar(pasta)
    resposta = requests.post(API.format(pub=pub), json=post, timeout=60,
                             headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"})
    if resposta.status_code >= 300:
        raise SystemExit(f"beehiiv recusou o post ({resposta.status_code}): {resposta.text[:500]}")
    print(f"beehiiv: post criado como {'envio' if post['status'] == 'confirmed' else 'rascunho'}.")
    return True
