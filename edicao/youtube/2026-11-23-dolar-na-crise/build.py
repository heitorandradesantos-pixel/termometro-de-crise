#!/usr/bin/env python3
"""Monta o HTML animado do vídeo piloto (dólar na crise) e o áudio final com pausas entre capítulos."""
import json, re, subprocess, unicodedata, html
from difflib import SequenceMatcher
from pathlib import Path

P = Path(__file__).resolve().parent
REPO = Path("/home/claude/termometro-de-crise")
LEAD, PAUSA, CAUDA = 0.8, 1.5, 8.0
CAPS = [(5, "A moeda do mundo"), (11, "A corrida para a segurança"), (18, "2008 e 2020 em números"),
        (25, "2022: até o euro apanhou"), (32, "E o ouro?"), (37, "Por que no Brasil sobe mais"),
        (41, "O que muda no seu bolso"), (48, "O que tirar disso")]

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))

# ---------- texto e alinhamento ----------
texto = (P.parent / "tts1.txt").read_text().strip().split("\n\n")
t2 = (P.parent / "tts2.txt").read_text().strip().split("\n\n")
# a divisão automática deixou "Ou seja..." no começo da parte 2; na geração ele foi para o fim da parte 1 (não muda a ordem)
paras = texto + t2
assert len(paras) == 59, len(paras)

pal = []  # (paragrafo, palavra original, normalizada)
for i, p in enumerate(paras):
    for w in p.split():
        n = norm(w)
        if n:
            pal.append([i, w, n])

tr = json.loads((P / "t" / "transcricao.json").read_text())
wh = [(w[0], w[1], norm(w[2])) for s in tr for w in s["palavras"] if norm(w[2])]
sm = SequenceMatcher(None, [x[2] for x in pal], [x[2] for x in wh], autojunk=False)
ini = [None] * len(pal); fim = [None] * len(pal)
for a, b, n in sm.get_matching_blocks():
    for k in range(n):
        ini[a + k], fim[a + k] = wh[b + k][0], wh[b + k][1]
casadas = sum(1 for x in ini if x is not None)
# interpola as que não casaram
conhecidos = [i for i, x in enumerate(ini) if x is not None]
for i in range(len(pal)):
    if ini[i] is None:
        ant = max([c for c in conhecidos if c < i], default=None)
        pos = min([c for c in conhecidos if c > i], default=None)
        if ant is None: ini[i] = fim[i] = max(0.0, ini[pos] - 0.3)
        elif pos is None: ini[i] = fim[i] = fim[ant] + 0.3
        else:
            f = (i - ant) / (pos - ant)
            ini[i] = fim[ant] + (ini[pos] - fim[ant]) * f
            fim[i] = ini[i] + 0.2
print(f"palavras {len(pal)}, casadas {casadas} ({100*casadas/len(pal):.0f}%)")

prim = {}  # primeira palavra de cada parágrafo
for k, (i, _, _) in enumerate(pal):
    prim.setdefault(i, k)

# ---------- linha do tempo com pausas ----------
dur_audio = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(P / "narracao.wav")]))
cortes = []
for pi, nome in CAPS:
    k = prim[pi]
    cortes.append(max(fim[k - 1] + 0.02, ini[k] - 0.14))

def T(t):  # tempo do áudio original -> tempo do vídeo
    return t + LEAD + PAUSA * sum(1 for c in cortes if c <= t + 1e-6)

TOTAL = T(dur_audio) + CAUDA
pt = lambda i: T(ini[prim[i]])  # começo do parágrafo no vídeo

# áudio final
partes, ant = [], 0.0
filtro, n = [], 0
filtro.append(f"anullsrc=r=44100:cl=stereo,atrim=0:{LEAD}[s{n}]"); partes.append(f"[s{n}]"); n += 1
for c in cortes + [dur_audio]:
    filtro.append(f"[0:a]atrim={ant}:{c},asetpts=PTS-STARTPTS[s{n}]"); partes.append(f"[s{n}]"); n += 1
    if c != dur_audio:
        filtro.append(f"anullsrc=r=44100:cl=stereo,atrim=0:{PAUSA}[s{n}]"); partes.append(f"[s{n}]"); n += 1
    ant = c
