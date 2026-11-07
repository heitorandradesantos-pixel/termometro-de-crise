"""Agente publicador: manda a edição aprovada para a newsletter (Kit; o beehiiv fica como alternativa).

Kit: segredo KIT_API_KEY (Settings > Developer, API v4). O modo vem da variável KIT_ENVIO ou do arquivo
newsletter.txt: "rascunho" (padrão) cria o e-mail como rascunho no Kit, para você só apertar enviar;
"agendar" agenda para domingo às 8h (ou para dali a 10 minutos, se já passou).
beehiiv: segredos BEEHIIV_API_KEY e BEEHIIV_PUBLICATION_ID; BEEHIIV_ENVIO=rascunho ou enviar.
"""

import json
import os
from pathlib import Path

import markdown
import requests

from . import config

API = "https://api.beehiiv.com/v2/publications/{pub}/posts"
KIT_API = "https://api.kit.com/v4/broadcasts"
ARQ_MODO_KIT = Path(__file__).resolve().parent.parent / "newsletter.txt"


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


def modo_kit() -> str:
    m = (os.environ.get("KIT_ENVIO") or "").strip().lower()
    if not m and ARQ_MODO_KIT.exists():
        m = ARQ_MODO_KIT.read_text().strip().lower()
    return m if m in ("rascunho", "agendar") else "rascunho"


def quando_enviar(agora=None) -> str:
    """Domingo às 8h em Brasília; se já passou, daqui a 10 minutos (em UTC, como o Kit pede)."""
    import pandas as pd
    agora = agora or pd.Timestamp.now(tz="America/Sao_Paulo")
    alvo = agora.normalize() + pd.Timedelta(hours=8)
    if agora.weekday() != 6 or alvo <= agora + pd.Timedelta(minutes=5):
        alvo = agora + pd.Timedelta(minutes=10)
    return alvo.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def email_kit(pasta: Path) -> dict:
    """A edição como broadcast do Kit: o mesmo corpo do site, com o card, o convite para o grupo e o aviso."""
    import pandas as pd
    post = montar(pasta)
    site = config.SITE_URL or "https://termometrodecrise.com"
    rodape = (f'<hr><p><strong>Todo dia útil</strong>, o fechamento do dia (o card, o balanço e o panorama) sai no grupo do '
              f'WhatsApp: <a href="{config.WHATSAPP_URL}">entrar no grupo</a>.</p>'
              f'<p>O termômetro de hoje, país por país: <a href="{site}/?utm_source=newsletter&utm_campaign={pasta.name}">'
              f'termometrodecrise.com</a></p>'
              f'<p style="font-size:12px;color:#666666">Conteúdo educativo, com fonte em cada fato. Não é recomendação de '
              f'investimento.</p>')
    modo = modo_kit()
    corpo = {"subject": post["email_settings"]["email_subject_line"],
             "preview_text": post["email_settings"]["email_preview_text"],
             "description": f"Termômetro da Semana · {pasta.name}", "content": post["body_content"] + rodape,
             "public": False, "published_at": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
             "send_at": quando_enviar() if modo == "agendar" else None}
    if post.get("thumbnail_image_url"):
        corpo.update(thumbnail_url=post["thumbnail_image_url"], thumbnail_alt="Termômetro de Crise da semana")
    return corpo


def newsletter_kit(pasta: Path) -> bool:
    chave = os.environ.get("KIT_API_KEY", "").strip()
    if not chave:
        return False
    revisao = json.loads((pasta / "revisao.json").read_text())
    if not revisao["aprovado"] and os.environ.get("PUBLICAR_MESMO_ASSIM") != "sim":
        print("O Revisor não aprovou esta edição; envio pulado. Corrija ou use PUBLICAR_MESMO_ASSIM=sim.")
        return False
    corpo = email_kit(pasta)
    cabecalho = {"X-Kit-Api-Key": chave, "Content-Type": "application/json", "Accept": "application/json"}
    resposta = requests.post(KIT_API, json=corpo, headers=cabecalho, timeout=60)
    if resposta.status_code == 422 and "subscriber_filter" in resposta.text:  # versões da API que exigem o campo
        resposta = requests.post(KIT_API, json={**corpo, "subscriber_filter": []}, headers=cabecalho, timeout=60)
    if resposta.status_code >= 300:
        raise SystemExit(f"Kit recusou a edição ({resposta.status_code}): {resposta.text[:500]}")
    print(f"Kit: edição criada como {'agendada para ' + corpo['send_at'] if corpo['send_at'] else 'rascunho'}.")
    return True
