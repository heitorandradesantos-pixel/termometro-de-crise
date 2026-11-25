#!/usr/bin/env python3
"""Monta o HTML animado do vídeo 3 (Selic) e o áudio final com pausas entre capítulos."""
import json, re, subprocess, unicodedata, html
from difflib import SequenceMatcher
from pathlib import Path

P = Path(__file__).resolve().parent
REPO = Path("/home/claude/termometro-de-crise")
LEAD, PAUSA, CAUDA = 0.8, 1.5, 8.0
CAPS = [(6, "O que é a Selic"), (13, "Onde ela está hoje"), (23, "O dinheiro guardado"), (38, "Quem ganha com a queda"),
        (46, "E a sua dívida?"), (59, "Bolsa, dólar e preços"), (64, "Já aconteceu: de 14,25% a 2%"), (73, "O que tirar disso")]

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))

# ---------- texto e alinhamento ----------
texto = (P.parent / "v3-tts1.txt").read_text().strip().split("\n\n")
t2 = (P.parent / "v3-tts2.txt").read_text().strip().split("\n\n")
# a divisão automática deixou "Ou seja..." no começo da parte 2; na geração ele foi para o fim da parte 1 (não muda a ordem)
paras = texto + t2
assert len(paras) == 83, len(paras)

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
legs, atual = [], []
for k, (i, w, _) in enumerate(pal):
    atual.append([round(T(ini[k]), 2), w])
    ultimo = k + 1 == len(pal) or pal[k + 1][0] != i
    if ultimo or w[-1] in ".?!" or (len(atual) >= 4 and w[-1] in ":,;") or len(atual) >= 8:
        legs.append([atual[0][0], atual]); atual = []
legs = [[a, ws, min(legs[j + 1][0] if j + 1 < len(legs) else a + 2.5, a + 4.2)] for j, (a, ws) in enumerate(legs)]

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

CSS_EXTRA = """
.cards.c5{grid-template-columns:repeat(5,1fr);gap:20px;width:1740px}.cards.c5 .card{padding:30px 24px 26px;min-height:350px}.cards.c5 h3{font-size:35px}.cards.c5 p{font-size:29px}.cards.c5 .card i{font-size:56px;top:12px;right:16px}
.cards.c2{grid-template-columns:1fr 1fr;width:1560px}.cards.c2 .card{min-height:270px;padding:36px 40px}.cards.c2 h3{font-size:50px}.cards.c2 p{font-size:38px}
.card.vd{border-color:#3FCF8E}.card.vd h3{color:#8FF0C0}.card.vm{border-color:#E5554A}.card.vm h3{color:#F0776C}
.cards .big{font-size:76px;font-weight:900;color:#F2C14E;line-height:1.05;margin:6px 0 10px}
.fluxo{display:flex;align-items:center;gap:26px;margin-top:14px}.fluxo .st{font-size:90px;font-weight:900;color:#F2C14E}
.barras.lg{width:1560px}.barras.lg .rot{width:520px;font-size:40px;font-weight:700;color:#EEF2F5}.barras.lg .val{width:250px;font-size:46px}
.lista.pq li{font-size:44px}.lista.pq{gap:16px}
.pais{fill:#F2C14E;stroke:#0E141B;stroke-width:.25}.tx{font-size:3.1px;font-weight:700;fill:#C9D3DE;text-anchor:middle}.tx.g{font-size:3.6px;fill:#fff;font-weight:900}.tx.am{fill:#F2C14E;font-weight:900;font-size:3.4px}
.zoom .terra{stroke-width:.2}.zoom .arc{stroke-width:.7}.anel{fill:none;stroke:#E5554A;stroke-width:.5}
.an.p{font-size:29px}.pm.amf{fill:#F2C14E}.lgraf.tr{stroke:#6C8098;filter:none;stroke-width:6}
"""


CSS_EXTRA += """
.cards.c3{grid-template-columns:repeat(3,1fr);width:1620px}.cards.c3 .card{min-height:300px}.cards.c3 h3{font-size:46px}.cards.c3 p{font-size:34px}
.cards.c4 .card{min-height:300px}.cards.c4 h3{font-size:36px}.cards.c4 p{font-size:31px}
"""

