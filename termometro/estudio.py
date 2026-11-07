"""Estúdio: a página de trabalho dos vídeos (fora do menu e fora do Google).

Para cada dia com roteiro do Roteirista, uma página com os vídeos do dia, prontos para o Google Flow: a legenda do
post, o texto da tela e as 6 cenas de 8 s, cada uma com a fala e o prompt, com botão de copiar. No topo, o prompt da
foto da Clara, para gerar uma vez e usar como "ingrediente" em todas as cenas da apresentadora.

Uso interno: NÃO vai para o site público (decisão do Heitor, 07/11/2026). Gera as páginas numa pasta local,
para conferir os vídeos do dia: estudio.gerar(Path("pasta"), Path("diario")).
"""

import html
import json
from pathlib import Path

from . import roteirista

DIAS = 14  # quantos dias ficam no estúdio
NOMES = {"abertura": "Abertura", "fechamento": "Fechamento", "explica": "Explica"}

CSS = """*{box-sizing:border-box}body{margin:0;background:#0f1722;color:#e8edf3;font:16px/1.5 system-ui,-apple-system,
'Segoe UI',Roboto,sans-serif}main{max-width:860px;margin:0 auto;padding:20px 16px 60px}a{color:#7cc4ff}
h1{font-size:1.5rem;margin:.2em 0}h2{font-size:1.2rem;margin:1.6em 0 .4em;padding-top:1em;border-top:1px solid #2a3646}
h3{font-size:1rem;margin:1em 0 .3em;color:#ffb35c}.suave{color:#9fb0c3;font-size:.92rem}
.caixa{background:#172231;border:1px solid #2a3646;border-radius:10px;padding:12px 14px;margin:8px 0}
.caixa pre{white-space:pre-wrap;word-wrap:break-word;margin:0;font:14px/1.45 ui-monospace,Menlo,Consolas,monospace;color:#dfe7f0}
button{background:#ffb35c;color:#111;border:0;border-radius:8px;padding:7px 12px;font-weight:600;cursor:pointer;
margin-top:8px}button.ok{background:#5cd18a}.cena{border-left:3px solid #ffb35c;padding-left:12px;margin:14px 0}
.cena.imagem{border-color:#7cc4ff}.selo{display:inline-block;font-size:.78rem;padding:1px 8px;border-radius:99px;
background:#2a3646;margin-left:6px}.mal{background:#7a2b2b}ol{padding-left:1.2em}li{margin:.3em 0}"""

JS = """document.querySelectorAll('button[data-copiar]').forEach(b=>b.addEventListener('click',async()=>{
const t=document.getElementById(b.dataset.copiar).innerText;try{await navigator.clipboard.writeText(t)}catch(e){
const a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');a.remove()}
const v=b.textContent;b.textContent='Copiado';b.classList.add('ok');setTimeout(()=>{b.textContent=v;b.classList.remove('ok')},1500)}))"""


def _pagina(titulo: str, corpo: str, raiz: str) -> str:
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">'
            f"<title>{html.escape(titulo)}</title><style>{CSS}</style></head><body><main>"
            f'<p class="suave"><a href="{raiz}estudio/index.html">Estúdio</a> · <a href="{raiz}index.html">Site</a></p>'
            f"{corpo}</main><script>{JS}</script></body></html>")


def _copiavel(ident: str, texto: str, rotulo: str = "Copiar") -> str:
    return (f'<div class="caixa"><pre id="{ident}">{html.escape(texto)}</pre>'
            f'<button type="button" data-copiar="{ident}">{rotulo}</button></div>')


def _ordem(arq: Path) -> tuple:
    tipo = arq.stem.split("-")[0]
    return ({"abertura": 0, "explica": 1, "fechamento": 2}.get(tipo, 3), arq.stat().st_mtime)


def _titulo(arq: Path, diario: Path, dia: str) -> str:
    tipo = arq.stem.split("-")[0]
    if tipo == "explica":
        artigo = diario / "plantao" / f"{dia}-{arq.stem[len('explica-'):]}.json"
        if artigo.exists():
            return f"Explica: {json.loads(artigo.read_text()).get('titulo', '')}"
    return NOMES.get(tipo, tipo.capitalize())


def roteiros_do_dia(diario: Path, dia: str) -> list[tuple[Path, dict]]:
    pasta = diario / dia / "roteiros"
    if not pasta.is_dir():
        return []
    saida = []
    for arq in sorted(pasta.glob("*.json"), key=_ordem):
        try:
            saida.append((arq, json.loads(arq.read_text())))
        except (OSError, json.JSONDecodeError):
            continue
    return saida


