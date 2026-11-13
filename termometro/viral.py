"""Especialista em viralização: confere se cada roteiro tem chance de parar o dedo, segurar até o fim e ser enviado.

Assento do squad desde 11/11/2026; virou etapa obrigatória em 13/11 (pedido do Heitor: "passar por ele os roteiros
antes de mandar pra mim"). Ele não confere fatos (isso é da conferência) nem a marca (é do Estrategista): só o
desempenho do vídeo nas redes. Nota de 0 a 10 em cinco pontos e até três sugestões concretas. Abaixo de
NOTA_MINIMA, o Roteirista reescreve. As regras estão em manuais/viralizacao.md.
"""

from . import config, ia

NOTA_MINIMA = 8
CRITERIOS = {
    "gancho": "Os 3 primeiros segundos param o dedo: lacuna ESPECÍFICA (um número, um objeto, uma pessoa) do bolso "
              "de quem assiste, dita na primeira frase; nada de 'fala, galera', apresentação ou curiosidade vaga",
    "pagamento": "O gancho é pago rápido (primeira resposta até uns 10 s) e por completo até o fim; nada de isca que o "
                 "corpo não entrega",
    "retencao": "Ritmo: frases curtas, uma ideia por fala, uma virada no meio ('mas tem um detalhe', o número mais "
                "forte guardado) para segurar quem ia sair; nada de parágrafo explicativo comprido",
    "envio": "Motivo para mandar para alguém: um número que a pessoa quer mostrar, uma comparação que vira conversa, "
             "e o pedido de envio para uma situação concreta ('manda pra quem tem...'), não 'manda pro amigo'",
    "conversa": "Puxa comentário ou identificação: a pessoa se reconhece ('se você...'), uma crença comum desmontada "
                "com fonte, ou uma pergunta simples que dá vontade de responder; sem polêmica política",
}

SISTEMA = f"""Você é o Especialista em Viralização do "{config.NOME}" (Reels, TikTok e Shorts). Avalia um roteiro já
conferido nos fatos e na marca: não discuta números nem fontes. A pergunta é uma só: quem nunca ouviu falar do
Termômetro para de rolar, fica até o fim e manda o vídeo para alguém?

Dê nota de 0 a 2 em cada critério (0 = falha, 1 = em parte, 2 = acerta):
""" + "\n".join(f"- {k}: {v}" for k, v in CRITERIOS.items()) + """

Depois, até 3 sugestões concretas, cada uma citando a frase e mostrando a reescrita (com os mesmos números e fatos
da peça, sem inventar nada, sem promessa de ganho, sem medo sem saída, sem sensacionalismo). Priorize o gancho.
Se o roteiro já está forte, não invente problema: sugestões vazias.""" + config.manual("viralizacao", "marca")


def ferramenta() -> dict:
    nota = {"type": "integer", "minimum": 0, "maximum": 2}
    return {"name": "registrar_avaliacao_viral", "description": "A avaliação do potencial viral do roteiro.",
            "input_schema": {"type": "object", "required": ["notas", "sugestoes", "veredito"], "properties": {
                "notas": {"type": "object", "required": list(CRITERIOS), "properties": {k: nota for k in CRITERIOS}},
                "sugestoes": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
                "veredito": {"type": "string", "description": "Uma frase: a força do vídeo e o que falta para viralizar."}}}}


def avaliar(cliente, peca: str, pauta: str = "") -> dict:
    """Nota de 0 a 10 e sugestões. Em caso de falha da IA, devolve aprovado (o especialista não trava o vídeo)."""
    texto = (f"PAUTA: {pauta}\n\n" if pauta else "") + f"O ROTEIRO:\n{peca}"
    bruto = ia.estruturado(cliente, SISTEMA, texto, ferramenta(), max_tokens=1500) or {}
    notas = {k: max(0, min(2, int((bruto.get("notas") or {}).get(k, 2)))) for k in CRITERIOS}
    nota = sum(notas.values())
    return {"nota": nota, "notas": notas, "aprovado": nota >= NOTA_MINIMA,
            "sugestoes": [s for s in (bruto.get("sugestoes") or []) if s.strip()][:3],
            "veredito": bruto.get("veredito", "")}
