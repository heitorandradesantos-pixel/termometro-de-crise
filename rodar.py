#!/usr/bin/env python3
"""Programa principal do Termômetro de Crise.

    python rodar.py                 gera a edição da semana com todos os agentes
    python rodar.py --site          monta o site com as edições da pasta edicoes/
    python rodar.py --newsletter    manda a edição mais recente ao beehiiv
    python rodar.py --aprovado      termina com código 0 se o Revisor aprovou a edição mais recente
    python rodar.py --so-coleta     só baixa os dados (o robô roda os testes antes de chamar a IA)

Agentes, em ordem: Coletor → Analista → Arte (gráfico) → Buscador → Redator → Copy → Arte (card) → Revisor.
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from termometro import buscador, coleta, config, copywriter, grafico, ia, motor, publicar, redator, revisor, site  # noqa: E402

EDICOES = RAIZ / "edicoes"


def etapa(registro: list, nome: str):
    """Marca o tempo e o resultado de cada agente para o relatório da edição."""
    class _Etapa:
        def __enter__(self):
            self.inicio = time.time()
            print(f"\n▸ {nome}")
            return self

        def __exit__(self, tipo, erro, _tb):
            registro.append({"agente": nome, "segundos": round(time.time() - self.inicio, 1),
                             "ok": erro is None, "erro": None if erro is None else str(erro)[:300]})
            return False
    return _Etapa()


def tentar(registro: list, nome: str, funcao, reserva):
    """Para agentes de IA: se falharem, a edição segue com a reserva e o Revisor segura a publicação."""
    try:
        with etapa(registro, nome):
            return funcao()
    except Exception:
        traceback.print_exc()
        return reserva


def gerar(dados_dir: Path, data_edicao: str, coletar: bool) -> Path:
    pasta = EDICOES / data_edicao
    pasta.mkdir(parents=True, exist_ok=True)
    registro: list = []
    cliente = ia.novo_cliente() if ia.disponivel() else None

    if coletar:
        with etapa(registro, "Coletor"):
            coleta.coletar(dados_dir)
    with etapa(registro, "Analista"):
        resultado, dados = motor.rodar(dados_dir, pasta)
    with etapa(registro, "Arte: gráfico histórico"):
        grafico.historico(resultado, dados, pasta / "historico.png")
        grafico.historico(resultado, dados, pasta / "historico_celular.png", mobile=True)

    dossie = tentar(registro, "Buscador", lambda: buscador.pesquisar(dados, data_edicao, cliente),
                    {"eventos": [], "agenda": [], "descartados": [], "modo": "falhou"})
    (pasta / "pesquisa.json").write_text(json.dumps(dossie, ensure_ascii=False, indent=2))
    print(f"  Dossiê: {len(dossie.get('eventos', []))} eventos, {len(dossie.get('agenda', []))} itens de agenda, "
          f"{len(dossie.get('descartados', []))} descartados ({dossie.get('modo')})")

    texto, modo = tentar(registro, "Redator", lambda: redator.escrever(dados, dossie, data_edicao, cliente),
                         redator.escrever(dados, {"eventos": []}, data_edicao))
    (pasta / "edicao.md").write_text(texto)

    copy = tentar(registro, "Copy", lambda: copywriter.escrever(dados, texto, data_edicao, cliente),
                  {**copywriter.padrao(dados, data_edicao), "modo": "padrão (falhou)", "ajustes": []})
    (pasta / "copy.json").write_text(json.dumps(copy, ensure_ascii=False, indent=2))
    (pasta / "redes.md").write_text(
        f"# Redes sociais — {data_edicao}\n\n## Instagram (use card.png)\n\n{copy['legenda_instagram']}\n\n"
        f"## X\n\n{copy['post_x']}\n\n## LinkedIn\n\n{copy['post_linkedin']}\n")

    with etapa(registro, "Arte: card das redes"):
        grafico.card(dados, data_edicao, pasta / "card.png", copy["chamada_card"])
    with etapa(registro, "Revisor"):
        revisao = revisor.checar(texto, dados, dossie, copy)
    revisao.update({"agentes": registro, "modo_redator": modo, "modo_buscador": dossie.get("modo"),
                    "modo_copy": copy.get("modo")})
    (pasta / "revisao.json").write_text(json.dumps(revisao, ensure_ascii=False, indent=2))
    (pasta / "resumo_pr.md").write_text(resumo_pr(dados, dossie, copy, revisao))

    if os.environ.get("GITHUB_OUTPUT"):  # avisa o robô do GitHub qual edição foi gerada
        with open(os.environ["GITHUB_OUTPUT"], "a") as saida:
            saida.write(f"data={data_edicao}\naprovado={'sim' if revisao['aprovado'] else 'nao'}\n")
    print(f"\nEdição {data_edicao}: {'APROVADA' if revisao['aprovado'] else 'PRECISA DE VOCÊ'} pelo Revisor.")
    for c in revisao["checagens"]:
        print(f"  {'ok ' if c['ok'] else ('XX ' if c['bloqueia'] else '!! ')} {c['regra']}"
              + ("" if c["ok"] else f" — {c['detalhe']}"))
    return pasta


def resumo_pr(dados: dict, dossie: dict, copy: dict, revisao: dict) -> str:
    linhas = "\n".join(f"| {'✅' if c['ok'] else ('⛔' if c['bloqueia'] else '⚠️')} {c['regra']} | {c['detalhe'] if not c['ok'] else ''} |"
                       for c in revisao["checagens"])
    eventos = "\n".join(f"- **{e['titulo']}** ({e['regiao']}, {e['status']})" for e in dossie.get("eventos", [])[:6])
    veredito = "✅ **Aprovada pelo Revisor.**" if revisao["aprovado"] else "⛔ **O Revisor segurou esta edição.** Veja abaixo."
    return f"""## Termômetro: {dados['valor']} · {dados['nivel']} (leitura de {grafico.mes_curto(dados['referencia'])})

