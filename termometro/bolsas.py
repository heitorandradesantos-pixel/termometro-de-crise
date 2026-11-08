"""Horário das bolsas: que horas abrem e fecham as principais bolsas do mundo, no horário de Brasília.

Ferramenta fora da home (menu Ferramentas), aprovada pelo conselho em 08/11/2026 (issue #24):
- hub /horario-bolsas/ com a tabela em HTML estático (o Google e o leitor de tela leem sem JavaScript);
- páginas próprias só da B3 e de Nova York, as únicas com calendário oficial de feriados (selo "aberta agora");
- nas outras bolsas, só o horário regular, com "feriados podem alterar";
- uma linha com a hora local e o horário da bolsa em cada página de país.
Sem cotação nessas páginas (veto do guardião de regras). Os horários são o pregão regular, sem leilões.
"""

import html
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config

BRASILIA = ZoneInfo("America/Sao_Paulo")
REVISADO = "08/11/2026"  # última revisão dos horários e dos calendários
SEG_A_SEX = (0, 1, 2, 3, 4)
DOM_A_QUI = (6, 0, 1, 2, 3)

# chave, nome, cidade, país (como no termômetro), fuso, sessões no horário local, dias de pregão, site oficial
BOLSAS = [
    ("b3", "B3", "São Paulo", "Brasil", "America/Sao_Paulo", None, SEG_A_SEX, "https://www.b3.com.br"),
    ("nyse", "NYSE e Nasdaq", "Nova York", "EUA", "America/New_York", [("09:30", "16:00")], SEG_A_SEX,
     "https://www.nyse.com/markets/hours-calendars"),
    ("tsx", "Bolsa de Toronto (TSX)", "Toronto", "Canadá", "America/Toronto", [("09:30", "16:00")], SEG_A_SEX,
     "https://www.tsx.com"),
    ("bmv", "Bolsa Mexicana (BMV)", "Cidade do México", "México", "America/Mexico_City", [("08:30", "15:00")],
     SEG_A_SEX, "https://www.bmv.com.mx"),
    ("byma", "BYMA", "Buenos Aires", "Argentina", "America/Argentina/Buenos_Aires", [("10:30", "17:00")], SEG_A_SEX,
     "https://www.byma.com.ar"),
    ("lse", "Bolsa de Londres (LSE)", "Londres", "Reino Unido", "Europe/London", [("08:00", "16:30")], SEG_A_SEX,
     "https://www.londonstockexchange.com"),
    ("xetra", "Bolsa de Frankfurt (Xetra)", "Frankfurt", "Alemanha", "Europe/Berlin", [("09:00", "17:30")],
     SEG_A_SEX, "https://www.xetra.com"),
    ("paris", "Euronext Paris", "Paris", "França", "Europe/Paris", [("09:00", "17:30")], SEG_A_SEX,
     "https://www.euronext.com"),
    ("milao", "Euronext Milão (Borsa Italiana)", "Milão", "Itália", "Europe/Rome", [("09:00", "17:30")], SEG_A_SEX,
     "https://www.borsaitaliana.it"),
    ("madri", "Bolsa de Madri (BME)", "Madri", "Espanha", "Europe/Madrid", [("09:00", "17:30")], SEG_A_SEX,
     "https://www.bolsasymercados.es"),
    ("lisboa", "Euronext Lisboa", "Lisboa", "Portugal", "Europe/Lisbon", [("08:00", "16:30")], SEG_A_SEX,
     "https://www.euronext.com"),
    ("six", "SIX Swiss Exchange", "Zurique", "Suíça", "Europe/Zurich", [("09:00", "17:30")], SEG_A_SEX,
     "https://www.six-group.com"),
    ("istambul", "Borsa Istanbul", "Istambul", "Turquia", "Europe/Istanbul", [("10:00", "18:00")], SEG_A_SEX,
     "https://www.borsaistanbul.com"),
    ("tadawul", "Saudi Exchange (Tadawul)", "Riad", "Arábia Saudita", "Asia/Riyadh", [("10:00", "15:00")], DOM_A_QUI,
     "https://www.saudiexchange.sa"),
    ("jse", "Bolsa de Joanesburgo (JSE)", "Joanesburgo", "África do Sul", "Africa/Johannesburg", [("09:00", "17:00")],
     SEG_A_SEX, "https://www.jse.co.za"),
    ("toquio", "Bolsa de Tóquio", "Tóquio", "Japão", "Asia/Tokyo", [("09:00", "11:30"), ("12:30", "15:30")], SEG_A_SEX,
     "https://www.jpx.co.jp/english/"),
    ("xangai", "Bolsa de Xangai", "Xangai", "China", "Asia/Shanghai", [("09:30", "11:30"), ("13:00", "15:00")],
     SEG_A_SEX, "https://english.sse.com.cn"),
    ("hk", "Bolsa de Hong Kong (HKEX)", "Hong Kong", "Hong Kong", "Asia/Hong_Kong", [("09:30", "12:00"), ("13:00", "16:00")],
     SEG_A_SEX, "https://www.hkex.com.hk"),
    ("india", "NSE (Índia)", "Mumbai", "Índia", "Asia/Kolkata", [("09:15", "15:30")], SEG_A_SEX, "https://www.nseindia.com"),
    ("coreia", "Bolsa da Coreia (KRX)", "Seul", "Coreia do Sul", "Asia/Seoul", [("09:00", "15:30")], SEG_A_SEX,
     "https://global.krx.co.kr"),
    ("taiwan", "Bolsa de Taiwan (TWSE)", "Taipé", "Taiwan", "Asia/Taipei", [("09:00", "13:30")], SEG_A_SEX,
     "https://www.twse.com.tw/en/"),
    ("singapura", "Bolsa de Singapura (SGX)", "Singapura", "Singapura", "Asia/Singapore", [("09:00", "12:00"), ("13:00", "17:00")],
     SEG_A_SEX, "https://www.sgx.com"),
    ("asx", "Bolsa da Austrália (ASX)", "Sydney", "Austrália", "Australia/Sydney", [("10:00", "16:00")], SEG_A_SEX,
     "https://www.asx.com.au"),
]
POR_CHAVE = {b[0]: b for b in BOLSAS}
POR_PAIS = {b[3]: b for b in BOLSAS}