filtro.append(f"anullsrc=r=44100:cl=stereo,atrim=0:{CAUDA}[s{n}]"); partes.append(f"[s{n}]"); n += 1
filtro.append("".join(partes) + f"concat=n={n}:v=0:a=1[a]")
subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", str(P / "narracao.wav"), "-filter_complex", ";".join(filtro),
                       "-map", "[a]", "-c:a", "aac", "-b:a", "192k", str(P / "audio-final.m4a")])

# ---------- legendas ----------
legs, atual, k0 = [], [], 0
for k, (i, w, _) in enumerate(pal):
    if not atual: k0 = k
    atual.append(w)
    ultimo = k + 1 == len(pal) or pal[k + 1][0] != i
    if ultimo or w[-1] in ".?!" or (len(atual) >= 4 and w[-1] in ":,;") or len(atual) >= 8:
        legs.append([round(T(ini[k0]), 2), " ".join(atual)]); atual = []
legs = [[a, tx, (legs[j + 1][0] if j + 1 < len(legs) else a + 2.5)] for j, (a, tx) in enumerate(legs)]
legs =[[a, tx, min(b, a + 4.2)] for a, tx, b in legs]

# ---------- deixas ----------
def deixa(spec, cena_ini, k_ini):
    """'p12' começo do parágrafo; 'w:frase' quando a frase é dita (a partir da cena); '|+0.3' soma segundos; número = segundos."""
    extra = 0.0
    if "|" in spec:
        spec, e = spec.split("|"); extra = float(e)
    if spec.startswith("p"):
        t = pt(int(spec[1:]))
    elif spec.startswith("w:"):
        alvo = [norm(x) for x in spec[2:].split() if norm(x)]
        t = None
        for k in range(k_ini, len(pal) - len(alvo) + 1):
            if [pal[k + j][2] for j in range(len(alvo))] == alvo:
                t = T(ini[k]); break
        assert t is not None, f"deixa não achada: {spec}"
    else:
        return round(float(spec) + extra, 2)
    return round(max(0.12, t - cena_ini + extra), 2)

# ---------- mapa ----------
mapa = json.loads((REPO / "termometro" / "mapa_mundo.json").read_text())
def centro(d):
    melhor, pts, x, y = [], [], 0.0, 0.0
    for cmd, args in re.findall(r"([MmLlHhVvZz])([^MmLlHhVvZz]*)", d):
        nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", args)]
        if cmd in "Mm":
            if len(pts) > len(melhor): melhor = pts
            pts = []
        if cmd in "MmLl":
            for j in range(0, len(nums) - 1, 2):
                if cmd.islower() and not (cmd == "m" and j == 0 and not pts and x == 0 and y == 0): x, y = x + nums[j], y + nums[j + 1]
                else: x, y = nums[j], nums[j + 1]
                pts.append((x, y))
        elif cmd in "Hh":
            for v in nums: x = x + v if cmd == "h" else v; pts.append((x, y))
        elif cmd in "Vv":
            for v in nums: y = y + v if cmd == "v" else v; pts.append((x, y))
    if len(pts) > len(melhor): melhor = pts
    xs, ys = [p[0] for p in melhor], [p[1] for p in melhor]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
C = {c["a2"]: centro(c["d"]) for c in mapa["paises"]}
MAPA_DEFS = '<g id="mapa">' + "".join(f'<path d="{c["d"]}"/>' for c in mapa["paises"]) + "</g>"
EUA_D = next(c["d"] for c in mapa["paises"] if c["a2"] == "US")
BR_D = next(c["d"] for c in mapa["paises"] if c["a2"] == "BR")

def arco(a, b, cor, d, dur=1.0, alt=0.28):
    (x1, y1), (x2, y2) = C[a], C[b]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - abs(x2 - x1) * alt - 14
    return (f'<path class="arc" d="M{x1:.1f},{y1:.1f} Q{mx:.1f},{my:.1f} {x2:.1f},{y2:.1f}" stroke="{cor}" data-draw="{d}:1" data-dur="{dur}"/>'
            f'<circle class="pt" cx="{x1:.1f}" cy="{y1:.1f}" r="3.2" fill="{cor}" data-d="{d}"/>')

