"""Edição de domingo no grupo do WhatsApp: piloto de 8 domingos, às 18h30 (conselho, issue #23).

Formato fixo, em 1 a 2 telas:
1. o termômetro do mundo e do Brasil, e quanto mudou desde a semana anterior;
2. o que vem na semana (os fatos do Plantão de domingo de manhã, que é sempre a agenda da semana, já conferidos);
3. commodities (fechamento de sexta) e cripto (bitcoin e ethereum, 7 dias, corte domingo 12h de Brasília), só com
   FDS_NUMEROS=sim e sempre com "Fonte: Yahoo Finance";
4. IA e tecnologia, só quando o Plantão da semana publicou um fato com fonte sobre isso;
5. um convite só: a newsletter.
FDS_MODO: "previa" (padrão: vai para a conversa do próprio número, para o Heitor aprovar), "grupo" ou "nao".
"""

import json
import os
import re
from pathlib import Path

import pandas as pd
import requests

from . import config
from .abertura import UA, _num
from .revisor import linguagem_proibida

FUSO = "America/Sao_Paulo"
COMMODITIES = [("Petróleo Brent", "BZ=F"), ("Ouro", "GC=F"), ("Soja", "ZS=F"), ("Milho", "ZC=F"), ("Café", "KC=F"),
               ("Açúcar", "SB=F")]
CRIPTO = [("Bitcoin", "BTC-USD"), ("Ethereum", "ETH-USD")]
IA_TECNOLOGIA = re.compile(r"\b(IA|inteligência artificial|OpenAI|ChatGPT|Nvidia|Anthropic|Gemini|chips?|semicondutor\w*|"
                           r"data centers?|big techs?)\b", re.IGNORECASE)
VAZIO = re.compile(r"primeiro pregão|não há pregão|calendário normal", re.IGNORECASE)  # não é agenda
AVISO = "_Conteúdo educativo, com fonte em cada fato. Não é recomendação de investimento._"


def modo() -> str:
    m = (os.environ.get("FDS_MODO") or "previa").strip().lower()
    return m if m in ("previa", "grupo", "nao") else "previa"


def com_numeros() -> bool:
    return (os.environ.get("FDS_NUMEROS") or "nao").strip().lower() == "sim"


def _var(v: float) -> str:
    return f"{'▲' if v > 0 else '▼' if v < 0 else '='}{_num(abs(v), 1)}%"


def _pontos(v: int) -> str:
    return f"{'▲' if v > 0 else '▼' if v < 0 else '='}{abs(v)}" if v else "estável"


# ---------------------------------------------------------------- 1. termômetro

