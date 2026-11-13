"""Estrategista de marca e comportamento: confere se cada roteiro e cada copy falam com o público certo, no
arquétipo e no temperamento da marca, com gatilhos éticos.

É o especialista em comportamento humano, arquétipos de marca (Mark e Pearson), temperamentos e psicologia do
consumidor do squad. Ele não escreve a peça: dá nota de 0 a 10 em cinco pontos e até três sugestões concretas.
O Roteirista reescreve quando a nota fica abaixo de NOTA_MINIMA. A plataforma de marca está em manuais/marca.md.
"""

from . import config, ia

NOTA_MINIMA = 8  # abaixo disso, o Roteirista reescreve (decisão do Heitor, 07/11/2026)
CRITERIOS = {
    "persona": "Fala com quem sente a economia no bolso (ou com o iniciante curioso): responde 'isso mexe no meu "
               "bolso? o que eu faço?' e passa no Teste do CLT do manual de marca (quem trabalha em loja, obra ou "
               "aplicativo entende cada fala de primeira: uma ideia e no máximo um número por fala, sem palavra de RH, "
               "contador ou banco sem tradução, sem nome de site na fala)",
    "arquetipo": "Sábio com jeito de Cara Comum: verdade com fonte, na língua do dia a dia; nada de Fora da lei, "
                 "Mago ou Governante",
    "temperamentos": "Fala com os quatro: o ponto e o que fazer (colérico), uma comparação viva (sanguíneo), o número "
                     "com fonte e o porquê (melancólico), calma e um passo simples (fleumático)",
    "gatilhos": "Gatilhos éticos: curiosidade que o texto paga, concretude, identificação, perda sempre com a saída; "
                "nada de urgência falsa, promessa, medo sem saída ou conspiração",
    "voz": "Popular e descontraído com assunto sério, bordões da casa, termo técnico traduzido, sem sensacionalismo",
}

SISTEMA = f"""Você é o Estrategista de marca e comportamento do "{config.NOME}": especialista em comportamento humano,
arquétipos de marca, temperamentos e psicologia do consumidor. Você avalia uma peça (roteiro de vídeo ou copy) já
conferida nos fatos: não discuta números nem fontes, só se a peça fala com a pessoa certa, do jeito certo.

Dê nota de 0 a 2 em cada critério (0 = falha, 1 = em parte, 2 = acerta):
""" + "\n".join(f"- {k}: {v}" for k, v in CRITERIOS.items()) + """

Depois, até 3 sugestões concretas, cada uma citando a frase e dizendo como reescrever (sem inventar número ou fato
que não está na peça). Se a peça já está boa, não invente problema: sugestões vazias.""" + config.manual("marca", "comportamento", "referencias")


def ferramenta() -> dict:
    nota = {"type": "integer", "minimum": 0, "maximum": 2}
    return {"name": "registrar_avaliacao", "description": "A avaliação da peça pela plataforma de marca.",
            "input_schema": {"type": "object", "required": ["notas", "sugestoes", "veredito"], "properties": {
                "notas": {"type": "object", "required": list(CRITERIOS), "properties": {k: nota for k in CRITERIOS}},
                "sugestoes": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
                "veredito": {"type": "string", "description": "Uma frase: o que a peça faz bem e o que falta."}}}}


def avaliar(cliente, peca: str, tipo: str = "roteiro de Reel") -> dict:
    """Nota de 0 a 10 e sugestões. Em caso de falha da IA, devolve aprovado (a marca não trava a publicação)."""
    bruto = ia.estruturado(cliente, SISTEMA, f"TIPO DE PEÇA: {tipo}\n\nA PEÇA:\n{peca}", ferramenta(), max_tokens=1500) or {}
    notas = {k: max(0, min(2, int((bruto.get("notas") or {}).get(k, 2)))) for k in CRITERIOS}
    nota = sum(notas.values())
    return {"nota": nota, "notas": notas, "aprovado": nota >= NOTA_MINIMA,
            "sugestoes": [s for s in (bruto.get("sugestoes") or []) if s.strip()][:3],
            "veredito": bruto.get("veredito", "")}
