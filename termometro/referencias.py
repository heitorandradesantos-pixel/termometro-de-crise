"""Referências: 6 vezes por dia, o robô olha os Reels novos dos criadores que o Heitor acompanha (Pablo Spyer, Rian e
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

PERFIS = tuple(p.strip().lstrip("@") for p in (os.environ.get("REFERENCIAS_PERFIS") or "pablospyer,falecomrian,shimoncomunica,andreynousi").split(",")
               if p.strip())
GRAPH = "https://graph.facebook.com/v21.0"
DIAS = int(os.environ.get("REFERENCIAS_DIAS") or "3")  # só o que saiu nos últimos dias
MAX_PAUTAS_DIA = 2  # só notícia de relevância alta vira artigo; o resto vira ideia de Reel (pedido do Heitor, 09/11)
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
4. "relevancia": "alta" só para notícia de dinheiro do momento que mexe com muita gente ou com o mercado (juros,
   inflação, dólar, impostos, golpe em massa, empresa gigante, decisão do governo). Bastidor, fofoca, opinião, assunto
   educativo ou atemporal é "baixa" ou "media".
5. "pauta": preencha só quando a relevância é "alta". É um fato a conferir ("O que se sabe sobre X"), não opinião.
   Nos outros casos, deixe vazio. Na dúvida, deixe vazio: o artigo só sai quando vale muito a pena.
6. "ja_coberto": verdadeiro se a pauta já está entre os títulos que publicamos (lista no pedido).
7. "ideia_reel": um assunto que renderia um Reel nosso, com o ângulo do Termômetro (o que muda no bolso, com fonte),
   em 1 ou 2 frases. Vale para assunto educativo e atemporal também. Nunca o mesmo roteiro do criador. Se o vídeo
   é política, opinião ou não tem efeito no bolso, deixe vazio (não escreva "não serve" nem explique)."""
SISTEMA += config.manual("marca")


def ferramenta() -> dict:
    return {"name": "registrar_analise", "description": "A análise do Reel de referência.",
            # pauta e ideia podem ficar vazias de propósito: não entram como obrigatórias
            "input_schema": {"type": "object", "required": ["tema", "gancho", "tecnicas", "formato", "relevancia"],
                             "properties": {
                                 "tema": {"type": "string", "description": "O assunto, em uma frase curta."},
                                 "gancho": {"type": "string", "description": "Como o vídeo prende nos 3 primeiros segundos (a técnica)."},
                                 "tecnicas": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
                                 "formato": {"type": "string", "description": "Cenário, enquadramento, duração aproximada, texto na tela."},
                                 "relevancia": {"type": "string", "enum": ["alta", "media", "baixa"]},
                                 "pauta": {"type": "string"},
                                 "ja_coberto": {"type": "boolean"},
                                 "ideia_reel": {"type": "string"}}}}


# ---------------------------------------------------------------- Instagram (API oficial)

def posts(perfil: str, token: str, conta: str, buscar=requests.get) -> list[dict]:
    campos = (f"business_discovery.username({perfil}){{media.limit(8){{id,caption,media_type,media_product_type,permalink,"
              "timestamp,media_url}}")
    r = buscar(f"{GRAPH}/{conta}", params={"fields": campos, "access_token": token}, timeout=60)
    _conferir(r)
    return (((r.json().get("business_discovery") or {}).get("media") or {}).get("data")) or []


def _conferir(r) -> None:
    """Erro da API com a mensagem da Meta, sem o endereço (que leva o token)."""
    if getattr(r, "status_code", 200) >= 400:
        try:
            e = r.json().get("error", {})
        except ValueError:
            e = {}
        raise RuntimeError(f"HTTP {r.status_code}: {e.get('message', '')} (code {e.get('code')}, "
                           f"subcode {e.get('error_subcode')}, tipo {e.get('type')})")


