"""Calculadoras grátis do site (pedido do Heitor em 21/11/2026): juros compostos, inflação, rendimento na Selic e
dólar no cartão. Tudo roda no navegador de quem usa; nenhum dado digitado sai da página.

Regras: é simulação educativa, com taxa constante e contas simplificadas, sempre com a fonte de cada número
(Banco Central, IBGE, Receita Federal). Sem recomendação de investimento e sem promessa de ganho.
"""

import html
import json
import os
from pathlib import Path

import requests

from . import bcb, config

# IPCA fechado de cada ano, em % (IBGE). Serve de base; os meses do ano corrente vêm do Banco Central na hora de
# gerar o site e, se a consulta falhar, a conta vai só até dezembro do último ano fechado.
IPCA_ANUAL = {1995: 22.41, 1996: 9.56, 1997: 5.22, 1998: 1.65, 1999: 8.94, 2000: 5.97, 2001: 7.67, 2002: 12.53,
              2003: 9.30, 2004: 7.60, 2005: 5.69, 2006: 3.14, 2007: 4.46, 2008: 5.90, 2009: 4.31, 2010: 5.91,
              2011: 6.50, 2012: 5.84, 2013: 5.91, 2014: 6.41, 2015: 10.67, 2016: 6.29, 2017: 2.95, 2018: 3.75,
              2019: 4.31, 2020: 4.52, 2021: 10.06, 2022: 5.79, 2023: 4.62, 2024: 4.83, 2025: 4.26}
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
IOF_CARTAO = 3.5      # % sobre compra internacional no cartão (Decreto 12.499/2025)
SELIC_RESERVA, DOLAR_RESERVA = 13.75, 5.89  # usados só se o dado do dia não estiver na pasta do diário

CSS = """
.calc{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,6fr);gap:20px;align-items:start;margin:20px 0}
.calc form,.calc .saida{background:var(--painel);border:1px solid #233140;border-radius:16px;padding:20px}
.calc label{display:block;font-weight:600;font-size:15px;margin:14px 0 6px}.calc label:first-child{margin-top:0}
.calc label small{display:block;font-weight:400;color:var(--suave);font-size:13px}
.calc input,.calc select{width:100%;min-height:48px;border-radius:12px;border:1px solid #A9B4C4;background:#0B1220;color:var(--texto);padding:0 14px;font:500 17px 'IBM Plex Sans',sans-serif}
.calc input:focus,.calc select:focus{outline:3px solid #7CC3E0;outline-offset:1px}
.calc .marca-caixa{display:flex;gap:10px;align-items:center;font-weight:400;min-height:44px}.calc .marca-caixa input{width:22px;min-height:22px;height:22px;flex:none}
.calc .saida h2{margin:0 0 4px;font-size:15px;font-weight:600;color:var(--suave);font-family:'IBM Plex Sans',sans-serif}
.calc .grande{font:700 44px/1.1 'Space Grotesk',sans-serif;color:#F2C14E;overflow-wrap:anywhere}
.calc .frase{margin:8px 0 14px;font-size:16px}
.calc dl{margin:0;display:grid;grid-template-columns:1fr auto;gap:0}
.calc dt,.calc dd{margin:0;padding:10px 0;border-top:1px solid var(--linha);font-size:15px}.calc dd{text-align:right;font-weight:600;font-family:'Space Grotesk',sans-serif}
.calc dt{color:var(--suave)}.calc .barras{margin:16px 0 0}.calc .barras svg{width:100%;height:auto;display:block}
.calc .leg{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;color:var(--suave);margin-top:8px}
.calc .leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
.calc table{font-size:15px}.calc td,.calc th{padding:10px 6px}.calc td:not(:first-child),.calc th:not(:first-child){text-align:right}
.calc .melhor td{color:#F2C14E;font-weight:600}
.calc-nota{font-size:13px;color:var(--suave)}.calc-texto{max-width:760px}.calc-texto h2{font-size:22px;margin-top:32px}
.outras{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:14px 0}
.outras a{display:block;background:var(--painel);border:1px solid #233140;border-radius:12px;padding:14px 16px;color:var(--texto);text-decoration:none;font-weight:600}
.outras a:hover{border-color:#3A5066;background:#1E2A37;color:var(--texto)}.outras span{display:block;font-weight:400;font-size:13px;color:var(--suave);margin-top:2px}
@media (max-width:760px){.calc{grid-template-columns:1fr;gap:14px}.calc form,.calc .saida{padding:16px}.calc .grande{font-size:36px}.outras{grid-template-columns:1fr}}
"""

