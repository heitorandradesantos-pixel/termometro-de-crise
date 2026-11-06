"""Squad de design: o agente de UI e o agente de UX olham o site de verdade, toda semana.

1. Auditoria automática (sem IA): abre cada página num navegador (celular e computador), tira os prints e mede
   o que dá para medir: rolagem horizontal, alvos de toque pequenos, fonte mínima, contraste (WCAG AA),
   títulos, textos alternativos, foco visível, link para pular ao conteúdo, peso da página e, quando
   disponível, o axe-core (o motor de acessibilidade mais usado do mundo).
2. Agente de UI: recebe os prints e os números e avalia hierarquia, tipografia, cor, gráficos e consistência,
   seguindo o manual termometro/manuais/ui.md.
3. Agente de UX: avalia se um leigo entende, confia e age, com as heurísticas de Nielsen e a WCAG,
   seguindo o manual termometro/manuais/ux.md.
4. Relatório: notas, o que está bom, problemas por gravidade e o plano da semana (o que fazer primeiro).
"""

import base64
import functools
import http.server
import json
import os
import threading
from pathlib import Path

from . import config, ia

TELAS = {"celular": {"width": 390, "height": 844}, "computador": {"width": 1280, "height": 900}}
# Portais de referência que os agentes de UI e UX usam para comparar (aprender, nunca copiar)
REFERENCIAS = {"Investing.com Brasil": "https://br.investing.com/", "InfoMoney": "https://www.infomoney.com.br/",
               "CNN Fear & Greed": "https://edition.cnn.com/markets/fear-and-greed",
               "Bloomberg Markets": "https://www.bloomberg.com/markets", "Reuters Markets": "https://www.reuters.com/markets/"}
ESFORCO = ["pequeno", "médio", "grande"]

DIMENSOES = {
    "ui": {"hierarquia": "o olho cai no que importa", "tipografia": "escala, tamanhos, linhas",
           "cor_e_contraste": "paleta e WCAG", "graficos": "gráficos claros e anotados",
           "consistencia": "mesmos padrões em todo o site", "celular": "visual no celular"},
    "ux": {"clareza_para_leigo": "entende em 5 segundos", "navegacao": "acha o que procura",
           "confianca": "fonte, data, método, sem exagero", "acessibilidade": "WCAG 2.2 AA",
           "celular": "uso no celular", "conversao": "ação principal clara, sem truque"},
}

PAPEIS = {
    "ui": f"""Você é o agente de UI do "{config.NOME}", o diretor de arte da squad. Avalie a interface visual
das páginas a partir dos prints (celular e computador) e dos números da auditoria automática. Seja específico:
cite a página, a tela e o elemento, e proponha mudanças com valores concretos. Não reescreva o produto: melhore-o.
Quando houver prints de portais de referência (Investing, InfoMoney, CNN, Bloomberg, Reuters), compare: o que eles fazem
melhor e que caberia no nosso estilo, sem copiar. Mantenha a identidade própria do Termômetro, com um toque brasileiro.
Escreva em português do Brasil.""" + config.manual("ui"),
    "ux": f"""Você é o agente de UX do "{config.NOME}", o pesquisador sênior da squad. Avalie se um brasileiro
leigo, no celular, entende o que é o site, quanto está o termômetro, por quê, e o que fazer em seguida, e se ele
confia no que vê. Use os prints (celular e computador) e os números da auditoria automática. Compare com os prints
dos portais de referência quando houver (posição dos botões, como mostram números, o que vira hábito). Seja específico:
cite a página, a tela e o elemento. Escreva em português do Brasil.""" + config.manual("ux", "redacao"),
}