def diagnostico(token: str, conta: str, buscar=requests.get) -> str:
    """Confere se o token enxerga a conta do Termômetro (ajuda a achar permissão ou Página faltando)."""
    saida = []
    for host in (GRAPH, GRAPH.replace("graph.facebook.com", "graph.instagram.com")):
        try:
            r = buscar(f"{host}/{conta}", params={"fields": "id,username", "access_token": token}, timeout=30)
            _conferir(r)
            saida.append(f"{host.split('/')[2]}: ok (@{r.json().get('username')})")
        except Exception as erro:  # noqa: BLE001
            saida.append(f"{host.split('/')[2]}: {str(erro)[:200]}")
    try:  # quais permissões o token tem de verdade (sem mostrar o token)
        r = buscar(f"{GRAPH}/debug_token", params={"input_token": token, "access_token": token}, timeout=30)
        _conferir(r)
        d = r.json().get("data", {})
        granular = "; ".join(f"{g.get('scope')}→{len(g.get('target_ids') or [])} alvo(s)" for g in d.get("granular_scopes", []))
        saida.append(f"tipo {d.get('type')}, app {d.get('application')}, válido {d.get('is_valid')}, "
                     f"permissões: {', '.join(d.get('scopes', []))} [{granular}]")
    except Exception as erro:  # noqa: BLE001
        saida.append(f"debug_token: {str(erro)[:200]}")
    try:
        r = buscar(f"{GRAPH}/me/accounts", params={"fields": "name,instagram_business_account", "access_token": token},
                   timeout=30)
        _conferir(r)
        saida.append("páginas: " + ", ".join(f"{p.get('name')} (insta: {'sim' if p.get('instagram_business_account') else 'não'})"
                                           for p in r.json().get("data", [])))
    except Exception as erro:  # noqa: BLE001
        saida.append(f"me/accounts: {str(erro)[:200]}")
    return " | ".join(saida)


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
    import subprocess

    import numpy as np
    # o áudio sai pelo ffmpeg do robô (o leitor de vídeo do faster-whisper quebrou com o av 15)
    bruto = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(video), "-f", "s16le", "-ac", "1",
                            "-ar", "16000", "-"], capture_output=True, check=True, timeout=300).stdout
    audio = np.frombuffer(bruto, np.int16).astype(np.float32) / 32768.0
    modelo = WhisperModel(os.environ.get("WHISPER_MODELO") or "small", device="cpu", compute_type="int8")
    trechos, _ = modelo.transcribe(audio, language="pt", vad_filter=True)
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


SEM_PAUTA = re.compile(r"^\W*(sem pauta|sem ideia|nenhum|nenhuma|vazio|n/?a|-+|não serve|nao serve|não vale|nao vale|"
                       r"não se aplica|nao se aplica|não há|nao ha|fora do escopo)\b|^\W*$", re.IGNORECASE)
_PALAVRAS_VAZIAS = {
    "sobre", "como", "para", "porque", "quando", "quanto", "qual", "quais", "isso", "essa", "esse", "este", "esta",
    "mostrar", "explicar", "reel", "nosso", "nossa", "seus", "suas", "você", "voce", "fonte", "bolso", "muda",
    "mudar", "pode", "com", "sem", "mais", "menos", "entre", "depois", "antes", "cada"
}


def _termos(texto: str) -> set[str]:
    return {p for p in re.findall(r"[a-záàâãéêíóôõúç0-9]{4,}", texto.lower()) if p not in _PALAVRAS_VAZIAS}


def _parecida(a: str, b: str) -> bool:
    """Duas ideias sobre o mesmo assunto (ex.: duas do FGC) contam como uma só no resumo."""
    ta, tb = _termos(a), _termos(b)
    return bool(ta and tb) and len(ta & tb) / min(len(ta), len(tb)) >= 0.35


