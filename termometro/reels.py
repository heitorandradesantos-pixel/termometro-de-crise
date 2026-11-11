"""Publica um Reel no Instagram do Termômetro pela API oficial (upload direto, sem link público do vídeo).

O vídeo chega criptografado num ramo temporário (o repositório é público) e a legenda vem num arquivo junto.
Modo "testar": sobe o vídeo e confere que a Meta aceitou, mas NÃO publica (o contêiner expira sozinho em 24 h).
Cada publicação é pedida e confirmada pelo Heitor; o horário é dele."""
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

from termometro import painel

GRAPH = painel.GRAPH
RUPLOAD = "https://rupload.facebook.com/ig-api-upload/" + GRAPH.rsplit("/", 1)[-1]


def _erro(r: requests.Response) -> str:
    try:
        e = r.json().get("error") or {}
        return f"{r.status_code} {e.get('message', '')[:200]} (código {e.get('code')}) {r.text[:300]}"
    except ValueError:
        return f"{r.status_code} {r.text[:200]}"


# Hashtags que a Meta recusa no envio pela API (descoberto em 11/11: "#cambio" derruba o upload)
BLOQUEADAS = ("#cambio",)


def limpar(legenda: str) -> str:
    for h in BLOQUEADAS:
        legenda = re.sub(rf"(?<!\w){re.escape(h)}\b ?", "", legenda, flags=re.IGNORECASE)
    return legenda.strip()


def subir(video: Path, legenda: str, token: str, ig: str) -> str:
    """Cria o contêiner do Reel, manda o arquivo e espera a Meta processar. Devolve o id do contêiner."""
    legenda = limpar(legenda)
    r = requests.post(f"{GRAPH}/{ig}/media", timeout=60, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": legenda, "share_to_feed": "true",
        "access_token": token})
    if r.status_code != 200:
        raise RuntimeError(f"criar contêiner: {_erro(r)}")
    cont, uri = r.json()["id"], r.json().get("uri") or f"{RUPLOAD}/{r.json()['id']}"
    dados = video.read_bytes()
    r = requests.post(uri, data=dados, timeout=600, headers={
        "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(dados))})
    if r.status_code != 200:
        raise RuntimeError(f"enviar vídeo: {_erro(r)}")
    for _ in range(60):  # até 10 min
        r = requests.get(f"{GRAPH}/{cont}", timeout=60,
                         params={"fields": "status_code,status", "access_token": token})
        estado = r.json() if r.status_code == 200 else {}
        if estado.get("status_code") == "FINISHED":
            return cont
        if estado.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"processamento: {estado.get('status')}")
        time.sleep(10)
    raise RuntimeError("a Meta não terminou de processar em 10 min")


def publicar(cont: str, token: str, ig: str) -> str:
    r = requests.post(f"{GRAPH}/{ig}/media_publish", timeout=120,
                      data={"creation_id": cont, "access_token": token})
    if r.status_code != 200:
        raise RuntimeError(f"publicar: {_erro(r)}")
    mid = r.json()["id"]
    r = requests.get(f"{GRAPH}/{mid}", timeout=60, params={"fields": "permalink", "access_token": token})
    return (r.json() if r.status_code == 200 else {}).get("permalink") or mid


if __name__ == "__main__":
    pasta, modo = Path(sys.argv[1]), (sys.argv[2] if len(sys.argv) > 2 else "testar")
    token, ig = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
    info = json.loads((pasta / "post.json").read_text())
    for tentativa in range(1, 5):  # a Meta às vezes recusa o envio sem motivo; tenta de novo com outro contêiner
        try:
            cont = subir(pasta / "video.mp4", info["legenda"], token, ig)
            break
        except RuntimeError as erro:
            print(f"tentativa {tentativa}: {erro}")
            if tentativa == 4:
                raise
            time.sleep(60 * tentativa)
    if modo == "publicar":
        print("PUBLICADO:", publicar(cont, token, ig))
    else:
        print("TESTE OK: a Meta aceitou o vídeo e a legenda (não publicado).")
