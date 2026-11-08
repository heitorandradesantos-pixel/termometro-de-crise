"""Referências: 5 vezes por dia, o robô olha os Reels novos dos criadores que o Heitor acompanha (Pablo Spyer, Rian e
Shimon) e
alimenta o Roteirista, o Copywriter e o Estrategista com o que funciona neles. Roda na nuvem, sem o computador.

Como: a API oficial do Instagram ("Business Discovery") deixa uma conta profissional (a do Termômetro) ler os posts
públicos de outras contas profissionais: legenda, link, tipo e o arquivo do vídeo. O áudio é transcrito no próprio
robô do GitHub (faster-whisper) e o Claude tira daí o tema, o gancho e as técnicas, com as nossas palavras.

O repositório é público: nunca guardamos a legenda nem a transcrição, só a nossa análise (tema e técnicas) e o link.
Se o assunto do vídeo for notícia de dinheiro quente que ainda não cobrimos, sugere a pauta ao Plantão (que confere
tudo de novo, com fonte, antes de publicar).

Precisa de IG_TOKEN (token da conta do Termômetro) e IG_USER_ID (id da conta profissional) nos secrets do GitHub.
"""

import json
import os
import re
import tempfile
from pathlib import Path

import pandas as pd
import requests

from . import config, ia

PERFIS = tuple(p.strip().lstrip("@") for p in (os.environ.get("REFERENCIAS_PERFIS") or "pablospyer,falecomrian,shimoncomunica").split(",")
               if p.strip())
GRAPH = "https://graph.facebook.com/v21.0"
DIAS = int(os.environ.get("REFERENCIAS_DIAS") or "3")  # só o que saiu nos últimos dias
MAX_PAUTAS_DIA = 3  # pautas que as referências mandam ao Plantão por dia (o tema do editor não tem limite lá)
MAX_NOTAS = 15  # o diário de referências no manual fica curto (entra nas instruções dos agentes)
ARQ_MANUAL = config.MANUAIS / "referencias.md"
MARCA_DIARIO = "## Diário de referências (atualizado pelo robô)"

SISTEMA = f"""Você é o analista de referências do "{config.NOME}". Recebe a legenda e a transcrição de um Reel de um
criador de conteúdo de finanças que o dono admira, e explica o que faz o vídeo funcionar, para o nosso Roteirista
aprender a técnica (nunca para copiar).

Regras:
1. Escreva com as suas palavras. Nunca copie frases do criador: no máximo uma expressão curta (até 6 palavras) entre aspas.
2. Técnicas, não conteúdo: gancho, estrutura, ritmo, prova na tela, tom, gesto, chamada final.
3. Nada de opinião sobre o criador, nem sobre investimento. Não repita recomendações de compra que ele tenha feito.
4. "pauta": só se o vídeo trata de uma notícia de dinheiro do momento (fato do dia ou da semana) que interessa ao
   leigo brasileiro. Escreva a pauta como um fato a conferir ("O que se sabe sobre X"), não como opinião. Se o vídeo é
   atemporal, educativo ou opinião, deixe vazio.
5. "ja_coberto": verdadeiro se a pauta já está entre os títulos que publicamos (lista no pedido)."""
SISTEMA += config.manual("marca")


def ferramenta() -> dict:
    return {"name": "registrar_analise", "description": "A análise do Reel de referência.",
            "input_schema": {"type": "object", "required": ["tema", "gancho", "tecnicas", "formato", "pauta", "ja_coberto"],
                             "properties": {
                                 "tema": {"type": "string", "description": "O assunto, em uma frase curta."},
                                 "gancho": {"type": "string", "description": "Como o vídeo prende nos 3 primeiros segundos (a técnica)."},
                                 "tecnicas": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
                                 "formato": {"type": "string", "description": "Cenário, enquadramento, duração aproximada, texto na tela."},
                                 "pauta": {"type": "string"},
                                 "ja_coberto": {"type": "boolean"}}}}


# ---------------------------------------------------------------- Instagram (API oficial)

def posts(perfil: str, token: str, conta: str, buscar=requests.get) -> list[dict]:
    campos = (f"business_discovery.username({perfil}){{media.limit(8){{id,caption,media_type,media_product_type,permalink,"
              "timestamp,media_url}}")
    r = buscar(f"{GRAPH}/{conta}", params={"fields": campos, "access_token": token}, timeout=60)
    r.raise_for_status()
    return (((r.json().get("business_discovery") or {}).get("media") or {}).get("data")) or []


def baixar(url: str, destino: Path, buscar=requests.get) -> Path:
    r = buscar(url, timeout=120)
    r.raise_for_status()
    destino.write_bytes(r.content)
    return destino