# Funções comuns às quatro páginas: ler número digitado à brasileira ("1.234,56") e escrever em reais.
JS_COMUM = """
function num(id){var v=(document.getElementById(id).value||'').trim().replace(/\\s/g,'');
if(v.indexOf(',')>-1)v=v.replace(/\\./g,'').replace(',','.');var n=parseFloat(v);return isFinite(n)&&n>0?n:0}
function brl(v){return v.toLocaleString('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:v>=100000?0:2})}
function pct(v,c){return v.toLocaleString('pt-BR',{minimumFractionDigits:c==null?1:c,maximumFractionDigits:c==null?1:c})+'%'}
function poe(id,t){document.getElementById(id).textContent=t}
function liga(f){var c=document.querySelectorAll('.calc input,.calc select');for(var i=0;i<c.length;i++){c[i].addEventListener('input',f);c[i].addEventListener('change',f)}f()}
"""

JS_JUROS = """
function calcula(){var ini=num('ini'),ap=num('aporte'),tx=num('taxa'),anos=Math.min(Math.round(num('anos')),60);
var i=Math.pow(1+tx/100,1/12)-1,saldo=ini,posto=ini,serie=[];
for(var m=1;m<=anos*12;m++){saldo=saldo*(1+i)+ap;posto+=ap;if(m%12===0)serie.push([posto,saldo])}
var juros=saldo-posto,ir=document.getElementById('ir').checked?juros*0.15:0,liq=saldo-ir;
poe('total',brl(liq));poe('posto',brl(posto));poe('juros',brl(juros));poe('ir-v',ir?'- '+brl(ir):'não descontado');poe('bruto',brl(saldo));
poe('frase',anos&&posto?'Do seu bolso saem '+brl(posto)+'. O resto, '+brl(juros)+(ir?' antes do imposto':'')+', é juro sobre juro.':'Preencha os campos para ver a conta.');
var W=560,H=200,n=serie.length,max=n?serie[n-1][1]:1,g='';
for(var k=0;k<n;k++){var bw=(W-10)/n,x=5+k*bw,hp=serie[k][0]/max*(H-22),hs=serie[k][1]/max*(H-22);
g+='<rect x="'+(x+1).toFixed(1)+'" y="'+(H-20-hs).toFixed(1)+'" width="'+Math.max(bw-2,1).toFixed(1)+'" height="'+(hs-hp).toFixed(1)+'" fill="#F2C14E"/>'
+'<rect x="'+(x+1).toFixed(1)+'" y="'+(H-20-hp).toFixed(1)+'" width="'+Math.max(bw-2,1).toFixed(1)+'" height="'+hp.toFixed(1)+'" fill="#7CC3E0"/>'}
g+='<text x="5" y="'+(H-4)+'" font-size="12" fill="#A9B4C4">ano 1</text><text x="'+(W-5)+'" y="'+(H-4)+'" font-size="12" fill="#A9B4C4" text-anchor="end">ano '+n+'</text>';
document.getElementById('graf').innerHTML=g}
liga(calcula);
"""

