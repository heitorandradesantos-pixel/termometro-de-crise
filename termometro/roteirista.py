"""Roteirista: transforma o material conferido do dia em roteiro de Reel (Instagram, TikTok, Shorts) de 45 a 60 s.

Três tipos: "abertura" (a mensagem da Abertura no WhatsApp), "fechamento" (o balanço e o panorama do dia) e
"explica" (um artigo do Plantão). O vídeo não cria fato: cada número falado tem de estar no material. O programa
confere tudo (tamanho, números, linguagem proibida, vícios de texto de máquina, gancho) e, se algo falhar, pede
outra versão dizendo o que corrigir. A apresentação do apresentador e o fecho com o aviso são postos pelo programa,
nunca pela IA.

Quem apresenta é uma pessoa de verdade (o Heitor), que grava no celular lendo um teleprompter. Depois de aprovado, o
roteiro ganha de 2 a 3 imagens de apoio: falas que, na edição, são cobertas por um clipe do Google Flow (sem gente,
sem texto) enquanto a voz continua. O pacote (teleprompter, texto da tela, apoios e legenda) vai para a conversa do
próprio número no WhatsApp.

Grava diario/AAAA-MM-DD/roteiros/<tipo>[-slug].json.
"""

import json
import os
import re
from pathlib import Path

import pandas as pd

from . import config, estrategista, ia
from .revisor import linguagem_proibida

PERSONA = os.environ.get("PERSONA_NOME") or "Heitor"
ASSINATURA = f"Fala, galera, aqui é o {PERSONA}, do Termômetro de Crise."
FECHO = "Isso não é recomendação: quem decide é você."
BORDAO = os.environ.get("BORDAO") or "Sem alarde. Eu sou só o termômetro!"  # a última frase de todo vídeo
CHAMADAS = {"grupo": "O grupo do WhatsApp está no link da bio.",
            "newsletter": "O Termômetro da Semana chega por e-mail: link na bio."}
AVISO_LEGENDA = "Conteúdo educativo, não é recomendação de investimento."
PALAVRAS_POR_MINUTO = 150
PALAVRAS = (105, 145)  # 45 a 60 s de fala, contando apresentação, fecho e chamada
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

SISTEMA = f"""Você é o Roteirista do "{config.NOME}", um portal financeiro brasileiro para leigos. Escreve o que o
{PERSONA}, apresentador do {config.NOME} (uma pessoa de verdade, que grava no celular lendo um teleprompter), fala em
vídeos verticais de 45 a 60 segundos.

O programa põe sozinho, depois do gancho, a apresentação "{ASSINATURA}" e, no fim, a chamada para o link da bio,
o aviso "{FECHO}" e o bordão "{BORDAO}" (a última frase de todo vídeo). Não escreva nada disso, nem uma
frase parecida com o bordão no fim do corpo. Você escreve só o gancho (3 opções, com nota) e o corpo, mais o texto da tela e a legenda.

Regras:
1. Todo número que você escrever tem de estar no material, escrito do mesmo jeito (vírgula decimal, ponto de milhar).
   Número que não está no material não entra. Prefira poucos números: 2 ou 3 bem escolhidos valem mais que 8.
2. Uma ideia por vídeo. Corpo entre 6 e 10 falas, cada uma com 4 a 15 palavras (uma respiração). O tamanho
   exato (gancho e corpo juntos) vem no pedido: conte as palavras antes de entregar.
3. Nada de recomendação, previsão, alarmismo, política partidária ou opinião sobre governo.
4. Tom popular e descontraído, de quem explica dinheiro para um amigo no bar: assunto sério, linguagem do dia a dia.
   Frases curtas que se dizem em voz alta, para uma pessoa ("você"), com energia. Ele fala em primeira pessoa
   ("olha só", "eu fui atrás", "bora entender") e usa comparação da vida real (o mercado, a conta de luz, o cartão,
   o salário) para explicar o que é técnico; a comparação tem de ser correta, não só engraçada. Gíria leve e pouca:
   forçada soa falsa. Humor pontual, nunca sobre prejuízo, golpe ou quem perdeu dinheiro: aí o tom é sério.
   Todo roteiro tem pelo menos uma comparação viva com a vida real e um passo simples e calmo no fim; use a
   metáfora do termômetro (temperatura, febre, sinal amarelo) quando couber.
6. Popular não é sensacionalista: o que aconteceu, o que muda para você e o que fazer. Fato atribuído a quem disse
   ("segundo o Banco Central"); nada de acusar empresa ou pessoa além do que a fonte diz, nada de política.
7. Escreva também a VERSÃO RUA, para gravar de improviso na rua ou no carro parado, sem teleprompter: um gancho
   curto (até 12 palavras) e de 3 a 4 tópicos de até 14 palavras cada, na ordem da fala. Cada tópico é um fato com
   o número e quem disse; o último é o que fazer. Mesmas regras de número e de linguagem do roteiro.
8. Diga o formato que combina mais: "rua" para notícia quente do dia, que acabou de acontecer e pede urgência
   ("tô aqui e preciso te contar isso"); "bancada" para explicação, contexto ou assunto com muitos números.
9. No texto da tela, a fonte é a original: "Yahoo Finance" para cotações, "Banco Central" para Selic, PTAX e Focus,
   "Termômetro de Crise" para as leituras do termômetro e o nome do veículo para as notícias."""
