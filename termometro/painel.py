"""Painel de desempenho (privado): o robô lê as métricas dos posts do @termometrodecrise pela API oficial do Instagram
e guarda tudo criptografado em painel/dados.enc (AES-GCM, chave tirada da senha PAINEL_SENHA, que só o Heitor sabe).
O site publica em /painel/ uma página fora do menu e do Google que baixa esse arquivo e só abre com a senha: a conta é
feita no navegador. Sem a senha ninguém lê os números, nem no repositório público.

A "força" de um post é quanto ele faz as pessoas agirem sozinhas: (compartilhamentos x 2 + salvamentos + comentários)
a cada 100 pessoas alcançadas. É o melhor sinal de que o vídeo aguenta dinheiro de anúncio."""
from __future__ import annotations

import base64
import html
import json
import os
import shutil
from pathlib import Path

import pandas as pd
import requests

from . import config

GRAPH = "https://graph.facebook.com/v21.0"
RAIZ = Path(__file__).resolve().parent.parent
ARQ = RAIZ / "painel" / "dados.enc"
REPO = os.environ.get("GITHUB_REPOSITORY") or "heitorandradesantos-pixel/termometro-de-crise"
ITERACOES = 310_000
MAXIMO_POSTS = 100
MINIMO_ALCANCE = 200  # abaixo disso, é cedo para dizer se o post aguenta anúncio
METRICAS = {"REELS": ["views", "reach", "saved", "shares", "comments", "likes", "total_interactions",
                      "ig_reels_avg_watch_time"],
            "FEED": ["views", "reach", "saved", "shares", "comments", "likes", "total_interactions", "follows",
                     "profile_visits"]}
_INVALIDAS: set[str] = set()  # métrica que a API recusou nesta rodada não é pedida de novo


# ---------------------------------------------------------------- cofre (o mesmo formato que a página abre)

def _chave(senha: str, sal: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=ITERACOES).derive(senha.encode())