# Hora local dos países do termômetro sem bolsa conferida aqui: cidade de referência e fuso
CIDADES = {"Chile": ("Santiago", "America/Santiago"), "Colômbia": ("Bogotá", "America/Bogota"),
           "Peru": ("Lima", "America/Lima"), "Paraguai": ("Assunção", "America/Asuncion"),
           "Uruguai": ("Montevidéu", "America/Montevideo"), "Rússia": ("Moscou", "Europe/Moscow"),
           "Israel": ("Tel Aviv", "Asia/Jerusalem"), "Egito": ("Cairo", "Africa/Cairo"),
           "Nigéria": ("Lagos", "Africa/Lagos"), "Quênia": ("Nairóbi", "Africa/Nairobi"),
           "Marrocos": ("Casablanca", "Africa/Casablanca"), "Indonésia": ("Jacarta", "Asia/Jakarta")}

# Calendários oficiais (os únicos com selo "aberta agora"). Fora do período coberto, o selo some ("em revisão").
CALENDARIOS = {
    "b3": {
        "fonte": "https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm",
        "ate": "2026-12-31",
        "feriados": {"2026-01-01": "Confraternização Universal", "2026-02-16": "Carnaval", "2026-02-17": "Carnaval",
                     "2026-04-03": "Sexta-feira Santa", "2026-04-21": "Tiradentes", "2026-05-01": "Dia do Trabalho",
                     "2026-06-04": "Corpus Christi", "2026-09-07": "Independência do Brasil",
                     "2026-10-12": "Nossa Senhora Aparecida", "2026-11-02": "Finados",
                     "2026-11-20": "Dia Nacional de Zumbi e da Consciência Negra",
                     "2026-12-24": "Véspera de Natal (sem pregão)", "2026-12-25": "Natal",
                     "2026-12-31": "Véspera de Ano Novo (sem pregão)"},
        "especiais": {"2026-02-18": [("13:00", None)]},  # quarta-feira de cinzas: abre às 13h, fecha no horário normal
    },
    "nyse": {
        "fonte": "https://www.businesswire.com/news/home/20251223981478/en/NYSE-Group-Announces-2026-2027-and-2028-Holiday-and-Early-Closings-Calendar",
        "ate": "2027-12-31",
        "feriados": {"2026-01-01": "Ano Novo", "2026-01-19": "Dia de Martin Luther King Jr.",
                     "2026-02-16": "Dia dos Presidentes", "2026-04-03": "Sexta-feira Santa", "2026-05-25": "Memorial Day",
                     "2026-06-19": "Juneteenth", "2026-07-03": "Independência (observado)", "2026-09-07": "Labor Day",
                     "2026-11-26": "Ação de Graças", "2026-12-25": "Natal",
                     "2027-01-01": "Ano Novo", "2027-01-18": "Dia de Martin Luther King Jr.",
                     "2027-02-15": "Dia dos Presidentes", "2027-03-26": "Sexta-feira Santa", "2027-05-31": "Memorial Day",
                     "2027-06-18": "Juneteenth (observado)", "2027-07-05": "Independência (observado)",
                     "2027-09-06": "Labor Day", "2027-11-25": "Ação de Graças", "2027-12-24": "Natal (observado)"},
        "especiais": {"2026-11-27": [(None, "13:00")], "2026-12-24": [(None, "13:00")], "2027-11-26": [(None, "13:00")]},
    },
}
COM_SELO = tuple(CALENDARIOS)