def grafico(pts, x0, x1, y0, y1, ticks, rot_x, W=1500, H=520):
    ml, mr, mt, mb = 130, 70, 30, 70
    x = lambda v: ml + (v - x0) * (W - ml - mr) / (x1 - x0)
    y = lambda v: mt + (y1 - v) * (H - mt - mb) / (y1 - y0)
    grade = "".join(f'<line x1="{ml}" x2="{W-mr}" y1="{y(v):.0f}" y2="{y(v):.0f}" class="gr"/><text x="{ml-14}" y="{y(v)+8:.0f}" class="ey" text-anchor="end">{str(v).replace(".", ",")}%</text>' for v in ticks)
    eixo = "".join(f'<text x="{x(v):.0f}" y="{H-22}" class="ex" text-anchor="middle">{t}</text>' for v, t in rot_x)
    P = [(x(a), y(b)) for a, b in pts]
    comp = [((P[i+1][0]-P[i][0])**2 + (P[i+1][1]-P[i][1])**2) ** .5 for i in range(len(P)-1)]
    tot = sum(comp); fr = [sum(comp[:i+1]) / tot for i in range(len(comp))]
    d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in P)
    return W, H, x, y, grade, eixo, P, d, fr

# Selic meta: 15% de jun/2025 a mar/2026; cinco cortes de 0,25 (mar, abr, jun, ago, set de 2026); 13,75% mantida em nov
S26 = [(0, 15), (9.6, 15), (9.6, 14.75), (11, 14.75), (11, 14.5), (12.55, 14.5), (12.55, 14.25), (14.15, 14.25), (14.15, 14), (15.5, 14), (15.5, 13.75), (17.3, 13.75)]
def c_hoje(D):
    W, H, x, y, grade, eixo, P, d, fr = grafico(S26, 0, 18, 13, 15.5, (13.5, 14, 14.5, 15), [(0.5, "jun/25"), (3.5, "set"), (6.5, "dez"), (9.5, "mar/26"), (12.5, "jun"), (15.5, "set"), (17.5, "nov")])
    return f'''<div class="col c">{R("h2","h md","0.2","A Selic em <b>2025 e 2026</b>")}
 <svg class="graf" style="width:{W*0.8:.0f}px;height:{H*0.8:.0f}px;flex:none" viewBox="0 0 {W} {H}">{grade}{eixo}
  <path class="lgraf" d="{d}" data-draw="0.5:{fr[0]:.3f},{D("p15")}:{fr[-2]:.3f},{D("w:o banco central parou")}:1" data-dur="1.6"/>
  <g class="r" data-d="{D("w:dez meses")}"><text x="{x(4.6):.0f}" y="{y(15)-22:.0f}" class="an" text-anchor="middle">15% por dez meses</text></g>
  <g class="r" data-d="{D("w:cinco cortes")}"><text x="{x(13.4):.0f}" y="{y(14.6):.0f}" class="an">5 cortes</text></g>
  <g class="r" data-d="{D("w:treze vírgula setenta")}"><circle cx="{P[-1][0]:.0f}" cy="{P[-1][1]:.0f}" r="12" class="pm amf"/><text x="{P[-1][0]:.0f}" y="{P[-1][1]+52:.0f}" class="an" text-anchor="end">13,75%: parou em novembro</text></g>
 </svg>
 <div class="chips">{R("span","chip",D("p17"),"Inflação esperada <b>acima da meta</b>")}{R("span","chip",D("w:o dólar subiu"),"💵 Dólar subiu")}{R("span","chip am",D("p18"),"Próxima decisão: <b>9 de dezembro</b>")}</div>
 {R("div","src","1.0","Fonte: Banco Central (Copom). 15% de junho de 2025 a março de 2026.")}</div>'''