def transcrever(video: Path) -> str:
    """Transcrição em português no próprio robô (faster-whisper, modelo pequeno, CPU). Sem ele, segue só a legenda."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return ""
    modelo = WhisperModel(os.environ.get("WHISPER_MODELO") or "small", device="cpu", compute_type="int8")
    trechos, _ = modelo.transcribe(str(video), language="pt", vad_filter=True)
    return " ".join(t.text.strip() for t in trechos)


# ---------------------------------------------------------------- análise e registro

def vistos(pasta: Path) -> dict:
    arq = pasta / "vistos.json"
    return json.loads(arq.read_text()) if arq.exists() else {}


def titulos_publicados(diario: Path, dias: int = 10) -> list[str]:
    limite = (pd.Timestamp.now(tz="America/Sao_Paulo") - pd.Timedelta(days=dias)).strftime("%Y-%m-%d")
    saida = []
    for arq in sorted((diario / "plantao").glob("20*.json")):
        if arq.name[:10] >= limite:
            saida.append(json.loads(arq.read_text()).get("titulo", ""))
    return saida


def analisar(cliente, perfil: str, legenda: str, transcricao: str, titulos: list[str]) -> dict:
    pedido = (f"Criador: @{perfil}\n\nLEGENDA:\n{legenda[:2500] or '(sem legenda)'}\n\nTRANSCRIÇÃO DO ÁUDIO:\n"
              f"{transcricao[:6000] or '(sem áudio transcrito; analise pela legenda)'}\n\nTÍTULOS QUE JÁ PUBLICAMOS "
              f"(últimos dias):\n" + "\n".join(f"- {t}" for t in titulos))
    return ia.estruturado(cliente, SISTEMA, pedido, ferramenta(), max_tokens=2000) or {}


def nota(perfil: str, post: dict, a: dict) -> str:
    dia = str(post.get("timestamp", ""))[:10]
    tecnicas = "; ".join(a.get("tecnicas") or [])
    return (f"- {dia} · @{perfil} · {a.get('tema', '').strip()}. Gancho: {a.get('gancho', '').strip()} "
            f"Técnicas: {tecnicas}. Formato: {a.get('formato', '').strip()} ({post.get('permalink', '')})")


def atualizar_manual(notas_novas: list[str], arq: Path = ARQ_MANUAL) -> None:
    """Põe as notas novas no topo do diário e guarda só as últimas MAX_NOTAS."""
    texto = arq.read_text() if arq.exists() else "# Referências de conteúdo\n"
    if MARCA_DIARIO not in texto:
        texto = texto.rstrip() + f"\n\n{MARCA_DIARIO}\n"
    cabeca, diario = texto.split(MARCA_DIARIO, 1)
    antigas = [li for li in diario.strip().splitlines() if li.startswith("- ")]
    linhas = (notas_novas + antigas)[:MAX_NOTAS]
    arq.write_text(f"{cabeca.rstrip()}\n\n{MARCA_DIARIO}\n" + "\n".join(linhas) + "\n")


def rodar(diario: Path, pasta: Path, cliente=None, buscar=requests.get, transcritor=transcrever) -> dict:
    """Analisa os Reels novos. Devolve {"notas": [...], "pautas": [...]} (as pautas vão para o Plantão no workflow)."""
    token, conta = os.environ.get("IG_TOKEN", "").strip(), os.environ.get("IG_USER_ID", "").strip()
    if not token or not conta:
        print("Referências: falta IG_TOKEN ou IG_USER_ID nos secrets; nada a fazer.")
        return {"notas": [], "pautas": []}
    if cliente is None and not ia.disponivel():
        print("Referências: sem chave de IA, nada a fazer.")
        return {"notas": [], "pautas": []}
    cliente = cliente or ia.novo_cliente()
    pasta.mkdir(parents=True, exist_ok=True)
    ja, titulos = vistos(pasta), titulos_publicados(diario)
    limite = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=DIAS)
    notas, pautas = [], []
    hoje = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
    vagas = MAX_PAUTAS_DIA - sum(1 for v in ja.values() if v.get("pauta_enviada") == hoje)
    for perfil in PERFIS:
        try:
            lista = posts(perfil, token, conta, buscar)
        except Exception as erro:  # noqa: BLE001 — um perfil fora do ar não para os outros
            print(f"  @{perfil}: não consegui ler ({str(erro)[:100]})")
            continue
        for post in lista:
            quando = pd.Timestamp(post.get("timestamp", "1970-01-01T00:00:00+0000"))
            if post.get("id") in ja or quando < limite:
                continue
            transcricao = ""
            if post.get("media_type") == "VIDEO" and post.get("media_url"):
                with tempfile.TemporaryDirectory() as tmp:
                    try:
                        transcricao = transcritor(baixar(post["media_url"], Path(tmp) / "reel.mp4", buscar))
                    except Exception as erro:  # noqa: BLE001 — sem áudio, analisa pela legenda
                        print(f"  @{perfil}: sem transcrição ({str(erro)[:80]})")
            a = analisar(cliente, perfil, post.get("caption") or "", transcricao, titulos)
            if not a.get("tema"):
                continue
            notas.append(nota(perfil, post, a))
            pauta = (a.get("pauta") or "").strip()
            enviar = (pauta and not a.get("ja_coberto") and len(pautas) < vagas
                      and not re.search(r"\b(compre|venda|invista)\b", pauta, re.IGNORECASE))
            ja[post["id"]] = {"perfil": perfil, "link": post.get("permalink", ""), "dia": str(quando.date()),
                              "pauta": pauta}  # só o link e a nossa pauta: nada do texto do criador
            if enviar:
                pautas.append(pauta)
                titulos.append(pauta)  # o mesmo assunto em outro criador conta como já coberto
                ja[post["id"]]["pauta_enviada"] = hoje
            print(f"  @{perfil} {quando.date()}: {a['tema']}" + (f" → pauta: {pauta}" if pauta else ""))
    if notas:
        atualizar_manual(notas)
    (pasta / "vistos.json").write_text(json.dumps(ja, ensure_ascii=False, indent=1))
    return {"notas": notas, "pautas": pautas}