def mapa_svg(extra, destaque_eua=None, destaque_br=False):
    eua = f'<path class="eua" d="{EUA_D}" data-d="{destaque_eua}"/>' if destaque_eua is not None else ""
    br = f'<path class="brd" d="{BR_D}" data-d="0.3"/>' if destaque_br else ""
    return f'<svg class="mapa" viewBox="60 20 900 420"><use href="#mapa" class="terra"/>{eua}{br}{extra}</svg>'

VERM, VERDE, AMAR, AZUL = "#E5554A", "#3FCF8E", "#F2C14E", "#7CC3E0"
ORIG = ["BR", "MX", "AR", "DE", "GB", "FR", "ZA", "NG", "IN", "CN", "JP", "AU", "ID", "SA", "TR", "RU"]
ORIG = [o for o in ORIG if o in C]

# ---------- cenas ----------
def R(tag, cls, d, inner, extra=""):
    return f'<{tag} class="{cls} r" data-d="{d}" {extra}>{inner}</{tag}>'
def cnt(de, ate, dec, d, dur=1.4, pre="", suf=""):
    return f'<span class="cnt" data-de="{de}" data-ate="{ate}" data-dec="{dec}" data-d="{d}" data-dur="{dur}" data-pre="{pre}" data-suf="{suf}">{pre}{suf}</span>'

# gráfico de 2008 (média mensal da Ptax, Banco Central)
V08 = [1.7735, 1.7269, 1.7068, 1.6881, 1.6597, 1.6181, 1.5906, 1.6115, 1.7988, 2.1721, 2.2655, 2.3936]
MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
def graf08():
    W, H, ml, mr, mt, mb = 1500, 620, 110, 60, 30, 120
    x = lambda i: ml + i * (W - ml - mr) / 11
    y = lambda v: mt + (2.6 - v) * (H - mt - mb) / (2.6 - 1.4)
    grade = "".join(f'<line x1="{ml}" x2="{W-mr}" y1="{y(v):.0f}" y2="{y(v):.0f}" class="gr"/><text x="{ml-14}" y="{y(v)+8:.0f}" class="ey" text-anchor="end">R$ {str(v).replace(".", ",")}0</text>' for v in (1.5, 2.0, 2.5))
    meses = "".join(f'<text x="{x(i):.0f}" y="{H-76}" class="ex" text-anchor="middle">{m}</text>' for i, m in enumerate(MES))
    d = "M" + " L".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(V08))
    return W, H, x, y, grade, meses, d

CENAS = []  # (parágrafo inicial, html com {deixas}, capítulo)
def cena(p, corpo):
    CENAS.append([p, corpo])

cena(0, lambda D: f'''<div class="col c">
 {R("div","k","0.2","TODA CRISE É IGUAL")}
 {R("h1","h xl","0.45","O mundo entra em crise.<br><b>O dólar dispara.</b>")}
 <div class="chips">{R("span","chip",D("w:foi assim em 2008"),"2008")}{R("span","chip",D("w:foi assim em 2020"),"2020")}{R("span","chip am",D("w:na próxima"),"A próxima?")}</div></div>''')

cena(2, lambda D: f'''<div class="comapa">{mapa_svg("".join(arco(o,"US",VERM,D("w:o mundo inteiro correu|"+str(0.08*j)),1.1) for j,o in enumerate(ORIG)), destaque_eua="0.5")}
 <div class="sobre">{R("div","k","0.2","2008")}{R("h2","h","0.5","A crise começou <b>dentro dos Estados Unidos</b>")}
 {R("p","s",D("w:o mundo inteiro correu"),"E o mundo inteiro correu pra comprar <b>a moeda deles</b>.")}</div></div>''')