{veredito}

**Assunto do e-mail:** {copy['assuntos_email'][copy['assunto_escolhido']]}
**Pré-cabeçalho:** {copy['pre_cabecalho']}

| Regra | Detalhe |
|---|---|
{linhas}

### O que o Buscador encontrou
{eventos or '_Nada: Buscador sem chave de IA ou com falha._'}

### Para publicar
Toque em **Merge pull request**. O site atualiza e a newsletter segue para o beehiiv sozinhos.
Para descartar esta edição, feche o pedido. Os arquivos estão em `edicoes/` (edição, card, legendas e pesquisa).
"""


def mais_recente() -> Path:
    pastas = sorted(p for p in EDICOES.iterdir() if (p / "revisao.json").exists())
    if not pastas:
        raise SystemExit("Nenhuma edição em edicoes/.")
    return pastas[-1]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", action="store_true")
    p.add_argument("--newsletter", action="store_true")
    p.add_argument("--aprovado", action="store_true")
    p.add_argument("--so-coleta", action="store_true")
    p.add_argument("--dados", default=str(RAIZ / "dados"), help="pasta dos dados baixados")
    p.add_argument("--sem-coleta", action="store_true", help="usa os dados já baixados")
    p.add_argument("--data", help="data da edição (AAAA-MM-DD); padrão: hoje em Brasília")
    a = p.parse_args()
    if a.site:
        site.gerar(EDICOES, RAIZ / "_site")
    elif a.so_coleta:
        coleta.coletar(Path(a.dados))
    elif a.newsletter:
        pasta = mais_recente()
        if (pasta / "enviado.json").exists():
            print(f"A edição {pasta.name} já foi enviada ao beehiiv; nada a fazer.")
        elif publicar.newsletter(pasta):
            (pasta / "enviado.json").write_text(json.dumps(
                {"enviado_em": pd.Timestamp.now(tz="America/Sao_Paulo").isoformat()}, ensure_ascii=False))
    elif a.aprovado:
        sys.exit(0 if json.loads((mais_recente() / "revisao.json").read_text())["aprovado"] else 1)
    else:
        data = a.data or pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
        gerar(Path(a.dados), data, coletar=not a.sem_coleta)


if __name__ == "__main__":
    main()
