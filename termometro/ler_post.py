"""Lê um post do Instagram pelo link (API oficial): legenda, autor, data e, se for vídeo, a fala transcrita.
Serve para o Heitor mandar "isso é fato ou mito?" pelo celular. O resultado sai CRIPTOGRAFADO no log (a chave vem
no disparo), porque o repositório é público e o texto é do criador."""
import json
import os
import re
import subprocess
import sys
import tempfile

import requests

from termometro import referencias

GRAPH = referencias.GRAPH


def codigo(url: str) -> str:
    m = re.search(r"instagram\.com/(?:[^/]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", url)
    if not m:
        raise SystemExit("link do Instagram não reconhecido")
    return m.group(1)


def achar(url: str, token: str, ig: str, perfis: list[str]) -> dict:
    cod = codigo(url)
    saida = {"url": url, "codigo": cod}
    r = requests.get(f"{GRAPH}/instagram_oembed", params={"url": f"https://www.instagram.com/p/{cod}/", "access_token": token},
                     timeout=60)
    if r.ok:
        saida["oembed"] = {k: r.json().get(k) for k in ("author_name", "title")}
        if r.json().get("author_name"):
            perfis = [r.json()["author_name"], *perfis]
    else:
        saida["oembed_erro"] = (r.json().get("error") or {}).get("message", "")[:200]
    campos = "media.limit(60){id,caption,media_type,media_product_type,permalink,timestamp,media_url,like_count,comments_count}"
    for perfil in dict.fromkeys(p for p in perfis if p):
        r = requests.get(f"{GRAPH}/{ig}", params={"fields": f"business_discovery.username({perfil}){{{campos}}}",
                                                   "access_token": token}, timeout=60)
        if not r.ok:
            continue
        for m in ((r.json().get("business_discovery") or {}).get("media") or {}).get("data", []):
            if cod in (m.get("permalink") or ""):
                return {**saida, "perfil": perfil, **{k: m.get(k) for k in ("caption", "media_type", "media_product_type",
                                                                              "permalink", "timestamp", "like_count",
                                                                              "comments_count", "media_url")}}
    return {**saida, "achado": False, "procurado_em": perfis}


def transcrever(media_url: str) -> str:
    from termometro import transcrever as t
    with tempfile.TemporaryDirectory() as pasta:
        arq = os.path.join(pasta, "v.mp4")
        with requests.get(media_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(arq, "wb") as f:
                for parte in r.iter_content(1 << 20):
                    f.write(parte)
        os.environ.setdefault("MODELO", "small")
        return " ".join(s["texto"] for s in t.rodar(arq))


if __name__ == "__main__":
    url = sys.argv[1]
    extras = [p.strip().lstrip("@") for p in (sys.argv[2] if len(sys.argv) > 2 else "").split(",")]
    dados = achar(url, os.environ["IG_TOKEN"], os.environ["IG_USER_ID"], [*extras, *referencias.PERFIS])
    if dados.get("media_url") and dados.get("media_type") == "VIDEO":
        try:
            dados["fala"] = transcrever(dados["media_url"])
        except Exception as erro:  # noqa: BLE001
            dados["fala_erro"] = str(erro)[:200]
    dados.pop("media_url", None)
    claro = json.dumps(dados, ensure_ascii=False).encode()
    cifrado = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:CHAVE", "-a", "-A"],
                             input=claro, capture_output=True, check=True).stdout.decode()
    print("POST_INICIO"); print(cifrado); print("POST_FIM")
    print("achado:", "perfil" in dados, "| tem fala:", "fala" in dados)