def ferramenta(papel: str, paginas: list[str]) -> dict:
    dims = DIMENSOES[papel]
    return {
        "name": "registrar_avaliacao",
        "description": f"Registra a avaliação de {papel.upper()} do site.",
        "input_schema": {
            "type": "object",
            "properties": {
                "notas": {"type": "object", "description": "Nota de 0 a 10 para cada dimensão",
                          "properties": {k: {"type": "integer", "minimum": 0, "maximum": 10, "description": v}
                                         for k, v in dims.items()},
                          "required": list(dims)},
                "pontos_fortes": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string"}},
                "achados": {"type": "array", "minItems": 3, "maxItems": 12, "items": {
                    "type": "object",
                    "properties": {
                        "pagina": {"type": "string", "enum": paginas},
                        "tela": {"type": "string", "enum": ["celular", "computador", "ambas"]},
                        "severidade": {"type": "integer", "minimum": 1, "maximum": 4,
                                       "description": "1 cosmético, 2 pequeno, 3 grande, 4 catástrofe"},
                        "principio": {"type": "string", "description": "Heurística ou regra violada"},
                        "problema": {"type": "string"}, "evidencia": {"type": "string"},
                        "sugestao": {"type": "string", "description": "Mudança concreta, com valores"},
                        "esforco": {"type": "string", "enum": ESFORCO},
                    },
                    "required": ["pagina", "tela", "severidade", "principio", "problema", "sugestao", "esforco"]}},
                "primeiro_passo": {"type": "string", "description": "A única coisa a fazer primeiro, e por quê"},
                "resposta_ao_dono": {"type": "string", "description": "Se houver pergunta do dono, a resposta direta, "
                                     "com recomendações concretas (cores em hex, tamanhos, posições)"},
            },
            "required": ["notas", "pontos_fortes", "achados", "primeiro_passo"],
        },
    }


# ---------------------------------------------------------------- auditoria automática
MEDIR = r"""() => {
  const vis = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const corta = (t, n) => (t || '').replace(/\s+/g, ' ').trim().slice(0, n);
  const o = {};
  o.rolagem_horizontal = document.documentElement.scrollWidth > window.innerWidth + 1;
  const alvos = [...document.querySelectorAll('a[href], button, input, select, textarea, [role=button]')].filter(vis);
  // links no meio de uma frase são exceção na WCAG 2.5.8
  const noTexto = a => { const p = a.parentElement; return a.tagName === 'A' && p &&
    ['P', 'LI', 'SPAN', 'TD', 'EM', 'STRONG'].includes(p.tagName) && (p.textContent.length - a.textContent.length) > 15; };
  const pequenos = alvos.filter(a => { const r = a.getBoundingClientRect();
    return (r.width < 24 || r.height < 24) && !noTexto(a) && !a.closest('svg[aria-hidden="true"]'); });
  o.alvos_total = alvos.length; o.alvos_pequenos = pequenos.length;
  o.exemplos_alvos = pequenos.slice(0, 5).map(a => { const r = a.getBoundingClientRect();
    return `${corta(a.textContent || a.getAttribute('aria-label') || a.tagName, 40)} (${Math.round(r.width)}×${Math.round(r.height)})`; });
  const textos = [...document.querySelectorAll('body *')].filter(el => vis(el) &&
    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 1));
  let menor = 99; const miudos = [];
  for (const el of textos) { const fs = parseFloat(getComputedStyle(el).fontSize);
    menor = Math.min(menor, fs); if (fs < 12) miudos.push(`${corta(el.textContent, 40)} (${fs}px)`); }
  o.menor_fonte = menor; o.textos_menores_que_12px = miudos.length; o.exemplos_fonte = miudos.slice(0, 5);
  const rgb = s => { const m = (s || '').match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(',').map(parseFloat); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const fundo = el => { for (let e = el; e; e = e.parentElement) { const c = rgb(getComputedStyle(e).backgroundColor);
    if (c && c.a > 0.5) return c; } return {r: 255, g: 255, b: 255, a: 1}; };
  const falhas = [];
  for (const el of textos) { const cs = getComputedStyle(el), fg = rgb(cs.color); if (!fg) continue;
    const L1 = lum(fg), L2 = lum(fundo(el)), razao = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const fs = parseFloat(cs.fontSize), grande = fs >= 24 || (parseInt(cs.fontWeight) >= 700 && fs >= 18.66);
    if (razao < (grande ? 3 : 4.5)) falhas.push(`${corta(el.textContent, 40)} (${razao.toFixed(2)}:1)`); }
  o.contraste_falhas = falhas.length; o.exemplos_contraste = falhas.slice(0, 5);
  o.h1 = document.querySelectorAll('h1').length;
  const niveis = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => +h.tagName[1]);
  o.titulos_pulados = niveis.filter((n, i) => i > 0 && n - niveis[i - 1] > 1).length;
  o.imagens_sem_alt = [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).length;
  o.graficos_sem_rotulo = [...document.querySelectorAll('svg')].filter(s => vis(s) && s.getAttribute('aria-hidden') !== 'true' &&
    !s.getAttribute('aria-label') && !s.querySelector('title')).length;
  o.idioma = document.documentElement.lang || '';
  o.titulo = document.title; o.tem_descricao = !!document.querySelector('meta[name=description]');
  o.link_para_pular = [...document.querySelectorAll('a[href^="#"]')].some(a => /pular|conte[uú]do|skip/i.test(a.textContent));
  o.nova_aba_sem_aviso = [...document.querySelectorAll('a[target=_blank]')].filter(a =>
    !/nova aba|abre em/i.test((a.getAttribute('aria-label') || '') + a.textContent + (a.title || ''))).length;
  const v = document.querySelector('.valor');
  o.numero_sem_rolar = v ? v.getBoundingClientRect().bottom <= window.innerHeight : null;
  const nav = performance.getEntriesByType('navigation')[0];
  o.peso_kb = Math.round(performance.getEntriesByType('resource').reduce((s, r) => s + (r.transferSize || r.encodedBodySize || 0), 0) / 1024
    + (nav ? (nav.transferSize || nav.encodedBodySize || 0) / 1024 : 0));
  o.elementos = document.querySelectorAll('*').length;
  return o;
}"""