def limpar_pauta(pauta: str) -> str:
    """O modelo às vezes escreve "Sem pauta: ..." no campo; isso é pauta vazia."""
    pauta = pauta.strip()
    return "" if SEM_PAUTA.search(pauta) else pauta


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
    if os.environ.get("REFERENCIAS_DIAGNOSTICO"):
        print("Diagnóstico do token:", diagnostico(token, conta, buscar))
    ja, titulos = vistos(pasta), titulos_publicados(diario)
    limite = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=DIAS)
    notas, pautas = [], []
    hoje = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
    vagas = MAX_PAUTAS_DIA - sum(1 for v in ja.values() if v.get("pauta_enviada") == hoje)
    for perfil in PERFIS:
        try:
            lista = posts(perfil, token, conta, buscar)
        except Exception as erro:  # noqa: BLE001 — um perfil fora do ar não para os outros
            print(f"  @{perfil}: não consegui ler ({str(erro)[:240]})")
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
            legenda = (post.get("caption") or "").strip()
            if not legenda and not transcricao:  # nada para analisar: tenta de novo na próxima leitura
                print(f"  @{perfil}: sem legenda e sem áudio transcrito; fica para a próxima")
                continue
            try:
                a = analisar(cliente, perfil, legenda, transcricao, titulos)
            except Exception as erro:  # noqa: BLE001 — um vídeo que não deu não para os outros
                print(f"  @{perfil}: análise falhou ({str(erro)[:120]}); fica para a próxima")
                continue
            if not a.get("tema"):
                continue
            notas.append(nota(perfil, post, a))
            pauta = limpar_pauta(a.get("pauta") or "")
            enviar = (pauta and a.get("relevancia") == "alta" and not a.get("ja_coberto") and len(pautas) < vagas
                      and not re.search(r"\b(compre|venda|invista)\b", pauta, re.IGNORECASE))
            ideia = limpar_pauta(a.get("ideia_reel") or "")
            ja[post["id"]] = {"perfil": perfil, "link": post.get("permalink", ""), "dia": str(quando.date()),
                              "pauta": pauta, "ideia_reel": ideia}  # só o link e a nossa análise, nada do criador
            if enviar:
                pautas.append(pauta)
                titulos.append(pauta)  # o mesmo assunto em outro criador conta como já coberto
                ja[post["id"]]["pauta_enviada"] = hoje
            print(f"  @{perfil} {quando.date()}: {a['tema']}" + (f" → pauta: {pauta}" if pauta else ""))
    if notas:
        atualizar_manual(notas)
    (pasta / "vistos.json").write_text(json.dumps(ja, ensure_ascii=False, indent=1))
    return {"notas": notas, "pautas": pautas}


def ideias_pendentes(pasta: Path, dias: int = 3) -> list[tuple[str, dict]]:
    """As ideias de Reel que ainda não foram para o WhatsApp do Heitor (as mais novas primeiro)."""
    limite = (pd.Timestamp.now(tz="America/Sao_Paulo") - pd.Timedelta(days=dias)).strftime("%Y-%m-%d")
    itens = [(k, v) for k, v in vistos(pasta).items()
             if v.get("ideia_reel") and not v.get("ideia_enviada") and v.get("dia", "") >= limite]
    return sorted(itens, key=lambda kv: kv[1].get("dia", ""), reverse=True)


def selecionar_ideias(itens: list[tuple[str, dict]], maximo: int = 6) -> tuple[list, list[str]]:
    """Tira ideias vazias, as do tipo "não serve" e as que repetem o assunto de outra; fica com até `maximo`.
    Devolve (escolhidas, chaves descartadas), para as descartadas não voltarem no resumo do dia seguinte."""
    escolhidas: list[tuple[str, dict]] = []
    descartadas: list[str] = []
    for k, v in itens:
        if len(escolhidas) >= maximo:
            break
        ideia = limpar_pauta(v.get("ideia_reel") or "")
        if ideia and not any(_parecida(ideia, e["ideia_reel"]) for _, e in escolhidas):
            escolhidas.append((k, v))
        else:
            descartadas.append(k)
    return escolhidas, descartadas


def sem_repetidas(itens: list[tuple[str, dict]], maximo: int = 6) -> list[tuple[str, dict]]:
    return selecionar_ideias(itens, maximo)[0]


def mensagem_ideias(itens: list[tuple[str, dict]], maximo: int = 6) -> str:
    linhas = [f"• {v['ideia_reel']} _(inspirado em @{v['perfil']})_" for _, v in sem_repetidas(itens, maximo)]
    return ("💡 IDEIAS DE REELS (das referências mais recentes)\n\nAssuntos que renderiam vídeo nosso, com o ângulo do "
            "Termômetro. Se quiser roteiro de algum, me pede.\n\n" + "\n".join(linhas))


def marcar_ideias(pasta: Path, chaves: list[str]) -> None:
    ja = vistos(pasta)
    hoje = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
    for k in chaves:
        if k in ja:
            ja[k]["ideia_enviada"] = hoje
    (pasta / "vistos.json").write_text(json.dumps(ja, ensure_ascii=False, indent=1))
