"""Agente copy: assuntos de e-mail, título e descrição do site, legendas e chamada do card.

Cada peça tem limite de tamanho. Se o Claude passar do limite ou usar linguagem
proibida em alguma peça, o programa troca só aquela peça pela versão-padrão e anota.
"""

import pandas as pd

from . import config, ia
from .grafico import mes_curto
from .revisor import linguagem_proibida

LIMITES = {  # campo: (mínimo, máximo) em caracteres
    "pre_cabecalho": (40, 110), "titulo_site": (20, 70), "descricao_seo": (100, 160),
    "legenda_instagram": (200, 1500), "post_x": (60, 270), "post_linkedin": (300, 1300), "chamada_card": (15, 48),
}
LIMITE_ASSUNTO = 60
FUNCAO = {
    "pre_cabecalho": "Texto que aparece ao lado do assunto na caixa de entrada.",
    "titulo_site": "Título da página da edição (aba do navegador e Google).",
    "descricao_seo": "Resumo que o Google mostra abaixo do título.",
    "legenda_instagram": "Legenda do post com o card.",
    "post_x": "Post para o X.",
    "post_linkedin": "Post para o LinkedIn.",
    "chamada_card": "Convite para assinar, no rodapé do card (o card já mostra o número e o nível; não repita). "
                    "Ex.: 'Receba o Termômetro todo domingo · link na bio'.",
}

SISTEMA = f"""Você é o agente Copy do "{config.NOME}". Escreve as peças curtas que levam as pessoas
a abrir o e-mail, clicar no site e assinar a newsletter, em português do Brasil.

Princípios:
- Clareza antes de esperteza. O número e o nível do Termômetro são o gancho principal.
- Curiosidade honesta: prometa só o que a edição entrega. Nada de caça-clique.
- Proibido: promessa de lucro ou de proteção garantida, alarmismo ("colapso", "vai quebrar"),
  recomendação de compra ou venda, códigos de ações, CAIXA ALTA para gritar, mais de 2 emojis por peça.
- Instagram: primeira linha forte (é a única que aparece antes do "mais"), parágrafos curtos,
  chamada para o link na bio, até 5 hashtags no fim, e a frase "Conteúdo educativo, não é recomendação de investimento."
- X: uma ideia, até 270 caracteres, sem hashtags.
- LinkedIn: tom profissional, 3 a 5 parágrafos curtos, termine com uma pergunta ao leitor.
Respeite os limites de caracteres de cada campo. Registre tudo com a ferramenta registrar_copy."""
SISTEMA += config.manual('redacao')

FERRAMENTA = {
    "name": "registrar_copy",
    "description": "Registra as peças de copy da edição.",
    "input_schema": {
        "type": "object",
        "properties": {
            "assuntos_email": {"type": "array", "minItems": 3, "maxItems": 3,
                               "items": {"type": "string", "description": f"Até {LIMITE_ASSUNTO} caracteres"}},
            "assunto_escolhido": {"type": "integer", "minimum": 0, "maximum": 2,
                                  "description": "Índice do assunto que você recomenda"},
            **{campo: {"type": "string", "description": f"{FUNCAO[campo]} Entre {a} e {b} caracteres."}
               for campo, (a, b) in LIMITES.items()},
        },
        "required": ["assuntos_email", "assunto_escolhido", *LIMITES],
    },
}