S16 = [(2016.8, 14.25), (2018.2, 6.5), (2019.55, 6.5), (2020.6, 2), (2021.2, 2), (2022.6, 13.75)]
def c_hist(D):
    W, H, x, y, grade, eixo, P, d, fr = grafico(S16, 2016.3, 2023, 0, 16, (2, 6, 10, 14), [(v, str(v)) for v in range(2017, 2023)])
    return f'''<div class="col c">{R("h2","h md","0.2","Selic: de <b>14,25%</b> a <b>2%</b>, e de volta")}
 <svg class="graf" style="width:{W*0.8:.0f}px;height:{H*0.8:.0f}px;flex:none" viewBox="0 0 {W} {H}">{grade}{eixo}
  <path class="lgraf" d="{d}" data-draw="{D("p66")}:{fr[2]:.3f},{D("p69")}:1" data-dur="2.2"/>
  <g class="r" data-d="{D("w:catorze vírgula")}"><circle cx="{P[0][0]:.0f}" cy="{P[0][1]:.0f}" r="12" class="pm az"/><text x="{P[0][0]+22:.0f}" y="{P[0][1]+10:.0f}" class="an">2016: 14,25%</text></g>
  <g class="r" data-d="{D("w:dois por cento")}"><circle cx="{P[3][0]:.0f}" cy="{P[3][1]:.0f}" r="12" class="pm amf"/><text x="{P[3][0]-30:.0f}" y="{P[3][1]+46:.0f}" class="an" text-anchor="end">agosto de 2020: 2%</text></g>
  <g class="r" data-d="{D("w:voltou pra treze")}"><circle cx="{P[5][0]:.0f}" cy="{P[5][1]:.0f}" r="12" class="pm vmf"/><text x="{P[5][0]-22:.0f}" y="{P[5][1]+8:.0f}" class="an" text-anchor="end">2022: 13,75%</text></g>
 </svg>
 <div class="chips">{R("span","chip",D("p67"),"Renda fixa rendia quase nada")}{R("span","chip",D("w:correu pra bolsa"),"📈 Corrida pra bolsa")}{R("span","chip vm",D("p68"),"Inflação de 2021: <b>10,06%</b>")}</div>
 {R("div","src","1.0","Fonte: Banco Central (meta da Selic) e IBGE (IPCA de 2021)")}</div>'''

CENAS = []
def cena(p, corpo):
    CENAS.append([p, corpo])

cena(0, lambda D: f'''<div class="col c">{R("div","k vm","0.15","QUANDO A SELIC CAI")}
 <div class="cards c2">
  {R("div","card vm","0.3","<h3>💰 Seu dinheiro guardado</h3><p>Vai render <b>menos</b>.</p>")}
  {R("div","card vm",D("w:e a sua dívida"),"<h3>💳 Sua dívida</h3><p>Pode continuar <b>tão cara quanto hoje</b>.</p>")}
 </div>{R("div","faixa",D("p1"),"Parece injusto? É o que costuma acontecer quando a <b>Selic cai</b>.")}</div>''')

cena(2, lambda D: f'''<div class="col c">{R("h2","h lg","0.25","Quem <b>ganha</b> e quem <b>perde</b><br>com o juro caindo")}
 {R("p","s",D("p3"),"O caminho inteiro: do <b>Banco Central</b> até o seu bolso")}
 <div class="chips g">{R("span","chip gr",D("w:no seu cdb"),"CDB")}{R("span","chip gr",D("w:na poupança"),"Poupança")}{R("span","chip gr",D("w:no tesouro"),"Tesouro")}{R("span","chip gr",D("w:no financiamento"),"Financiamento")}{R("span","chip gr",D("w:no cartão"),"Cartão")}{R("span","chip gr",D("w:no dólar"),"Dólar")}</div>
 {R("span","chip am",D("p5"),"Fica até o final: a parte da dívida")}</div>''')

cena(6, lambda D: f'''<div class="col c">{R("div","k","0.2","PRIMEIRO, O BÁSICO")}{R("h1","h xl","0.4","O que é a <b>Selic</b>?")}
 {R("p","s lgs",D("p7"),"A <b>taxa básica de juros</b> do Brasil: a referência pra todas as outras")}
 {R("span","chip",D("p8"),"Quem decide: <b>Banco Central</b>, a cada 45 dias")}</div>''')

cena(9, lambda D: f'''<div class="col c">{R("h2","h lg","0.25","A Selic é o <b>preço do dinheiro</b>")}
 <div class="cards c2">
  {R("div","card vm",D("w:selic alta"),"<h3>📈 Selic alta</h3><p>Dinheiro caro</p>")}
  {R("div","card vd",D("w:selic baixa"),"<h3>📉 Selic baixa</h3><p>Dinheiro barato</p>")}
 </div></div>''')

