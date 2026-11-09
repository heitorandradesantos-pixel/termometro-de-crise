#!/usr/bin/env python3
"""Programa principal do Termômetro de Crise.

    python rodar.py                 gera a edição da semana com todos os agentes
    python rodar.py --site          monta o site com as edições da pasta edicoes/
    python rodar.py --newsletter    manda a edição mais recente à newsletter (Kit ou beehiiv)
    python rodar.py --aprovado      termina com código 0 se o Revisor aprovou a edição mais recente
    python rodar.py --so-coleta     só baixa os dados (o robô roda os testes antes de chamar a IA)
    python rodar.py --diario        atualização de dia útil: motor mundial, Correspondente e panorama do WhatsApp
    python rodar.py --design        squad de design: auditoria do site + agentes de UI e UX (relatório em design/)
    python rodar.py --conselho      conselho de monetização: marketing, comportamento, vendas, SEO, UX e regras debatem

Agentes, em ordem: Coletor → Analista → Arte (gráfico) → Buscador → SEO → Redator → Copy → Arte (card) → Revisor.
Todo dia útil: Coletor mundial → Analista mundial → Correspondente → Panorama → conferência.
Toda semana: Editor do site → auditoria automática (Playwright + axe-core) → agente de UI → agente de UX → relatório.
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

from termometro import (acoes, bcb, buscador, coleta, plantao, config, conselho, copywriter, correspondente, design, grafico, ia, motor,  # noqa: E402
                        mundo, paginas, panorama, publicar, redator, revisor, seo, site)

EDICOES = RAIZ / "edicoes"
DIARIO = RAIZ / "diario"
FALHAS_ACEITAS = 7  # séries de país que podem faltar num dia sem segurar o panorama (de cerca de 60)


def coleta_mundo(dados_dir: Path, coletar: bool) -> None:
    if coletar or not (dados_dir / "mundo" / "coleta_mundo.json").exists():
        mundo.coletar(dados_dir / "mundo")


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
    regional = tentar(registro, "Analista mundial",
                      lambda: (coleta_mundo(dados_dir, coletar), mundo.rodar(dados_dir / "mundo", pasta))[1], None)
    if regional:  # o Redator, o Copy e o Revisor passam a enxergar as regiões e o Brasil
        dados["regioes"] = [{k: r.get(k) for k in ("nome", "valor", "nivel")} for r in regional["regioes"]
                            if r.get("valor") is not None]
        if regional.get("brasil", {}).get("valor") is not None:
            dados["brasil"] = {k: regional["brasil"].get(k) for k in ("valor", "nivel", "referencia")}
    with etapa(registro, "Arte: gráfico histórico"):
        grafico.historico(resultado, dados, pasta / "historico.png")
        grafico.historico(resultado, dados, pasta / "historico_celular.png", mobile=True)

    dossie = tentar(registro, "Buscador", lambda: buscador.pesquisar(dados, data_edicao, cliente),
                    {"eventos": [], "agenda": [], "descartados": [], "modo": "falhou"})
    (pasta / "pesquisa.json").write_text(json.dumps(dossie, ensure_ascii=False, indent=2))
    print(f"  Dossiê: {len(dossie.get('eventos', []))} eventos, {len(dossie.get('agenda', []))} itens de agenda, "
          f"{len(dossie.get('descartados', []))} descartados ({dossie.get('modo')})")

    pauta = tentar(registro, "SEO", lambda: seo.pauta(dados, dossie, data_edicao, cliente), {})
    (pasta / "seo.json").write_text(json.dumps(pauta, ensure_ascii=False, indent=2))
    if pauta.get("palavra_chave"):
        dados["seo"] = pauta
        print(f"  Pauta de SEO: '{pauta['palavra_chave']}' + {len(pauta['secundarias'])} secundárias")

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


def diario(dados_dir: Path, data: str, coletar: bool = True) -> Path:
    """Atualização de dia útil: números do mundo, explicações com notícias e o panorama do WhatsApp."""
    pasta, historico = DIARIO / data, DIARIO / "historico"
    pasta.mkdir(parents=True, exist_ok=True)
    registro: list = []
    with etapa(registro, "Coletor mundial"):
        coleta_rel = mundo.coletar(dados_dir / "mundo") if coletar else \
            json.loads((dados_dir / "mundo" / "coleta_mundo.json").read_text())
    falhas = sorted(k for k, v in coleta_rel.items() if str(v).startswith("FALHOU"))
    with etapa(registro, "Analista mundial"):
        regional = mundo.rodar(dados_dir / "mundo", historico)
        (historico / "mundo.json").replace(pasta / "mundo.json")
    bc = tentar(registro, "Banco Central", lambda: bcb.coletar(data), None) if coletar else None
    if coletar:
        tentar(registro, "Cotações das empresas", lambda: acoes.gravar(pasta, data), None)
    if bc is not None:
        (pasta / "bcb.json").write_text(json.dumps(bc, ensure_ascii=False, indent=1))
    cliente = ia.novo_cliente() if ia.disponivel() else None
    corr = tentar(registro, "Correspondente", lambda: correspondente.pesquisar(regional, data, cliente),
                  {"regioes": {}, "modo": "falhou"})
    (pasta / "correspondente.json").write_text(json.dumps(corr, ensure_ascii=False, indent=1))

    dias_antes = [d for d in paginas.dias_do_diario(DIARIO) if d.name < data][-10:]
    anteriores = [{**json.loads((d / "mundo.json").read_text()), "_data": d.name} for d in dias_antes
                  if (d / "mundo.json").exists()]
    anterior = anteriores[-1] if anteriores else None
    recentes = [(d / "panorama.txt").read_text() for d in dias_antes if (d / "panorama.txt").exists()]
    with etapa(registro, "Panorama"):
        destaque = panorama.marco(regional, anteriores, recentes)
        texto = panorama.montar(regional, corr, anterior, data, bc=bc, destaque=destaque)
        conferencia = panorama.checar(texto, regional, bc)
        if not conferencia["aprovado"]:  # sem as manchetes, fica só o que o programa calculou
            texto = panorama.montar(regional, None, anterior, data, noticias=[], bc=bc, destaque=destaque)
            conferencia = {**panorama.checar(texto, regional, bc), "sem_noticias": True}
    (pasta / "panorama.txt").write_text(texto)

    noticias = correspondente.todas_as_noticias(corr)
    descartes = [d for r in corr.get("regioes", {}).values() for d in r.get("descartados", [])]
    aprovado = conferencia["aprovado"] and len(falhas) <= FALHAS_ACEITAS
    revisao = {"aprovado": aprovado, "panorama": conferencia, "series_que_falharam": falhas,
               "noticias": len(noticias), "descartes": descartes, "modo_correspondente": corr.get("modo"),
               "agentes": registro}
    (pasta / "revisao.json").write_text(json.dumps(revisao, ensure_ascii=False, indent=1))
    (pasta / "resumo.md").write_text(
        f"## Panorama de {pd.Timestamp(data):%d/%m/%Y}\n\n"
        + ("✅ Conferido. " if aprovado else "⛔ **O robô segurou a publicação automática.** ")
        + f"{len(noticias)} notícias com fonte, {len(descartes)} descartadas na conferência.\n\n"
        + (f"Séries que falharam: {', '.join(falhas)}\n\n" if falhas else "")
        + (f"Problemas no panorama: {', '.join(conferencia['problemas'])}\n\n" if conferencia["problemas"] else "")
        + f"### Texto para o WhatsApp\n\n```\n{texto}\n```\n\nToque em **Merge** para publicar no site.\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as saida:
            saida.write(f"data={data}\naprovado={'sim' if aprovado else 'nao'}\n")
    print(f"\nPanorama de {data}: {'APROVADO' if aprovado else 'SEGURADO'} · {len(noticias)} notícias, "
          f"{len(descartes)} descartes, {len(falhas)} séries com falha\n\n{texto}")
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


JANELA_PARCIAL = 40  # minutos: o horário de reserva (meia hora depois) não repete uma leitura que já saiu


def _minutos(hora: str) -> int:
    h, m = hora.split("h")
    return int(h) * 60 + int(m or 0)


def recente(arquivo: Path, hora: str) -> bool:
    """A leitura parcial gravada nesse arquivo foi feita há menos de JANELA_PARCIAL minutos de `hora`?"""
    if not arquivo.exists():
        return False
    antes = (json.loads(arquivo.read_text()).get("parcial") or {}).get("hora")
    return bool(antes) and 0 <= _minutos(hora) - _minutos(antes) < JANELA_PARCIAL


def parcial(dados_dir: Path, data: str, hora: str, coletar: bool = True) -> Path | None:
    """Leitura do meio do dia (11h e 14h): só os números, sem notícias nem panorama, que seguem no fechamento.

    Não mexe num dia que já fechou (com panorama) e não publica se faltarem séries demais."""
    pasta, historico = DIARIO / data, DIARIO / "historico"
    if (pasta / "panorama.txt").exists():
        print(f"O fechamento de {data} já saiu; a leitura parcial não sobrescreve.")
        return None
    if recente(pasta / "mundo.json", hora):
        print(f"Já há uma leitura parcial de {data} há menos de {JANELA_PARCIAL} minutos; nada a fazer.")
        return None
    rel = mundo.coletar(dados_dir / "mundo") if coletar else \
        json.loads((dados_dir / "mundo" / "coleta_mundo.json").read_text())
    falhas = sorted(k for k, v in rel.items() if str(v).startswith("FALHOU"))
    if len(falhas) > FALHAS_ACEITAS:
        print(f"{len(falhas)} séries falharam ({', '.join(falhas)}); fica a leitura anterior.")
        return None
    pasta.mkdir(parents=True, exist_ok=True)
    regional = mundo.rodar(dados_dir / "mundo", historico)
    regional["parcial"] = {"hora": hora}
    (pasta / "mundo.json").write_text(json.dumps(regional, ensure_ascii=False, indent=1))
    (historico / "mundo.json").unlink(missing_ok=True)
    if coletar:
        try:
            acoes.gravar(pasta, data)
        except Exception as erro:  # noqa: BLE001 — sem cotações novas, a página usa as anteriores
            print(f"Cotações das empresas falharam: {erro}")
    print(f"Leitura parcial de {data} às {hora}: mundo em {(regional.get('mundo') or {}).get('valor')}.")
    return pasta


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", action="store_true")
    p.add_argument("--newsletter", action="store_true")
    p.add_argument("--aprovado", action="store_true")
    p.add_argument("--so-coleta", action="store_true")
    p.add_argument("--diario", action="store_true", help="atualização de dia útil (mundo, notícias e panorama)")
    p.add_argument("--parcial", action="store_true", help="leitura do meio do dia: só os números do mundo")
    p.add_argument("--plantao", action="store_true", help="Plantão: notícia de dinheiro do momento, com fonte")
    p.add_argument("--whatsapp", choices=["preparar", "concluir", "roteiros", "fimdesemana"],
                   help="WhatsApp: prepara o envio do fechamento (card, balanço e panorama) ou registra o resultado")
    p.add_argument("--teste", action="store_true", help="WhatsApp: prepara o envio para o próprio número")
    p.add_argument("--tipo", choices=["fechamento", "abertura"], default="fechamento", help="WhatsApp: o que enviar")
    p.add_argument("--roteiro", choices=["abertura", "fechamento", "explica"],
                   help="Roteirista: escreve o roteiro do Reel (abertura e fechamento a partir da mensagem preparada "
                        "para o WhatsApp; explica a partir dos artigos do Plantão do dia)")
    p.add_argument("--pasta", default=str(RAIZ / "_whatsapp"), help="WhatsApp: pasta do envio")
    p.add_argument("--tema", default="", help="Plantão: assunto escolhido pelo editor (pula a pauta automática)")
    p.add_argument("--design", action="store_true", help="auditoria do site e avaliação dos agentes de UI e UX")
    p.add_argument("--referencias", action="store_true",
                   help="Referências: analisa os Reels novos dos criadores que o Heitor acompanha (API do Instagram)")
    p.add_argument("--conselho", action="store_true", help="conselho de monetização: os agentes debatem e fecham um plano")
    p.add_argument("--dados", default=str(RAIZ / "dados"), help="pasta dos dados baixados")
    p.add_argument("--sem-coleta", action="store_true", help="usa os dados já baixados")
    p.add_argument("--data", help="data da edição (AAAA-MM-DD); padrão: hoje em Brasília")
    a = p.parse_args()
    if a.site:
        site.gerar(EDICOES, RAIZ / "_site")
    elif a.conselho:
        data = a.data or pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
        r = conselho.rodar(RAIZ, RAIZ / "conselho" / data, data)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as saida:
                saida.write(f"data={data}\n")
        print(r["ata"])
    elif a.design:
        data = a.data or pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
        site.gerar(EDICOES, RAIZ / "_site")
        r = design.rodar(RAIZ / "_site", RAIZ / "design" / data, data)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as saida:
                saida.write(f"data={data}\n")
        print(r["relatorio"])
    elif a.diario:
        data = a.data or pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
        diario(Path(a.dados), data, coletar=not a.sem_coleta)
    elif a.roteiro:
        from termometro import roteirista
        roteirista.rodar(DIARIO, a.roteiro, Path(a.pasta), a.data or "")
    elif a.whatsapp:
        from termometro import whatsapp
        if a.whatsapp == "roteiros":
            dia = a.data or pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
            print(whatsapp.preparar_roteiros(DIARIO, dia, Path(a.pasta)))
        elif a.whatsapp == "fimdesemana":
            from termometro import fimdesemana
            dia = a.data or pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
            print(fimdesemana.preparar(DIARIO, dia, Path(a.pasta)))
        elif a.whatsapp == "preparar":
            dias = [d.name for d in paginas.dias_do_diario(DIARIO) if (d / "panorama.txt").exists()]
            dia = a.data or (dias[-1] if dias else "")
            print(whatsapp.preparar(DIARIO, dia, Path(a.pasta), teste=a.teste, tipo=a.tipo))
        else:
            print(whatsapp.concluir(DIARIO, Path(a.pasta)))
    elif a.referencias:
        from termometro import referencias
        r = referencias.rodar(DIARIO, DIARIO / "referencias")
        print(f"Referências: {len(r['notas'])} vídeo(s) novo(s), {len(r['pautas'])} pauta(s) para o Plantão.")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as saida:
                saida.write(f"pautas={json.dumps(r['pautas'], ensure_ascii=False)}\n")
    elif a.plantao:
        gravados = plantao.rodar(DIARIO, tema=a.tema, turno=os.environ.get("PLANTAO_TURNO", ""),
                                 sugerido=os.environ.get("PLANTAO_ORIGEM", "") == "referencias")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as saida:
                saida.write(f"publicar={'sim' if gravados else 'nao'}\n")
    elif a.parcial:
        agora = pd.Timestamp.now(tz="America/Sao_Paulo")
        pasta = parcial(Path(a.dados), a.data or agora.strftime("%Y-%m-%d"), agora.strftime("%Hh%M"),
                        coletar=not a.sem_coleta)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as saida:
                saida.write(f"publicar={'sim' if pasta else 'nao'}\n")
    elif a.so_coleta:
        coleta.coletar(Path(a.dados))
    elif a.newsletter:
        pasta = mais_recente()
        if (pasta / "enviado.json").exists():
            print(f"A edição {pasta.name} já foi para a newsletter; nada a fazer.")
        elif os.environ.get("KIT_API_KEY") and publicar.newsletter_kit(pasta):
            (pasta / "enviado.json").write_text(json.dumps(
                {"enviado_em": pd.Timestamp.now(tz="America/Sao_Paulo").isoformat(), "plataforma": "kit",
                 "modo": publicar.modo_kit()}, ensure_ascii=False))
        elif not os.environ.get("KIT_API_KEY") and publicar.newsletter(pasta):
            (pasta / "enviado.json").write_text(json.dumps(
                {"enviado_em": pd.Timestamp.now(tz="America/Sao_Paulo").isoformat(), "plataforma": "beehiiv"},
                ensure_ascii=False))
    elif a.aprovado:
        sys.exit(0 if json.loads((mais_recente() / "revisao.json").read_text())["aprovado"] else 1)
    else:
        data = a.data or pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
        gerar(Path(a.dados), data, coletar=not a.sem_coleta)


if __name__ == "__main__":
    main()
