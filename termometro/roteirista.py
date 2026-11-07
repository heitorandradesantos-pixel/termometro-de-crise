"""Roteirista: transforma o material conferido do dia em roteiro de Reel (Instagram, TikTok, Shorts) de 45 a 60 s.

Três tipos: "abertura" (a mensagem da Abertura no WhatsApp), "fechamento" (o balanço e o panorama do dia) e
"explica" (um artigo do Plantão). O vídeo não cria fato: cada número falado tem de estar no material. O programa
confere tudo (tamanho, números, linguagem proibida, vícios de texto de máquina, gancho) e, se algo falhar, pede
uma segunda versão dizendo o que corrigir. A assinatura da apresentadora e o fecho com o aviso são postos pelo
programa, nunca pela IA.

Grava diario/AAAA-MM-DD/roteiros/<tipo>[-slug].json, que a esteira de vídeo (voz e avatar) usa depois.
"""

import json
import os
import re
from pathlib import Path

import pandas as pd

from . import config, ia
from .revisor import linguagem_proibida

PERSONA = os.environ.get("PERSONA_NOME") or "Clara"
ASSINATURA = f"Aqui é a {PERSONA}, com o Termômetro de Crise."
FECHO = "Isso não é recomendação: é o termômetro."
CHAMADAS = {"grupo": "O grupo do WhatsApp está no link da bio.",
            "newsletter": "O Termômetro da Semana chega por e-mail: link na bio."}
AVISO_LEGENDA = "Conteúdo educativo, não é recomendação de investimento."
PALAVRAS_POR_MINUTO = 150
PALAVRAS = (105, 160)  # 42 a 64 segundos falados, contando assinatura e fecho
MAXIMO_FALA = 18  # palavras por fala (uma respiração)
NOTA_MINIMA = 7

VICIOS = [  # palavras que entregam texto de máquina (manual "roteiro")
    r"\bmergulh", r"\bdesvend", r"\bjornada\b", r"\balavanc", r"\bpotencializ", r"\brobust",
    r"cen[áa]rio atual", r"no mundo de hoje", r"vale (a pena )?ressaltar", r"[ée] importante (destacar|notar|ressaltar)",
    r"\bem suma\b", r"\bem resumo\b", r"sem mais delongas", r"n[ãa]o [ée] (s[óo]|apenas) .{1,40}, [ée] ", "—",
]
TIPOS = {
    "abertura": "Reel da Abertura (de manhã, logo depois que a B3 abre): como o mundo amanheceu, como o Brasil abriu "
                "e o que observar hoje.",
    "fechamento": "Reel do Fechamento (fim da tarde): o número do dia, o porquê com a fonte, onde está o termômetro "
                  "do Brasil e do mundo e o que fica para amanhã.",
    "explica": "Reel Explica: a notícia de dinheiro do dia explicada (o que se sabe, por que importa para o bolso, "
               "o que ainda não se sabe e como se proteger, sem recomendar investimento).",
}

SISTEMA = f"""Você é o Roteirista do "{config.NOME}", um portal financeiro brasileiro para leigos. Escreve o que a
{PERSONA}, apresentadora virtual do {config.NOME}, fala em vídeos verticais de 45 a 60 segundos.

O programa põe sozinho, depois do gancho, a assinatura "{ASSINATURA}" e, no fim, o fecho "{FECHO}" com a chamada
para o link da bio. Você escreve só o gancho (3 opções, com nota) e o corpo, mais o texto da tela e a legenda.

Regras:
1. Todo número que você escrever tem de estar no material, escrito do mesmo jeito (vírgula decimal, ponto de milhar).
   Número que não está no material não entra. Prefira poucos números: 2 ou 3 bem escolhidos valem mais que 8.
2. Uma ideia por vídeo. Corpo entre 7 e 12 falas, cada uma com 4 a 15 palavras.
3. Nada de recomendação, previsão, alarmismo, política partidária ou opinião sobre governo.
4. Escreva para o ouvido: frases que se dizem em voz alta, para uma pessoa ("você").
5. No texto da tela, a fonte é a original: "Yahoo Finance" para cotações, "Banco Central" para Selic, PTAX e Focus,
   "Termômetro de Crise" para as leituras do termômetro e o nome do veículo para as notícias."""
