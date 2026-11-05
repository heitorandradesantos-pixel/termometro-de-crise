"""Panorama do fim de tarde: o texto curto que vai para o canal do WhatsApp todo dia útil.

O texto é montado pelo programa (não pela IA) a partir dos números do motor mundial e das
notícias já conferidas do Correspondente. Assim nenhum número sai diferente do site.
"""

import pandas as pd

from . import config
from .correspondente import todas_as_noticias
from .revisor import linguagem_proibida

EMOJI = {"Calmaria": "🔵", "Atenção": "🟦", "Alerta": "🟡", "Tensão": "🟠", "Crise": "🔴"}
AVISO_CURTO = "Conteúdo educativo. Não é recomendação de investimento."
LIMITE = 1500


def _seta(agora, antes, quando: str = "") -> str:
    """Variação desde o panorama anterior: " (▲4 desde 04/11)"."""
    if agora is None or antes is None:
        return ""
    d, desde = agora - antes, f" desde {quando}" if quando else ""
    return f" (▲{d}{desde})" if d > 0 else (f" (▼{-d}{desde})" if d < 0 else f" (estável{desde})")


def montar(mundo: dict, correspondente: dict | None, anterior: dict | None, data: str,
           noticias: list | None = None) -> str:
    antes_regiao = {r["nome"]: r.get("valor") for r in (anterior or {}).get("regioes", [])}
    m, b = mundo.get("mundo") or {}, mundo.get("brasil") or {}
    quando = f"{pd.Timestamp(anterior['_data']):%d/%m}" if (anterior or {}).get("_data") else ""
    linhas = [f"*TERMÔMETRO DE CRISE · Panorama de {pd.Timestamp(data):%d/%m}*", ""]
    if m.get("valor") is not None:
        linhas.append(f"🌍 *Mundo: {m['valor']}/100 · {m['nivel']}*"
                      f"{_seta(m['valor'], ((anterior or {}).get('mundo') or {}).get('valor'), quando)}")
        linhas.append("")
    regioes = sorted((r for r in mundo.get("regioes", []) if r.get("valor") is not None), key=lambda r: -r["valor"])
    for r in regioes:
        linhas.append(f"{EMOJI.get(r['nivel'], '•')} {r['nome']}: {r['valor']} · {r['nivel']}"
                      f"{_seta(r['valor'], antes_regiao.get(r['nome']))}")
    if b.get("valor") is not None:
        s = b.get("sinais", {})
        nomes = {"bolsa": "Bolsa", "volatilidade": "Sobe e desce", "moeda": "Dólar"}
        detalhe = " · ".join(f"{nomes[k]} {s[k]}" for k in nomes if s.get(k) is not None)
        linhas += ["", f"🇧🇷 *Brasil: {b['valor']} · {b['nivel']}*"
                   f"{_seta(b['valor'], ((anterior or {}).get('brasil') or {}).get('valor'), quando)}"]
        if detalhe:
            linhas.append(f"{detalhe} (0 = calmo, 100 = mais tenso da história)")
    noticias = (todas_as_noticias(correspondente) or noticias or [])[:3]
    if noticias:
        linhas += ["", "*O que mexeu com o termômetro*"]
        linhas += [f"• {n['titulo']} ({n['regiao']})" for n in noticias]
    site = config.SITE_URL or "https://termometrodecrise.com"
    linhas += ["", f"Toque na sua região e entenda o porquê: {site}", "", f"_{AVISO_CURTO}_"]
    texto = "\n".join(linhas)
    if len(texto) > LIMITE and noticias:  # corta notícias antes de cortar números
        return montar(mundo, None, anterior, data, noticias=noticias[:-1])
    return texto


def checar(texto: str, mundo: dict) -> dict:
    """Confere o panorama antes de sair: números iguais ao motor, aviso, tamanho e linguagem."""
    problemas = []
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