cena(3, lambda D: f'''<div class="col c">{R("h1","h xxl","0.2","<b>Por quê?</b>")}
 <div class="chips g">{R("span","chip gr",D("w:preço do pão"),"🍞 Pão")}{R("span","chip gr",D("w:da gasolina"),"⛽ Gasolina")}{R("span","chip gr",D("w:seu celular"),"📱 Celular")}</div>
 {R("p","s",D("p4"),"Fica até o fim: você nunca mais esquece.")}</div>''')

cena(5, lambda D: f'''<div class="col c">{R("h1","h lg","0.3","O dólar não é só a moeda dos Estados Unidos.")}
 {R("h1","h xl",D("w:ele é a moeda"),"<b>É a moeda do mundo.</b>")}</div>''')

cena(6, lambda D: f'''<div class="col c">{R("div","num","0.2",cnt(0,89,0,D("w:89|-0.5"),1.5,"","%"))}
 {R("p","s lgs",D("w:89|0.3"),"de todas as trocas de moeda do planeta<br>têm o <b>dólar de um lado</b>")}
 {R("div","src",D("w:89|0.8"),"Fonte: Banco de Compensações Internacionais (BIS), pesquisa trienal de abril de 2025")}</div>''')

cena(7, lambda D: f'''<div class="comapa">{mapa_svg(arco("BR","KR",AMAR,D("w:empresa do brasil"),1.6,0.18)+f'<text class="us r" x="{(C["BR"][0]+C["KR"][0])/2:.0f}" y="{(C["BR"][1]+C["KR"][1])/2-150:.0f}" data-d="{D("w:quase sempre")}">US$</text>', destaque_br=True)}
 <div class="sobre baixo"><div class="chips">{R("span","chip",D("w:petróleo"),"Petróleo: em dólar")}{R("span","chip",D("w:soja"),"Soja: em dólar")}{R("span","chip",D("w:minério"),"Minério de ferro: em dólar")}</div></div>
 <div class="sobre">{R("h2","h",D("0.3"),"Brasil vende pra Coreia.<br>O preço? <b>Em dólar.</b>")}</div></div>''')

cena(8, lambda D: f'''<div class="col c">{R("div","k","0.2","A POUPANÇA DE EMERGÊNCIA DOS PAÍSES")}
 {R("h2","h","0.5","Reservas internacionais: quanto está em dólar")}
 <div class="barras">
  <div class="lin r" data-d="{D("p9")}"><span class="rot">2000</span><div class="tr"><div class="bar cz" data-w="71" data-d="{D("p9|0.2")}" data-dur="1.2"></div></div><span class="val">71%</span></div>
  <div class="lin r" data-d="{D("w:57|-0.4")}"><span class="rot">2026</span><div class="tr"><div class="bar" data-w="57" data-d="{D("w:57|-0.2")}" data-dur="1.2"></div></div><span class="val am">57%</span></div>
 </div>
 {R("p","s",D("w:nenhuma outra moeda"),"Caiu devagar. Mas <b>nenhuma outra moeda chegou perto</b>.")}
 {R("div","src",D("w:57|0.6"),"Fonte: Fundo Monetário Internacional (COFER), 2026. Valores aproximados.")}</div>''')

cena(10, lambda D: f'''<div class="col c">{R("div","k","0.2","PRIMEIRA IDEIA")}{R("h1","h xl","0.45","O mundo inteiro<br><b>precisa de dólar</b><br>pra funcionar.")}</div>''')

cena(11, lambda D: f'''<div class="col c">{R("h1","h xl","0.25","Agora vem a parte<br>que <b>pouca gente viu</b>.")}</div>''')

EMERG = [o for o in ["BR", "MX", "ZA", "IN", "ID", "TR"] if o in C]
cena(12, lambda D: f'''<div class="comapa">{mapa_svg("".join(arco("US",o,VERDE,D("w:ele tira dinheiro|"+str(0.15*j)),1.3) for j,o in enumerate(EMERG)), destaque_eua="0.3")}
 <div class="sobre">{R("div","k vd","0.2","QUANDO ESTÁ TUDO CALMO")}{R("h2","h","0.5","O dinheiro sai dos EUA<br>atrás de <b>juro maior</b>")}
 {R("span","chip vd",D("w:ele fica mais barato"),"Entra dólar no Brasil → dólar mais barato")}</div></div>''')