SISTEMA += config.manual("roteiro", "redacao", "marca", "referencias")


def ferramenta() -> dict:
    nota = {"type": "integer", "minimum": 0, "maximum": 2}
    return {"name": "registrar_roteiro", "description": "O roteiro do Reel, pronto para o teleprompter.",
            "input_schema": {"type": "object", "required": ["ganchos", "gancho_escolhido", "falas", "retomada",
                                                            "na_tela", "rua", "formato", "busca", "legenda",
                                                            "hashtags"],
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
                "rua": {"type": "object", "required": ["gancho", "topicos"], "properties": {
                    "gancho": {"type": "string", "description": "Até 12 palavras."},
                    "topicos": {"type": "array", "minItems": 3, "maxItems": 4, "items": {"type": "string"},
                                "description": "Até 14 palavras cada: fato, número e quem disse; o último é o que fazer."}}},
                "formato": {"type": "string", "enum": ["bancada", "rua"]},
                "por_que_formato": {"type": "string", "description": "Uma frase."},
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
    """O roteiro final: gancho, assinatura, corpo, chamada, aviso e o bordão por último."""
    ganchos = bruto.get("ganchos") or []
    i = bruto.get("gancho_escolhido", 0)
    gancho = ganchos[i] if 0 <= i < len(ganchos) else (ganchos[0] if ganchos else {"texto": "", "na_tela": ""})
    falas = [f.strip() for f in bruto.get("falas") or [] if f.strip()]
    linhas = [gancho["texto"].strip(), ASSINATURA, *falas, CHAMADAS.get(chamada, CHAMADAS["grupo"]), FECHO, BORDAO]
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
            "legenda": legenda + ("\n\n" + " ".join(hashtags) if hashtags else ""), "hashtags": hashtags,
            "rua": {"gancho": ((bruto.get("rua") or {}).get("gancho") or "").strip(),
                    "topicos": [t.strip() for t in (bruto.get("rua") or {}).get("topicos") or [] if t.strip()]},
            "formato": bruto.get("formato") if bruto.get("formato") in ("bancada", "rua") else "bancada",
            "por_que_formato": (bruto.get("por_que_formato") or "").strip()}


def conferir(r: dict, material: str) -> list[str]:
    """O que impede o roteiro de ir para a voz. Lista vazia = aprovado."""
    problemas = []
    if r["palavras"] > PALAVRAS[1]:
        problemas.append(f"tamanho: {r['palavras']} palavras faladas, o máximo é {PALAVRAS[1]}: corte pelo menos "
                         f"{r['palavras'] - PALAVRAS[1] + 5} palavras do gancho e do corpo (tire uma fala inteira)")
    elif r["palavras"] < PALAVRAS[0]:
        problemas.append(f"tamanho: {r['palavras']} palavras faladas, o mínimo é {PALAVRAS[0]}: acrescente cerca de "
                         f"{PALAVRAS[0] - r['palavras'] + 5} palavras ao corpo")
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
    rua = r.get("rua") or {}
    if not rua.get("gancho") or not 3 <= len(rua.get("topicos") or []) <= 4:
        problemas.append("versão rua incompleta: um gancho e de 3 a 4 tópicos")
    else:
        texto_rua = rua["gancho"] + " " + " ".join(rua["topicos"])
        if _palavras(rua["gancho"]) > 12 or any(_palavras(t) > 14 for t in rua["topicos"]):
            problemas.append("versão rua: gancho até 12 palavras e tópicos até 14")
        soltos_rua = sorted(_numeros(texto_rua) - permitidos(material))
        if soltos_rua:
            problemas.append("versão rua com números que não estão no material: " + ", ".join(soltos_rua))
        if linguagem_proibida(texto_rua):
            problemas.append("versão rua com linguagem proibida: " + ", ".join(linguagem_proibida(texto_rua)))
    return problemas


def escrever(cliente, tipo: str, material: str, chamada: str = "grupo") -> dict:
    """Pede o roteiro; se a conferência reprovar, pede outra versão (até 3) com a lista do que corrigir."""
    fixo = _palavras(" ".join([ASSINATURA, FECHO, BORDAO, CHAMADAS.get(chamada, CHAMADAS["grupo"])]))
    pedido = (f"Tipo de vídeo: {TIPOS[tipo]}\nChamada do fim (o programa põe): {CHAMADAS.get(chamada)}\n"
              f"Tamanho: o gancho e o corpo, juntos, têm de {PALAVRAS[0] - fixo} a {PALAVRAS[1] - fixo} palavras "
              f"(mire em {PALAVRAS[1] - fixo - 8}); o programa soma mais {fixo} da assinatura, da chamada, do aviso e do bordão.\n\n"
              f"MATERIAL CONFERIDO (a única fonte de números e fatos):\n{material}")
    problemas, marca, melhor = [], None, None
    for tentativa in range(3):
        texto = pedido if not problemas else (
            pedido + "\n\nA VERSÃO ANTERIOR FOI REPROVADA NA CONFERÊNCIA. Corrija exatamente isto:\n- "
            + "\n- ".join(problemas))
        r = montar(ia.estruturado(cliente, SISTEMA, texto, ferramenta(), max_tokens=6000), chamada)
        problemas = conferir(r, material)
        if problemas:
            continue
        marca = avaliar_marca(cliente, r)  # fatos conferidos: agora o Estrategista vê se fala com o público certo
        if melhor is None or (marca["nota"] or 0) > (melhor[1]["nota"] or 0):
            melhor = (r, marca, tentativa)
        if marca["aprovado"] or tentativa == 2:
            break
        problemas = [f"(estrategista de marca, nota {marca['nota']}/10) {s}" for s in marca["sugestoes"]] or \
            [f"(estrategista de marca, nota {marca['nota']}/10) {marca['veredito']}"]
    if problemas and melhor:  # a última versão errou um fato: fica a melhor versão já conferida
        problemas = []
    if melhor and not problemas:
        r, marca, _ = melhor
    saida = {**r, "tipo": tipo, "persona": PERSONA, "aprovado": not problemas, "problemas": problemas,
             "tentativas": tentativa + 1, "marca": marca}
    if not problemas:  # só roteiro aprovado ganha imagens de apoio
        try:
            saida.update(apoiar(cliente, r))
        except Exception as erro:  # noqa: BLE001 — sem apoio, o roteiro continua valendo
            saida.update(apoios=[], apoios_ok=False, apoios_problemas=[f"imagens de apoio falharam: {erro}"])
    saida["teleprompter"] = teleprompter(r)
    return saida


def avaliar_marca(cliente, r: dict) -> dict:
    """A nota do Estrategista de marca e comportamento. Se ele falhar, o roteiro segue (a marca não trava o vídeo)."""
    try:
        return estrategista.avaliar(cliente, "\n".join(r["linhas"]) + "\n\nLEGENDA DO POST:\n" + r["legenda"])
    except Exception as erro:  # noqa: BLE001
        return {"nota": None, "aprovado": True, "notas": {}, "sugestoes": [], "veredito": f"estrategista falhou: {erro}"}


# ---------------------------------------------------------------- imagens de apoio e teleprompter

APOIOS = (2, 3)  # quantas falas ganham imagem de apoio (o resto é o apresentador olhando para a câmera)
SEGUNDOS_APOIO = 6
SISTEMA_APOIO = f"""Você é o editor de vídeo do "{config.NOME}". O {PERSONA} grava o roteiro no celular, olhando para a
câmera e lendo num teleprompter. Na edição, algumas falas são cobertas por uma imagem de apoio gerada no Google Flow,
enquanto a voz dele continua por baixo.

Escolha de {APOIOS[0]} a {APOIOS[1]} falas do corpo para cobrir com imagem (nunca o gancho, a apresentação, o fecho ou
a chamada final). Prefira as falas que contam um fato concreto (um lugar, um objeto, uma situação), não as de opinião.
Para cada uma, escreva "visual" em inglês, para o Flow: uma cena concreta de {SEGUNDOS_APOIO} segundos, vertical, com
movimento de câmera. Proibido no visual: pessoas reconhecíveis ou rosto em foco, texto, letras, números, logotipos,
marcas, bandeiras de partido."""


def ferramenta_apoio() -> dict:
    return {"name": "registrar_apoios", "description": "As falas que ganham imagem de apoio e a imagem de cada uma.",
            "input_schema": {"type": "object", "required": ["apoios"], "properties": {"apoios": {
                "type": "array", "minItems": APOIOS[0], "maxItems": APOIOS[1], "items": {
                    "type": "object", "required": ["fala", "visual"],
                    "properties": {"fala": {"type": "integer", "description": "O número da fala, como na lista."},
                                   "visual": {"type": "string", "description": "A cena, em inglês."}}}}}}}


FORMATO = re.compile(r"(?i)\b(vertical\s*)?9:16(\s*video)?[,.]?\s*|\b\d+\s*(seconds?|segundos?|s)\b[,.]?\s*")


def limpar_visual(visual: str) -> str:
    """Tira do visual o formato que o modelo às vezes repete ("Vertical 9:16, 6 seconds."): o programa já põe."""
    return re.sub(r"\s{2,}", " ", FORMATO.sub("", visual)).strip(" ,.")


def prompt_apoio(visual: str) -> str:
    """O prompt do Flow para uma imagem de apoio: sempre vertical, sem gente, sem texto e sem fala."""
    v = limpar_visual(visual)
    return (f"Vertical 9:16 video, cinematic, shallow depth of field, {SEGUNDOS_APOIO} seconds. {v[:1].upper() + v[1:]}. "
            "Slow, smooth camera movement. No people in focus, no faces, no on-screen text, no subtitles, no captions, "
            "no logos. No dialogue: soft ambient sound only.")


def conferir_apoios(apoios: list[dict], roteiro: dict) -> list[str]:
    problemas = []
    corpo = range(2, len(roteiro["linhas"]) - 3)  # sem gancho, apresentação, chamada, aviso e bordão
    if not APOIOS[0] <= len(apoios) <= APOIOS[1]:
        problemas.append(f"são {len(apoios)} imagens de apoio; precisam ser de {APOIOS[0]} a {APOIOS[1]}")
    fora = [a.get("fala") for a in apoios if a.get("fala") not in corpo]
    if fora:
        problemas.append(f"falas fora do corpo (use de {corpo.start} a {corpo.stop - 1}): {fora}")
    if len({a.get("fala") for a in apoios}) != len(apoios):
        problemas.append("a mesma fala aparece duas vezes")
    soltos = sorted(_numeros(" ".join(a.get("visual", "") for a in apoios)))
    if soltos:
        problemas.append("número dentro da imagem (número entra só no texto da tela): " + ", ".join(soltos))
    return problemas


def apoiar(cliente, roteiro: dict) -> dict:
    """Escolhe as falas com imagem de apoio e escreve o prompt do Flow de cada uma. Duas tentativas."""
    pedido = "O ROTEIRO, FALA POR FALA:\n" + "\n".join(f"{i}. {l}" for i, l in enumerate(roteiro["linhas"]))
    problemas = []
    for _ in range(2):
        texto = pedido if not problemas else pedido + "\n\nCORRIJA:\n- " + "\n- ".join(problemas)
        apoios = (ia.estruturado(cliente, SISTEMA_APOIO, texto, ferramenta_apoio(), max_tokens=2000) or {}).get("apoios", [])
        apoios = [{**a, "visual": limpar_visual(a.get("visual", ""))} for a in apoios]
        problemas = conferir_apoios(apoios, roteiro)
        if not problemas:
            break
    apoios = sorted(({**a, "texto_da_fala": roteiro["linhas"][a["fala"]], "prompt_flow": prompt_apoio(a["visual"])}
                     for a in apoios if a.get("fala") in range(len(roteiro["linhas"]))), key=lambda a: a["fala"])
    return {"apoios": apoios, "apoios_ok": not problemas, "apoios_problemas": problemas}


PRINTS = 3  # quantos prints de fonte, no máximo, entram na edição (a prova na tela, no terço de cima)
PRINTS_MERCADO = [{"veiculo": "Yahoo Finance", "url": "https://finance.yahoo.com/quote/%5EBVSP/",
                   "destaque": "gráfico do Ibovespa no mês"},
                  {"veiculo": "Yahoo Finance", "url": "https://finance.yahoo.com/quote/BRL%3DX/",
                   "destaque": "gráfico do dólar no mês"}]


def _frase(texto: str, limite: int = 140) -> str:
    primeira = re.split(r"(?<=[.!?])\s", texto.strip(), maxsplit=1)[0]
    return primeira if len(primeira) <= limite else primeira[:limite].rsplit(" ", 1)[0] + "…"


def prints_artigo(artigo: dict) -> list[dict]:
    """Os prints de prova para a edição: as fontes reais dos fatos do artigo, uma por veículo, com a frase a grifar."""
    prints, vistos = [], set()
    for f in artigo.get("o_que_se_sabe", []):
        url = f.get("fonte_url") or ""
        if not url.startswith("http") or url in vistos or f.get("confiavel") is False:
            continue
        vistos.add(url)
        prints.append({"veiculo": f.get("veiculo") or "fonte", "url": url, "destaque": _frase(f.get("texto", ""))})
        if len(prints) == PRINTS:
            break
    return prints


def teleprompter(roteiro: dict) -> str:
    """O texto para colar no app de teleprompter: uma fala por parágrafo, exatamente como foi aprovado."""
    return "\n\n".join(roteiro["linhas"])


DICAS = ("Dicas: celular na vertical, na altura dos olhos, luz de frente (janela ou ring light). Grave tudo de uma vez; "
         "se errar, pare, respire e repita só a frase. Na rua, microfone na roupa e nunca grave dirigindo. "
         f"O bordão \"{BORDAO}\" é a última frase: olho na câmera, calmo e firme. "
         "Me mande o vídeo aqui que eu edito.")


LINHA = "━━━━━━━━━━━━━━━━━━"


def pacote_whatsapp(roteiro: dict, titulo: str, numero: int = 1, total: int = 1) -> list[str]:
    """Um roteiro por bloco na conversa do próprio número: (1) tudo junto (cenário, rua, edição e legenda),
    (2) só o texto do teleprompter, para copiar e colar, e (3) a linha de fim, que separa do próximo roteiro."""
    nome = f"ROTEIRO {numero} de {total}" if total > 1 else "ROTEIRO"
    tela = " · ".join(t["texto"] for t in roteiro.get("na_tela") or [] if t.get("texto"))
    apoios = "\n".join(f"- fala {a['fala'] + 1}: \"{a['texto_da_fala']}\"" for a in roteiro.get("apoios") or [])
    formato = roteiro.get("formato") or "bancada"
    sugestao = ("Formato sugerido: RUA (notícia quente; grave de improviso com a parte 2)" if formato == "rua"
                else "Formato sugerido: CENÁRIO (com o teleprompter, no fundo dos prédios)")
    if roteiro.get("por_que_formato"):
        sugestao += f"\n{roteiro['por_que_formato']}"
    rua = roteiro.get("rua") or {}
    if rua.get("gancho") and rua.get("topicos"):
        parte_rua = (f"Sem teleprompter: decore o gancho e fale os tópicos do seu jeito.\n\nGancho: {rua['gancho']}\n"
                     + "\n".join(f"• {t}" for t in rua["topicos"]) + "\n\nFecho: " + " ".join(roteiro["linhas"][-3:]))
    else:
        parte_rua = "Este é melhor gravar no cenário."
    prints = "\n".join(f"- {p['veiculo']}: \"{p['destaque']}\" ({p['url']})" for p in roteiro.get("prints") or [])
    edicao = (f"Texto na tela: {tela or '-'}"
              + f"\nNo fim: o bordão \"{BORDAO}\" em letra grande e a tela de \"siga\""
              + (f"\nPrints da fonte no terço de cima (a prova, sem tapar o rosto):\n{prints}" if prints else "")
              + (f"\nImagens de apoio do Flow por cima das falas:\n{apoios}" if apoios else "")
              + (f"\n\n🧠 Estrategista de marca: {marca['nota']}/10. {marca.get('veredito', '')}".rstrip()
                 if (marca := roteiro.get("marca") or {}).get("nota") is not None else ""))
    bloco = (f"{LINHA}\n🎬 {nome}: {titulo} (cerca de {roteiro['segundos']} s)\n{LINHA}\n{sugestao}\n\n"
             f"🏙️ 1) GRAVAR NO CENÁRIO\nO texto do teleprompter vem na próxima mensagem, sozinho, "
             f"para copiar e colar.{chr(10) + chr(10) + DICAS if numero == 1 else ''}\n\n"
             f"🚶 2) GRAVAR NA RUA\n{parte_rua}\n\n"
             f"✂️ 3) EDIÇÃO (eu faço)\n{edicao}\n\n"
             f"📝 4) LEGENDA DO POST\n\n{roteiro['legenda']}")
    return [bloco, teleprompter(roteiro), f"{LINHA}\n✅ FIM DO {nome}\n{LINHA}"]


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
    trabalhos = []  # (dia, nome, material, prints)
    if tipo in ("abertura", "fechamento"):
        arq = (pasta_envio or Path("_whatsapp")) / "envio.json"
        if not arq.exists():
            print(f"Roteirista: sem a mensagem da {tipo} preparada ({arq}); nada a fazer.")
            return []
        envio = json.loads(arq.read_text())
        if envio.get("tipo", "fechamento") != tipo:
            print(f"Roteirista: a mensagem preparada é de {envio.get('tipo')}, não de {tipo}.")
            return []
        trabalhos.append((envio["dia"], tipo, material_envio(envio), PRINTS_MERCADO))
    else:
        dia = dia or pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
        for a in sorted((diario / "plantao").glob(f"{dia}-*.json")):
            if (diario / dia / "roteiros" / f"explica-{a.stem[11:]}.json").exists():
                continue  # já tem roteiro
            artigo = json.loads(a.read_text())
            trabalhos.append((dia, f"explica-{artigo['slug']}", material_artigo(artigo), prints_artigo(artigo)))
    if not trabalhos:
        print("Roteirista: nada novo para roteirizar.")
        return []
    cliente = cliente or ia.novo_cliente()
    gravados = []
    for d, nome, material, prints in trabalhos:
        r = escrever(cliente, "explica" if nome.startswith("explica") else tipo, material, chamada)
        r["prints"] = prints
        gravados.append(gravar(diario, d, r, nome))
        estado = "aprovado" if r["aprovado"] else "reprovado: " + "; ".join(r["problemas"])
        print(f"  roteiro {nome} ({r['segundos']} s, gancho {nota(r['gancho'])}/10): {estado}")
    return gravados