cena(10, lambda D: f'''<div class="col e">{R("div","k","0.2","POR QUE O BANCO CENTRAL MEXE NELA?")}{R("h2","h lg",D("w:pra segurar"),"Pra segurar a <b>inflação</b>")}
 <ul class="lista pq">{R("li","",D("w:o povo compra"),"Juro alto: o povo compra menos a prazo")}{R("li","",D("w:as empresas investem"),"As empresas investem menos")}{R("li","",D("w:os preços param"),"Os preços param de subir tanto")}</ul>
 {R("div","faixa",D("p12"),"Juro baixo: a economia esquenta, e os preços <b>podem esquentar junto</b>.")}</div>''')

cena(13, c_hoje)

cena(19, lambda D: f'''<div class="col c">{R("div","k","0.2","O QUE OS ECONOMISTAS ESPERAM")}
 <div class="dea r" data-d="0.5"><span class="de">13,75%</span><span class="seta">→</span><span class="ate">{cnt(13.75,12.75,2,D("w:doze vírgula|-0.6"),1.4,"","%")}</span></div>
 {R("p","s lgs",D("w:no fim do ano"),"no fim de <b>2027</b>")}
 <div class="chips">{R("span","chip am",D("w:só que aposta"),"Aposta não é garantia")}{R("span","chip",D("p21"),"Há poucas semanas, a aposta era outra")}</div>
 {R("div","faixa",D("p22"),"Vale mais <b>entender o mecanismo</b> do que decorar o número.")}
 {R("div","src","1.0","Fonte: Banco Central, boletim Focus de 16/11/2026 (mediana das projeções)")}</div>''')

cena(23, lambda D: f'''<div class="col c">{R("h1","h xl","0.25","Se a Selic cair,<br>o que muda <b>pra você</b>?")}
 {R("div","k",D("p24"),"COMEÇA PELO DINHEIRO GUARDADO")}
 <div class="chips">{R("span","chip",D("p25"),"Tesouro Selic")}{R("span","chip",D("w:cdb que paga"),"CDB a 100% do CDI")}{R("span","chip",D("w:conta que rende"),"Conta que rende todo dia")}</div>
 {R("div","faixa",D("p26"),"Se ela cai, o rendimento cai junto. <b>No mesmo dia.</b>")}</div>''')

cena(27, lambda D: f'''<div class="col c">{R("h2","h md","0.2","<b>R$ 10 mil</b> a 100% do CDI, em um ano")}
 <div class="barras lg">
  <div class="lin r" data-d="{D("w:uns mil trezentos|-0.6")}"><span class="rot">Selic de hoje (13,75%)</span><div class="tr"><div class="bar" data-w="100" data-d="{D("w:uns mil trezentos|-0.4")}" data-dur="1.2"></div></div><span class="val am">R$ 1.365</span></div>
  <div class="lin r" data-d="{D("p28")}"><span class="rot">Se a Selic fosse 10%</span><div class="tr"><div class="bar cz" data-w="73" data-d="{D("w:menos de mil|-0.6")}" data-dur="1.2"></div></div><span class="val">R$ 990</span></div>
 </div>
 {R("div","faixa",D("p29"),"Regra de bolso: cada <b>1 ponto</b> a menos = uns <b>R$ 100</b> a menos por ano.")}
 {R("span","chip",D("p30|1.2"),"Com R$ 100 mil: uns R$ 1.000 a menos por ano, por ponto")}
 {R("div","src","1.0","Simulação própria, antes do imposto, com CDI 0,10 ponto abaixo da Selic. Não é promessa de rendimento.")}</div>''')

cena(31, lambda D: f'''<div class="col e">{R("div","k","0.2","E NÃO É SÓ O CDB")}
 <ul class="lista">{R("li","",D("w:fundo de renda"),"Fundo de renda fixa")}{R("li","",D("w:previdência"),"Previdência conservadora")}{R("li","",D("w:a caixinha"),"A caixinha do aplicativo do banco")}</ul>
 {R("div","faixa",D("w:quase tudo"),"Quase tudo que rende um pouquinho todo dia <b>segue a mesma lógica</b>.")}</div>''')

