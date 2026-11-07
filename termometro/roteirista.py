"""Roteirista: transforma o material conferido do dia em roteiro de Reel (Instagram, TikTok, Shorts) de 45 a 60 s.

Três tipos: "abertura" (a mensagem da Abertura no WhatsApp), "fechamento" (o balanço e o panorama do dia) e
"explica" (um artigo do Plantão). O vídeo não cria fato: cada número falado tem de estar no material. O programa
confere tudo (tamanho, números, linguagem proibida, vícios de texto de máquina, gancho) e, se algo falhar, pede
uma segunda versão dizendo o que corrigir. A assinatura da apresentadora e o fecho com o aviso são postos pelo
programa, nunca pela IA.

Depois de aprovado, o roteiro é decupado em 6 cenas de 8 segundos (o limite de cada clipe do Veo, o modelo do
Google Flow): a Clara na bancada com o telão atrás e cenas só de imagem, alternadas. Cada cena sai com o prompt pronto
para o Flow, montado pelo programa a partir da "bíblia" da persona (o mesmo rosto, roupa, estúdio, voz e câmera em
todas), para os 6 pedaços parecerem um vídeo só.

Grava diario/AAAA-MM-DD/roteiros/<tipo>[-slug].json, que a esteira de vídeo usa depois.
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
PALAVRAS = (95, 122)  # 6 cenas de 8 s = 48 s; cerca de 20 palavras por cena, contando assinatura e fecho
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
2. Uma ideia por vídeo. O vídeo tem 48 segundos (6 cenas de 8 s): corpo entre 6 e 9 falas, cada uma com 4 a 15
   palavras. O tamanho exato (gancho e corpo juntos) vem no pedido: conte as palavras antes de entregar.
   Menos é mais: cada palavra a mais acelera a fala.
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
                "falas": {"type": "array", "minItems": 5, "maxItems": 10, "items": {"type": "string"},
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


EXTENSO = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
           "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14,
           "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30,
           "quarenta": 40, "cinquenta": 50, "cem": 100}


def permitidos(material: str) -> set[str]:
    """Números que o roteiro pode usar: os do material, com e sem casas decimais finais, e os escritos por extenso
    no material ("seis das nove cadeiras" deixa a tela mostrar 6 e 9)."""
    saida = {str(EXTENSO[w]) for w in re.findall(r"\w+", _sem_acento(material).lower()) if w in EXTENSO}
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
    if r["palavras"] > PALAVRAS[1]:
        problemas.append(f"tamanho: {r['palavras']} palavras faladas, o máximo é {PALAVRAS[1]}: corte pelo menos "
                         f"{r['palavras'] - PALAVRAS[1] + 5} palavras do gancho e do corpo (tire uma fala inteira)")
    elif r["palavras"] < PALAVRAS[0]:
        problemas.append(f"tamanho: {r['palavras']} palavras faladas, o mínimo é {PALAVRAS[0]}: acrescente cerca de "
                         f"{PALAVRAS[0] - r['palavras'] + 5} palavras ao corpo")
    else:
        maior = max(map(_palavras, dividir(r["linhas"])))
        if maior > MAXIMO_CENA:
            problemas.append(f"não cabe em {CENAS} cenas de {SEGUNDOS_CENA} s: a cena mais longa teria {maior} "
                             f"palavras (máximo {MAXIMO_CENA}); encurte as falas mais longas")
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
    """Pede o roteiro; se a conferência reprovar, pede outra versão (até 3) com a lista do que corrigir."""
    fixo = _palavras(" ".join([ASSINATURA, FECHO, CHAMADAS.get(chamada, CHAMADAS["grupo"])]))
    pedido = (f"Tipo de vídeo: {TIPOS[tipo]}\nChamada do fim (o programa põe): {CHAMADAS.get(chamada)}\n"
              f"Tamanho: o gancho e o corpo, juntos, têm de {PALAVRAS[0] - fixo} a {PALAVRAS[1] - fixo} palavras "
              f"(mire em {PALAVRAS[1] - fixo - 8}); o programa soma mais {fixo} da assinatura, do fecho e da chamada.\n\n"
              f"MATERIAL CONFERIDO (a única fonte de números e fatos):\n{material}")
    problemas = []
    for tentativa in range(3):
        texto = pedido if not problemas else (
            pedido + "\n\nA VERSÃO ANTERIOR FOI REPROVADA NA CONFERÊNCIA. Corrija exatamente isto:\n- "
            + "\n- ".join(problemas))
        r = montar(ia.estruturado(cliente, SISTEMA, texto, ferramenta(), max_tokens=6000), chamada)
        problemas = conferir(r, material)
        if not problemas:
            break
    saida = {**r, "tipo": tipo, "persona": PERSONA, "aprovado": not problemas, "problemas": problemas,
             "tentativas": tentativa + 1}
    if not problemas:  # só roteiro aprovado vira cena
        try:
            saida.update(decupar(cliente, r))
        except Exception as erro:  # noqa: BLE001 — sem cenas, o roteiro continua valendo
            saida.update(cenas=[], cenas_ok=False, cenas_problemas=[f"decupagem falhou: {erro}"], flow="")
    return saida


# ---------------------------------------------------------------- cenas para o Google Flow

CENAS = 6
SEGUNDOS_CENA = 8
MAXIMO_CENA = 22  # palavras faladas que cabem em 8 s num ritmo de telejornal
BIBLIA = {  # a persona e o estúdio, iguais em todo prompt (no Flow, use a foto da Clara como "ingrediente")
    "persona": ("Clara, a Brazilian woman in her early 30s with shoulder-length dark brown hair, warm light-brown skin "
                "and brown eyes, wearing a navy blue blazer over a white blouse and small gold earrings"),
    "estudio": ("a modern dark navy TV news studio with soft amber and blue rim lights and a large video wall behind "
                "her"),
    "voz": "She speaks Brazilian Portuguese in a calm, clear, mid-pitched voice, at a steady news-anchor pace.",
    "camera": "Vertical 9:16 video, cinematic, shallow depth of field, natural skin texture, 8 seconds.",
    "proibido": "No on-screen text, no subtitles, no captions, no logos, no real public figures.",
}

SISTEMA_CENAS = f"""Você é o diretor de vídeo do "{config.NOME}". Recebe um roteiro aprovado e o divide em exatamente
{CENAS} cenas de {SEGUNDOS_CENA} segundos para o Google Flow (Veo).