def _hm(t: str) -> tuple[int, int]:
    h, m = t.split(":")
    return int(h), int(m)


def horario_verao_eua(dia: date) -> bool:
    meio_dia = datetime(dia.year, dia.month, dia.day, 12, tzinfo=ZoneInfo("America/New_York"))
    return bool(meio_dia.dst())


def sessoes_locais(chave: str, dia: date) -> list[tuple[str, str]]:
    """As sessões do pregão regular no horário local, num dia de pregão. A B3 acompanha o horário de verão dos EUA:
    com ele, 10h às 17h; sem ele, 10h às 18h (o pregão vai até 17h55 e o call de fechamento até 18h)."""
    b = POR_CHAVE[chave]
    if chave == "b3":
        return [("10:00", "17:00")] if horario_verao_eua(dia) else [("10:00", "18:00")]
    return list(b[5])


def pregao(chave: str, dia: date, calendario: bool = True) -> list[tuple[datetime, datetime]] | None:
    """Os intervalos de pregão do dia (no fuso da bolsa). [] = não tem pregão; None = sem calendário para saber
    (só para as bolsas com selo, fora do período coberto). Com calendario=False, só o horário regular do dia."""
    b = POR_CHAVE[chave]
    fuso = ZoneInfo(b[4])
    if dia.weekday() not in b[6]:
        return []
    cal = CALENDARIOS.get(chave) if calendario else None
    sessoes = sessoes_locais(chave, dia)
    if cal:
        iso = dia.isoformat()
        if iso > cal["ate"]:
            return None
        if iso in cal["feriados"]:
            return []
        for inicio, fim in cal.get("especiais", {}).get(iso, []):
            sessoes = [(inicio or sessoes[0][0], fim or sessoes[-1][1])]
    saida = []
    for ini, fim in sessoes:
        (h1, m1), (h2, m2) = _hm(ini), _hm(fim)
        saida.append((datetime(dia.year, dia.month, dia.day, h1, m1, tzinfo=fuso),
                      datetime(dia.year, dia.month, dia.day, h2, m2, tzinfo=fuso)))
    return saida


def hora(dt: datetime) -> str:
    dt = dt.astimezone(BRASILIA) if dt.tzinfo else dt
    return f"{dt.hour}h{dt.minute:02d}" if dt.minute else f"{dt.hour}h"


def _hora_texto(t: str) -> str:
    h, m = _hm(t)
    return f"{h}h{m:02d}" if m else f"{h}h"


def faixa_local(sessoes: list[tuple[str, str]]) -> str:
    return " e ".join(f"{_hora_texto(a)} às {_hora_texto(b)}" for a, b in sessoes)


def faixa_brasilia(intervalos: list[tuple[datetime, datetime]]) -> str:
    return " e ".join(f"{hora(a.astimezone(BRASILIA))} às {hora(b.astimezone(BRASILIA))}" for a, b in intervalos)


def dia_tipico(chave: str, referencia: date) -> date:
    """O primeiro dia de pregão regular a partir da data (para mostrar o horário de Brasília de 'hoje')."""
    for i in range(14):
        d = referencia + timedelta(days=i)
        if pregao(chave, d, calendario=False):
            return d
    return referencia


def regular(chave: str, referencia: date) -> list[tuple[datetime, datetime]]:
    """O horário regular do próximo dia de pregão (para a tabela), sem depender do calendário de feriados."""
    return pregao(chave, dia_tipico(chave, referencia), calendario=False) or []


def janela(chave: str, inicio: date, dias: int = 14) -> list[list[int]]:
    """Intervalos de pregão (em milissegundos UTC) dos próximos dias, para o relógio da página."""
    saida = []
    for i in range(-1, dias):
        p = pregao(chave, inicio + timedelta(days=i))
        for a, b in p or []:
            saida.append([int(a.timestamp() * 1000), int(b.timestamp() * 1000)])
    return saida