FOCO = r"""() => { const e = document.activeElement; if (!e || e === document.body) return {foco: null};
  const cs = getComputedStyle(e);
  return {foco: (e.textContent || e.getAttribute('aria-label') || e.tagName).trim().slice(0, 40),
          visivel: (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) || cs.boxShadow !== 'none'}; }"""

AXE = r"""async () => { const r = await axe.run(document, {runOnly: {type: 'tag',
  values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']}});
  return r.violations.map(v => ({id: v.id, impacto: v.impact, ajuda: v.help, nos: v.nodes.length,
    exemplo: v.nodes[0] ? v.nodes[0].target.join(' ') : ''})); }"""


def paginas_para_auditar(site: Path) -> dict[str, str]:
    """Nome legível → caminho. Uma página de cada tipo, para caber na avaliação."""
    escolhidas = {"Início": "index.html"}
    regioes = sorted((site / "regioes").glob("*.html")) if (site / "regioes").exists() else []
    if regioes:
        escolhidas["Região"] = "regioes/" + (("oriente-medio.html" if (site / "regioes" / "oriente-medio.html").exists()
                                             else regioes[0].name))
    if (site / "paises" / "brasil.html").exists():
        escolhidas["País (Brasil)"] = "paises/brasil.html"
    for nome, caminho in (("Ranking", "mundo.html"), ("Panorama", "panorama.html"), ("Metodologia", "metodologia.html")):
        if (site / caminho).exists():
            escolhidas[nome] = caminho
    edicoes = sorted((site / "edicoes").glob("20*.html")) if (site / "edicoes").exists() else []
    if edicoes:
        escolhidas["Edição"] = f"edicoes/{edicoes[-1].name}"
    return escolhidas


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _servidor(site: Path):
    manipulador = functools.partial(_Silencioso, directory=str(site))
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manipulador)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