def bloco_video(n: int, arq: Path, r: dict, diario: Path, dia: str) -> str:
    base = f"v{n}"
    titulo = _titulo(arq, diario, dia)
    if not r.get("aprovado"):
        return (f'<h2>{html.escape(titulo)} <span class="selo mal">reprovado</span></h2>'
                f'<p class="suave">O roteiro não passou na conferência e não deve virar vídeo: '
                f'{html.escape("; ".join(r.get("problemas") or []))}</p>')
    cenas = r.get("cenas") or []
    aviso = "" if r.get("cenas_ok") else ' <span class="selo mal">cenas com problema</span>'
    partes = [f'<h2 id="{base}">{html.escape(titulo)} <span class="selo">{r.get("segundos", "?")} s</span>{aviso}</h2>',
              f'<p class="suave">Gancho: “{html.escape(r.get("gancho", {}).get("texto", ""))}”</p>',
              "<h3>Legenda do post (Instagram, TikTok e Shorts)</h3>", _copiavel(f"{base}-legenda", r.get("legenda", ""))]
    tela = [t.get("texto", "") for t in r.get("na_tela") or [] if t.get("texto")]
    if tela:
        partes += ["<h3>Texto na tela (edição)</h3>",
                   '<p class="suave">' + " · ".join(html.escape(t) for t in tela) + "</p>"]
    if not cenas:
        partes.append('<p class="suave">Sem cenas para o Flow neste roteiro. Roteiro falado:</p>'
                      + _copiavel(f"{base}-texto", "\n".join(r.get("linhas") or [])))
        return "\n".join(partes)
    partes.append(f"<h3>As {len(cenas)} cenas para o Flow</h3>")
    for i, c in enumerate(cenas, 1):
        inicio = c.get("inicio_s", (i - 1) * roteirista.SEGUNDOS_CENA)
        quem = "Clara no estúdio (use a foto como ingrediente)" if c.get("tipo") == "apresentadora" else "Imagem com a voz dela"
        partes.append(f'<div class="cena {html.escape(c.get("tipo", ""))}"><strong>Cena {i}</strong> · {inicio}-'
                      f'{inicio + roteirista.SEGUNDOS_CENA} s · {quem}'
                      f'<p>Fala: “{html.escape(c.get("fala", ""))}”</p>'
                      + (f'<p class="suave">Na tela: {html.escape(c["na_tela"])}</p>' if c.get("na_tela") else "")
                      + _copiavel(f"{base}-c{i}", roteirista.prompt_flow(c), f"Copiar prompt da cena {i}") + "</div>")
    return "\n".join(partes)


def pagina_dia(diario: Path, dia: str, raiz: str = "../") -> str:
    videos = roteiros_do_dia(diario, dia)
    d = f"{dia[8:10]}/{dia[5:7]}/{dia[:4]}"
    indice = "".join(f'<li><a href="#v{n}">{html.escape(_titulo(a, diario, dia))}</a></li>'
                     for n, (a, r) in enumerate(videos, 1) if r.get("aprovado"))
    corpo = [f"<h1>Vídeos de {d}</h1>",
             f'<p class="suave">{len(videos)} roteiro(s). Cada vídeo tem 6 cenas de 8 s: gere uma por uma no Google Flow '
             "e junte na ordem.</p>",
             f"<ol>{indice}</ol>" if indice else "",
             "<h2>Como gerar no Google Flow</h2><ol>"
             "<li>Uma vez só: gere a foto da Clara com o prompt abaixo, escolha a melhor e guarde. Use sempre a mesma.</li>"
             "<li>Cenas da Clara: <em>Ingredients to Video</em>, com a foto dela como ingrediente, vertical 9:16, 8 s.</li>"
             "<li>Cenas de imagem: <em>Text to Video</em>, vertical 9:16, 8 s, só com o prompt.</li>"
             "<li>Junte as 6 cenas no editor, ponha o texto da tela e a legenda. O número sempre com a fonte.</li></ol>",
             "<h3>Prompt da foto da Clara (ingrediente)</h3>", _copiavel("foto", roteirista.PROMPT_FOTO)]
    corpo += [bloco_video(n, a, r, diario, dia) for n, (a, r) in enumerate(videos, 1)]
    return _pagina(f"Estúdio {d}", "\n".join(corpo), raiz)


def gerar(saida: Path, diario: Path) -> list[str]:
    """Escreve /estudio/. Devolve os caminhos (que NÃO vão para o sitemap)."""
    dias = sorted((p.parent.name for p in diario.glob("*/roteiros") if p.is_dir() and any(p.glob("*.json"))),
                  reverse=True)[:DIAS]
    pasta = saida / "estudio"
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for dia in dias:
        (pasta / f"{dia}.html").write_text(pagina_dia(diario, dia))
        caminhos.append(f"estudio/{dia}.html")
    itens = "".join(f'<li><a href="{dia}.html">{dia[8:10]}/{dia[5:7]}/{dia[:4]}</a> · '
                    f"{len(roteiros_do_dia(diario, dia))} roteiro(s)</li>" for dia in dias)
    corpo = ("<h1>Estúdio de vídeos</h1><p class=\"suave\">Os roteiros do dia, prontos para o Google Flow. Esta página "
             "não aparece no menu nem no Google.</p>"
             + (f"<ul>{itens}</ul>" if itens else "<p>Nenhum roteiro ainda.</p>"))
    (pasta / "index.html").write_text(_pagina("Estúdio de vídeos", corpo, "../"))
    return caminhos