def proximas_trocas(hoje: date, dias: int = 400) -> list[tuple[date, str]]:
    """As próximas mudanças de horário de verão nos EUA e na Europa (que mexem no horário de Brasília)."""
    trocas = []
    for nome, fuso in (("EUA", "America/New_York"), ("Europa", "Europe/London")):
        z = ZoneInfo(fuso)
        antes = None
        for i in range(dias):
            d = hoje + timedelta(days=i)
            dst = bool(datetime(d.year, d.month, d.day, 12, tzinfo=z).dst())
            if antes is not None and dst != antes:
                trocas.append((d, f"{'começa' if dst else 'termina'} o horário de verão {'nos EUA' if nome == 'EUA' else 'na Europa'}"))
            antes = dst
    return sorted(trocas)[:4]


def data_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def dados_js(hoje: date) -> dict:
    """O que o JavaScript da página precisa: fuso e, nas bolsas com selo, os intervalos e feriados."""
    out = {}
    for chave, nome, cidade, pais, fuso, *_ in BOLSAS:
        item = {"fuso": fuso}
        if chave in COM_SELO:
            cal = CALENDARIOS[chave]
            item.update(pregao=janela(chave, hoje), ate=cal["ate"],
                        feriados={d: n for d, n in cal["feriados"].items() if d >= (hoje - timedelta(days=1)).isoformat()})
        out[chave] = item
    return out


SCRIPT = """<script>
(function(){
var D=JSON.parse(document.getElementById('bolsas-dados').textContent);
function hm(tz){try{return new Intl.DateTimeFormat('pt-BR',{timeZone:tz,hour:'2-digit',minute:'2-digit'}).format(new Date())}catch(e){return ''}}
function diaLocal(tz){return new Intl.DateTimeFormat('en-CA',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())}
function brasilia(ms){var d=new Date(ms);var f=new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',weekday:'short',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});return f.format(d)}
function selo(k){var b=D[k];if(!b||!b.pregao)return null;var agora=Date.now(),hoje=diaLocal(b.fuso);
if(hoje>b.ate)return {t:'Calendário em revisão',c:'revisao'};
for(var i=0;i<b.pregao.length;i++){var p=b.pregao[i];if(agora>=p[0]&&agora<p[1])return {t:'● Aberta agora (fecha às '+brasilia(p[1]).slice(-5)+' de Brasília)',c:'aberta'}}
var prox=null;for(var j=0;j<b.pregao.length;j++){if(b.pregao[j][0]>agora){prox=b.pregao[j][0];break}}
var fer=b.feriados&&b.feriados[hoje];var txt=(fer?'○ Feriado hoje ('+fer+')':'○ Fechada agora')+(prox?'. Abre '+brasilia(prox)+' (Brasília)':'');
return {t:txt,c:fer?'feriado':'fechada'}}
function tick(){document.querySelectorAll('[data-relogio]').forEach(function(e){e.textContent=hm(e.getAttribute('data-relogio'))});
document.querySelectorAll('[data-selo]').forEach(function(e){var s=selo(e.getAttribute('data-selo'));if(!s)return;e.textContent=s.t;e.className='selo '+s.c;e.hidden=false})}
tick();setInterval(tick,30000);
})();
</script>"""

CSS = """.bolsas td,.bolsas th{padding:10px 8px}.bolsas .num{white-space:nowrap}
.selo{display:inline-block;font-size:13px;font-weight:600;border-radius:8px;padding:4px 10px;margin:4px 0;border:1px solid var(--linha)}
.selo.aberta{color:#7FD99A;border-color:#2E6B44}.selo.fechada{color:var(--suave)}.selo.feriado{color:#F2C14E;border-color:#6B5A2E}
.selo.revisao{color:var(--suave)}.relogio{font-variant-numeric:tabular-nums;font-weight:600}
.bloco-fixo{font-size:13px;color:var(--suave);border-top:1px solid var(--linha);margin-top:28px;padding-top:14px}
@media (max-width:720px){.bolsas thead{display:none}.bolsas tr{display:block;background:var(--painel);border-radius:12px;padding:10px 12px;margin:10px 0}
.bolsas td{display:block;border:0;padding:3px 0;text-align:left}.bolsas td[data-r]::before{content:attr(data-r) ": ";color:var(--suave);font-size:13px}}"""


