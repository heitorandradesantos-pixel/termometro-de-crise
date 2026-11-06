"""Cotações das maiores empresas por bolsa e por setor (página Cotações).

A lista é editorial e fica em functions/_lib/acoes.json, a mesma que a função do Cloudflare usa para
atualizar os preços ao vivo. Aqui o robô guarda, 3 vezes por dia útil, o preço, a variação do dia, a de
30 dias e a linha dos últimos 30 dias (diario/AAAA-MM-DD/acoes.json). No navegador, a página troca o preço
e a variação do dia pelos de agora (functions/api/cotacoes.js?bolsa=...).

Fonte: Yahoo Finance, sempre escrita na página. Não é recomendação de compra ou venda.
"""

import html
import json
from pathlib import Path

import pandas as pd
import requests

from . import config

LISTA = config.RAIZ / "functions" / "_lib" / "acoes.json"
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
UA = {"User-Agent": "Mozilla/5.0 (compatible; termometro-de-crise/1.0)"}
MOEDAS = {"BRL": "R$", "USD": "US$", "EUR": "€", "GBP": "£", "GBp": "£", "JPY": "¥", "CNY": "CN¥", "HKD": "HK$",
          "TWD": "NT$", "KRW": "₩", "INR": "₹", "AUD": "A$"}
SEM_CENTAVOS = {"JPY", "KRW"}
ARQUIVO_SETOR = {"Tecnologia": "tecnologia", "Infraestrutura": "infraestrutura", "Commodities": "commodities"}
FALHAS_ACEITAS = 15  # de 60: acima disso, fica a coleta anterior


def lista() -> dict:
    return json.loads(LISTA.read_text())


def simbolos() -> list[dict]:
    return [{**a, "bolsa": b["chave"], "setor": s} for b in lista()["bolsas"] for s, itens in b["setores"].items()
            for a in itens]


def ticker(simbolo: str) -> str:
    """'PETR4.SA' -> 'PETR4'; '2330.TW' -> '2330'."""
    return simbolo.split(".")[0]


