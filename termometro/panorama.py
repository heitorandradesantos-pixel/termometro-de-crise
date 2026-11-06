"""Panorama do fim de tarde: o texto curto que vai para o canal do WhatsApp todo dia útil.

O texto é montado pelo programa (não pela IA) a partir dos números do motor mundial e das
notícias já conferidas do Correspondente. Assim nenhum número sai diferente do site.
"""

import re

import pandas as pd

from . import bcb, config
from .correspondente import todas_as_noticias
from .revisor import linguagem_proibida

EMOJI = {"Calmaria": "🔵", "Atenção": "🟦", "Alerta": "🟡", "Tensão": "🟠", "Crise": "🔴"}
AVISO_CURTO = "Conteúdo educativo, com fonte em cada fato. Não é recomendação de investimento."
LIMITE = 1600
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MARCOS_POR_SEMANA = 3  # decisão do conselho (consulta #17): no máximo 1 por mensagem e 3 por semana


def _seta(agora, antes, quando: str = "") -> str:
    """Variação desde o panorama anterior: " (▲4 desde 04/11)"."""
    if agora is None or antes is None:
        return ""
    d, desde = agora - antes, f" desde {quando}" if quando else ""
    return f" (▲{d}{desde})" if d > 0 else (f" (▼{-d}{desde})" if d < 0 else f" (estável{desde})")


def marco(mundo: dict, anteriores: list[dict], recentes: list[str] | None = None) -> str:
    """Um marco do próprio termômetro, com frase fixa e conferível. Nunca de preço de terceiros.

    anteriores: os mundo.json dos dias úteis anteriores, do mais antigo ao mais recente.
    recentes: os textos dos últimos panoramas, para não passar de MARCOS_POR_SEMANA."""
    if not anteriores or sum("📍" in t for t in (recentes or [])[-4:]) >= MARCOS_POR_SEMANA:
        return ""
    def nivel(m: dict, quem: str):
        if quem in ("mundo", "brasil"):
            return (m.get(quem) or {}).get("nivel")
        return next((r.get("nivel") for r in m.get("regioes", []) if r["nome"] == quem), None)
    ontem = anteriores[-1]
    for quem, nome in (("brasil", "O Brasil"), ("mundo", "O termômetro do mundo")):
        agora, antes = nivel(mundo, quem), nivel(ontem, quem)
        if agora and antes and agora != antes:
            return f"📍 {nome} mudou de faixa: de {antes} para {agora}."
    for r in sorted(mundo.get("regioes", []), key=lambda r: -(r.get("valor") or 0)):
        antes = nivel(ontem, r["nome"])
        if r.get("nivel") and antes and r["nivel"] != antes:
            return f"📍 {r['nome']} mudou de faixa: de {antes} para {r['nivel']}."
    for quem, nome in (("brasil", "O Brasil"), ("mundo", "O termômetro do mundo")):
        agora = nivel(mundo, quem)
        if agora not in ("Tensão", "Crise"):
            continue
        dias = 1
        for m in reversed(anteriores):
            if nivel(m, quem) != agora:
                break
            dias += 1
        if dias >= 3:
            return f"📍 {nome} está há {dias} dias úteis seguidos em {agora}."
    return ""