JS_INFLACAO = """
var D=__DADOS__;
function calcula(){var v=num('valor'),ano=parseInt(document.getElementById('ano').value,10),f=1;
for(var a=ano;a<=D.ultimoAno;a++)f*=1+D.anual[a]/100;f*=D.fatorCorrente;
var hoje=v*f,vale=v/f;
poe('total',brl(hoje));poe('acum',pct((f-1)*100,1));poe('vale',brl(vale));poe('perda',pct((1-1/f)*100,1));
poe('frase',v?'O que custava '+brl(v)+' em janeiro de '+ano+' custa cerca de '+brl(hoje)+' em '+D.ate+'.':'Preencha o valor para ver a conta.');
poe('frase2',v?'Quem guardou '+brl(v)+' em dinheiro vivo desde janeiro de '+ano+' compra hoje o que '+brl(vale)+' compravam naquela época.':'')}
liga(calcula);
"""

JS_SELIC = """
function aliquota(dias){return dias<=180?22.5:dias<=360?20:dias<=720?17.5:15}
function calcula(){var v=num('valor'),meses=Math.max(1,Math.min(Math.round(num('meses')),360)),selic=num('selic');
var dias=Math.round(meses*30.4),ir=aliquota(dias)/100,cdi=Math.max(selic-0.1,0);
var poup=selic>8.5?Math.pow(1.005,meses)-1:Math.pow(1+selic*0.7/100,meses/12)-1;
function liquido(taxa){var bruto=Math.pow(1+taxa/100,meses/12)-1;return bruto*(1-ir)}
var linhas=[['Poupança',poup,'isenta de IR'],['Tesouro Selic',liquido(selic),'IR de '+pct(ir*100,1)],['CDB 100% do CDI',liquido(cdi),'IR de '+pct(ir*100,1)]];
var melhor=0;for(var k=1;k<3;k++)if(linhas[k][1]>linhas[melhor][1])melhor=k;
var h='';for(k=0;k<3;k++){h+='<tr'+(k===melhor?' class="melhor"':'')+'><td>'+linhas[k][0]+'<br><span class="suave" style="font-size:12px;font-weight:400">'+linhas[k][2]+'</span></td><td>'+brl(v*linhas[k][1])+'</td><td>'+brl(v*(1+linhas[k][1]))+'</td></tr>'}
document.getElementById('linhas').innerHTML=h;
poe('total',brl(v*linhas[melhor][1]));
poe('frase',v?'É quanto '+brl(v)+' renderiam em '+meses+(meses===1?' mês':' meses')+' na opção que rende mais nesta simulação ('+linhas[melhor][0]+'), já com o imposto.':'Preencha o valor para ver a conta.')}
liga(calcula);
"""

JS_DOLAR = """
function calcula(){var usd=num('usd'),cot=num('cot'),sp=num('spread'),iof=__IOF__;
var base=usd*cot*(1+sp/100),imposto=base*iof/100,total=base+imposto;
poe('total',brl(total));poe('base',brl(usd*cot));poe('sp-v',brl(usd*cot*sp/100));poe('iof-v',brl(imposto));
poe('efetivo',usd?brl(total/usd):'-');
poe('frase',usd&&cot?'Cada dólar da compra sai por cerca de '+brl(total/usd)+', e não pelos '+brl(cot)+' da cotação.':'Preencha os campos para ver a conta.')}
liga(calcula);
"""

OUTRAS = {"juros-compostos": ("Juros compostos", "Quanto vira guardar todo mês"),
          "inflacao": ("Inflação (IPCA)", "Quanto o seu dinheiro perdeu"),
          "rendimento-selic": ("Quanto rende na Selic", "Poupança, Tesouro Selic e CDB"),
          "dolar-cartao": ("Dólar no cartão", "Com spread do banco e IOF")}


def _do_dia(pasta_diario: Path | None) -> tuple[float, float, str]:
    """Selic e dólar PTAX mais recentes gravados no diário (bcb.json), com a data do dado."""
    selic, dolar, quando = SELIC_RESERVA, DOLAR_RESERVA, ""
    for arq in sorted(pasta_diario.glob("*/bcb.json"), reverse=True)[:10] if pasta_diario and pasta_diario.exists() else []:
        try:
            d = json.loads(arq.read_text())
            selic, dolar = float(d["selic"]["valor"]), float(d["ptax"]["valor"])
            quando = "/".join(reversed(d["ptax"]["data"].split("-")))
            break
        except (KeyError, ValueError, TypeError):
            continue
    return selic, dolar, quando