def links_quebrados(site: Path) -> list[str]:
    import re
    quebrados = []
    for arquivo in site.rglob("*.html"):
        for href in re.findall(r'href="([^"#?]+)"', arquivo.read_text()):
            if href.startswith(("http", "mailto:", "//")):
                continue
            alvo = (arquivo.parent / href).resolve()
            if not alvo.exists():
                quebrados.append(f"{arquivo.relative_to(site)} → {href}")
    return quebrados


def auditar(site: Path, pasta: Path, axe_js: str | None = None) -> dict:
    """Abre cada página no celular e no computador, mede e tira os prints."""
    from playwright.sync_api import sync_playwright

    axe_js = axe_js or os.environ.get("AXE_JS")
    prints = pasta / "prints"
    prints.mkdir(parents=True, exist_ok=True)
    paginas = paginas_para_auditar(site)
    servidor = _servidor(site)
    base = f"http://127.0.0.1:{servidor.server_address[1]}/"
    resultado = {"paginas": {}, "links_quebrados": links_quebrados(site), "axe": bool(axe_js and Path(axe_js).exists())}
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            for nome, caminho in paginas.items():
                resultado["paginas"][nome] = {"caminho": caminho}
                for tela, tamanho in TELAS.items():
                    aba = navegador.new_page(viewport=tamanho, device_scale_factor=1)
                    try:
                        aba.goto(base + caminho, wait_until="load", timeout=30000)
                    except Exception:  # fontes externas lentas não podem travar a auditoria
                        pass
                    medidas = aba.evaluate(MEDIR)
                    if resultado["axe"]:  # antes do Tab: o link "pular" visível no foco cobre o topo de propósito
                        try:
                            aba.add_script_tag(path=axe_js)
                            medidas["axe"] = aba.evaluate(AXE)
                        except Exception as erro:
                            medidas["axe_erro"] = str(erro)[:200]
                    base_arquivo = f"{caminho.replace('/', '_').removesuffix('.html')}_{tela}"
                    aba.screenshot(path=str(prints / f"{base_arquivo}.png"), full_page=True)
                    altura = aba.evaluate("document.documentElement.scrollHeight")
                    telas = []
                    for i, topo in enumerate((0, tamanho["height"])):
                        if topo >= altura:
                            break
                        arquivo = prints / f"{base_arquivo}_{i + 1}.jpg"
                        aba.screenshot(path=str(arquivo), type="jpeg", quality=70, full_page=True,
                                       clip={"x": 0, "y": topo, "width": tamanho["width"],
                                             "height": min(tamanho["height"], altura - topo)})
                        telas.append(arquivo.name)
                    medidas["telas"] = telas
                    aba.keyboard.press("Tab")  # depois dos prints: o link "pular" aparece no foco
                    medidas["primeiro_tab"] = aba.evaluate(FOCO)
                    resultado["paginas"][nome][tela] = medidas
                    aba.close()
            resultado["referencias"] = referencias(navegador, prints)
            navegador.close()
    finally:
        servidor.shutdown()
    resultado["regras"] = regras(resultado)
    (pasta / "auditoria.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
    return resultado


def referencias(navegador, prints: Path) -> dict[str, list[str]]:
    """Primeira tela de cada portal de referência, no celular e no computador. Site que bloquear fica de fora."""
    if os.environ.get("SEM_REFERENCIAS"):
        return {}
    saida = {}
    for nome, url in REFERENCIAS.items():
        arquivos = []
        for tela, tamanho in TELAS.items():
            aba = navegador.new_page(viewport=tamanho, device_scale_factor=1, locale="pt-BR")
            try:
                aba.goto(url, wait_until="domcontentloaded", timeout=25000)
                aba.wait_for_timeout(2500)
                arquivo = prints / f"ref_{nome.split()[0].lower().replace('.', '')}_{tela}.jpg"
                aba.screenshot(path=str(arquivo), type="jpeg", quality=60)
                arquivos.append(arquivo.name)
            except Exception as erro:
                print(f"  referência {nome} ({tela}) indisponível: {type(erro).__name__}")
            finally:
                aba.close()
        if arquivos:
            saida[nome] = arquivos
    return saida


def regras(a: dict) -> list[dict]:
    """As checagens objetivas, como as do Revisor: passou ou não, com o detalhe."""
    def todas(func):
        return [(n, t, m) for n, pag in a["paginas"].items() for t in TELAS if (m := pag.get(t)) and func(m)]

    def lista(itens):
        return ", ".join(f"{n} ({t})" for n, t, _ in itens[:6])
    saida = []

    def regra(nome, falhas, detalhe=""):
        saida.append({"regra": nome, "ok": not falhas, "detalhe": detalhe if falhas else ""})
    f = todas(lambda m: m["rolagem_horizontal"])
    regra("Sem rolagem horizontal", f, lista(f))
    f = todas(lambda m: m["alvos_pequenos"] > 0)
    regra("Alvos de toque com pelo menos 24×24px", f,
          "; ".join(f"{n} ({t}): {', '.join(m['exemplos_alvos'][:3])}" for n, t, m in f[:4]))
    f = todas(lambda m: m["menor_fonte"] < 12)
    regra("Nenhum texto menor que 12px", f, "; ".join(f"{n} ({t}): {', '.join(m['exemplos_fonte'][:3])}" for n, t, m in f[:4]))
    f = todas(lambda m: m["contraste_falhas"] > 0)
    regra("Contraste de texto WCAG AA", f, "; ".join(f"{n} ({t}): {', '.join(m['exemplos_contraste'][:3])}" for n, t, m in f[:4]))
    f = todas(lambda m: m["h1"] != 1)
    regra("Exatamente um h1 por página", f, lista(f))
    f = todas(lambda m: m["titulos_pulados"] > 0)
    regra("Títulos sem pular nível", f, lista(f))
    f = todas(lambda m: m["imagens_sem_alt"] > 0 or m["graficos_sem_rotulo"] > 0)
    regra("Imagens e gráficos com texto alternativo", f, lista(f))
    f = todas(lambda m: not m["link_para_pular"])
    regra("Link para pular ao conteúdo", f, lista(f))
    f = todas(lambda m: (m.get("primeiro_tab") or {}).get("visivel") is False)
    regra("Foco visível no teclado", f, lista(f))
    f = todas(lambda m: m["nova_aba_sem_aviso"] > 0)
    regra("Links que abrem nova aba avisam", f, lista(f))
    f = [(n, t, m) for n, t, m in todas(lambda m: m["numero_sem_rolar"] is False) if t == "celular"]
    regra("Número do termômetro visível sem rolar (celular)", f, lista(f))
    f = todas(lambda m: any(v["impacto"] in ("critical", "serious") for v in m.get("axe", [])))
    if a.get("axe"):
        ids = sorted({v["id"] for _, _, m in f for v in m.get("axe", []) if v["impacto"] in ("critical", "serious")})
        regra("axe-core sem violações graves", f, ", ".join(ids))
    regra("Sem links internos quebrados", a["links_quebrados"], "; ".join(a["links_quebrados"][:5]))
    return saida


# ---------------------------------------------------------------- agentes de UI e UX
def _imagem(arquivo: Path) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.b64encode(arquivo.read_bytes()).decode()}}