def montar(mundo: dict, correspondente: dict | None, anterior: dict | None, data: str,
           noticias: list | None = None, bc: dict | None = None, destaque: str = "", com_focus: bool = True) -> str:
    """Panorama v2 (consulta #17): uma mensagem, horário do dado, resumo, regiões, Brasil com Banco Central,
    notícias com fonte no site, um link só e o aviso. Sem opinião, sem cotação de terceiros."""
    antes_regiao = {r["nome"]: r.get("valor") for r in (anterior or {}).get("regioes", [])}
    m, b = mundo.get("mundo") or {}, mundo.get("brasil") or {}
    quando = f"{pd.Timestamp(anterior['_data']):%d/%m}" if (anterior or {}).get("_data") else ""
    dia = pd.Timestamp(data)
    linhas = [f"*TERMÔMETRO DE CRISE · Panorama de {DIAS[dia.weekday()]}, {dia:%d/%m}*",
              f"_Fechamento de {dia:%d/%m} · de 0 (calmo) a 100 (mais tenso da história)_", ""]
    regioes = sorted((r for r in mundo.get("regioes", []) if r.get("valor") is not None), key=lambda r: -r["valor"])
    if m.get("valor") is not None:
        topo = f" Mais tenso: {regioes[0]['nome']} ({regioes[0]['valor']})." if regioes else ""
        linhas.append(f"🌍 Mundo em *{m['valor']}, {m['nivel']}*"
                      f"{_seta(m['valor'], ((anterior or {}).get('mundo') or {}).get('valor'), quando)}.{topo}")
    if destaque:
        linhas.append(destaque)
    if regioes:
        linhas += ["", "*Regiões*"]
        linhas += [f"{EMOJI.get(r['nivel'], '•')} {r['nome']}: {r['valor']} · {r['nivel']}"
                   f"{_seta(r['valor'], antes_regiao.get(r['nome']))}" for r in regioes]
    if b.get("valor") is not None:
        s = b.get("sinais", {})
        nomes = {"bolsa": "Bolsa", "volatilidade": "Sobe e desce", "moeda": "Dólar"}
        linhas += ["", f"🇧🇷 *Brasil: {b['valor']} · {b['nivel']}*"
                   f"{_seta(b['valor'], ((anterior or {}).get('brasil') or {}).get('valor'), quando)}"]
        detalhe = " · ".join(f"{nomes[k]} {s[k]}" for k in nomes if s.get(k) is not None)
        if detalhe:
            linhas.append(detalhe)
    if bc is not None:
        linha_bc = bcb.linha(bc if com_focus else {k: v for k, v in bc.items() if not k.startswith("focus")}, data)
        if linha_bc:
            linhas.append(linha_bc)
    noticias = (todas_as_noticias(correspondente) or noticias or [])[:3]
    if noticias:
        linhas += ["", "*O que mexeu com o termômetro*"]
        linhas += [f"• {n['titulo']} ({n['regiao']})" for n in noticias]
    site = config.SITE_URL or "https://termometrodecrise.com"
    linhas += ["", f"Veja o porquê de cada número, com as fontes: {site}/panorama.html?utm_source=whatsapp"
               "&utm_campaign=panorama", "", f"_{AVISO_CURTO}_"]
    texto = "\n".join(linhas)
    if len(texto) > LIMITE and noticias:  # corta notícias antes de cortar números
        return montar(mundo, None, anterior, data, noticias=noticias[:-1], bc=bc, destaque=destaque, com_focus=com_focus)
    if len(texto) > LIMITE and com_focus and bc:
        return montar(mundo, None, anterior, data, noticias=[], bc=bc, destaque=destaque, com_focus=False)
    return texto


def checar(texto: str, mundo: dict, bc: dict | None = None) -> dict:
    """Confere o panorama antes de sair: números iguais ao motor e ao Banco Central, aviso, tamanho e linguagem."""
    problemas = []
    m = mundo.get("mundo") or {}
    if m.get("valor") is not None and f"Mundo em *{m['valor']}, {m['nivel']}*" not in texto:
        problemas.append("número do mundo diferente do motor")
    b = mundo.get("brasil") or {}
    if b.get("valor") is not None and f"Brasil: {b['valor']} · {b['nivel']}" not in texto:
        problemas.append("número do Brasil diferente do motor")
    if bc and bc.get("selic") and f"Selic {bcb._num(bc['selic']['valor'])}%" not in texto:
        problemas.append("Selic diferente do Banco Central")
    if bc and bc.get("ptax") and f"R$ {bcb._num(bc['ptax']['valor'], 4)}" not in texto:
        problemas.append("PTAX diferente do Banco Central")
    for linha_marco in (x for x in texto.splitlines() if x.startswith("📍")):
        if not re.fullmatch(r"📍 .+ (mudou de faixa: de \w+ para \w+|está há \d+ dias úteis seguidos em \w+)\.", linha_marco):
            problemas.append("marco fora das frases fixas")
    for r in mundo.get("regioes", []):
        if r.get("valor") is not None and f"{r['nome']}: {r['valor']} ·" not in texto:
            problemas.append(f"número de {r['nome']} diferente do motor")
    if AVISO_CURTO not in texto:
        problemas.append("sem aviso")
    if len(texto) > LIMITE:
        problemas.append(f"texto longo ({len(texto)} caracteres)")
    proibido = linguagem_proibida(texto)
    if proibido:
        problemas.append("linguagem: " + ", ".join(proibido))
    return {"aprovado": not problemas, "problemas": problemas}