def bloco_fixo(raiz: str, fontes: list[tuple[str, str]]) -> str:
    links = " · ".join(f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(n)}</a>' for n, u in fontes)
    return (f'<p class="bloco-fixo">Horário regular de pregão (sem leilões de abertura e fechamento), conforme os sites '
            f'oficiais das bolsas. Última revisão: {REVISADO}. Feriados locais e horários especiais podem alterar: '
            f'confira no site da bolsa. Fontes: {links}. Conteúdo educativo; não é recomendação de investimento. '
            f'<a href="{raiz}metodologia.html">Metodologia</a> · <a href="{raiz}correcoes.html">Viu um erro? Avise</a>.</p>')


def _dados_tag(hoje: date) -> str:
    return f'<script type="application/json" id="bolsas-dados">{json.dumps(dados_js(hoje), ensure_ascii=False)}</script>'


def linha_tabela(chave: str, hoje: date) -> str:
    _, nome, cidade, pais, fuso, _, dias, _site = POR_CHAVE[chave]
    d = dia_tipico(chave, hoje)
    p = regular(chave, hoje)
    local = faixa_local(sessoes_locais(chave, d))
    dias_txt = "domingo a quinta" if dias == DOM_A_QUI else "segunda a sexta"
    selo = f'<br><span class="selo" data-selo="{chave}" hidden></span>' if chave in COM_SELO else ""
    pagina_propria = {"b3": "b3.html", "nyse": "nova-york.html"}.get(chave)
    nome_html = f'<a href="{pagina_propria}">{html.escape(nome)}</a>' if pagina_propria else html.escape(nome)
    return (f'<tr><td><strong>{nome_html}</strong><br><span class="suave">{html.escape(cidade)}, {html.escape(pais)}</span>{selo}</td>'
            f'<td data-r="Hora local agora" class="num"><span class="relogio" data-relogio="{fuso}"></span></td>'
            f'<td data-r="Horário local" class="num">{local}</td>'
            f'<td data-r="Em Brasília" class="num"><strong>{faixa_brasilia(p)}</strong></td>'
            f'<td data-r="Dias">{dias_txt}</td></tr>')


GRUPOS = [("Américas", ["b3", "nyse", "tsx", "bmv", "byma"]),
          ("Europa", ["lse", "xetra", "paris", "milao", "madri", "lisboa", "six", "istambul"]),
          ("Oriente Médio e África", ["tadawul", "jse"]),
          ("Ásia e Pacífico", ["toquio", "xangai", "hk", "india", "coreia", "taiwan", "singapura", "asx"])]


def faq(perguntas: list[tuple[str, str]]) -> tuple[str, dict]:
    corpo = "".join(f"<h3>{html.escape(p)}</h3><p>{html.escape(r)}</p>" for p, r in perguntas)
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": p, "acceptedAnswer": {"@type": "Answer", "text": r}} for p, r in perguntas]}
    return f'<section><h2>Perguntas frequentes</h2>{corpo}</section>', ld


def _jsonld(*itens: dict) -> str:
    return "".join(f'<script type="application/ld+json">{json.dumps(i, ensure_ascii=False)}</script>' for i in itens)


def _migalhas(*passos: tuple[str, str]) -> dict:
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": config.url_publica(c)} for i, (n, c) in enumerate(passos, 1)]}


def _trocas_html(hoje: date) -> str:
    trocas = proximas_trocas(hoje)
    if not trocas:
        return ""
    itens = "".join(f"<li><strong>{data_br(d)}</strong>: {t}</li>" for d, t in trocas)
    return f'<p>Próximas trocas de horário que mexem no horário de Brasília:</p><ul>{itens}</ul>'