def ipca_corrente() -> tuple[float, str]:
    """Fator acumulado do IPCA nos meses já divulgados do ano seguinte ao último ano fechado e o texto do período.
    Sem internet (ou com a série fora do ar), devolve 1 e 'dezembro do último ano fechado'."""
    ultimo = max(IPCA_ANUAL)
    if os.environ.get("PYTEST_CURRENT_TEST"):  # os testes não saem para a internet
        return 1.0, f"dez/{ultimo}"
    try:
        r = requests.get(bcb.SGS.format(433), params={"formato": "json", "dataInicial": f"01/01/{ultimo + 1}"},
                         headers=bcb.UA, timeout=8)
        r.raise_for_status()
        meses = [(x["data"], float(x["valor"])) for x in r.json() if x["data"].endswith(str(ultimo + 1))]
        if not meses or len(meses) > 12:
            raise ValueError("série vazia")
        fator = 1.0
        for _, v in meses:
            fator *= 1 + v / 100
        return fator, f"{MESES[int(meses[-1][0][3:5]) - 1]}/{ultimo + 1}"
    except Exception as erro:  # noqa: BLE001 (dado oficial que falha: a conta para no último ano fechado)
        print(f"  [calculadoras] IPCA do ano corrente indisponível ({str(erro)[:80]}); usando até dez/{ultimo}")
        return 1.0, f"dez/{ultimo}"


def _outras(atual: str) -> str:
    itens = "".join(f'<a href="{slug}.html">{nome}<span>{sub}</span></a>' for slug, (nome, sub) in OUTRAS.items() if slug != atual)
    return f'<h2>Outras calculadoras</h2><div class="outras">{itens}</div>'


def _moldura(slug: str, titulo: str, lead: str, formulario: str, saida: str, texto: str, js: str) -> str:
    return (f'<p class="trilha"><a href="../index.html">Início</a> › <a href="index.html">Ferramentas</a> › {html.escape(OUTRAS[slug][0])}</p>'
            f'<section class="edicao" style="max-width:none;padding-top:8px"><h1>{titulo}</h1><p class="suave" style="max-width:760px">{lead}</p>'
            f'<div class="calc"><form onsubmit="return false" aria-label="Dados da simulação">{formulario}</form>'
            f'<div class="saida" aria-live="polite">{saida}</div></div>'
            f'<p class="calc-nota">Simulação educativa, feita no seu aparelho: nada do que você digita é enviado para nós. '
            f'Não é recomendação de investimento nem garantia de resultado.</p>'
            f'<div class="calc-texto">{texto}{_outras(slug)}</div></section><script>{JS_COMUM}{js}</script>')