SISTEMA += config.manual("roteiro", "redacao")


def ferramenta() -> dict:
    nota = {"type": "integer", "minimum": 0, "maximum": 2}
    return {"name": "registrar_roteiro", "description": "O roteiro do Reel, pronto para a voz e o avatar.",
            "input_schema": {"type": "object", "required": ["ganchos", "gancho_escolhido", "falas", "retomada",
                                                            "na_tela", "busca", "legenda", "hashtags"],
                             "properties": {
                "ganchos": {"type": "array", "minItems": 3, "maxItems": 3, "items": {
                    "type": "object", "required": ["formula", "texto", "na_tela", "nota"],
                    "properties": {"formula": {"type": "string"},
                                   "texto": {"type": "string", "description": "A primeira frase falada, até 15 palavras."},
                                   "na_tela": {"type": "string", "description": "Até 6 palavras."},
                                   "nota": {"type": "object", "required": ["especifico", "tensao", "espectador",
                                                                           "rapido", "verdadeiro"],
                                            "properties": {k: nota for k in ("especifico", "tensao", "espectador",
                                                                             "rapido", "verdadeiro")}}}}},
                "gancho_escolhido": {"type": "integer", "minimum": 0, "maximum": 2},
                "falas": {"type": "array", "minItems": 5, "maxItems": 14, "items": {"type": "string"},
                          "description": "O corpo, uma frase por fala, sem o gancho, sem assinatura e sem fecho."},
                "retomada": {"type": "integer", "description": "Índice (a partir de 0) da fala que reacende a atenção."},
                "na_tela": {"type": "array", "maxItems": 12, "items": {
                    "type": "object", "required": ["fala", "texto"],
                    "properties": {"fala": {"type": "integer"}, "texto": {"type": "string"},
                                   "fonte": {"type": "string"}}}},
                "busca": {"type": "string", "description": "A busca que a pessoa faz (\"dólar hoje\"), para a 1ª linha."},
                "legenda": {"type": "string", "description": "A legenda do post, até 1.500 caracteres, sem hashtags."},
                "hashtags": {"type": "array", "minItems": 3, "maxItems": 5, "items": {"type": "string"}}}}}


def _palavras(texto: str) -> int:
    return len(re.findall(r"\w+(?:[.,]\d+)*", texto))


def _numeros(texto: str) -> set[str]:
    """Os números de um texto, do jeito que se escrevem (168.501; 1,39; 5,51; 2027)."""
    return {n.rstrip(".,") for n in re.findall(r"\d[\d.,]*", texto)}


def permitidos(material: str) -> set[str]:
    """Números que o roteiro pode usar: os do material, com e sem casas decimais finais."""
    saida = set()
    for n in _numeros(material):
        saida.add(n)
        if "," in n:  # 1,50 também vale como 1,5 (só zeros à direita; nada de arredondar)
            saida.add(n.rstrip("0").rstrip(","))
    return saida