def resumo_numeros(a: dict) -> str:
    linhas = []
    for nome, pag in a["paginas"].items():
        for tela in TELAS:
            m = pag.get(tela)
            if not m:
                continue
            axe = m.get("axe", [])
            linhas.append(f"- {nome} ({tela}): rolagem horizontal {'sim' if m['rolagem_horizontal'] else 'não'}; "
                          f"alvos <24px {m['alvos_pequenos']}/{m['alvos_total']}; menor fonte {m['menor_fonte']}px; "
                          f"falhas de contraste {m['contraste_falhas']}; h1 {m['h1']}; número sem rolar "
                          f"{m['numero_sem_rolar']}; peso {m['peso_kb']} KB; axe {len(axe)} violações"
                          + (f" ({', '.join(v['id'] for v in axe[:5])})" if axe else ""))
    regras_txt = "\n".join(f"- {'OK' if r['ok'] else 'FALHOU'}: {r['regra']} {r['detalhe']}" for r in a["regras"])
    return f"Números por página:\n" + "\n".join(linhas) + f"\n\nChecagens objetivas:\n{regras_txt}"


def pedido(a: dict, pasta: Path, papel: str) -> list:
    blocos = [{"type": "text", "text": f"Auditoria automática do site (prints a seguir):\n\n{resumo_numeros(a)}"}]
    for nome, pag in a["paginas"].items():
        if nome in ("Metodologia", "Edição") and papel == "ui":
            continue
        for tela in TELAS:
            for i, arq in enumerate((pag.get(tela) or {}).get("telas", [])[: 2 if nome == "Início" else 1]):
                blocos.append({"type": "text", "text": f"Print: {nome}, {tela}, tela {i + 1}"})
                blocos.append(_imagem(pasta / "prints" / arq))
    for nome, arquivos in (a.get("referencias") or {}).items():
        for arq in arquivos:
            if (pasta / "prints" / arq).exists():
                blocos.append({"type": "text", "text": f"Referência de mercado (para comparar, não copiar): {nome}, "
                                                       f"{'celular' if 'celular' in arq else 'computador'}"})
                blocos.append(_imagem(pasta / "prints" / arq))
    pergunta = os.environ.get("PERGUNTA_DO_DONO", "").strip()
    if pergunta:
        blocos.append({"type": "text", "text": f"PERGUNTA DO DONO DO PROJETO (responda em resposta_ao_dono, com a sua "
                                               f"opinião de especialista e recomendações concretas): {pergunta}"})
    blocos.append({"type": "text", "text": f"Faça a avaliação de {papel.upper()}: notas, pontos fortes, de 6 a 12 achados "
                                           "ordenados por gravidade, e o primeiro passo."})
    return blocos