def hub(hoje: date) -> str:
    blocos = ""
    for titulo, chaves in GRUPOS:
        linhas = "".join(linha_tabela(c, hoje) for c in chaves)
        blocos += (f'<h2>{titulo}</h2><table class="bolsas"><thead><tr><th>Bolsa</th><th>Hora local agora</th>'
                   f'<th>Pregão (hora local)</th><th>Pregão (horário de Brasília)</th><th>Dias</th></tr></thead>'
                   f'<tbody>{linhas}</tbody></table>')
    ny, b3, tq = regular("nyse", hoje), regular("b3", hoje), regular("toquio", hoje)
    perguntas = [
        ("Que horas abre a bolsa de Nova York no horário de Brasília?",
         (f"Hoje, a NYSE e a Nasdaq negociam das {faixa_brasilia(ny)} pelo horário de Brasília (9h30 às 16h em Nova "
          "York). Quando os EUA estão no horário de verão (de março a novembro), o pregão começa uma hora mais cedo "
          "para quem está no Brasil.")),
        ("Que horas abre e fecha a B3?",
         (f"Hoje, o pregão regular de ações da B3 vai das {faixa_brasilia(b3)}. A B3 acompanha o horário de verão dos "
          "EUA: com ele, fecha às 17h; sem ele, às 18h.")),
        ("Por que a bolsa de Tóquio abre de noite no Brasil?",
         (f"Porque o Japão está 12 horas à frente de Brasília. O pregão de Tóquio, das 9h às 15h30 no Japão, acontece "
          f"das {faixa_brasilia(tq)} pelo horário de Brasília, começando na noite anterior.")),
        ("O Brasil ainda tem horário de verão?",
         ("Não. O horário de verão no Brasil acabou em 2019. Quem muda são os EUA e a Europa, e por isso a diferença "
          "para Nova York, Londres e Frankfurt muda em março e em novembro.")),
    ]
    faq_html, faq_ld = faq(perguntas)
    corpo = (f'<p class="trilha"><a href="../index.html">Início</a> › <a href="../ferramentas/index.html">Ferramentas</a> › Horário das bolsas</p>'
             f'<section class="edicao"><h1>Horário das bolsas do mundo no horário de Brasília</h1>'
             f'<p>Que horas abre e fecha cada bolsa, no horário local e no horário de Brasília, com a hora de agora em cada cidade. '
             f'A <a href="b3.html">B3</a> e <a href="nova-york.html">Nova York</a> mostram também se estão abertas agora, '
             f'com os feriados oficiais.</p>'
             f'<p class="suave">Horário de Brasília calculado para o próximo dia de pregão de cada bolsa a partir de {data_br(hoje)}.</p>'
             f'{blocos}'
             f'<h2>Por que o horário muda durante o ano</h2>'
             f'<p>O Brasil não tem horário de verão desde 2019, mas os EUA e a Europa têm. Quando eles adiantam ou atrasam o '
             f'relógio, a diferença para Brasília muda em uma hora: o pregão de Nova York, por exemplo, vai de 10h30 às 17h '
             f'(com horário de verão nos EUA) para 11h30 às 18h (sem). A B3 acompanha Nova York e muda o fechamento junto.</p>'
             f'{_trocas_html(hoje)}'
             f'<h2>Pausa para o almoço na Ásia</h2>'
             f'<p>Tóquio, Xangai, Hong Kong e Singapura param no meio do dia. Por isso aparecem duas faixas de horário. '
             f'As outras bolsas da tabela negociam direto, sem pausa.</p>'
             f'{faq_html}'
             f'<p><a class="contorno" href="../mundo.html">Ver o termômetro de crise de cada país</a></p>'
             f'{bloco_fixo("../", [("B3", CALENDARIOS["b3"]["fonte"]), ("NYSE", CALENDARIOS["nyse"]["fonte"])])}'
             f'</section>{_dados_tag(hoje)}{SCRIPT}'
             + _jsonld(faq_ld, _migalhas(("Início", ""), ("Horário das bolsas", "horario-bolsas/index.html"))))
    return corpo


def _feriados_html(chave: str, hoje: date) -> str:
    cal = CALENDARIOS[chave]
    itens = [(d, n) for d, n in sorted(cal["feriados"].items()) if d >= hoje.isoformat()]
    especiais = {d: s for d, s in cal.get("especiais", {}).items() if d >= hoje.isoformat()}
    linhas = "".join(f"<li><strong>{data_br(date.fromisoformat(d))}</strong>: {html.escape(n)}, sem pregão</li>" for d, n in itens)
    for d, sess in sorted(especiais.items()):
        fim = sess[0][1]
        ini = sess[0][0]
        txt = f"fecha mais cedo, às {_hora_texto(fim)} (hora local)" if fim else f"abre mais tarde, às {_hora_texto(ini)}"
        linhas += f"<li><strong>{data_br(date.fromisoformat(d))}</strong>: {txt}</li>"
    return (f'<h2>Feriados e dias especiais</h2><ul>{linhas}</ul>'
            f'<p class="suave">Calendário oficial publicado até {data_br(date.fromisoformat(cal["ate"]))}. '
            f'<a href="{html.escape(cal["fonte"])}" target="_blank" rel="noopener">Fonte</a>.</p>') if linhas else ""