cena(32, lambda D: f'''<div class="col c">{R("div","k am","0.2","A PEGADINHA DA POUPANÇA")}
 {R("h1","h xl",D("p33"),"<b>0,5% ao mês</b> + TR")}
 {R("p","s",D("w:e isso não muda"),"Não muda enquanto a Selic estiver <b>acima de 8,5%</b>")}
 <div class="chips">{R("span","chip",D("p34"),"Selic de 13 pra 10: poupança <b>igual</b>")}{R("span","chip vm",D("p35"),"Selic em 8,5% ou menos: aí rende menos")}</div>
 {R("div","src","1.0","Fonte: Banco Central. Com Selic até 8,5%, a poupança rende 70% da Selic + TR.")}</div>''')

cena(36, lambda D: f'''<div class="col c">{R("div","k","0.2","NA PRÁTICA")}{R("h2","h lg","0.4","Hoje a poupança <b>perde feio</b><br>pra 100% do CDI")}
 {R("div","faixa",D("p37"),"Com a Selic mais baixa, a diferença <b>encolhe</b>. Não some, mas encolhe.")}</div>''')

cena(38, lambda D: f'''<div class="col c">{R("div","k vd","0.2","O OUTRO LADO")}{R("h1","h xl","0.4","Tem gente que <b>ganha</b><br>quando a Selic cai")}
 {R("p","s",D("p39"),"Quem <b>travou uma taxa</b> lá atrás")}
 <div class="chips">{R("span","chip",D("w:o tesouro prefixado"),"Tesouro Prefixado")}{R("span","chip",D("w:inflação mais"),"Tesouro que paga inflação + juro fixo")}</div></div>''')

cena(40, lambda D: f'''<div class="col c">{R("div","k","0.2","FUNCIONA ASSIM")}
 <div class="cards c2">
  {R("div","card vd",D("w:você comprou"),"<h3>Seu título</h3><div class=big>15% ao ano</div><p>Taxa travada na compra</p>")}
  {R("div","card",D("w:os títulos novos"),"<h3>Títulos novos</h3><div class=big>12% ao ano</div><p>Depois que os juros caem</p>")}
 </div>{R("div","faixa",D("p41"),"O seu, que paga 15, fica <b>mais valioso</b>. Exemplo, não é taxa de hoje.")}</div>''')

cena(42, lambda D: f'''<div class="col c">{R("div","k","0.2","ACONTECEU NESTA SEMANA · TESOURO PREFIXADO 2029")}
 <div class="dea r" data-d="{D("w:caiu de quinze|-0.2")}"><span class="de">15,33%</span><span class="seta">→</span><span class="ate">{cnt(15.33,14.87,2,D("w:catorze vírgula|-0.6"),1.3,"","%")}</span></div>
 {R("span","chip am",D("p43"),"R$ 10 mil num título longo: <b>+R$ 112</b> em um dia")}
 {R("div","src","1.0","Fonte: Money Times (19/11 e 24/11/2026) e InvestNews (24/11/2026). Antes do imposto.")}</div>''')

cena(44, lambda D: f'''<div class="col e">{R("div","k vm","0.2","MAS ATENÇÃO")}
 <ul class="lista">{R("li","",D("w:esse ganho"),"O ganho só vira dinheiro se <b>vender antes do prazo</b>")}{R("li","",D("w:e se os juros sobem"),"Se os juros sobem, o título <b>perde valor</b> no caminho")}</ul>
 {R("div","faixa",D("p45"),"Quem segura até o vencimento recebe <b>a taxa que combinou</b>.")}</div>''')

cena(46, lambda D: f'''<div class="col c">{R("div","k vm","0.2","A PARTE QUE QUASE NINGUÉM TE CONTA")}{R("h1","h xxl",D("w:a sua dívida"),"A sua <b>dívida</b>")}
 {R("p","s lgs",D("p47"),"Selic caindo <b>não</b> deixa toda dívida mais barata. Depende de qual.")}</div>''')

cena(48, lambda D: f'''<div class="col c">{R("h2","h md","0.2","Cada dívida <b>reage de um jeito</b>")}
 <div class="cards c4">
  {R("div","card vd",D("p48"),"<h3>🚗 Financiamento novo</h3><p>Tende a baratear, devagar</p>")}
  {R("div","card",D("p49"),"<h3>📄 Parcela fixa antiga</h3><p>Não muda nada</p>")}
  {R("div","card",D("p50"),"<h3>🏠 Contrato com índice</h3><p>Muda pelo índice, não pela Selic direto</p>")}
  {R("div","card vd",D("p51"),"<h3>💼 Consignado</h3><p>Costuma acompanhar melhor</p>")}
 </div></div>''')