def validar(bruto: dict, papel: str, paginas: list[str]) -> dict:
    dims = DIMENSOES[papel]
    notas = {k: max(0, min(10, int((bruto.get("notas") or {}).get(k, 0) or 0))) for k in dims}
    achados = []
    for x in bruto.get("achados", []):
        if not x.get("problema") or not x.get("sugestao"):
            continue
        achados.append({"pagina": x.get("pagina") if x.get("pagina") in paginas else "Geral",
                        "tela": x.get("tela") if x.get("tela") in ("celular", "computador", "ambas") else "ambas",
                        "severidade": max(1, min(4, int(x.get("severidade") or 1))),
                        "principio": str(x.get("principio", "")), "problema": str(x["problema"]),
                        "evidencia": str(x.get("evidencia", "")), "sugestao": str(x["sugestao"]),
                        "esforco": x.get("esforco") if x.get("esforco") in ESFORCO else "médio"})
    achados.sort(key=lambda x: (-x["severidade"], ESFORCO.index(x["esforco"])))
    return {"papel": papel, "notas": notas, "nota_geral": round(sum(notas.values()) / len(notas), 1),
            "pontos_fortes": [str(p) for p in bruto.get("pontos_fortes", [])][:5], "achados": achados,
            "primeiro_passo": str(bruto.get("primeiro_passo", "")),
            "resposta_ao_dono": str(bruto.get("resposta_ao_dono", "") or "")}


def avaliar(a: dict, pasta: Path, papel: str, cliente) -> dict:
    paginas = list(a["paginas"])
    bruto = ia.estruturado(cliente, PAPEIS[papel], pedido(a, pasta, papel), ferramenta(papel, paginas),
                           max_tokens=8000)
    return validar(bruto, papel, paginas)