cena(13, lambda D: f'''<div class="comapa">{mapa_svg("".join(arco(o,"US",VERM,D("w:todo mundo corre|"+str(0.07*j)),1.0) for j,o in enumerate(ORIG)), destaque_eua="0.3")}
 <div class="sobre">{R("div","k vm","0.2","QUANDO BATE O MEDO")}{R("h2","h","0.5","Todo mundo corre<br>pra <b>mesma porta</b>")}
 {R("p","s",D("p14"),"A porta é o dólar: os <b>títulos do governo americano</b>.")}
 {R("span","chip vm",D("w:fuga para a segurança"),"FUGA PARA A SEGURANÇA")}</div></div>''')

cena(16, lambda D: f'''<div class="col e">{R("div","k","0.2","O TERCEIRO MOTIVO")}{R("h2","h lg","0.45","Dívida <b>em dólar</b>")}
 <ul class="lista">{R("li","",D("w:empresas e governos"),"Empresas e governos do mundo inteiro devem em dólar")}{R("li","",D("w:o crédito some"),"Na crise, o crédito some")}{R("li","",D("w:todo mundo precisa"),"Todo mundo precisa de dólar <b>ao mesmo tempo</b>")}</ul>
 {R("div","faixa",D("p17"),"Mais gente comprando, menos gente vendendo = <b>o preço sobe</b>")}</div>''')

cena(18, lambda D: f'''<div class="col c">{R("h1","h xl","0.25","Os números contam<br><b>a história sozinhos</b>.")}</div>''')

def c08(D):
    W, H, x, y, grade, meses, d = graf08()
    est = f'{D("0.6")}:0.63,{D("p20")}:0.74,{D("p21")}:1'
    return f'''<div class="col c">{R("h2","h md","0.2","Dólar em 2008 <i>(média de cada mês)</i>")}
 <svg class="graf" viewBox="0 0 {W} {H}">{grade}{meses}
  <path class="lgraf" d="{d}" data-draw="{est}" data-dur="1.6"/>
  <g class="r" data-d="{D("w:um real e cinquenta")}"><circle cx="{x(7):.0f}" cy="{y(1.559):.0f}" r="11" class="pm az"/><text x="{x(7)-10:.0f}" y="{H-36:.0f}" class="an" text-anchor="middle">R$ 1,56 em 1º de agosto</text><text x="{x(7)-10:.0f}" y="{H-4:.0f}" class="an2" text-anchor="middle">menor valor em quase 10 anos</text></g>
  <g class="r" data-d="{D("w:lehman")}"><line x1="{x(8.5):.0f}" x2="{x(8.5):.0f}" y1="40" y2="{H-120}" class="vl"/><text x="{x(8.5)-18:.0f}" y="205" class="an vm" text-anchor="end">Lehman Brothers quebra</text></g>
  <g class="r" data-d="{D("w:dois reais e cinquenta")}"><circle cx="{x(9.4):.0f}" cy="{y(2.5):.0f}" r="11" class="pm vmf"/><text x="{x(9.4)-20:.0f}" y="{y(2.5)+10:.0f}" class="an" text-anchor="end">encostou em R$ 2,50</text></g>
  <g class="r" data-d="{D("w:31 por cento|-0.3")}"><rect x="{W-350}" y="{H-290}" width="290" height="96" rx="16" class="cx"/><text x="{W-205}" y="{H-226}" class="gd" text-anchor="middle">+31% no ano</text></g>
 </svg>
 {R("p","s",D("p22"),"A crise nasceu lá. <b>A moeda mais fraca ficou aqui.</b>")}
 {R("div","src","1.0","Fonte: Banco Central (Ptax) e G1. Fechamento do ano: R$ 2,33.")}</div>'''
cena(19, c08)