def juros(selic: float) -> str:
    taxa = f"{selic:.2f}".replace(".", ",")
    form = (f'<label for="ini">Quanto você já tem<small>Pode deixar zero</small></label><input id="ini" inputmode="decimal" value="0">'
            f'<label for="aporte">Quanto guarda por mês</label><input id="aporte" inputmode="decimal" value="500">'
            f'<label for="taxa">Taxa de juros ao ano (%)<small>Já vem com a Selic de hoje, {taxa}% (Banco Central). Troque à vontade.</small></label>'
            f'<input id="taxa" inputmode="decimal" value="{taxa}">'
            f'<label for="anos">Por quantos anos</label><input id="anos" inputmode="numeric" value="20">'
            f'<label class="marca-caixa"><input type="checkbox" id="ir" checked> Descontar 15% de Imposto de Renda sobre o ganho</label>')
    saida = ('<h2>No fim do período você teria</h2><div class="grande" id="total">-</div><p class="frase" id="frase"></p>'
             '<dl><dt>Saiu do seu bolso</dt><dd id="posto">-</dd><dt>Juros no período</dt><dd id="juros">-</dd>'
             '<dt>Imposto de Renda (15% do ganho)</dt><dd id="ir-v">-</dd><dt>Total antes do imposto</dt><dd id="bruto">-</dd></dl>'
             '<div class="barras"><svg id="graf" viewBox="0 0 560 200" role="img" aria-label="Crescimento ano a ano: o que saiu do bolso e os juros"></svg>'
             '<div class="leg"><span><i style="background:#7CC3E0"></i>Saiu do seu bolso</span><span><i style="background:#F2C14E"></i>Juros</span></div></div>')
    texto = ('<h2>Como a conta é feita</h2><p>Juro composto é juro sobre juro: o rendimento de um mês entra no saldo e passa a render '
             'também no mês seguinte. A calculadora transforma a taxa ao ano em taxa ao mês, aplica sobre o saldo e soma o que você '
             'guarda no fim de cada mês.</p>'
             '<h2>O que a simulação não considera</h2><ul><li>A taxa fica parada o tempo todo. Na vida real a Selic sobe e desce: '
             'ninguém sabe os juros dos próximos 20 anos.</li><li>O valor final não desconta a inflação. Daqui a 20 anos, o mesmo '
             'dinheiro compra menos do que hoje.</li><li>O imposto usa 15% sobre o ganho, a alíquota da renda fixa para aplicações com '
             'mais de 720 dias (Receita Federal). Prazo menor paga mais; LCI, LCA e poupança hoje são isentas.</li></ul>'
             '<p>Use para comparar cenários (guardar R$ 300 ou R$ 500, por 10 ou por 20 anos), não como previsão.</p>')
    return _moldura("juros-compostos", "Calculadora de juros compostos",
                    "Veja quanto vira guardar um valor todo mês, quanto sai do seu bolso e quanto é juro sobre juro.", form, saida, texto, JS_JUROS)


def inflacao(fator: float, ate: str) -> str:
    anos = "".join(f'<option value="{a}"{" selected" if a == 2013 else ""}>{a}</option>' for a in sorted(IPCA_ANUAL, reverse=True))
    form = (f'<label for="valor">Valor em reais</label><input id="valor" inputmode="decimal" value="100">'
            f'<label for="ano">Desde janeiro de<small>A conta vai de janeiro do ano escolhido até {ate}</small></label>'
            f'<select id="ano">{anos}</select>')
    saida = ('<h2>Para comprar a mesma coisa hoje, você precisa de</h2><div class="grande" id="total">-</div><p class="frase" id="frase"></p>'
             '<dl><dt>Inflação acumulada no período (IPCA)</dt><dd id="acum">-</dd>'
             '<dt>Quanto o valor parado compra hoje</dt><dd id="vale">-</dd>'
             '<dt>Poder de compra perdido</dt><dd id="perda">-</dd></dl><p class="frase" id="frase2" style="margin:14px 0 0"></p>')
    dados = json.dumps({"anual": IPCA_ANUAL, "ultimoAno": max(IPCA_ANUAL), "fatorCorrente": round(fator, 6), "ate": ate})
    texto = ('<h2>Como a conta é feita</h2><p>A calculadora junta a inflação oficial do Brasil, o IPCA, medido pelo IBGE, de janeiro '
             f'do ano que você escolher até {ate}. Os anos fechados usam o IPCA anual divulgado pelo IBGE; os meses do ano em '
             'andamento vêm da série do Banco Central (SGS 433).</p>'
             '<h2>Para que serve</h2><ul><li><strong>Salário:</strong> coloque o que você ganhava e veja quanto precisaria ganhar hoje '
             'só para empatar com a inflação.</li><li><strong>Dinheiro parado:</strong> veja quanto perdeu de poder de compra o valor '
             'que ficou na conta ou na gaveta.</li><li><strong>Preços:</strong> compare quanto algo custava com quanto deveria custar '
             'se tivesse subido só a inflação.</li></ul>'
             '<p>O IPCA é uma média do país. A inflação da sua casa pode ser maior ou menor, conforme o que você mais compra. Para '
             'uma conta mês a mês, o Banco Central tem a Calculadora do Cidadão, também grátis.</p>')
    return _moldura("inflacao", "Calculadora de inflação: quanto o seu dinheiro perdeu",
                    "Descubra quanto um valor antigo vale hoje e quanto do poder de compra a inflação levou.", form, saida, texto,
                    JS_INFLACAO.replace("__DADOS__", dados))