def padrao(dados: dict, data_edicao: str) -> dict:
    v, n, mes = dados["valor"], dados["nivel"], mes_curto(dados["referencia"])
    leitura = dados["leitura"]
    link = config.SITE_URL or "link no perfil"
    return {
        "assuntos_email": [f"Termômetro em {v}: {n}", f"{n} nos mercados: o que mudou na semana",
                           "Os 3 riscos globais da semana, em 5 minutos"],
        "assunto_escolhido": 0,
        "pre_cabecalho": f"Leitura de {mes}: {leitura}."[:110],
        "titulo_site": f"Termômetro de Crise: {v}, {n} ({pd.Timestamp(data_edicao):%d/%m/%Y})",
        "descricao_seo": (f"O índice de estresse dos mercados marcou {v} de 100 em {mes}, nível {n}. "
                          f"Veja o que mexeu e os riscos globais da semana.")[:160],
        "legenda_instagram": (f"O Termômetro de Crise marcou {v} de 100: nível {n}.\n\n{leitura}.\n\n"
                              "O índice junta 5 indicadores públicos (petróleo, juros dos EUA, volatilidade, ações e ouro), "
                              "cada um comparado com o próprio histórico desde 1990.\n\n"
                              "A análise completa sai todo domingo. Link na bio.\n\n"
                              "Conteúdo educativo, não é recomendação de investimento.\n\n"
                              "#economia #investimentos #geopolitica #mercadofinanceiro #termometrodecrise"),
        "post_x": f"Termômetro de Crise: {v}/100, nível {n}. {leitura}. Análise da semana: {link}"[:270],
        "post_linkedin": (f"O Termômetro de Crise, índice que mede o estresse dos mercados globais, marcou {v} de 100 "
                          f"em {mes}: nível {n}.\n\n{leitura}.\n\nO método é aberto: 5 indicadores públicos, cada um "
                          "comparado com o próprio histórico desde 1990. Em 2008 o índice chegou a "
                          f"{dados['picos_historicos']['Crise de 2008']['valor']}; na Covid, a "
                          f"{dados['picos_historicos']['Covid']['valor']}.\n\nA análise completa, com os riscos da semana "
                          f"e a agenda, está em {link}.\n\nQual risco global você está acompanhando mais de perto?"),
        "chamada_card": "Receba o Termômetro todo domingo · link na bio",
    }


def validar(peca: dict, reserva: dict) -> tuple[dict, list[str]]:
    final, ajustes = dict(reserva), []
    assuntos = [a.strip() for a in peca.get("assuntos_email", []) if isinstance(a, str)]
    bons = [a for a in assuntos if len(a) <= LIMITE_ASSUNTO and not linguagem_proibida(a)]
    if len(bons) == 3:
        final["assuntos_email"] = bons
        final["assunto_escolhido"] = min(max(int(peca.get("assunto_escolhido", 0)), 0), 2)
    else:
        ajustes.append("assuntos_email: algum assunto passou de 60 caracteres ou usou linguagem proibida")
    for campo, (minimo, maximo) in LIMITES.items():
        valor = str(peca.get(campo, "")).strip()
        problemas = linguagem_proibida(valor)
        if not (minimo <= len(valor) <= maximo):
            ajustes.append(f"{campo}: {len(valor)} caracteres (limite {minimo}–{maximo})")
        elif problemas:
            ajustes.append(f"{campo}: linguagem proibida ({', '.join(problemas)})")
        elif campo == "legenda_instagram" and valor.count("#") > 5:
            ajustes.append("legenda_instagram: mais de 5 hashtags")
        else:
            final[campo] = valor
    return final, ajustes


def escrever(dados: dict, edicao_md: str, data_edicao: str, cliente=None) -> dict:
    reserva = padrao(dados, data_edicao)
    if not (cliente or ia.disponivel()) or "PENDENTE" in edicao_md:
        return {**reserva, "modo": "padrão (sem IA)", "ajustes": []}
    pedido = (f"Termômetro: {dados['valor']} de 100, nível {dados['nivel']}, leitura de {mes_curto(dados['referencia'])}.\n"
              f"Site: {config.SITE_URL or '(ainda sem domínio: use link na bio)'}\n\nEDIÇÃO\n{edicao_md}")
    bruto = ia.estruturado(cliente or ia.novo_cliente(), SISTEMA, pedido, FERRAMENTA, max_tokens=4000)
    final, ajustes = validar(bruto, reserva)
    return {**final, "modo": f"claude ({config.MODELO_CLAUDE})", "ajustes": ajustes}