cena(52, lambda D: f'''<div class="col c">{R("div","k vm","0.2","E O CARTÃO DE CRÉDITO? ESSE É O PIOR")}
 {R("div","num vmn",D("p53"),cnt(0,400,0,D("w:quatrocentos por cento|-1.0"),1.4,"+","%"))}
 {R("p","s lgs",D("w:quatrocentos por cento|0.4"),"ao ano no rotativo do cartão")}
 {R("div","faixa",D("p54"),"Selic 1 ponto menor? <b>420% ou 419%</b> dá no mesmo.")}
 {R("div","src","1.0","Fonte: Banco Central (taxa média do rotativo: 428,3% ao ano em março de 2026)")}</div>''')

cena(55, lambda D: f'''<div class="col c">
 <div class="cards c2">
  {R("div","card vm",D("w:o seu investimento"),"<h3>💰 Seu investimento</h3><p>Sente a queda <b>no mesmo dia</b></p>")}
  {R("div","card vm",D("w:a sua dívida cara"),"<h3>💳 Sua dívida cara</h3><p><b>Quase não sente</b></p>")}
 </div>
 {R("div","k",D("p56"),"NO JURO DA DÍVIDA NÃO ENTRA SÓ A SELIC")}
 <div class="chips">{R("span","chip",D("w:o risco de calote"),"Risco de calote")}{R("span","chip",D("w:o imposto"),"Imposto")}{R("span","chip",D("w:o custo"),"Custo")}{R("span","chip",D("w:o lucro"),"Lucro de quem empresta")}</div>
 {R("div","faixa",D("p57"),"Risco alto: a Selic vira um <b>pedacinho pequeno</b> da conta.")}</div>''')

cena(59, lambda D: f'''<div class="col c">{R("h2","h md","0.2","Mais <b>3 coisas</b> que a Selic mexe")}
 <div class="cards c3">
  {R("div","card",D("p60"),"<i>1</i><h3>📈 Bolsa</h3><p>Juro caindo costuma ajudar. Não é regra nem garantia</p>")}
  {R("div","card",D("p61"),"<i>2</i><h3>💵 Dólar</h3><p>Parte do dinheiro de fora pode ir embora, e o dólar pode subir</p>")}
  {R("div","card",D("p62"),"<i>3</i><h3>🛒 Preços</h3><p>Juro baixo demais, na hora errada, vira inflação</p>")}
 </div>{R("div","faixa",D("p63"),"Efeito bom que demora: crédito barato, <b>empresa investe e contrata</b>.")}</div>''')

cena(64, c_hist)

cena(70, lambda D: f'''<div class="col e">{R("div","k","0.2","QUEM LEVOU O SUSTO")}
 <ul class="lista">{R("li","","0.4","Quem pegou dívida achando que o juro ia <b>ficar baixo pra sempre</b>")}{R("li","",D("p71"),"Quem travou taxa baixa e viu o título <b>perder valor</b> na alta")}</ul>
 {R("div","faixa",D("p72"),"O que dá lucro na queda dá prejuízo na alta. <b>É uma gangorra.</b>")}</div>''')

cena(73, lambda D: f'''<div class="col c">{R("h1","h xl","0.25","O que dá pra<br><b>tirar disso tudo</b>?")}
 {R("p","s lgs",D("w:guarda três"),"Guarda três coisas.")}
 {R("div","src",D("p74"),"Conteúdo educativo. Não é recomendação de investimento.")}</div>''')

cena(75, lambda D: f'''<div class="col e">{R("div","k","0.15","TRÊS COISAS PRA GUARDAR")}
 <ol class="tres">{R("li","",D("p75"),"<i>1</i><span>Selic caindo: ruim pra quem só guarda no <b>pós-fixado</b>, bom pra quem <b>travou taxa</b> antes</span>")}
 {R("li","",D("p76"),"<i>2</i><span>A <b>dívida cara</b> não espera a Selic: cartão e cheque especial seguem caros</span>")}
 {R("li","",D("p77"),"<i>3</i><span><b>Juro é ciclo.</b> Ele sobe e desce</span>")}</ol></div>''')