Regras:
1. A fala de cada cena já vem pronta, dividida pelo programa (cada cena termina no fim de uma frase). Não mude nem
   repita a fala: para cada cena, na ordem, você escolhe o tipo, o visual, o texto da tela e a transição.
2. Alterne: a cena 1 (o gancho) e a cena {CENAS} (o fecho) são da apresentadora; no meio, intercale apresentadora e
   imagem (pelo menos 2 cenas de imagem).
3. "visual" é escrito em inglês, para o Veo: na cena da apresentadora, só o que aparece no telão, como um nome
   ("a modern central bank building at dawn"), sem repetir "screen behind the presenter"; na cena de imagem, a cena
   inteira (lugar, objeto, movimento de câmera). Concreto e filmável: um prédio, uma sala de reunião,
   moedas, um navio, um gráfico abstrato subindo.
4. Nunca mostre pessoa real (político, ministro, presidente, empresário) nem rosto reconhecível; nada de texto, número
   ou logotipo dentro da imagem: os números entram na edição.
5. "transicao" diz como a cena termina para emendar na próxima (por exemplo: "camera keeps slowly pushing in")."""


def ferramenta_cenas() -> dict:
    return {"name": "registrar_cenas", "description": "As cenas do Reel para o Google Flow.",
            "input_schema": {"type": "object", "required": ["cenas"], "properties": {"cenas": {
                "type": "array", "minItems": CENAS, "maxItems": CENAS, "items": {
                    "type": "object", "required": ["tipo", "visual", "transicao"],
                    "properties": {"tipo": {"type": "string", "enum": ["apresentadora", "imagem"]},
                                   "visual": {"type": "string", "description": "Em inglês."},
                                   "na_tela": {"type": "string", "description": "Texto da edição, até 6 palavras."},
                                   "transicao": {"type": "string", "description": "Em inglês."}}}}}}}


PROMPT_FOTO = (  # a foto de referência da Clara: gerar uma vez, escolher a melhor e usar como "ingrediente" no Flow
    f"Photorealistic studio portrait, vertical 9:16. {BIBLIA['persona']}. She stands in {BIBLIA['estudio']}, the video "
    "wall softly blurred. Waist-up medium shot, looking straight into the camera with a calm, confident, friendly "
    "expression, mouth closed, hands relaxed at her sides. Soft key light, natural skin texture, 85 mm lens, shallow "
    f"depth of field. {BIBLIA['proibido']}")

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
GRANDEZA = r"(mil|milhão|milhões|bilhão|bilhões|trilhão|trilhões)"


def falado(texto: str) -> str:
    """A fala como a voz deve ler: sem símbolo que o Veo soletra ("US$", "%", "7/11", "EUA")."""
    t = re.sub(r"US\$ ?(\d[\d.,]*) " + GRANDEZA, r"\1 \2 de dólares", texto)
    t = re.sub(r"US\$ ?(\d[\d.,]*)", r"\1 dólares", t)
    t = re.sub(r"R\$ ?(\d[\d.,]*) " + GRANDEZA, r"\1 \2 de reais", t)
    t = re.sub(r"R\$ ?(\d[\d.,]*)", r"\1 reais", t)
    t = re.sub(r"(\d[\d.,]*) ?%", r"\1 por cento", t)
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})\b(?!/)",
               lambda m: f"{int(m[1])} de {MESES[int(m[2]) - 1]}" if 1 <= int(m[2]) <= 12 else m[0], t)
    return re.sub(r"\bEUA\b", "Estados Unidos", t)


TELAO = re.compile(r"^(a |the )?(large |big )?(studio |video )?(screen|wall|video wall)( behind (her|the presenter))?"
                   r"( shows| showing| displaying| with)?\s*", re.I)


def prompt_flow(cena: dict) -> str:
    """O prompt de uma cena, sempre com a mesma persona, estúdio, voz e câmera."""
    b = BIBLIA
    if cena["tipo"] == "apresentadora":
        cena = {**cena, "visual": TELAO.sub("", cena["visual"].strip())}
    fala = falado(cena["fala"]).replace('"', "'")
    visual = cena["visual"].strip().rstrip(".")
    cena = {**cena, "visual": visual[:1].upper() + visual[1:] if cena["tipo"] == "imagem" else visual}
    if cena["tipo"] == "apresentadora":
        return (f"{b['camera']} Medium close-up of {b['persona']}, standing in {b['estudio']}. The video wall behind "
                f"her shows {cena['visual'].rstrip('.')}. She looks into the camera with a subtle natural hand gesture "
                f'and says: "{fala}" {b["voz"]} Ending: {cena["transicao"].rstrip(".")}. {b["proibido"]}')
    return (f"{b['camera']} {cena['visual'].rstrip('.')}. Slow, smooth camera movement. Voice-over in the same calm "
            f'Brazilian woman\'s voice, in Brazilian Portuguese: "{fala}" No faces in focus. Ending: '
            f"{cena['transicao'].rstrip('.')}. {b['proibido']}")


FIM_DE_FRASE = re.compile(r"[.!?]['\"”]?$")


def dividir(linhas: list[str], n: int = CENAS) -> list[str]:
    """As falas das n cenas: falas inteiras, na ordem, cortando só onde uma frase termina, com a cena mais longa o
    mais curta possível (e as cenas o mais parecidas possível). Feito pelo programa, não pela IA: nunca corta uma
    frase no meio nem perde uma palavra."""
    linhas = [l.strip() for l in linhas if l.strip()]
    if len(linhas) <= n:
        return linhas
    pesos = [_palavras(l) for l in linhas]
    total = len(linhas)

    def resolver(pode: list[bool]):
        memo = {}

        def melhor(i: int, k: int):
            if (i, k) in memo:
                return memo[i, k]
            if k == 1:
                w = sum(pesos[i:])
                memo[i, k] = ((w, w * w), (total,))
                return memo[i, k]
            achado, acum = None, 0
            for j in range(i, total - k + 1):  # a cena vai da fala i até a j
                acum += pesos[j]
                if not pode[j]:
                    continue
                resto = melhor(j + 1, k - 1)
                if resto is None:
                    continue
                custo = (max(acum, resto[0][0]), acum * acum + resto[0][1])
                if achado is None or custo < achado[0]:
                    achado = (custo, (j + 1,) + resto[1])
            memo[i, k] = achado
            return achado

        return melhor(0, n)

    achado = resolver([bool(FIM_DE_FRASE.search(l)) for l in linhas]) or resolver([True] * total)
    cortes = (0,) + achado[1]
    return [" ".join(linhas[a:b]) for a, b in zip(cortes, cortes[1:])]


def _normal(t: str) -> str:
    return re.sub(r"\W+", " ", _sem_acento(t).lower()).strip()


def conferir_cenas(cenas: list[dict], roteiro: dict) -> list[str]:
    problemas = []
    if len(cenas) != CENAS:
        problemas.append(f"são {len(cenas)} cenas; precisam ser {CENAS}")
    if _normal(" ".join(c.get("fala", "") for c in cenas)) != _normal(roteiro["texto_falado"]):
        problemas.append("as falas das cenas, juntas, não são exatamente o roteiro (sem tirar nem mudar palavras)")
    cortadas = [i + 1 for i, c in enumerate(cenas) if not FIM_DE_FRASE.search(c.get("fala", "").strip())]
    if cortadas:
        problemas.append("cenas que cortam uma frase no meio (cada cena termina em ponto): " + ", ".join(map(str, cortadas)))
    longas = [i + 1 for i, c in enumerate(cenas) if _palavras(c.get("fala", "")) > MAXIMO_CENA]
    if longas:
        problemas.append(f"cenas com mais de {MAXIMO_CENA} palavras (não cabem em 8 s): " + ", ".join(map(str, longas)))
    if cenas and (cenas[0].get("tipo") != "apresentadora" or cenas[-1].get("tipo") != "apresentadora"):
        problemas.append("a primeira e a última cena são da apresentadora")
    if sum(c.get("tipo") == "imagem" for c in cenas) < 2:
        problemas.append("pelo menos 2 cenas de imagem")
    soltos = sorted(_numeros(" ".join(c.get("visual", "") for c in cenas)))
    if soltos:
        problemas.append("número dentro da imagem (entra só na edição): " + ", ".join(soltos))
    return problemas


def decupar(cliente, roteiro: dict) -> dict:
    """Divide o roteiro aprovado em cenas de 8 s com o prompt do Flow. O programa corta as falas; a IA dirige
    (tipo de cena, imagem, texto da tela, transição). Duas tentativas."""
    falas = dividir(roteiro["linhas"])
    pedido = "AS CENAS, COM A FALA DE CADA UMA (já divididas; não mude):\n" + "\n".join(
        f"CENA {i}: {f}" for i, f in enumerate(falas, 1))
    problemas = []
    for _ in range(2):
        texto = pedido if not problemas else pedido + "\n\nCORRIJA:\n- " + "\n- ".join(problemas)
        cenas = (ia.estruturado(cliente, SISTEMA_CENAS, texto, ferramenta_cenas(), max_tokens=3000) or {}).get("cenas", [])
        if len(cenas) == len(falas):
            cenas = [{**c, "fala": f} for c, f in zip(cenas, falas)]
        problemas = conferir_cenas(cenas, roteiro)
        if not problemas:
            break
    cenas = [{**c, "inicio_s": i * SEGUNDOS_CENA, "prompt_flow": prompt_flow(c)} for i, c in enumerate(cenas)]
    return {"cenas": cenas, "cenas_ok": not problemas, "cenas_problemas": problemas, "flow": texto_flow(cenas)}


def texto_flow(cenas: list[dict]) -> str:
    """O pacote para colar no Flow: uma cena por bloco, na ordem."""
    blocos = ["Google Flow: 6 cenas de 8 s (Veo). Nas cenas da apresentadora, use a foto da Clara como ingrediente.",
              ""]
    for i, c in enumerate(cenas, 1):
        blocos += [f"CENA {i} ({c['inicio_s']}-{c['inicio_s'] + SEGUNDOS_CENA} s, {c['tipo']})",
                   f"Fala: {c['fala']}", f"Tela: {c.get('na_tela') or '-'}", f"Prompt: {c['prompt_flow']}", ""]
    return "\n".join(blocos).strip()


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