def uma(simbolo: str) -> dict:
    r = requests.get(URL.format(simbolo), headers=UA, params={"range": "3mo", "interval": "1d"}, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    meta = res.get("meta", {})
    serie = pd.Series(res["indicators"]["quote"][0].get("close", []),
                      index=pd.to_datetime(res.get("timestamp", []), unit="s"), dtype=float).dropna()
    if len(serie) < 2:
        raise RuntimeError(f"{simbolo}: sem dados")
    moeda = meta.get("currency", "")
    fator = 0.01 if moeda == "GBp" else 1.0  # bolsa de Londres cota em pence; mostramos em libras
    serie = serie * fator
    ultimo, ontem = float(serie.iloc[-1]), float(serie.iloc[-2])
    mes = serie[serie.index <= serie.index[-1] - pd.Timedelta(days=30)]
    trinta = serie[serie.index > serie.index[-1] - pd.Timedelta(days=30)]
    return {"ultimo": round(ultimo, 4), "dia_pct": round(100 * (ultimo / ontem - 1), 2),
            "mes_pct": round(100 * (ultimo / float(mes.iloc[-1]) - 1), 2) if len(mes) else None,
            "linha": [round(float(x), 4) for x in trinta.tolist()], "data": serie.index[-1].strftime("%Y-%m-%d"),
            "moeda": "GBP" if moeda == "GBp" else moeda}


def coletar(data: str) -> dict | None:
    """Busca as 60; devolve None se falharem demais (aí o site segue com a coleta anterior)."""
    itens, falhas = {}, {}
    for a in simbolos():
        try:
            itens[a["simbolo"]] = uma(a["simbolo"])
        except Exception as erro:  # noqa: BLE001 — uma ação que falha vira "sem dado", não derruba a página
            falhas[a["simbolo"]] = str(erro)[:120]
    if len(falhas) > FALHAS_ACEITAS:
        print(f"Cotações: {len(falhas)} falharam; fica a coleta anterior.")
        return None
    return {"data": data, "fonte": "Yahoo Finance", "itens": itens, "falhas": falhas}


def gravar(pasta: Path, data: str) -> None:
    dados = coletar(data)
    if dados:
        (pasta / "acoes.json").write_text(json.dumps(dados, ensure_ascii=False))


# ---------------------------------------------------------------- página

def preco(valor: float, moeda: str) -> str:
    casas = 0 if moeda in SEM_CENTAVOS or valor >= 10000 else 2
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{MOEDAS.get(moeda, moeda)} {texto}".strip()


def variacao(pct, quando: str = "no dia") -> str:
    if pct is None:
        return '<span class="suave">—</span>'
    seta, verbo = ("▲", "subiu") if pct > 0 else (("▼", "caiu") if pct < 0 else ("", "ficou estável"))
    numero = f"{abs(pct):.2f}".replace(".", ",")
    return (f'<span aria-hidden="true">{seta}</span><span class="sr">{verbo} </span>{numero}%'
            f'<span class="sr"> {quando}</span>')


def linha_svg(pontos: list[float], pct) -> str:
    if len(pontos) < 2:
        return ""
    lo, hi = min(pontos), max(pontos)
    amp = (hi - lo) or 1
    larg, alt = 96, 28
    xy = [(round(i * (larg - 4) / (len(pontos) - 1) + 2, 1), round(alt - 3 - (p - lo) / amp * (alt - 6), 1))
          for i, p in enumerate(pontos)]
    texto = ("sem variação" if pct is None else
             f"{'subiu' if pct > 0 else 'caiu' if pct < 0 else 'ficou estável'} {abs(pct):.0f}% em 30 dias")
    return (f'<svg class="linha" viewBox="0 0 {larg} {alt}" width="{larg}" height="{alt}" role="img" aria-label="{texto}">'
            f'<polyline fill="none" stroke="#9AA7B8" stroke-width="1.5" points="{" ".join(f"{x},{y}" for x, y in xy)}"/>'
            f'<circle cx="{xy[-1][0]}" cy="{xy[-1][1]}" r="2.5" fill="#EAF0F7"/></svg>')


CSS = """
.abas-bolsa{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 12px}.abas-bolsa a{display:inline-flex;align-items:center;
min-height:44px;padding:0 18px;border-radius:999px;border:1px solid var(--linha);color:var(--texto);text-decoration:none;
font-weight:600}.abas-bolsa a[aria-current]{background:var(--texto);color:var(--fundo)}
.chips-setor{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.chips-setor a{display:inline-flex;align-items:center;
min-height:40px;padding:0 14px;border-radius:999px;background:#121B25;color:var(--texto);text-decoration:none;font-size:14px}
.carimbo-cot{font-size:13px;color:#9AA7B8;margin:4px 0 0}
.cotas{width:100%;border-collapse:collapse;margin:8px 0 24px}.cotas th{font-size:12px;font-weight:600;color:var(--suave);
text-align:left;padding:8px;border-bottom:1px solid var(--linha)}.cotas td{padding:10px 8px;border-bottom:1px solid var(--linha);
vertical-align:middle}.cotas .num{text-align:right;font-variant-numeric:tabular-nums;font-family:ui-monospace,SFMono-Regular,
Menlo,monospace;white-space:nowrap}.cotas .empresa strong{display:block;font-size:16px}.cotas .tk{font-family:ui-monospace,
SFMono-Regular,Menlo,monospace;font-size:13px;color:#9AA7B8}.cotas .linha{display:block}.cotas .pais a{font-size:13px}
.cotas .antigo{display:block;font-size:12px;color:var(--suave)}
.cotas .pais a{display:inline-block;padding:5px 0}.trilha a{display:inline-block;padding:4px 0}
@media (max-width:640px){.cotas thead{display:none}.cotas tr{display:grid;grid-template-columns:1fr 64px auto;
grid-template-areas:"empresa linha preco" "empresa linha dia" "pais pais mes";column-gap:10px;padding:10px 0;
border-bottom:1px solid var(--linha);min-height:72px}.cotas td{border:0;padding:0}.cotas .c-empresa{grid-area:empresa}
.cotas .c-linha{grid-area:linha;align-self:center}.cotas .c-linha svg{width:64px;height:24px}.cotas .c-preco{grid-area:preco;
font-size:16px}.cotas .c-dia{grid-area:dia;font-size:13px}.cotas .c-mes{grid-area:mes;font-size:12px;color:var(--suave)}
.cotas .c-mes::before{content:"30 dias: "}.cotas .c-pais{grid-area:pais;font-size:12px;padding-top:4px}}
"""

AO_VIVO = """<script>(function(){var t=document.querySelector('[data-bolsa]');if(!t||location.protocol==='file:')return;
function n(x,c){return x.toLocaleString('pt-BR',{minimumFractionDigits:c,maximumFractionDigits:c})}
var M=%s;function fmt(v,m){var c=(m==='JPY'||m==='KRW'||v>=10000)?0:2;return ((M[m]||m)+' '+n(v,c)).trim()}
function hora(s){return new Date(s*1000).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit',timeZone:'America/Sao_Paulo'}).replace(':','h')}
function vai(){if(document.hidden)return;fetch('/api/cotacoes?bolsa='+t.dataset.bolsa).then(function(r){return r.ok?r.json():null})
.then(function(d){if(!d||!d.itens||!d.itens.length)return;d.itens.forEach(function(i){
var tr=t.querySelector('tr[data-s="'+i.simbolo+'"]');if(!tr)return;tr.querySelector('.c-preco').textContent=fmt(i.ultimo,i.moeda);
var v=i.variacao_pct;tr.querySelector('.c-dia').innerHTML='<span aria-hidden="true">'+(v>0?'▲':v<0?'▼':'')+'</span><span class="sr">'
+(v>0?'subiu ':v<0?'caiu ':'ficou estável ')+'</span>'+n(Math.abs(v),2)+'%%<span class="sr"> no dia</span>';
if(i.hora)tr.title=i.nome+': cotação das '+hora(i.hora);var a=tr.querySelector('.antigo');if(a)a.remove()});
var c=document.querySelector('.carimbo-cot');if(c)c.textContent='Atualizado às '+hora(d.gerado)+' · fonte: Yahoo Finance'})
.catch(function(){})}vai();setInterval(vai,30000);document.addEventListener('visibilitychange',vai)})();</script>"""


def _termometro(pais: str, medidos: dict, regiao_de: dict, raiz: str) -> str:
    if pais in medidos:
        p = medidos[pais]
        return f'<a href="{raiz}paises/{p["slug"]}.html">Termômetro {html.escape(pais)}: {p["valor"]}</a>'
    r = regiao_de.get(pais)
    return (f'<a href="{raiz}regioes/{r["slug"]}.html">Termômetro {html.escape(r["nome"])}: {r["valor"]}</a>' if r else "")


def paginas(saida: Path, dados: dict | None, m: dict) -> list[str]:
    """Gera cotacoes/index.html (Brasil), cotacoes/eua.html, europa.html e asia.html (o menu sempre aponta para elas)."""
    from .site import pagina
    sem_dados = not dados or not dados.get("itens")
    dados = dados if not sem_dados else {"data": "", "itens": {}}
    medidos = {p["nome"]: p for r in m.get("regioes", []) for p in r.get("paises", []) if p.get("valor") is not None}
    regiao_de = {"Holanda": "Europa", "Finlândia": "Europa"}
    regioes = {r["nome"]: r for r in m.get("regioes", [])}
    regiao_de = {k: regioes[v] for k, v in regiao_de.items() if v in regioes and regioes[v].get("valor") is not None}
    bolsas = lista()["bolsas"]
    arquivo = {b["chave"]: ("index" if b["chave"] == "brasil" else b["chave"]) for b in bolsas}
    (saida / "cotacoes").mkdir(parents=True, exist_ok=True)
    feitas = []
    for b in bolsas:
        atual = ' aria-current="page"'
        abas = "".join(f'<a href="{arquivo[x["chave"]]}.html"{atual if x["chave"] == b["chave"] else ""}>'
                       f'{html.escape(x["nome"])}</a>' for x in bolsas)
        chips = "".join(f'<a href="#{ARQUIVO_SETOR[s]}">{s}</a>' for s in b["setores"])
        secoes = []
        for setor, empresas in b["setores"].items():
            linhas = []
            for a in empresas:
                c = dados["itens"].get(a["simbolo"])
                tk = html.escape(ticker(a["simbolo"]))
                termometro = _termometro(a["pais"], medidos, regiao_de, "../")
                if not c:  # sem coleta guardada: o preço e o dia chegam ao vivo; o termômetro do país vale sempre
                    linhas.append(f'<tr data-s="{a["simbolo"]}"><td class="c-empresa empresa"><strong>{html.escape(a["nome"])}'
                                  f'</strong><span class="tk">{tk}</span></td><td class="num c-preco">—</td>'
                                  f'<td class="num c-dia">—</td><td class="num c-mes">—</td><td class="c-linha"></td>'
                                  f'<td class="c-pais pais">{termometro}</td></tr>')
                    continue
                antigo = ("" if c["data"] >= dados["data"] else
                          f'<span class="antigo">último pregão {pd.Timestamp(c["data"]):%d/%m}</span>')
                linhas.append(
                    f'<tr data-s="{a["simbolo"]}"><td class="c-empresa empresa"><strong>{html.escape(a["nome"])}</strong>'
                    f'<span class="tk">{tk}</span>{antigo}</td><td class="num c-preco">{preco(c["ultimo"], c["moeda"])}</td>'
                    f'<td class="num c-dia">{variacao(c["dia_pct"])}</td>'
                    f'<td class="num c-mes">{variacao(c["mes_pct"], "em 30 dias")}</td>'
                    f'<td class="c-linha">{linha_svg(c["linha"], c["mes_pct"])}</td>'
                    f'<td class="c-pais pais">{termometro}</td></tr>')
            secoes.append(f'<h2 id="{ARQUIVO_SETOR[setor]}">{setor}</h2><table class="cotas"><thead><tr><th>Empresa</th>'
                          f'<th class="num">Preço</th><th class="num">Dia</th><th class="num">30 dias</th><th>Tendência</th>'
                          f'<th>Termômetro</th></tr></thead><tbody>{"".join(linhas)}</tbody></table>')
        hora = (m.get("parcial") or {}).get("hora")
        carimbo = ("Sem cotações guardadas no momento: elas voltam na próxima atualização (11h07, 14h07 e 18h17 nos "
                   "dias úteis) · fonte: Yahoo Finance" if sem_dados else
                   f"Preços {'parciais das ' + hora + ' de ' if hora else 'de fechamento de '}"
                   f"{pd.Timestamp(dados['data']):%d/%m/%Y} · fonte: Yahoo Finance")
        corpo = (f'<section class="edicao" style="max-width:none" data-bolsa="{b["chave"]}"><p class="trilha">'
                 f'<a href="../index.html">Início</a> › Cotações</p><h1>Cotações: {html.escape(b["nome"])}</h1>'
                 f'<nav class="abas-bolsa" aria-label="Bolsas">{abas}</nav><p class="carimbo-cot">{carimbo}</p>'
                 f'<nav class="chips-setor" aria-label="Setores">{chips}</nav>'
                 f'<p class="suave" style="font-size:14px">Seleção editorial: algumas das maiores empresas de cada setor em '
                 f'valor de mercado. Não é recomendação de compra ou venda.</p>{"".join(secoes)}'
                 f'<p class="suave" style="font-size:14px">Os preços se atualizam sozinhos a cada 30 segundos com a página '
                 f'aberta. Algumas bolsas chegam à fonte com atraso de até 15 minutos. A variação de 30 dias e a linha de '
                 f'tendência usam os fechamentos diários.</p></section>'
                 + AO_VIVO % json.dumps(MOEDAS, ensure_ascii=False))
        caminho = f"cotacoes/{arquivo[b['chave']]}.html"
        (saida / caminho).write_text(pagina(
            f"Cotações {b['nome']}: tecnologia, infraestrutura e commodities | {config.NOME}",
            f"Preço, variação do dia e de 30 dias das maiores empresas de tecnologia, infraestrutura e commodities "
            f"da bolsa {'brasileira' if b['chave'] == 'brasil' else 'de ' + b['nome']}, atualizados ao longo do dia.",
            corpo, raiz="../", caminho=caminho, extra_css=CSS))
        feitas.append(caminho)
    return feitas