def termometro_semana(pasta_diario: Path, dia: str) -> dict | None:
    """O último termômetro do mundo e do Brasil até o dia, e o de cerca de uma semana antes (para a variação)."""
    leituras = []
    for arq in sorted(pasta_diario.glob("20*/mundo.json")):
        d = arq.parent.name
        if d <= dia:
            m = json.loads(arq.read_text())
            if (m.get("mundo") or {}).get("valor") is not None:
                leituras.append((d, m))
    if not leituras:
        return None
    hoje_d, atual = leituras[-1]
    alvo = (pd.Timestamp(hoje_d) - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    antes = next(((d, m) for d, m in leituras if d >= alvo and d < hoje_d), None)
    return {"data": hoje_d, "mundo": atual["mundo"], "brasil": atual.get("brasil") or {},
            "antes": {"data": antes[0], "mundo": antes[1]["mundo"], "brasil": antes[1].get("brasil") or {}} if antes else None}


def bloco_termometro(t: dict) -> str:
    m, b = t["mundo"], t["brasil"]
    linha = f"🌡️ *Termômetro do mundo: {m['valor']} de 100 ({m['nivel']})*"
    if t["antes"]:
        a = t["antes"]
        dm = m["valor"] - a["mundo"]["valor"]
        linha += f"\nNa semana: {_pontos(dm)} (era {a['mundo']['valor']} em {pd.Timestamp(a['data']):%d/%m})."
        if b.get("valor") is not None and a["brasil"].get("valor") is not None:
            linha += f" Brasil: {b['valor']} ({b['nivel']}), {_pontos(b['valor'] - a['brasil']['valor'])}."
    elif b.get("valor") is not None:
        linha += f"\nBrasil: {b['valor']} de 100 ({b['nivel']})."
    return linha


# ---------------------------------------------------------------- 2. agenda e 4. IA (do Plantão, já conferido)

def _artigos(pasta_diario: Path, de: str, ate: str) -> list[dict]:
    saida = []
    for arq in sorted((pasta_diario / "plantao").glob("20*.json")):
        if de <= arq.name[:10] <= ate:
            saida.append(json.loads(arq.read_text()))
    return saida


def _frase(texto: str, limite: int = 150) -> str:
    primeira = re.split(r"(?<=[.!?])\s", texto.strip(), maxsplit=1)[0]
    return primeira if len(primeira) <= limite else primeira[:limite].rsplit(" ", 1)[0] + "…"


def _melhor(nova: str, velha: str) -> bool:
    """Entre duas frases do mesmo evento: a que traz data ou hora; empatando, a mais curta."""
    def tem_numero(t: str) -> bool:
        return bool(re.search(r"\d", t))
    if tem_numero(nova) != tem_numero(velha):
        return tem_numero(nova)
    return len(nova) < len(velha)


def agenda(pasta_diario: Path, dia: str) -> list[str]:
    """Os fatos do artigo da agenda da semana (Plantão de domingo de manhã), um por linha."""
    candidatos = [a for a in _artigos(pasta_diario, dia, dia)
                  if a.get("turno") == "manha" or re.search(r"semana|esperar", a.get("slug", ""))]
    if not candidatos:
        return []
    a = candidatos[0]
    fatos = sorted((f for f in a.get("o_que_se_sabe", []) + a.get("linha_do_tempo", [])
                    if f.get("texto") and (f.get("data") or "") >= dia and not VAZIO.search(f["texto"])),
                   key=lambda f: f["data"])
    itens: list[tuple[str, set, str]] = []  # (data, palavras, frase)
    for f in fatos:  # só o que ainda vai acontecer; o mesmo evento (fato e linha do tempo) entra uma vez, o mais curto
        frase = _frase(f["texto"])
        palavras = {w for w in re.findall(r"\w{4,}", frase.lower())}
        igual = next((i for i, (d, ps, _) in enumerate(itens)
                      if d == f["data"] and len(ps & palavras) >= 0.5 * min(len(ps), len(palavras))), None)
        if igual is None:
            itens.append((f["data"], palavras, frase))
        elif _melhor(frase, itens[igual][2]):
            itens[igual] = (f["data"], palavras, frase)
    return [frase for _, _, frase in itens][:4]


def ia_da_semana(pasta_diario: Path, dia: str) -> list[str]:
    de = (pd.Timestamp(dia) - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    achados = [a for a in _artigos(pasta_diario, de, dia)
               if IA_TECNOLOGIA.search(" ".join([a.get("titulo", ""), a.get("lead", ""), a.get("assunto", "")]))]
    return [_frase(a.get("lead") or a["titulo"]) for a in achados[:2]]


# ---------------------------------------------------------------- 3. commodities e cripto (Yahoo Finance)

def variacao_7d(simbolo: str, corte: pd.Timestamp, buscar=requests.get) -> dict | None:
    """Variação do último preço até o corte contra o preço de 7 dias antes (fechamentos diários; cripto, por hora)."""
    horario = simbolo.endswith("-USD")
    r = buscar(f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}", headers=UA, timeout=30,
               params={"range": "14d" if horario else "1mo", "interval": "1h" if horario else "1d"})
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    serie = pd.Series(res["indicators"]["quote"][0]["close"],
                      index=pd.to_datetime(res["timestamp"], unit="s", utc=True)).dropna()
    serie = serie[serie.index <= corte.tz_convert("UTC")]
    if serie.empty:
        return None
    ultimo_t, ultimo = serie.index[-1], float(serie.iloc[-1])
    antes = serie[serie.index <= ultimo_t - pd.Timedelta(days=7)]
    if antes.empty:
        return None
    return {"variacao_pct": (ultimo / float(antes.iloc[-1]) - 1) * 100, "quando": ultimo_t.tz_convert(FUSO).isoformat()}


def precos(dia: str, buscar=requests.get) -> dict:
    corte = pd.Timestamp(f"{dia} 12:00", tz=FUSO)
    saida = {"commodities": [], "cripto": [], "falhas": []}
    for grupo, itens in (("commodities", COMMODITIES), ("cripto", CRIPTO)):
        for nome, simbolo in itens:
            try:
                v = variacao_7d(simbolo, corte, buscar)
            except Exception as erro:  # noqa: BLE001 — um preço fora do ar só some da mensagem
                saida["falhas"].append(f"{nome}: {str(erro)[:80]}")
                continue
            if v:
                saida[grupo].append((nome, v["variacao_pct"]))
    return saida


def bloco_precos(p: dict) -> list[str]:
    blocos = []
    if p["commodities"]:
        blocos.append("🛢️ *Commodities na semana* (fechamento de sexta)\n"
                      + " · ".join(f"{n} {_var(v)}" for n, v in p["commodities"]) + "\n_Fonte: Yahoo Finance._")
    if p["cripto"]:
        blocos.append("₿ *Cripto em 7 dias* (até domingo, 12h de Brasília)\n"
                      + " · ".join(f"{n} {_var(v)}" for n, v in p["cripto"])
                      + "\n_Fonte: Yahoo Finance. Cripto oscila muito; não é recomendação._")
    return blocos


# ---------------------------------------------------------------- a mensagem

def montar(pasta_diario: Path, dia: str, numeros: bool, buscar=requests.get) -> dict | None:
    t = termometro_semana(pasta_diario, dia)
    if not t:
        return None
    partes = [f"*TERMÔMETRO DE CRISE · Domingo, {pd.Timestamp(dia):%d/%m}*\n_A semana em 1 minuto_", bloco_termometro(t)]
    itens = agenda(pasta_diario, dia)
    if itens:
        partes.append("📅 *O que vem na semana*\n" + "\n".join(f"• {i}" for i in itens))
    falhas = []
    if numeros:
        p = precos(dia, buscar)
        partes += bloco_precos(p)
        falhas = p["falhas"]
    ia = ia_da_semana(pasta_diario, dia)
    if ia:
        partes.append("🤖 *IA e tecnologia que mexem no bolso*\n" + "\n".join(f"• {i}" for i in ia))
    partes.append(f"📩 Toda semana, o resumo completo com o porquê de cada número chega por e-mail, de graça: "
                  f"{config.url_publica('newsletter/')}")
    partes.append(AVISO)
    texto = "\n\n".join(partes)
    return {"texto": texto, "proibido": linguagem_proibida(texto), "falhas": falhas}


def preparar(pasta_diario: Path, dia: str, pasta_saida: Path, buscar=requests.get) -> str:
    """Grava pasta_saida/envio.json. Na prévia vai para o próprio número, com os números ligados para o Heitor ver."""
    import shutil
    como = modo()
    if como == "nao":
        return "Edição de domingo desligada (FDS_MODO=nao)."
    if pd.Timestamp(dia).weekday() != 6:
        return f"{dia} não é domingo: sem edição de fim de semana."
    from .whatsapp import ja_enviado
    destino = "teste" if como == "previa" else "sim"
    if ja_enviado(pasta_diario / dia, "fimdesemana", destino):
        return f"A edição de domingo de {dia} já foi enviada ({como})."
    m = montar(pasta_diario, dia, numeros=com_numeros() or como == "previa", buscar=buscar)
    if not m:
        return f"Sem termômetro até {dia}: nada a enviar."
    if m["proibido"]:
        return f"Edição de domingo bloqueada: linguagem vetada ({', '.join(m['proibido'])})."
    if pasta_saida.exists():
        shutil.rmtree(pasta_saida)
    pasta_saida.mkdir(parents=True)
    textos = [m["texto"]]
    if como == "previa":
        textos.insert(0, "👀 PRÉVIA DA EDIÇÃO DE DOMINGO (só você está vendo). Os números de commodities e cripto "
                         "aparecem aqui para você decidir; no grupo eles só entram se você liberar.")
    envio = {"modo": destino, "dia": dia, "tipo": "fimdesemana", "textos": textos}
    (pasta_saida / "envio.json").write_text(json.dumps(envio, ensure_ascii=False, indent=1))
    extra = f" Preços fora do ar: {'; '.join(m['falhas'])}." if m["falhas"] else ""
    return f"Edição de domingo de {dia} pronta ({'prévia no próprio número' if como == 'previa' else 'grupo'}).{extra}"