# ---------------------------------------------------------------- relatório
def _tabela_achados(av: dict) -> str:
    sev = {4: "🔴 4", 3: "🟠 3", 2: "🟡 2", 1: "⚪ 1"}
    linhas = [f"| {sev[x['severidade']]} | {x['pagina']} ({x['tela']}) | {x['problema']} | {x['sugestao']} | {x['esforco']} |"
              for x in av["achados"]]
    return "| Gravidade | Onde | Problema | Sugestão | Esforço |\n|---|---|---|---|---|\n" + "\n".join(linhas)


def relatorio(data: str, a: dict, ui: dict | None, ux: dict | None) -> str:
    regras_ok = sum(r["ok"] for r in a["regras"])
    partes = [f"# Squad de design: relatório de {data}", ""]
    pergunta = os.environ.get("PERGUNTA_DO_DONO", "").strip()
    respostas = [av for av in (ui, ux) if av and av.get("resposta_ao_dono")]
    if pergunta and respostas:
        partes += [f"## Sua pergunta: {pergunta}", ""]
        partes += [f"**Agente de {av['papel'].upper()}:** {av['resposta_ao_dono']}\n" for av in respostas]
    if ui or ux:
        notas = " · ".join(f"**{av['papel'].upper()} {av['nota_geral']}/10**" for av in (ui, ux) if av)
        partes += [f"{notas} · checagens objetivas: **{regras_ok}/{len(a['regras'])}**", ""]
        plano = sorted([dict(x, papel=av["papel"]) for av in (ui, ux) if av for x in av["achados"] if x["severidade"] >= 3],
                       key=lambda x: (-x["severidade"], ESFORCO.index(x["esforco"])))[:6]
        if plano:
            partes += ["## Plano da semana (gravidade alta, menor esforço primeiro)", ""]
            partes += [f"{i}. **[{x['papel'].upper()}] {x['pagina']} ({x['tela']}):** {x['problema']} → {x['sugestao']}"
                       for i, x in enumerate(plano, 1)]
            partes.append("")
    else:
        partes += [f"Checagens objetivas: **{regras_ok}/{len(a['regras'])}**. Sem chave de IA: só a parte automática.", ""]
    partes += ["## Checagens objetivas", "", "| | Regra | Detalhe |", "|---|---|---|"]
    partes += [f"| {'✅' if r['ok'] else '⛔'} | {r['regra']} | {r['detalhe']} |" for r in a["regras"]]
    for av, titulo in ((ui, "Agente de UI"), (ux, "Agente de UX")):
        if not av:
            continue
        notas = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in av["notas"].items())
        partes += ["", f"## {titulo}: {av['nota_geral']}/10", "", f"Notas: {notas}.", "",
                   f"**Primeiro passo:** {av['primeiro_passo']}", "", "**O que está bom:**"]
        partes += [f"- {p}" for p in av["pontos_fortes"]]
        partes += ["", _tabela_achados(av)]
    partes += ["", "_Prints de cada página (celular e computador) nos arquivos da execução, na aba Actions._"]
    return "\n".join(partes) + "\n"


def rodar(site: Path, pasta: Path, data: str, cliente=None) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    a = auditar(site, pasta)
    ui = ux = None
    if cliente is not None or ia.disponivel():
        cliente = cliente or ia.novo_cliente()
        for papel in ("ui", "ux"):
            try:
                av = avaliar(a, pasta, papel, cliente)
                (pasta / f"{papel}.json").write_text(json.dumps(av, ensure_ascii=False, indent=1))
                ui, ux = (av, ux) if papel == "ui" else (ui, av)
            except Exception as erro:  # um agente com problema não derruba o relatório
                print(f"  Agente de {papel.upper()} falhou: {erro}")
    texto = relatorio(data, a, ui, ux)
    (pasta / "relatorio.md").write_text(texto[:60000])
    return {"auditoria": a, "ui": ui, "ux": ux, "relatorio": texto}