cena(78, lambda D: f'''<div class="col c">{R("div","k am","0.2","CALCULADORA GRÁTIS")}{R("h1","h lg","0.45","Faça a <b>sua conta</b><br>com a Selic")}
 {R("div","url",D("w:o link está"),"termometrodecrise.com/ferramentas")}{R("p","s",D("w:o link está|0.4"),"O link está na descrição")}</div>''')

cena(79, lambda D: f'''<div class="col c">{R("h1","h lg","0.25","Você torce pra Selic...")}
 <div class="chips g">{R("span","chip gr",D("w:pra selic cair"),"📉 Cair")}{R("span","chip gr",D("w:ficar alta"),"📈 Ficar alta")}</div>
 {R("p","s",D("w:ficar alta|0.6"),"Conta aqui nos comentários")}</div>''')

LOGO = '''<svg viewBox="24 44 152 100"><g fill="none" stroke-width="18"><path d="M 38.06 117.3 A 62 62 0 0 1 48.3 85.78" stroke="#3B82C4"/><path d="M 51.48 81.4 A 62 62 0 0 1 78.29 61.93" stroke="#7CC3E0"/><path d="M 83.43 60.25 A 62 62 0 0 1 116.57 60.25" stroke="#F2C14E"/><path d="M 121.71 61.93 A 62 62 0 0 1 148.52 81.4" stroke="#EE8A3C"/><path d="M 151.7 85.78 A 62 62 0 0 1 161.94 117.3" stroke="#E5554A"/></g><line x1="100" y1="120" x2="120.44" y2="76.57" stroke="#EEF2F5" stroke-width="9" stroke-linecap="round"/><circle cx="100" cy="120" r="12" fill="#EEF2F5"/></svg>'''

cena(80, lambda D: f"""<div class="col c fim"><div class="lg2 r" data-d="0.2">{LOGO}</div>{R("h1","h lg","0.5","Termômetro de Crise")}
 {R("div","insc","0.9","INSCREVA-SE")}{R("p","s",D("w:segunda quarta"),"<b>Segunda, quarta e sexta</b>: o que acontece no mundo e o que muda no seu bolso")}
 {R("p","s pq",D("p81"),"Não recomendamos: só mostramos a temperatura do mundo.")}
 {R("div","bordao",D("p82"),"Sem alarde. Eu sou só o termômetro!")}</div>""")

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

CTA = [(caps[2]["b"] + 3.0, "Tá entendendo? Então", "INSCREVA-SE", "v"), (caps[4]["b"] + 3.0, "Curtiu até aqui?", "👍 DEIXA O LIKE", "a"),
       (caps[6]["b"] + 3.0, "Não perde o próximo:", "🔔 INSCREVA-SE", "v")]
dados = {"cta": [{"a": round(t, 2), "b": round(t + 5.2, 2), "tx": tx, "bt": bt, "cor": cor} for t, tx, bt, cor in CTA], "T": round(TOTAL, 2), "cenas": [{"a": c["a"], "b": c["b"]} for c in cenas], "caps": caps, "legs": legs}
tpl = (P / "modelo.html").read_text().replace("</style>", CSS_EXTRA + "</style>", 1)
saida = tpl.replace("/*DADOS*/", json.dumps(dados, ensure_ascii=False)).replace("<!--MAPA-->", MAPA_DEFS).replace("<!--LOGO-->", LOGO)
saida = saida.replace("<!--CENAS-->", "\n".join(f'<section class="cena" id="c{j}">{c["h"]}</section>' for j, c in enumerate(cenas)))
(P / "video.html").write_text(saida)
(P / "tempos.json").write_text(json.dumps({"cta": [round(t, 2) for t, *_ in CTA], "T": TOTAL, "cenas": [(c["a"], c["b"]) for c in cenas], "caps": caps, "paragrafos": [round(pt(i), 2) for i in range(83)]}, ensure_ascii=False, indent=1))
print(f"total {TOTAL:.1f}s = {int(TOTAL//60)}:{TOTAL%60:04.1f}; cenas {len(cenas)}; legendas {len(legs)}")