def rendimento(selic: float) -> str:
    taxa = f"{selic:.2f}".replace(".", ",")
    form = (f'<label for="valor">Quanto você vai aplicar</label><input id="valor" inputmode="decimal" value="10000">'
            f'<label for="meses">Por quantos meses</label><input id="meses" inputmode="numeric" value="12">'
            f'<label for="selic">Selic ao ano (%)<small>Já vem com a taxa de hoje, {taxa}% (Banco Central)</small></label>'
            f'<input id="selic" inputmode="decimal" value="{taxa}">')
    saida = ('<h2>Rendimento depois do imposto</h2><div class="grande" id="total">-</div><p class="frase" id="frase"></p>'
             '<table><thead><tr><th>Onde</th><th>Rende</th><th>Total</th></tr></thead><tbody id="linhas"></tbody></table>')
    texto = ('<h2>Como a conta é feita</h2><ul><li><strong>Poupança:</strong> com a Selic acima de 8,5% ao ano, rende 0,5% ao mês mais a TR '
             '(a simulação não soma a TR, então na prática a poupança rende um pouco mais do que aparece aqui). Com a Selic em 8,5% ou menos, rende 70% da Selic. É isenta de Imposto de Renda. '
             '(Banco Central)</li><li><strong>Tesouro Selic:</strong> acompanha a Selic. A simulação não desconta a taxa de custódia da '
             'B3 (0,20% ao ano sobre o que passar de R$ 10 mil).</li><li><strong>CDB de 100% do CDI:</strong> o CDI costuma ficar '
             '0,10 ponto abaixo da Selic, e é isso que a conta usa.</li><li><strong>Imposto de Renda:</strong> 22,5% do ganho até 180 dias, '
             '20% até 360, 17,5% até 720 e 15% acima disso. (Receita Federal)</li></ul>'
             '<h2>O que a simulação não considera</h2><p>A Selic fica parada no período, o que não acontece na prática. Resgate em '
             'menos de 30 dias paga IOF, e a poupança só rende no "aniversário" de cada depósito. CDB de banco tem a cobertura do FGC '
             'dentro dos limites; cada produto tem prazo e regra próprios. A linha em destaque é só a que rende mais nesta conta, '
             'não uma indicação.</p>')
    return _moldura("rendimento-selic", "Quanto rende o seu dinheiro na Selic de hoje",
                    "Compare, na mesma conta, a poupança, o Tesouro Selic e um CDB de 100% do CDI, já com o Imposto de Renda.",
                    form, saida, texto, JS_SELIC)