def cifrar(dados: dict, senha: str, sal: bytes | None = None) -> str:
    """O sal fica o mesmo enquanto a senha não muda (assim o "lembrar neste aparelho" da página continua valendo);
    o iv é novo a cada gravação."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    sal, iv = sal or os.urandom(16), os.urandom(12)
    bloco = AESGCM(_chave(senha, sal)).encrypt(iv, json.dumps(dados, ensure_ascii=False).encode(), None)
    b64 = lambda b: base64.b64encode(b).decode()
    return json.dumps({"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITERACOES, "sal": b64(sal), "iv": b64(iv),
                       "dados": b64(bloco)})


def decifrar(texto: str, senha: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    env = json.loads(texto)
    sal, iv, bloco = (base64.b64decode(env[k]) for k in ("sal", "iv", "dados"))
    return json.loads(AESGCM(_chave(senha, sal)).decrypt(iv, bloco, None))


def ler(senha: str, arq: Path | None = None) -> tuple[dict, bytes | None]:
    """Os dados guardados e o sal deles; se não existem (ou a senha mudou), começa do zero com sal novo."""
    arq = arq or ARQ
    if not arq.exists():
        return {}, None
    try:
        texto = arq.read_text()
        return decifrar(texto, senha), base64.b64decode(json.loads(texto)["sal"])
    except Exception:  # noqa: BLE001 — senha trocada: o histórico antigo não abre mais
        print("Painel: não deu para abrir os dados antigos com a senha atual; começando do zero.")
        return {}, None


# ---------------------------------------------------------------- Instagram (API oficial)

def _conferir(r) -> None:
    """Erro da API com a mensagem da Meta, sem o endereço (que leva o token)."""
    if getattr(r, "status_code", 200) >= 400:
        try:
            e = r.json().get("error", {})
        except ValueError:
            e = {}
        raise RuntimeError(f"HTTP {r.status_code}: {e.get('message', '')} (code {e.get('code')})")


def conta(token: str, ig: str, buscar=requests.get) -> dict:
    r = buscar(f"{GRAPH}/{ig}", params={"fields": "username,followers_count,media_count", "access_token": token},
               timeout=60)
    _conferir(r)
    return r.json()


def midias(token: str, ig: str, buscar=requests.get, maximo: int = MAXIMO_POSTS) -> list[dict]:
    campos = ("id,caption,media_type,media_product_type,permalink,timestamp,thumbnail_url,media_url,"
              "like_count,comments_count")
    url, params, saida = f"{GRAPH}/{ig}/media", {"fields": campos, "limit": 50, "access_token": token}, []
    while url and len(saida) < maximo:
        r = buscar(url, params=params, timeout=60)
        _conferir(r)
        corpo = r.json()
        saida += corpo.get("data") or []
        url, params = (corpo.get("paging") or {}).get("next"), None  # o "next" já traz os parâmetros
    return saida[:maximo]


def _valor(item: dict):
    if "total_value" in item:
        return (item.get("total_value") or {}).get("value")
    valores = item.get("values") or [{}]
    return valores[0].get("value")


def metricas(token: str, midia: dict, buscar=requests.get) -> dict:
    """As métricas de um post. Se a API recusar o pacote, pede uma por uma e lembra das que não existem."""
    tipo = "REELS" if midia.get("media_product_type") == "REELS" else "FEED"
    pedir = [m for m in METRICAS[tipo] if m not in _INVALIDAS]

    def chamar(lista: list[str]) -> dict:
        r = buscar(f"{GRAPH}/{midia['id']}/insights", params={"metric": ",".join(lista), "access_token": token},
                   timeout=60)
        _conferir(r)
        return {i.get("name"): _valor(i) for i in r.json().get("data") or []}

    try:
        return chamar(pedir) if pedir else {}
    except RuntimeError:
        saida = {}
        for m in pedir:
            try:
                saida.update(chamar([m]))
            except RuntimeError:
                _INVALIDAS.add(m)
        return saida


# ---------------------------------------------------------------- contas

def _iso(ts) -> str:
    """A Meta manda "2026-11-09T16:00:00+0000"; o navegador do iPhone só entende com dois-pontos no fuso."""
    try:
        return pd.Timestamp(ts).isoformat() if ts else ""
    except ValueError:
        return str(ts)


def _local(t: str) -> pd.Timestamp:
    ts = pd.Timestamp(t)
    return ts.tz_localize("America/Sao_Paulo") if ts.tzinfo is None else ts


def forca(p: dict) -> float | None:
    alcance = p.get("alcance") or 0
    if not alcance:
        return None
    acao = 2 * (p.get("compartilhamentos") or 0) + (p.get("salvos") or 0) + (p.get("comentarios") or 0)
    return round(acao / alcance * 100, 1)


def post(midia: dict, m: dict) -> dict:
    tempo = m.get("ig_reels_avg_watch_time")
    p = {"id": midia["id"], "tipo": midia.get("media_product_type") or midia.get("media_type") or "",
         "formato": midia.get("media_type") or "", "legenda": (midia.get("caption") or "").strip()[:300],
         "link": midia.get("permalink") or "", "data": _iso(midia.get("timestamp")),
         "capa": midia.get("thumbnail_url") or midia.get("media_url") or "",
         "views": m.get("views"), "alcance": m.get("reach"), "salvos": m.get("saved"),
         "compartilhamentos": m.get("shares"),
         "comentarios": m.get("comments", midia.get("comments_count")),
         "curtidas": m.get("likes", midia.get("like_count")), "interacoes": m.get("total_interactions"),
         "seguiram": m.get("follows"), "tempo_medio": round(tempo / 1000, 1) if tempo else None}
    p["forca"] = forca(p)
    return p


def candidatos(posts: list[dict], n: int = 3, minimo: int = MINIMO_ALCANCE) -> tuple[list[dict], bool]:
    """Os posts com mais força entre os que já têm alcance para dizer algo. Se nenhum chegou lá, os melhores
    assim mesmo, avisando que é cedo (o segundo valor é False)."""
    com_forca = [p for p in posts if p.get("forca") is not None]
    bons = [p for p in com_forca if (p.get("alcance") or 0) >= minimo]
    base = bons or com_forca
    return sorted(base, key=lambda p: (p["forca"], p.get("views") or 0), reverse=True)[:n], bool(bons)


def atualizar(antigo: dict, info: dict, posts: list[dict], agora: str) -> dict:
    """Junta a leitura de agora com o histórico: seguidores ao longo do tempo e a série de views de cada post."""
    seguidores = [s for s in antigo.get("seguidores", []) if s.get("t", "")[:13] != agora[:13]]
    if info.get("followers_count") is not None:
        seguidores.append({"t": agora, "n": info["followers_count"]})
    series = {p["id"]: p.get("serie", []) for p in antigo.get("posts", [])}
    for p in posts:
        serie = [s for s in series.get(p["id"], []) if s[0][:13] != agora[:13]]
        if p.get("views") is not None:
            serie.append([agora, p["views"]])
        p["serie"] = serie[-40:]
    return {"atualizado": agora, "conta": {"usuario": info.get("username", ""), "seguidores": info.get("followers_count"),
                                           "posts": info.get("media_count")},
            "seguidores": seguidores[-1500:], "posts": posts, "minimo_alcance": MINIMO_ALCANCE}


def rodar(arq: Path | None = None, buscar=requests.get, agora: str | None = None) -> str:
    arq = arq or ARQ
    token, ig, senha = (os.environ.get(k, "") for k in ("IG_TOKEN", "IG_USER_ID", "PAINEL_SENHA"))
    if not (token and ig and senha):
        return "Painel: faltam IG_TOKEN, IG_USER_ID ou PAINEL_SENHA nos secrets; nada a fazer."
    agora = agora or pd.Timestamp.now(tz="America/Sao_Paulo").isoformat(timespec="minutes")
    info = conta(token, ig, buscar)
    lista, falhas = [], 0
    for midia in midias(token, ig, buscar):
        try:
            lista.append(post(midia, metricas(token, midia, buscar)))
        except Exception as erro:  # noqa: BLE001 — um post que não deu não para os outros
            falhas += 1
            print(f"  post {midia.get('id')}: {str(erro)[:120]}")
    antigo, sal = ler(senha, arq)
    dados = atualizar(antigo, info, lista, agora)
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(cifrar(dados, senha, sal))
    recusadas = f"; métricas que a API não tem: {', '.join(sorted(_INVALIDAS))}" if _INVALIDAS else ""
    return (f"Painel: {len(lista)} post(s), {info.get('followers_count')} seguidores"
            + (f", {falhas} com erro" if falhas else "") + recusadas + ".")


# ---------------------------------------------------------------- ranking de sábado (WhatsApp)

def _numero(n) -> str:
    return "-" if n is None else f"{n:,}".replace(",", ".")


def _titulo(p: dict, limite: int = 70) -> str:
    linha = (p.get("legenda") or "").split("\n")[0].strip() or "(sem legenda)"
    return linha if len(linha) <= limite else linha[:limite - 1].rstrip() + "…"


def ranking(dados: dict, dias: int = 7, agora: pd.Timestamp | None = None) -> str:
    agora = agora or pd.Timestamp.now(tz="America/Sao_Paulo")
    corte = (agora - pd.Timedelta(days=dias)).tz_convert("UTC")
    recentes = [p for p in dados.get("posts", []) if p.get("data") and _local(p["data"]) >= corte]
    if not recentes:
        return ("📊 RANKING DA SEMANA (Instagram)\n\nNenhum post nos últimos 7 dias ainda. Assim que os Reels saírem, "
                "o ranking aparece aqui.")
    top, confiavel = candidatos(recentes)
    linhas = [f"{i}. {_titulo(p)}\n   força {str(p['forca']).replace('.', ',')} · {_numero(p.get('views'))} views · "
              f"{_numero(p.get('compartilhamentos'))} compart. · {_numero(p.get('salvos'))} salvos\n   {p['link']}"
              for i, p in enumerate(top, 1)]
    seg = dados.get("seguidores", [])
    antes = next((s["n"] for s in seg if _local(s["t"]) >= agora - pd.Timedelta(days=dias)), None)
    atual = (dados.get("conta") or {}).get("seguidores")
    ganho = f" ({'+' if atual - antes >= 0 else ''}{atual - antes} na semana)" if atual is not None and antes is not None else ""
    aviso = "" if confiavel else (f"\n\n⚠️ Ainda é cedo: nenhum post passou de {MINIMO_ALCANCE} pessoas alcançadas. "
                                  "Vale esperar mais uns dias antes de pôr dinheiro.")
    return ("📊 RANKING DA SEMANA (Instagram)\n\nCandidatos a anúncio: os que mais fazem as pessoas compartilharem, "
            "salvarem e comentarem a cada 100 alcançadas.\n\n" + "\n\n".join(linhas) + aviso
            + f"\n\n👥 Seguidores: {_numero(atual)}{ganho}\n🔒 Painel completo: {config.url_publica('painel/')} "
            "(abre com a sua senha)")


# ---------------------------------------------------------------- página do site

# ---------------------------------------------------------------- marcas (a do Termômetro e a da ferramenta para criadores)

PASTA = Path(__file__).resolve().parent
PRODUTO = os.environ.get("PRODUTO_NOME") or "Métricas"  # nome provisório da ferramenta para criadores
TEMA_CLARO = """:root{--fundo:#F5F8FC;--painel:#FFFFFF;--painel2:#EEF3FA;--linha:#DCE4EF;--grade:#C9D5E5;--texto:#0B1B33;
  --suave:#4A5B73;--apagado:#5F6E84;--acento:#1D5FD6;--acento-lavado:rgba(29,95,214,.10);--sobre-acento:#FFFFFF;
  --sobe:#157A4A;--desce:#B42318;--capa1:#DCE8FA;--capa2:#B9CFF2}
.capa .reserva{color:#2B4A7A}"""


def marca_produto(nome: str = "") -> str:
    nome = html.escape(nome or PRODUTO)
    return ('<div class="marca"><svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true">'
            '<rect x="3" y="13" width="4" height="8" rx="1.5" fill="#9DBBF0"/><rect x="10" y="8" width="4" height="13" rx="1.5" '
            'fill="#5B8DE6"/><rect x="17" y="3" width="4" height="18" rx="1.5" fill="#1D5FD6"/></svg>'
            f'<span style="letter-spacing:.01em;text-transform:none;font-size:18px">{nome}</span></div>')


def pagina(fonte: str = "", dados_demo: dict | None = None, raiz: str = "../", produto: bool = False) -> str:
    js = json.dumps(dados_demo, ensure_ascii=False).replace("</", "<\\/") if dados_demo else "null"
    return (PAGINA.replace("__FONTE__", html.escape(fonte)).replace("__ITER__", str(ITERACOES))
            .replace("/*__DEMO__*/null", js).replace('href="../favicon.svg"', f'href="{raiz}favicon.svg"')
            .replace("__TITULO__", f"{PRODUTO}: painel de exemplo" if produto else "Painel do Termômetro")
            .replace("__COR__", "#F5F8FC" if produto else "#0E141B")
            .replace("/*__TEMA__*/", TEMA_CLARO if produto else "")
            .replace("__MARCA__", marca_produto() if produto else MARCA_TERMOMETRO))


def gerar(saida: Path, arq: Path | None = None) -> None:
    """/painel/ (fechada com senha), /painel/demo/ (vitrine do Termômetro) e, em rascunho, /metricas/ (a ferramenta
    para criadores: apresentação e painel de exemplo em azul e branco)."""
    arq = arq or ARQ
    pasta = saida / "painel"
    (pasta / "demo").mkdir(parents=True, exist_ok=True)
    if arq.exists():
        shutil.copy(arq, pasta / "dados.enc")  # cópia, caso o GitHub esteja fora
    (pasta / "index.html").write_text(pagina(f"https://raw.githubusercontent.com/{REPO}/main/painel/dados.enc"))
    exemplo = demo()
    (pasta / "demo" / "index.html").write_text(pagina(dados_demo=exemplo, raiz="../../"))
    produto = saida / "metricas"
    (produto / "demo").mkdir(parents=True, exist_ok=True)
    (produto / "demo" / "index.html").write_text(pagina(dados_demo=exemplo, raiz="../../", produto=True))
    (produto / "index.html").write_text(vitrine(exemplo))
    cabecalhos = saida / "_headers"
    regra = ("/painel/*\n  X-Robots-Tag: noindex, nofollow\n  Cache-Control: no-store\n  Referrer-Policy: no-referrer\n"
             "/metricas/*\n  X-Robots-Tag: noindex, nofollow\n")  # rascunho: fora do Google até ter nome definitivo
    cabecalhos.write_text((cabecalhos.read_text() + "\n" if cabecalhos.exists() else "") + regra)


def vitrine(exemplo: dict) -> str:
    """A página de apresentação da ferramenta para criadores, com o cartão do melhor post da demo."""
    posts = [p for p in exemplo["posts"] if p.get("forca") is not None]
    melhor = max(posts, key=lambda p: p["forca"])
    media = sum(p["forca"] for p in posts) / len(posts)
    fmt = lambda n: f"{n:,}".replace(",", ".")
    um = lambda x: f"{x:.1f}".replace(".", ",")
    return (VITRINE.replace("__PRODUTO__", html.escape(PRODUTO)).replace("__MARCA__", marca_produto())
            .replace("__TITULO_POST__", html.escape(melhor["legenda"])).replace("__FORCA__", um(melhor["forca"]))
            .replace("__MEDIA__", um(media)).replace("__VEZES__", um(melhor["forca"] / media))
            .replace("__COMPART__", fmt(melhor["compartilhamentos"])).replace("__SALVOS__", fmt(melhor["salvos"]))
            .replace("__ALCANCE__", fmt(melhor["alcance"])))


DEMO_TITULOS = ["3 erros que travam o alcance do seu Reel", "Como eu gravo 5 vídeos em 1 hora",
                "O que ninguém te conta sobre o algoritmo", "Editei o mesmo vídeo de 2 jeitos: qual ganhou?",
                "Qual capa você clicaria?", "Meu setup de gravação de R$ 300", "Tendência da semana: vale entrar?",
                "Bastidores de um dia de produção", "Responda em 3 segundos: o que te faz parar de rolar?",
                "O roteiro que eu uso em todo vídeo"]


def demo(hoje: pd.Timestamp | None = None) -> dict:
    """Dados fictícios (sempre os mesmos números, com datas recentes) para a vitrine /painel/demo/."""
    import random
    sorteio = random.Random(42)
    hoje = (hoje or pd.Timestamp.now(tz="America/Sao_Paulo")).floor("h")
    posts = []
    for i, titulo in enumerate(DEMO_TITULOS):
        quando = hoje - pd.Timedelta(hours=34 * i + 3)  # 10 posts em duas semanas: dá para comparar com a anterior
        alcance = sorteio.randint(9000, 30000)
        p = {"id": f"demo{i}", "tipo": "REELS", "formato": "VIDEO", "legenda": titulo, "link": "#",
             "data": quando.isoformat(), "capa": "", "alcance": alcance, "views": int(alcance * sorteio.uniform(1.3, 1.9)),
             "salvos": int(alcance * sorteio.uniform(0.004, 0.04)), "compartilhamentos": int(alcance * sorteio.uniform(0.002, 0.05)),
             "comentarios": sorteio.randint(8, 160), "curtidas": int(alcance * sorteio.uniform(0.03, 0.08)),
             "interacoes": None, "seguiram": None, "tempo_medio": round(sorteio.uniform(4.5, 21), 1)}
        if i == 1:  # o post que "estourou": é ele que a vitrine mostra como o que vale impulsionar
            p.update(alcance=38500, views=71200, compartilhamentos=2950, salvos=1840, comentarios=212)
        p["forca"] = forca(p)
        p["serie"] = [[(hoje - pd.Timedelta(hours=h)).isoformat(timespec="minutes"), int(p["views"] * (1 - h / 120))]
                      for h in (24, 18, 12, 6, 0)]
        posts.append(p)
    seguidores = [{"t": (hoje - pd.Timedelta(hours=6 * k)).isoformat(timespec="minutes"),
                   "n": int(12480 + (40 - k) ** 1.6 + sorteio.randint(0, 25))} for k in range(40, -1, -1)]
    return {"atualizado": hoje.isoformat(timespec="minutes"),
            "conta": {"usuario": "seuperfil", "seguidores": seguidores[-1]["n"], "posts": len(posts)},
            "seguidores": seguidores, "posts": posts, "minimo_alcance": MINIMO_ALCANCE}


def _ler(nome: str) -> str:
    arq = PASTA / nome
    return arq.read_text() if arq.exists() else ""


PAGINA = _ler("painel.html")
MARCA_TERMOMETRO = _ler("painel_marca_termometro.html").strip()
VITRINE = _ler("metricas.html")