cena(23, lambda D: f'''<div class="col c">{R("div","k","0.2","2020 · PANDEMIA")}
 <div class="dea r" data-d="0.5"><span class="de">R$ 4,01</span><span class="seta">→</span><span class="ate">{cnt(4.01,5.90,2,D("w:cinco e noventa|-0.6"),1.6,"R$ ","")}</span></div>
 {R("p","s lgs",D("w:47 por cento|-0.2"),"<b>+47%</b> em pouco mais de quatro meses")}
 {R("div","faixa",D("p24"),"Crise de banco. Crise de saúde. <b>O mesmo resultado.</b>")}
 {R("div","src","1.0","Fonte: InvestNews e Agência Brasil. Fechamento de 13/5/2020, recorde da época.")}</div>''')

cena(25, lambda D: f'''<div class="col c">{R("div","k","0.2","O TERCEIRO CASO")}{R("h1","h xl",D("p26|-0.2"),"2022: a Rússia<br>invade a <b>Ucrânia</b>")}
 <div class="chips">{R("span","chip",D("w:a energia dispara"),"Energia dispara na Europa")}{R("span","chip",D("w:a inflação sobe"),"Inflação sobe no mundo")}{R("span","chip",D("w:aumentam os juros"),"EUA aumentam os juros")}</div></div>''')

cena(27, lambda D: f'''<div class="col c">{R("div","k","0.2","A FORÇA DO DÓLAR CONTRA AS MOEDAS DOS PAÍSES RICOS")}
 {R("div","num","0.3",cnt(96,114,0,D("w:cento e quatorze|-1.0"),1.8,"",""))}
 {R("p","s lgs",D("w:cento e quatorze|0.3"),"pontos: o <b>maior nível em 20 anos</b>")}
 {R("div","src",D("w:cento e quatorze|0.8"),"Fonte: índice do dólar (DXY) em 26/9/2022, via NeoFeed")}</div>''')

cena(28, lambda D: f'''<div class="col c"><div class="dea r" data-d="0.3"><span class="de br">1 euro</span><span class="seta vm">&lt;</span><span class="ate">1 dólar</span></div>
 {R("p","s lgs",D("w:isso não acontecia"),"Não acontecia fazia <b>20 anos</b>")}
 {R("div","faixa",D("p29"),"Na hora do aperto, até <b>moeda forte</b> apanha do dólar.")}
 {R("div","src","1.0","Fonte: AFP (22/8/2022)")}</div>''')

cena(30, lambda D: f'''<div class="col c">{R("div","k vd","0.2","UM DETALHE CURIOSO")}{R("h2","h","0.45","Em 2022, o real <b>aguentou o tranco</b>")}
 {R("div","num md","0.6",cnt(0,13.75,2,D("w:treze vírgula|-0.8"),1.5,"","%"))}
 {R("p","s",D("w:treze vírgula|0.6"),"de juros ao ano. Juro alto <b>atrai dólar</b> pra dentro do país.")}
 {R("div","faixa",D("p31"),"O medo empurra o dólar. O <b>juro de cada país</b> segura ou piora a pancada.")}</div>''')

cena(32, lambda D: f'''<div class="col c">{R("div","k am","0.2","E O OURO?")}{R("h2","h","0.45","O porto seguro mais antigo que existe")}
 {R("div","num md ou",D("w:maior preço|-0.4"),cnt(4000,5594,0,D("w:cinco mil e quinhentos|-1.0"),1.6,"US$ ",""))}
 {R("p","s",D("w:cinco mil e quinhentos|0.5"),"a onça (cerca de 31 gramas): <b>recorde em janeiro de 2026</b>")}
 {R("div","src",D("w:cinco mil e quinhentos|1.0"),"Fonte: Correio Braziliense (20/8/2026)")}</div>''')

cena(34, lambda D: f'''<div class="col c">{R("div","k vm","0.2","SÓ QUE OLHA O QUE ACONTECEU DEPOIS")}{R("h2","h","0.45","Conflito com o Irã: o investidor <b>correu pro dólar</b>")}
 {R("div","num md vmn",D("w:13 por cento|-0.9"),cnt(0,-13,0,D("w:13 por cento|-0.7"),1.3,"","%"))}
 {R("p","s",D("w:13 por cento|0.4"),"foi quanto o ouro perdeu em pouco mais de um mês")}
 {R("div","faixa",D("p35"),"No pânico, o mundo precisa de <b>dinheiro na mão</b>. E a conta é em dólar.")}
 {R("div","src","1.0","Fonte: Trading Economics (2/4/2026)")}</div>''')