def dolar(cotacao: float, quando: str) -> str:
    cot = f"{cotacao:.2f}".replace(".", ",")
    iof = f"{IOF_CARTAO:.1f}".replace(".", ",")
    dia = f" de {quando}" if quando else ""
    form = (f'<label for="usd">Valor da compra em dólar (US$)</label><input id="usd" inputmode="decimal" value="100">'
            f'<label for="cot">Cotação do dólar (R$)<small>Já vem com a PTAX{dia}, R$ {cot} (Banco Central). O cartão usa a do dia da compra.</small></label>'
            f'<input id="cot" inputmode="decimal" value="{cot}">'
            f'<label for="spread">Spread do banco (%)<small>A margem que o banco soma à cotação. Costuma ficar entre 0% e 7%; veja na sua fatura.</small></label>'
            f'<input id="spread" inputmode="decimal" value="4">')
    saida = (f'<h2>Vai chegar na fatura cerca de</h2><div class="grande" id="total">-</div><p class="frase" id="frase"></p>'
             f'<dl><dt>Compra pela cotação</dt><dd id="base">-</dd><dt>Spread do banco</dt><dd id="sp-v">-</dd>'
             f'<dt>IOF ({iof}%)</dt><dd id="iof-v">-</dd><dt>Custo de cada dólar</dt><dd id="efetivo">-</dd></dl>')
    texto = ('<h2>Como a conta é feita</h2><p>Compra internacional no cartão de crédito tem três partes: a cotação do dólar no dia da '
             f'compra, o spread (a margem do banco ou da bandeira sobre a cotação) e o IOF de {iof}% sobre o valor já convertido '
             '(Decreto 12.499/2025). A calculadora soma os três e mostra quanto cada dólar custa de verdade.</p>'
             '<h2>Dicas para conferir</h2><ul><li>Desde 2020 o banco tem que converter a compra pela cotação do dia em que ela foi feita, '
             'e não pela do fechamento da fatura (Banco Central).</li><li>O spread muda de banco para banco e aparece na fatura ou no '
             'aplicativo como "taxa de conversão" ou "VET".</li><li>Assinaturas e sites de fora cobrados em dólar entram na mesma regra.</li></ul>'
             '<p>A PTAX é a cotação de referência do Banco Central; a do seu cartão pode ser um pouco diferente.</p>')
    return _moldura("dolar-cartao", "Dólar no cartão de crédito: quanto vai custar com IOF",
                    "Coloque o valor em dólar e veja quanto chega na fatura, com a cotação, o spread do banco e o IOF.", form, saida,
                    texto, JS_DOLAR.replace("__IOF__", str(IOF_CARTAO)))


def lista() -> str:
    """Os cartões das calculadoras para a página de Ferramentas."""
    return "".join(f'<a href="{slug}.html"><strong>Calculadora: {nome}</strong><br>'
                   f'<span class="suave">{sub}.</span></a>' for slug, (nome, sub) in OUTRAS.items())


def gerar(saida: Path, pagina, pasta_diario: Path | None = None) -> list[str]:
    """Grava as quatro calculadoras em ferramentas/ e devolve os caminhos para o mapa do site."""
    selic, cotacao, quando = _do_dia(pasta_diario)
    fator, ate = ipca_corrente()
    pasta = saida / "ferramentas"
    pasta.mkdir(parents=True, exist_ok=True)
    paginas = {
        "juros-compostos": (f"Calculadora de juros compostos com aporte mensal · {config.NOME}",
                            "Simule quanto vira guardar um valor todo mês: total, juros, Imposto de Renda e o gráfico ano a ano. Grátis.",
                            juros(selic)),
        "inflacao": (f"Calculadora de inflação (IPCA): quanto o dinheiro perdeu · {config.NOME}",
                     "Veja quanto um valor antigo vale hoje pelo IPCA do IBGE e quanto do poder de compra a inflação levou desde 1995.",
                     inflacao(fator, ate)),
        "rendimento-selic": (f"Quanto rende na Selic hoje: poupança, Tesouro Selic e CDB · {config.NOME}",
                             "Simule quanto rendem R$ 1 mil, R$ 10 mil ou outro valor na poupança, no Tesouro Selic e em CDB, já com o IR.",
                             rendimento(selic)),
        "dolar-cartao": (f"Dólar no cartão de crédito com IOF: calculadora · {config.NOME}",
                         "Calcule quanto custa uma compra em dólar no cartão de crédito, com a cotação do dia, o spread do banco e o IOF.",
                         dolar(cotacao, quando)),
    }
    for slug, (titulo, descricao, corpo) in paginas.items():
        (pasta / f"{slug}.html").write_text(pagina(titulo, descricao, corpo, raiz="../", caminho=f"ferramentas/{slug}.html",
                                                   extra_css=CSS))
    return [f"ferramentas/{slug}.html" for slug in paginas]