def pagina_b3(hoje: date) -> str:
    p = regular("b3", hoje)
    perguntas = [
        ("A B3 abre no sábado?", "Não. O pregão de ações da B3 é de segunda a sexta, fora os feriados do calendário oficial."),
        ("Por que a B3 muda o horário em março e em novembro?",
         ("Para acompanhar Nova York. Quando os EUA entram no horário de verão, a B3 fecha às 17h; quando saem, "
          "às 18h.")),
        ("A B3 abre em feriado estadual de São Paulo?",
         "Depende do calendário do ano. Em 2026, a B3 teve pregão normal em 9 de julho, feriado paulista.")]
    faq_html, faq_ld = faq(perguntas)
    return (f'<p class="trilha"><a href="../index.html">Início</a> › <a href="index.html">Horário das bolsas</a> › B3</p>'
            f'<section class="edicao"><h1>Horário da B3 hoje: que horas abre e fecha a bolsa</h1>'
            f'<p><span class="selo" data-selo="b3" hidden></span></p>'
            f'<p>O pregão regular de ações da B3 vai das <strong>{faixa_brasilia(p)}</strong> (horário de Brasília), de segunda '
            f'a sexta. Agora em São Paulo são <span class="relogio" data-relogio="America/Sao_Paulo"></span>.</p>'
            f'<h2>Como o horário muda no ano</h2>'
            f'<ul><li><strong>Com horário de verão nos EUA</strong> (março a novembro): 10h às 17h.</li>'
            f'<li><strong>Sem horário de verão nos EUA</strong> (novembro a março): 10h às 18h. O pregão vai até 17h55 e o '
            f'call de fechamento, até 18h.</li></ul>'
            f'<p>A mudança mais recente foi em 3 de novembro de 2026, quando o fechamento passou para as 18h '
            f'(<a href="https://www.b3.com.br/pt_br/noticias/b3-ajusta-horarios-de-negociacao-de-acoes-e-derivativos-acompanhando-fim-do-horario-de-verao-nos-eua.htm" '
            f'target="_blank" rel="noopener">comunicado da B3</a>).</p>'
            f'{_trocas_html(hoje)}{_feriados_html("b3", hoje)}{faq_html}'
            f'<p><a class="contorno" href="index.html">Ver todas as bolsas</a> <a class="contorno" href="../paises/brasil.html">'
            f'Termômetro do Brasil</a></p>'
            f'{bloco_fixo("../", [("B3: calendário 2026", CALENDARIOS["b3"]["fonte"])])}'
            f'</section>{_dados_tag(hoje)}{SCRIPT}'
            + _jsonld(faq_ld, _migalhas(("Início", ""), ("Horário das bolsas", "horario-bolsas/index.html"),
                                        ("B3", "horario-bolsas/b3.html"))))


def pagina_nova_york(hoje: date) -> str:
    p = regular("nyse", hoje)
    perguntas = [
        ("A NYSE e a Nasdaq têm o mesmo horário?",
         "Sim. As duas negociam das 9h30 às 16h no horário de Nova York e seguem o mesmo calendário de feriados."),
        ("Que horas abre Nova York no horário de Brasília?",
         "Com horário de verão nos EUA (março a novembro), às 10h30 de Brasília. Sem ele (novembro a março), às 11h30."),
        ("O que é o pregão mais curto?",
         ("Em alguns dias, como a sexta depois do Dia de Ação de Graças, a bolsa fecha às 13h de Nova York, três horas "
          "antes do normal."))]
    faq_html, faq_ld = faq(perguntas)
    return (f'<p class="trilha"><a href="../index.html">Início</a> › <a href="index.html">Horário das bolsas</a> › Nova York</p>'
            f'<section class="edicao"><h1>Horário da bolsa de Nova York no horário de Brasília</h1>'
            f'<p><span class="selo" data-selo="nyse" hidden></span></p>'
            f'<p>A NYSE e a Nasdaq negociam das 9h30 às 16h em Nova York, de segunda a sexta. No horário de Brasília, hoje, '
            f'isso dá <strong>{faixa_brasilia(p)}</strong>. Agora em Nova York são '
            f'<span class="relogio" data-relogio="America/New_York"></span>.</p>'
            f'<h2>Por que muda no ano</h2><p>Os EUA têm horário de verão, e o Brasil não. De março a novembro, Nova York '
            f'fica 1 hora atrás de Brasília (pregão das 10h30 às 17h); de novembro a março, 2 horas (11h30 às 18h).</p>'
            f'{_trocas_html(hoje)}{_feriados_html("nyse", hoje)}{faq_html}'
            f'<p><a class="contorno" href="index.html">Ver todas as bolsas</a> <a class="contorno" href="../paises/eua.html">'
            f'Termômetro dos EUA</a></p>'
            f'{bloco_fixo("../", [("NYSE: feriados 2026 a 2028", CALENDARIOS["nyse"]["fonte"])])}'
            f'</section>{_dados_tag(hoje)}{SCRIPT}'
            + _jsonld(faq_ld, _migalhas(("Início", ""), ("Horário das bolsas", "horario-bolsas/index.html"),
                                        ("Nova York", "horario-bolsas/nova-york.html"))))


