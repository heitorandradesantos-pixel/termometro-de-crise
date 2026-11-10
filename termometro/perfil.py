"""Raio-x do perfil do Termômetro no Instagram (API oficial), para o editor dar feedback ao Heitor.
Lê bio, números da conta, os posts com métricas e o alcance da conta nos últimos dias. O resultado sai
CRIPTOGRAFADO no log (a chave vem no disparo), porque o repositório é público."""
import json
import os
import subprocess

import requests

from termometro import painel

GRAPH = painel.GRAPH


def _get(caminho: str, token: str, **params):
    r = requests.get(f"{GRAPH}/{caminho}", params={**params, "access_token": token}, timeout=60)
    painel._conferir(r)
    return r.json()


def conta_completa(token: str, ig: str) -> dict:
    campos = "username,name,biography,website,followers_count,follows_count,media_count"
    try:
        return _get(ig, token, fields=campos)
    except RuntimeError as erro:
        return {**painel.conta(token, ig), "erro_campos": str(erro)[:200]}


def insights_conta(token: str, ig: str) -> dict:
    """Alcance, visitas ao perfil, cliques no link e seguidores ganhos (últimos 28 dias, o máximo da API)."""
    import pandas as pd
    fim = pd.Timestamp.now(tz="UTC")
    ini = fim - pd.Timedelta(days=27)
    saida = {}
    for m in ["reach", "profile_views", "accounts_engaged", "website_clicks", "follows_and_unfollows",
              "total_interactions", "views"]:
        try:
            corpo = _get(f"{ig}/insights", token, metric=m, period="day", metric_type="total_value",
                         since=int(ini.timestamp()), until=int(fim.timestamp()))
            saida[m] = [painel._valor(i) for i in corpo.get("data") or []]
        except RuntimeError as erro:
            saida[m] = f"erro: {str(erro)[:120]}"
    try:
        corpo = _get(f"{ig}/insights", token, metric="reach", period="day",
                     since=int(ini.timestamp()), until=int(fim.timestamp()))
        saida["alcance_por_dia"] = [(v.get("end_time"), v.get("value"))
                                    for i in corpo.get("data") or [] for v in i.get("values") or []]
    except RuntimeError as erro:
        saida["alcance_por_dia"] = f"erro: {str(erro)[:120]}"
    return saida


def rodar() -> dict:
    token, ig = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
    posts = []
    for midia in painel.midias(token, ig):
        p = painel.post(midia, painel.metricas(token, midia))
        p["legenda"] = (midia.get("caption") or "").strip()[:600]
        p["capa"] = ""  # endereço temporário, não serve para a análise
        posts.append(p)
    return {"conta": conta_completa(token, ig), "insights": insights_conta(token, ig), "posts": posts}


if __name__ == "__main__":
    dados = rodar()
    claro = json.dumps(dados, ensure_ascii=False).encode()
    cifrado = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:CHAVE", "-a",
                              "-A"], input=claro, capture_output=True, check=True).stdout.decode()
    print("PERFIL_INICIO"); print(cifrado); print("PERFIL_FIM")
    print("posts:", len(dados["posts"]), "| seguidores:", dados["conta"].get("followers_count"))