cena(37, lambda D: f'''<div class="col e">{R("div","k","0.2","E NO BRASIL?")}{R("h2","h lg","0.45","Por que aqui o dólar <b>sobe mais</b>")}
 {R("p","s",D("p38"),"Na hora do medo, o investidor pergunta: <b>esse país consegue pagar as contas?</b>")}
 <ul class="lista">{R("li","",D("w:dívida alta"),"Dívida alta")}{R("li","",D("w:conta do governo"),"Conta do governo no vermelho")}{R("li","",D("w:muita incerteza"),"Muita incerteza")}</ul>
 {R("div","faixa",D("p40"),"O mundo espirra. O real pega uma <b>gripe mais forte</b>.")}</div>''')

cena(41, lambda D: f'''<div class="col c">{R("h1","h lg","0.25","Você não ganha em dólar.<br>Você não compra dólar.")}{R("h1","h xl",D("p42"),"<b>Mas muda muita coisa.</b>")}</div>''')

cena(43, lambda D: f'''<div class="col c">{R("h2","h md","0.2","Como o dólar chega <b>no seu bolso</b>")}
 <div class="cards">
  {R("div","card",D("p43"),"<i>1</i><h3>🍞 Comida</h3><p>Trigo mais caro: pão, macarrão e biscoito sobem</p>")}
  {R("div","card",D("p44"),"<i>2</i><h3>⛽ Combustível</h3><p>Gasolina e diesel. O diesel move o caminhão que leva quase tudo</p>")}
  {R("div","card",D("p45"),"<i>3</i><h3>📱 Importados</h3><p>Eletrônico, remédio e peça de carro</p>")}
  {R("div","card",D("p46"),"<i>4</i><h3>💳 Juros</h3><p>Inflação sobe, juro fica alto: cartão, empréstimo e financiamento</p>")}
 </div>{R("div","faixa",D("p47"),"Você pode nunca ter visto uma nota de dólar. E ele entra na sua casa <b>todo mês</b>.")}</div>''')

cena(48, lambda D: f'''<div class="col c">{R("div","k","0.2","ENTÃO, O QUE DÁ PRA TIRAR DISSO?")}{R("h1","h xl",D("p49"),"Não é pra comprar<br>dólar <b>no susto</b>.")}
 {R("p","s",D("w:quem compra no pânico"),"Quem compra no pânico costuma comprar no preço mais alto.")}
 {R("div","src",D("w:não estou aqui"),"Conteúdo educativo. Não é recomendação de investimento.")}</div>''')

cena(51, lambda D: f'''<div class="col e">{R("div","k","0.15","TRÊS COISAS PRA GUARDAR")}
 <ol class="tres">{R("li","",D("p51"),"<i>1</i><span>O dólar sobe na crise porque <b>o mundo inteiro corre pra ele</b> ao mesmo tempo</span>")}
 {R("li","",D("p52"),"<i>2</i><span>A alta chega no seu bolso: <b>mercado, posto e juros</b></span>")}
 {R("li","",D("p53"),"<i>3</i><span><b>Crise passa.</b> Reserva de emergência evita vender na pior hora</span>")}</ol></div>''')

cena(54, lambda D: f'''<div class="col c">{R("div","k am","0.2","CALCULADORA GRÁTIS")}{R("h1","h lg","0.45","Quanto o dólar pesa na sua<br><b>compra no cartão</b>?")}
 {R("div","url",D("w:o link está"),"termometrodecrise.com/ferramentas")}{R("p","s",D("w:o link está|0.4"),"O link está na descrição")}</div>''')