def ferramentas() -> str:
    return ('<p class="trilha"><a href="../index.html">Início</a> › Ferramentas</p>'
            '<section class="edicao"><h1>Ferramentas</h1><p>Ferramentas grátis do Termômetro de Crise para o dia a dia do '
            'seu dinheiro.</p><div class="lista"><a href="../horario-bolsas/index.html"><strong>Horário das bolsas</strong>'
            '<br><span class="suave">Que horas abre e fecha cada bolsa do mundo, no horário de Brasília, com a hora local '
            'agora.</span></a></div></section>')


def linha_pais(pais: str, raiz: str, hoje: date | None = None) -> str:
    """A linha 'Hora local e horário da bolsa' das páginas de país (sem cotação)."""
    hoje = hoje or datetime.now(BRASILIA).date()
    b = POR_PAIS.get(pais)
    if b:
        chave, nome, cidade, _, fuso, *_ = b
        p = regular(chave, hoje)
        selo = f' <span class="selo" data-selo="{chave}" hidden></span>' if chave in COM_SELO else ""
        texto = (f'Hora local em {html.escape(cidade)}: <span class="relogio" data-relogio="{fuso}"></span> · '
                 f'{html.escape(nome)}: pregão das {faixa_brasilia(p)} (horário de Brasília){selo}')
    elif pais in CIDADES:
        cidade, fuso = CIDADES[pais]
        texto = f'Hora local em {html.escape(cidade)}: <span class="relogio" data-relogio="{fuso}"></span>'
    else:
        return ""
    return (f'<p class="suave" style="font-size:14px;margin:4px 0 20px">🕒 {texto} · '
            f'<a href="{raiz}horario-bolsas/index.html">Horário das bolsas do mundo</a></p>'
            f'{_dados_tag(hoje)}{SCRIPT}')


def gerar(saida: Path, pagina, hoje: date | None = None) -> list[str]:
    """Grava o hub, as páginas da B3 e de Nova York e a página de ferramentas. Devolve os caminhos para o mapa."""
    hoje = hoje or datetime.now(BRASILIA).date()
    (saida / "horario-bolsas").mkdir(parents=True, exist_ok=True)
    (saida / "ferramentas").mkdir(parents=True, exist_ok=True)
    (saida / "horario-bolsas" / "index.html").write_text(pagina(
        f"Horário das bolsas do mundo no horário de Brasília · {config.NOME}",
        "Que horas abre e fecha cada bolsa: B3, Nova York, Londres, Frankfurt, Tóquio, Xangai e outras, no horário local "
        "e no de Brasília, com a hora de agora e os feriados.", hub(hoje), raiz="../", caminho="horario-bolsas/index.html",
        extra_css=CSS))
    (saida / "horario-bolsas" / "b3.html").write_text(pagina(
        f"Horário da B3 hoje: que horas abre e fecha a bolsa · {config.NOME}",
        "Horário do pregão de ações da B3 hoje, como ele muda com o horário de verão dos EUA e os feriados da bolsa.",
        pagina_b3(hoje), raiz="../", caminho="horario-bolsas/b3.html", extra_css=CSS))
    (saida / "horario-bolsas" / "nova-york.html").write_text(pagina(
        f"Horário da bolsa de Nova York no horário de Brasília · {config.NOME}",
        "Que horas abrem a NYSE e a Nasdaq no horário de Brasília hoje, com horário de verão e feriados da bolsa americana.",
        pagina_nova_york(hoje), raiz="../", caminho="horario-bolsas/nova-york.html", extra_css=CSS))
    (saida / "ferramentas" / "index.html").write_text(pagina(
        f"Ferramentas · {config.NOME}", "Ferramentas grátis do Termômetro de Crise: horário das bolsas do mundo.",
        ferramentas(), raiz="../", caminho="ferramentas/index.html"))
    return ["horario-bolsas/index.html", "horario-bolsas/b3.html", "horario-bolsas/nova-york.html", "ferramentas/index.html"]