def _sem_acento(t: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def nota(gancho: dict) -> int:
    return sum(int(v) for v in (gancho.get("nota") or {}).values())


def montar(bruto: dict, chamada: str = "grupo") -> dict:
    """O roteiro final: gancho, assinatura, corpo, fecho e chamada."""
    ganchos = bruto.get("ganchos") or []
    i = bruto.get("gancho_escolhido", 0)
    gancho = ganchos[i] if 0 <= i < len(ganchos) else (ganchos[0] if ganchos else {"texto": "", "na_tela": ""})
    falas = [f.strip() for f in bruto.get("falas") or [] if f.strip()]
    linhas = [gancho["texto"].strip(), ASSINATURA, *falas, FECHO, CHAMADAS.get(chamada, CHAMADAS["grupo"])]
    texto = " ".join(linhas)
    hashtags = ["#" + _sem_acento(h.lstrip("#").replace(" ", "")).lower() for h in bruto.get("hashtags") or []][:5]
    legenda = (bruto.get("legenda") or "").replace("\\n", "\n").strip()  # \n escrito como texto vira quebra
    if AVISO_LEGENDA not in legenda:
        legenda = f"{legenda}\n\n{AVISO_LEGENDA}"
    return {"gancho": gancho, "ganchos": ganchos, "linhas": linhas, "texto_falado": texto,
            "palavras": _palavras(texto), "segundos": round(_palavras(texto) / PALAVRAS_POR_MINUTO * 60),
            "na_tela": [{"texto": gancho.get("na_tela", ""), "fala": 0}]
                       + [{**t, "fala": int(t.get("fala", 0)) + 2} for t in bruto.get("na_tela") or []],
            "retomada": int(bruto.get("retomada", 0)) + 2, "busca": (bruto.get("busca") or "").strip(),
            "legenda": legenda + ("\n\n" + " ".join(hashtags) if hashtags else ""), "hashtags": hashtags}


def conferir(r: dict, material: str) -> list[str]:
    """O que impede o roteiro de ir para a voz. Lista vazia = aprovado."""
    problemas = []
    if not (PALAVRAS[0] <= r["palavras"] <= PALAVRAS[1]):
        problemas.append(f"tamanho: {r['palavras']} palavras faladas (precisa de {PALAVRAS[0]} a {PALAVRAS[1]}, "
                         f"45 a 60 segundos)")
    if nota(r["gancho"]) < NOTA_MINIMA:
        problemas.append(f"gancho fraco: nota {nota(r['gancho'])}/10 (mínimo {NOTA_MINIMA})")
    if _palavras(r["gancho"].get("texto", "")) > 15:
        problemas.append("gancho com mais de 15 palavras")
    longas = [f for f in r["linhas"] if _palavras(f) > MAXIMO_FALA]
    if longas:
        problemas.append(f"falas longas demais (mais de {MAXIMO_FALA} palavras): " + " | ".join(longas[:3]))
    soltos = sorted(_numeros(r["texto_falado"] + " " + " ".join(t.get("texto", "") for t in r["na_tela"]))
                    - permitidos(material))
    if soltos:
        problemas.append("números que não estão no material: " + ", ".join(soltos))
    proibidas = linguagem_proibida(r["texto_falado"] + "\n" + r["legenda"])
    if proibidas:
        problemas.append("linguagem proibida: " + ", ".join(proibidas))
    vicios = [v for v in VICIOS if re.search(v, r["texto_falado"] + " " + r["legenda"], re.I)]
    if vicios:
        problemas.append("vícios de texto de máquina: " + ", ".join(v.strip("\\b") for v in vicios))
    if len(r["legenda"]) > 2200:
        problemas.append("legenda passa de 2.200 caracteres (limite do Instagram)")
    if not 3 <= len(r["hashtags"]) <= 5:
        problemas.append("use de 3 a 5 hashtags")
    return problemas


def escrever(cliente, tipo: str, material: str, chamada: str = "grupo") -> dict:
    """Pede o roteiro; se a conferência reprovar, pede uma segunda versão com a lista do que corrigir."""
    pedido = (f"Tipo de vídeo: {TIPOS[tipo]}\nChamada do fim (o programa põe): {CHAMADAS.get(chamada)}\n\n"
              f"MATERIAL CONFERIDO (a única fonte de números e fatos):\n{material}")
    problemas = []
    for tentativa in range(2):
        texto = pedido if not problemas else (
            pedido + "\n\nA VERSÃO ANTERIOR FOI REPROVADA NA CONFERÊNCIA. Corrija exatamente isto:\n- "
            + "\n- ".join(problemas))
        r = montar(ia.estruturado(cliente, SISTEMA, texto, ferramenta(), max_tokens=4000), chamada)
        problemas = conferir(r, material)
        if not problemas:
            break
    return {**r, "tipo": tipo, "persona": PERSONA, "aprovado": not problemas, "problemas": problemas,
            "tentativas": tentativa + 1}


# ---------------------------------------------------------------- material

def material_envio(envio: dict) -> str:
    """A mensagem que foi para o WhatsApp (abertura ou fechamento): já conferida, com todos os números."""
    return "\n\n".join(t for t in [envio.get("legenda", ""), *envio.get("textos", [])] if t).strip()


def material_artigo(a: dict) -> str:
    fatos = "\n".join(f"- {f['texto']} (fonte: {f.get('veiculo', '')})" for f in a.get("o_que_se_sabe", []))
    nao = "\n".join(f"- {t}" for t in a.get("o_que_nao_se_sabe", []))
    muda = "\n".join(f"- {t}" for t in a.get("o_que_muda_para_voce", []))
    proteger = "\n".join(f"- {t}" for t in a.get("como_se_proteger", []))
    return (f"Título: {a['titulo']}\nResumo: {a.get('lead', '')}\n\nO que se sabe:\n{fatos}\n\nO que ainda não se sabe:\n"
            f"{nao or '- (nada listado)'}\n\nO que muda para você:\n{muda or '-'}\n\nComo se proteger:\n{proteger or '-'}")


def gravar(diario: Path, dia: str, roteiro: dict, nome: str) -> Path:
    destino = diario / dia / "roteiros" / f"{nome}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    roteiro = {**roteiro, "data": dia, "gerado_em": pd.Timestamp.now(tz="America/Sao_Paulo").isoformat()}
    destino.write_text(json.dumps(roteiro, ensure_ascii=False, indent=1))
    return destino


def rodar(diario: Path, tipo: str, pasta_envio: Path | None = None, dia: str = "", cliente=None) -> list[Path]:
    """Gera o(s) roteiro(s) do tipo pedido. Devolve os arquivos gravados (aprovados ou não, com os problemas)."""
    if cliente is None and not ia.disponivel():
        print("Roteirista: sem chave de IA, nada a fazer.")
        return []
    chamada = "newsletter" if os.environ.get("NEWSLETTER_ATIVA") == "sim" and tipo == "fechamento" else "grupo"
    trabalhos = []  # (dia, nome, material)
    if tipo in ("abertura", "fechamento"):
        arq = (pasta_envio or Path("_whatsapp")) / "envio.json"
        if not arq.exists():
            print(f"Roteirista: sem a mensagem da {tipo} preparada ({arq}); nada a fazer.")
            return []
        envio = json.loads(arq.read_text())
        if envio.get("tipo", "fechamento") != tipo:
            print(f"Roteirista: a mensagem preparada é de {envio.get('tipo')}, não de {tipo}.")
            return []
        trabalhos.append((envio["dia"], tipo, material_envio(envio)))
    else:
        dia = dia or pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
        for a in sorted((diario / "plantao").glob(f"{dia}-*.json")):
            if (diario / dia / "roteiros" / f"explica-{a.stem[11:]}.json").exists():
                continue  # já tem roteiro
            artigo = json.loads(a.read_text())
            trabalhos.append((dia, f"explica-{artigo['slug']}", material_artigo(artigo)))
    if not trabalhos:
        print("Roteirista: nada novo para roteirizar.")
        return []
    cliente = cliente or ia.novo_cliente()
    gravados = []
    for d, nome, material in trabalhos:
        r = escrever(cliente, "explica" if nome.startswith("explica") else tipo, material, chamada)
        gravados.append(gravar(diario, d, r, nome))
        estado = "aprovado" if r["aprovado"] else "reprovado: " + "; ".join(r["problemas"])
        print(f"  roteiro {nome} ({r['segundos']} s, gancho {nota(r['gancho'])}/10): {estado}")
    return gravados