cena(55, lambda D: f'''<div class="col c">{R("h1","h lg","0.25","Onde você sentiu a alta do dólar <b>primeiro</b>?")}
 <div class="chips g">{R("span","chip gr",D("w:no mercado"),"🛒 Mercado")}{R("span","chip gr",D("w:no posto"),"⛽ Posto")}{R("span","chip gr",D("w:no cartão"),"💳 Cartão")}</div>
 {R("p","s",D("w:no cartão|0.5"),"Conta aqui nos comentários")}</div>''')

LOGO = '''<svg viewBox="24 44 152 100"><g fill="none" stroke-width="18"><path d="M 38.06 117.3 A 62 62 0 0 1 48.3 85.78" stroke="#3B82C4"/><path d="M 51.48 81.4 A 62 62 0 0 1 78.29 61.93" stroke="#7CC3E0"/><path d="M 83.43 60.25 A 62 62 0 0 1 116.57 60.25" stroke="#F2C14E"/><path d="M 121.71 61.93 A 62 62 0 0 1 148.52 81.4" stroke="#EE8A3C"/><path d="M 151.7 85.78 A 62 62 0 0 1 161.94 117.3" stroke="#E5554A"/></g><line x1="100" y1="120" x2="120.44" y2="76.57" stroke="#EEF2F5" stroke-width="9" stroke-linecap="round"/><circle cx="100" cy="120" r="12" fill="#EEF2F5"/></svg>'''
cena(56, lambda D: f'''<div class="col c fim"><div class="lg2 r" data-d="0.2">{LOGO}</div>{R("h1","h lg","0.5","Termômetro de Crise")}
 {R("div","insc","0.9","INSCREVA-SE")}{R("p","s","1.2","Toda semana: o que acontece no mundo e o que muda no seu bolso")}
 {R("p","s pq",D("p57"),"Não recomendamos: só mostramos a temperatura do mundo.")}
 {R("div","bordao",D("p58"),"Sem alarde. Eu sou só o termômetro!")}</div>''')

# monta as cenas com tempos
cenas = []
for j, (p, f) in enumerate(CENAS):
    a = pt(p) - 0.25 if j else 0.0
    b = pt(CENAS[j + 1][0]) - 0.25 if j + 1 < len(CENAS) else TOTAL
    k_ini = prim[p]
    corpo = f(lambda spec, a=a, k=k_ini: deixa(spec, a, k))
    cenas.append({"a": round(a, 2), "b": round(b, 2), "h": corpo})

# capítulos (cartão durante a pausa)
caps = []
for n, ((pi, nome), c) in enumerate(zip(CAPS, cortes), 1):
    ini_pausa = T(c) - PAUSA
    caps.append({"a": round(ini_pausa, 2), "b": round(ini_pausa + PAUSA, 2), "n": n, "nome": nome})
# cena não muda durante o cartão: a cena anterior termina no começo da pausa
for cn in cenas:
    for cp in caps:
        if abs(cn["b"] - (cp["b"] - 0.25)) < 0.6: cn["b"] = cp["a"]
        if abs(cn["a"] - (cp["b"] - 0.25)) < 0.6: cn["a"] = round(cp["b"] - 0.05, 2)

dados = {"T": round(TOTAL, 2), "cenas": [{"a": c["a"], "b": c["b"]} for c in cenas], "caps": caps, "legs": legs}
tpl = (P / "modelo.html").read_text()
saida = tpl.replace("/*DADOS*/", json.dumps(dados, ensure_ascii=False)).replace("<!--MAPA-->", MAPA_DEFS).replace("<!--LOGO-->", LOGO)
saida = saida.replace("<!--CENAS-->", "\n".join(f'<section class="cena" id="c{j}">{c["h"]}</section>' for j, c in enumerate(cenas)))
(P / "video.html").write_text(saida)
(P / "tempos.json").write_text(json.dumps({"T": TOTAL, "cenas": [(c["a"], c["b"]) for c in cenas], "caps": caps, "paragrafos": [round(pt(i), 2) for i in range(59)]}, ensure_ascii=False, indent=1))
print(f"total {TOTAL:.1f}s = {int(TOTAL//60)}:{TOTAL%60:04.1f}; cenas {len(cenas)}; legendas {len(legs)}")
