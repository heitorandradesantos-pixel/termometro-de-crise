#!/usr/bin/env python3
"""Monta o HTML animado do vídeo 2 (petróleo) e o áudio final com pausas entre capítulos."""
import json, re, subprocess, unicodedata, html
from difflib import SequenceMatcher
from pathlib import Path

P = Path(__file__).resolve().parent
REPO = Path("/home/claude/termometro-de-crise")
LEAD, PAUSA, CAUDA = 0.8, 1.5, 8.0
CAPS = [(6, "O funil do mundo"), (14, "Já aconteceu antes"), (23, "2026: o estreito fechou"),
        (33, "Mas o Brasil não produz petróleo?"), (45, "Do barril à bomba"), (51, "O efeito dominó"), (61, "O que tirar disso")]

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))

# ---------- texto e alinhamento ----------
texto = (P.parent / "v2-tts1.txt").read_text().strip().split("\n\n")
t2 = (P.parent / "v2-tts2.txt").read_text().strip().split("\n\n")
# a divisão automática deixou "Ou seja..." no começo da parte 2; na geração ele foi para o fim da parte 1 (não muda a ordem)
paras = texto + t2
assert len(paras) == 71, len(paras)

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

def caixa(d):
    xs, ys, x, y = [], [], 0.0, 0.0
    for cmd, args in re.findall(r"([MmLlHhVvZz])([^MmLlHhVvZz]*)", d):
        nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", args)]
        if cmd in "MmLl":
            for j in range(0, len(nums) - 1, 2):
                if cmd.islower() and not (cmd == "m" and not xs): x, y = x + nums[j], y + nums[j + 1]
                else: x, y = nums[j], nums[j + 1]
                xs.append(x); ys.append(y)
        elif cmd in "Hh":
            for v in nums: x = x + v if cmd == "h" else v; xs.append(x); ys.append(y)
        elif cmd in "Vv":
            for v in nums: y = y + v if cmd == "v" else v; xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)
PD = {c["a2"]: c["d"] for c in mapa["paises"]}
_ae = caixa(PD["AE"])
ORMUZ = (_ae[2] + 0.6, _ae[1] - 0.9)
def zoom(extra, paises=()):
    """Mapa aproximado no Golfo. paises: [(a2, deixa)] pintados de amarelo."""
    hx, hy = ORMUZ; w = 138; h = w * 579 / 1240
    vb = f"{hx - w * 0.66:.1f} {hy - h * 0.56:.1f} {w} {h:.1f}"
    pint = "".join(f'<path class="eua pais" d="{PD[a]}" data-d="{d}"/>' for a, d in paises)
    return f'<svg class="mapa zoom" viewBox="{vb}"><use href="#mapa" class="terra"/>{pint}{extra}</svg>'
def rot(a2, nome, dx=0, dy=0, cls="tx", d="0.4"):
    x, y = C[a2]
    return f'<text class="{cls} r" x="{x + dx:.1f}" y="{y + dy:.1f}" data-d="{d}">{nome}</text>'
def ormuz(d, nome=True):
    hx, hy = ORMUZ
    t = f'<text class="tx am r" x="{hx + 3:.1f}" y="{hy - 4.2:.1f}" data-d="{d}" style="text-anchor:start">Estreito de Ormuz</text><text class="tx r" x="{hx + 3:.1f}" y="{hy - 0.6:.1f}" data-d="{d}" style="text-anchor:start;font-size:2.6px">33 km de largura</text>' if nome else ""
    return f'<circle class="pt" cx="{hx:.1f}" cy="{hy:.1f}" r="1.5" fill="#E5554A" data-d="{d}"/><circle class="pt anel" cx="{hx:.1f}" cy="{hy:.1f}" r="3.2" data-d="{d}"/>{t}'
def rota(d, cor=AMAR, dur=2.2):
    hx, hy = ORMUZ; kx, ky = C["KW"]
    return f'<path class="arc" d="M{kx + 2:.1f},{ky + 2.5:.1f} Q{(kx + hx) / 2 - 1:.1f},{hy + 1.5:.1f} {hx - 2.5:.1f},{hy + 0.8:.1f} T{hx + 4:.1f},{hy + 2.5:.1f} T{hx + 22:.1f},{hy + 16:.1f}" stroke="{cor}" data-draw="{d}:1" data-dur="{dur}"/>'
ROTS = lambda d: f'<text class="tx g r" x="{ORMUZ[0] - 9:.1f}" y="{ORMUZ[1] - 13:.1f}" data-d="{d}">IRÃ</text>' + rot("SA", "ARÁBIA SAUDITA", 0, 0, "tx", d) + rot("IQ", "IRAQUE", 0, 0, "tx", d)

# barril em 2026: só os momentos citados na narração
PT26 = [(0.93, 72.5), (2.0, 118.35), (5.0, 71.57), (7.3, 101), (9.75, 89.37)]
MES26 = ["fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov"]
def graf26():
    W, H, ml, mr, mt, mb = 1560, 560, 130, 70, 30, 70
    x = lambda m: ml + m * (W - ml - mr) / 10
    y = lambda v: mt + (130 - v) * (H - mt - mb) / (130 - 60)
    grade = "".join(f'<line x1="{ml}" x2="{W-mr}" y1="{y(v):.0f}" y2="{y(v):.0f}" class="gr"/><text x="{ml-14}" y="{y(v)+8:.0f}" class="ey" text-anchor="end">US$ {v}</text>' for v in (70, 90, 110, 130))
    meses = "".join(f'<text x="{x(i+0.5):.0f}" y="{H-22}" class="ex" text-anchor="middle">{m}</text>' for i, m in enumerate(MES26))
    P = [(x(a), y(b)) for a, b in PT26]
    seg = lambda pts: "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    comp = [((P[i+1][0]-P[i][0])**2 + (P[i+1][1]-P[i][1])**2) ** .5 for i in range(len(P)-1)]
    return W, H, x, y, grade, meses, P, seg, comp

def c26a(D):
    W, H, x, y, grade, meses, P, seg, comp = graf26()
    return f'''<div class="col c">{R("h2","h md","0.2","Preço do barril de petróleo em 2026")}
 <svg class="graf" style="width:{W*0.84:.0f}px;height:{H*0.84:.0f}px;flex:none" viewBox="0 0 {W} {H}">{grade}{meses}
  <path class="lgraf" d="{seg(P[:2])}" data-draw="{D("w:cento e dezoito|-1.6")}:1" data-dur="1.7"/>
  <g class="r" data-d="{D("w:casa dos setenta|-0.3")}"><circle cx="{P[0][0]:.0f}" cy="{P[0][1]:.0f}" r="11" class="pm az"/><text x="{P[0][0]+34:.0f}" y="{P[0][1]+16:.0f}" class="an p">fim de fevereiro: casa dos US$ 70</text></g>
  <g class="r" data-d="{D("p25")}"><line x1="{x(1.13):.0f}" x2="{x(1.13):.0f}" y1="34" y2="{y(81):.0f}" class="vl"/><text x="{x(1.13)+16:.0f}" y="{y(126):.0f}" class="an vm">início de março: Ormuz fechado</text></g>
  <g class="r" data-d="{D("w:cento e dezoito")}"><circle cx="{P[1][0]:.0f}" cy="{P[1][1]:.0f}" r="12" class="pm vmf"/><text x="{P[1][0]+24:.0f}" y="{P[1][1]+10:.0f}" class="an">31 de março: US$ 118</text></g>
  <g class="r" data-d="{D("w:60 por cento|-0.4")}"><rect x="{W-470}" y="{H-250}" width="400" height="96" rx="16" class="cx"/><text x="{W-270}" y="{H-186}" class="gd" text-anchor="middle">+63% em março</text></g>
 </svg>
 {R("span","chip",D("p26|0.3"),"Catar avisa os clientes: <b>não tem como entregar o gás</b>")}
 {R("div","src","1.0","Fonte: InfoMoney e CNN Brasil (fechamento de 31/3/2026: US$ 118,35, contrato de maio)")}</div>'''

def c26b(D):
    W, H, x, y, grade, meses, P, seg, comp = graf26()
    tot = sum(comp[1:]); f = [sum(comp[1:i+1]) / tot for i in range(1, 4)]
    return f'''<div class="col c">{R("h2","h md","0.2","O outro lado: <b>ele também desce</b>")}
 <svg class="graf" style="width:{W}px;height:{H}px;flex:none" viewBox="0 0 {W} {H}">{grade}{meses}
  <path class="lgraf tr" d="{seg(P[:2])}"/>
  <path class="lgraf" d="{seg(P[1:])}" data-draw="{D("w:setenta e um|-1.3")}:{f[0]:.3f},{D("w:passou de cem|-1.2")}:{f[1]:.3f},{D("w:abaixo de noventa|-1.2")}:1" data-dur="1.4"/>
  <circle cx="{P[1][0]:.0f}" cy="{P[1][1]:.0f}" r="12" class="pm vmf"/><text x="{P[1][0]+24:.0f}" y="{P[1][1]+10:.0f}" class="an">US$ 118</text>
  <g class="r" data-d="{D("w:setenta e um")}"><circle cx="{P[2][0]:.0f}" cy="{P[2][1]:.0f}" r="12" class="pm az"/><text x="{P[2][0]:.0f}" y="{P[2][1]+50:.0f}" class="an" text-anchor="middle">1º de julho: US$ 71</text></g>
  <g class="r" data-d="{D("w:passou de cem")}"><circle cx="{P[3][0]:.0f}" cy="{P[3][1]:.0f}" r="12" class="pm vmf"/><text x="{P[3][0]:.0f}" y="{P[3][1]-28:.0f}" class="an" text-anchor="middle">setembro: acima de US$ 100</text></g>
  <g class="r" data-d="{D("w:abaixo de noventa")}"><circle cx="{P[4][0]:.0f}" cy="{P[4][1]:.0f}" r="12" class="pm amf"/><text x="{P[4][0]+8:.0f}" y="{P[4][1]+52:.0f}" class="an" text-anchor="end">23/11: abaixo de US$ 90</text></g>
 </svg>
 {R("div","src","1.0","Fonte: fechamentos do Brent (Jornal de Brasília, ADVFN, Money Times). A linha liga só os momentos citados; entre eles o preço oscilou.")}</div>'''

CENAS = []
def cena(p, corpo):
    CENAS.append([p, corpo])

cena(0, lambda D: f'''<div class="col c">{R("div","k vm","0.15","FICOU TUDO MAIS CARO")}
 <div class="chips g">{R("span","chip gr","0.25","⛽ Gasolina")}{R("span","chip gr",D("w:a comida"),"🛒 Comida")}{R("span","chip gr",D("w:o frete"),"🚚 Frete")}</div>
 <div class="chips g">{R("span","chip gr",D("w:a passagem"),"🚌 Passagem")}{R("span","chip gr",D("w:a parcela"),"🏠 Parcela do financiamento")}</div></div>''')

cena(1, lambda D: f'''<div class="col c">{R("div","k","0.2","POR TRÁS DE TUDO ISSO: UM PEDAÇO DE MAR")}
 {R("div","num",D("w:33 quilômetros|-1.2"),cnt(0,33,0,D("w:33 quilômetros|-1.0"),1.3,""," km"))}
 {R("p","s lgs",D("w:33 quilômetros|0.4"),"de largura, lá no <b>Oriente Médio</b>")}
 {R("div","faixa",D("w:em março deste ano"),"Em março deste ano, alguém <b>fechou</b> esse pedaço de mar.")}</div>''')

cena(3, lambda D: f'''<div class="col c">{R("div","k","0.2","O CAMINHO INTEIRO")}
 {R("h1","h xl","0.45","Do barril de petróleo<br><b>até o seu bolso</b>.")}
 {R("p","s",D("p4"),"E no final: por que o Brasil, um dos grandes produtores do planeta, <b>sofre junto</b>.")}
 {R("span","chip am",D("p5"),"Fica comigo")}</div>''')

cena(6, lambda D: f'''<div class="comapa">{zoom(ROTS("0.5") + rot("OM","OMÃ",1,1,"tx","0.5") + ormuz(D("w:estreito de ormuz")))}
 <div class="sobre">{R("div","k","0.2","ORIENTE MÉDIO")}{R("h2","h",D("w:estreito de ormuz"),"Estreito de <b>Ormuz</b>")}
 {R("p","s",D("w:entre o irã"),"Fica entre o <b>Irã</b> e a <b>península árabe</b>.")}</div></div>''')

cena(7, lambda D: f'''<div class="comapa">{zoom(rota(D("0.5")) + ROTS("0.2") + ormuz("0.2", False), [("SA",D("w:arábia saudita")),("IQ",D("w:do iraque")),("KW",D("w:do kuwait")),("AE",D("w:dos emirados")),("IR",D("w:do próprio irã"))])}
 <div class="sobre">{R("div","k","0.2","POR ALI SAEM OS NAVIOS DE PETRÓLEO")}
 <ul class="lista pq">{R("li","",D("w:arábia saudita"),"Arábia Saudita")}{R("li","",D("w:do iraque"),"Iraque")}{R("li","",D("w:do kuwait"),"Kuwait")}{R("li","",D("w:dos emirados"),"Emirados")}{R("li","",D("w:do próprio irã"),"Irã")}</ul></div></div>''')

cena(8, lambda D: f'''<div class="col c">{R("div","num","0.2",cnt(0,20,0,D("w:20 por cento|-0.6"),1.4,"","%"))}
 {R("p","s lgs",D("w:20 por cento|0.4"),"de todo o petróleo do mundo<br>passa por esse <b>funil</b>")}
 {R("span","chip am",D("w:um em cada cinco"),"1 em cada 5 barris")}
 {R("div","src","1.2","Fonte: Trading Economics. Valor aproximado.")}</div>''')

cena(9, lambda D: f'''<div class="col c">{R("div","k","0.2","E NÃO É SÓ PETRÓLEO")}{R("h2","h lg","0.45","Por ali também passa o <b>gás</b>")}
 <div class="chips">{R("span","chip",D("w:vira energia"),"⚡ Energia na Europa e na Ásia")}{R("span","chip",D("w:fazer adubo|-0.4"),"🌱 Matéria-prima do adubo")}</div>
 {R("div","faixa",D("p10"),"Tudo isso por uma passagem estreita, que <b>qualquer conflito</b> consegue ameaçar.")}</div>''')

cena(11, lambda D: f'''<div class="col c">{R("h1","h xl","0.25","Pensa num <b>cano</b>.")}
 {R("p","s lgs",D("w:se o cano entope"),"Se o cano entope, a água <b>não chega na torneira</b>.")}
 {R("div","k vm",D("p12"),"E O PETRÓLEO NÃO TEM SUBSTITUTO RÁPIDO")}
 <div class="chips">{R("span","chip",D("w:o caminhão não passa"),"🚚 Caminhão")}{R("span","chip",D("w:o avião também"),"✈️ Avião")}</div>
 {R("div","faixa",D("p13"),"Quando falta um pouco, o preço não sobe um pouco. <b>Ele dispara.</b>")}</div>''')

cena(14, lambda D: f'''<div class="col c">{R("h1","h xl","0.25","Isso não é teoria.<br><b>Já aconteceu várias vezes.</b>")}</div>''')

cena(15, lambda D: f'''<div class="col c">{R("div","k","0.2","1973 · GUERRA NO ORIENTE MÉDIO")}
 {R("h2","h md",D("w:os países árabes"),"Países árabes cortam a venda de petróleo")}
 <div class="dea r" data-d="{D("p16")}"><span class="de">US$ 3</span><span class="seta">→</span><span class="ate">{cnt(3,12,0,D("w:perto de doze|-0.7"),1.4,"US$ ","")}</span></div>
 <div class="chips">{R("span","chip vm",D("w:o preço quadruplicou"),"O PREÇO QUADRUPLICOU")}{R("span","chip",D("w:fila de carro"),"⛽ Fila no posto nos Estados Unidos")}</div>
 {R("div","src","1.0","Fonte: IstoÉ/DW e EBC. Valores aproximados por barril.")}</div>''')

cena(17, lambda D: f'''<div class="col c">{R("div","k","0.2","1979 · REVOLUÇÃO NO IRÃ")}
 {R("h1","h xl",D("w:o preço triplica"),"O preço <b>triplica</b><br>de novo.")}</div>''')

cena(18, lambda D: f'''<div class="col c">{R("div","k","0.2","2008 · NÃO FOI GUERRA: FOI O MUNDO CONSUMINDO MUITO")}
 {R("div","num md",D("w:em julho"),cnt(90,147,0,D("w:cento e quarenta e sete|-1.1"),1.5,"US$ ",""))}
 {R("p","s",D("w:o maior preço"),"em julho: <b>o maior preço da história</b>")}
 {R("div","faixa",D("p19"),"Poucos meses depois, com a crise dos bancos: <b>menos de US$ 40</b>")}
 {R("span","chip am",D("p20"),"📌 Guarda isso")}
 {R("div","src","1.0","Fonte: Trading Economics")}</div>''')

cena(21, lambda D: f'''<div class="col c">{R("div","k","0.2","2022 · A RÚSSIA INVADE A UCRÂNIA")}
 {R("div","num md",D("w:em março"),cnt(95,139,0,D("w:cento e trinta e nove|-1.1"),1.5,"US$ ",""))}
 {R("p","s lgs",D("w:cento e trinta e nove|0.5"),"o barril, em março de 2022")}
 {R("div","src","1.0","Fonte: Forbes (US$ 139,13)")}</div>''')

cena(22, lambda D: f'''<div class="col c">{R("h2","h md","0.2","Quatro crises. <b>A mesma coisa.</b>")}
 <div class="cards">
  {R("div","card","0.5","<h3>1973</h3><div class=big>×4</div><p>Guerra no Oriente Médio</p>")}
  {R("div","card","0.8","<h3>1979</h3><div class=big>×3</div><p>Revolução no Irã</p>")}
  {R("div","card","1.1","<h3>2008</h3><div class=big>US$ 147</div><p>Mundo consumindo muito</p>")}
  {R("div","card","1.4","<h3>2022</h3><div class=big>US$ 139</div><p>Guerra na Ucrânia</p>")}
 </div>{R("div","faixa",D("w:o petróleo é o primeiro"),"O petróleo é o <b>primeiro preço a pular</b>.")}</div>''')

cena(23, c26a)

cena(28, lambda D: f'''<div class="col c">{R("div","k","0.2","E AQUI NO BRASIL?")}
 {R("div","num",D("w:60 por cento|-0.9"),cnt(0,60,0,D("w:60 por cento|-0.7"),1.4,"+","%"))}
 {R("p","s lgs",D("w:60 por cento|0.4"),"no preço de referência do petróleo, <b>só em março</b>")}
 {R("div","src","1.0","Fonte: Agência Nacional do Petróleo (ANP), 2026")}</div>''')

cena(29, lambda D: f'''<div class="col c">{R("div","k","0.2","GASOLINA NA BOMBA · PREÇO MÉDIO DO LITRO")}
 <div class="dea r" data-d="{D("w:seis reais e trinta|-0.3")}"><span class="de">R$ 6,30</span><span class="seta">→</span><span class="ate">{cnt(6.30,6.65,2,D("w:seis e sessenta e cinco|-0.7"),1.4,"R$ ","")}</span></div>
 {R("p","s lgs",D("w:trinta e cinco centavos"),"<b>+35 centavos</b> por litro, em quatro semanas")}
 {R("div","src","1.0","Fonte: ANP, sínteses semanais de preços (meados de fevereiro e meados de março de 2026)")}</div>''')

cena(30, c26b)

cena(32, lambda D: f'''<div class="col c">{R("h1","h xl","0.25","O petróleo sobe de elevador.<br><b>Mas ele também desce.</b>")}
 {R("div","faixa",D("w:decisão tomada no susto"),"Decisão tomada no susto costuma ser <b>decisão ruim</b>.")}</div>''')

cena(33, lambda D: f'''<div class="col c">{R("div","k","0.2","A PERGUNTA QUE TODO BRASILEIRO FAZ")}
 {R("h1","h xl",D("p34"),"O Brasil não<br><b>produz petróleo?</b>")}
 <div class="chips">{R("span","chip",D("w:não tem o pré-sal"),"🛢️ E o pré-sal?")}{R("span","chip vm",D("w:então por que"),"ENTÃO POR QUE A GENTE SOFRE?")}</div></div>''')

cena(35, lambda D: f'''<div class="col c">{R("h1","h xxl","0.2","<b>Produz.</b>")}{R("h1","h lg",D("w:e muito"),"E muito.")}
 {R("div","faixa",D("w:o brasil tira"),"O Brasil tira <b>mais petróleo do chão do que consome</b> e ainda vende pra fora.")}</div>''')

cena(36, lambda D: f'''<div class="col c">{R("h2","h lg","0.25","O problema está<br><b>no meio do caminho</b>")}
 <div class="fluxo">{R("span","chip gr",D("w:petróleo bruto"),"🛢️ Petróleo bruto")}{R("span","st",D("w:ele precisa virar"),"→")}{R("span","chip gr",D("w:virar gasolina"),"⛽ Gasolina e diesel")}</div>
 {R("span","chip am",D("w:isso se chama"),"Isso se chama REFINO")}</div>''')

cena(37, lambda D: f'''<div class="col c">{R("div","k","0.2","AS REFINARIAS NÃO DÃO CONTA DE TUDO")}{R("h2","h md","0.45","De onde vem o diesel que o Brasil consome")}
 <div class="barras lg">
  <div class="lin r" data-d="0.9"><span class="rot">Feito aqui</span><div class="tr"><div class="bar cz" data-w="67" data-d="1.1" data-dur="1.2"></div></div><span class="val">≈ 2/3</span></div>
  <div class="lin r" data-d="{D("w:um terço|-0.5")}"><span class="rot">Vem de fora</span><div class="tr"><div class="bar" data-w="33" data-d="{D("w:um terço|-0.3")}" data-dur="1.2"></div></div><span class="val am">≈ 1/3</span></div>
 </div>
 {R("div","faixa",D("p38"),"Diesel importado tem preço lá de fora. <b>Em dólar.</b>")}
 {R("div","src","1.0","Fonte: ANP, síntese de volumes (29,9% em janeiro de 2026)")}</div>''')

cena(39, lambda D: f'''<div class="col c">{R("div","k vm","0.2","A CONTA É DUPLA")}
 <div class="chips g">{R("span","chip gr",D("w:se o barril sobe"),"🛢️ Barril sobe")}{R("span","chip gr",D("w:se o dólar sobe"),"💵 Dólar sobe junto")}</div>
 {R("h2","h lg",D("w:fica mais caro ainda"),"Diesel <b>mais caro ainda</b>")}
 {R("p","s",D("w:e no último vídeo"),"No último vídeo a gente viu: na crise, o dólar costuma subir.")}</div>''')

cena(40, lambda D: f'''<div class="col c">{R("h2","h lg","0.25","Quem <b>ganha</b> e quem <b>perde</b>")}
 <div class="cards c2">
  {R("div","card vd",D("p41"),"<h3>🛢️ O país, que vende</h3><p>Vende o petróleo mais caro. Entra mais dólar. Estados e cidades que produzem recebem mais.</p>")}
  {R("div","card vm",D("p42"),"<h3>🛒 Você, que compra</h3><p>Enche o tanque e faz a compra do mês. O barril caro aperta a sua conta.</p>")}
 </div>{R("div","faixa",D("p43"),"Boa notícia num jornal, ruim no outro. Depende de <b>que lado do balcão</b> você está.")}</div>''')

cena(44, lambda D: f'''<div class="col e">{R("div","k","0.2","MARÇO DE 2026")}{R("h2","h lg",D("w:uma subvenção|-0.6"),"Uma <b>subvenção</b> pra segurar o preço do diesel")}
 <ul class="lista">{R("li","",D("w:segurou uma parte"),"Segurou uma parte")}{R("li","",D("w:sai do cofre|-0.4"),"O dinheiro sai do cofre público")}</ul>
 {R("div","faixa",D("w:de um jeito"),"De um jeito ou de outro, <b>a conta chega</b>.")}
 {R("div","src","1.0","Fonte: Decreto 12.878, de 13/3/2026")}</div>''')

cena(45, lambda D: f'''<div class="col c">{R("div","k vd","0.2","UMA COISA QUE ALIVIA")}
 {R("h1","h xl",D("p46"),"O preço na bomba<br><b>não é só petróleo</b>.")}</div>''')

cena(47, lambda D: f'''<div class="col c">{R("h2","h md","0.2","O que tem em <b>1 litro de gasolina</b>")}
 <div class="barras lg">
  <div class="lin r" data-d="{D("w:um terço|-0.5")}"><span class="rot">Refinaria</span><div class="tr"><div class="bar" data-w="34" data-d="{D("w:um terço|-0.3")}" data-dur="1.2"></div></div><span class="val am">≈ 1/3</span></div>
  <div class="lin r" data-d="{D("w:o resto|-0.2")}"><span class="rot">Imposto, etanol e margens</span><div class="tr"><div class="bar cz" data-w="66" data-d="{D("w:o resto")}" data-dur="1.4"></div></div><span class="val">≈ 2/3</span></div>
 </div>
 {R("div","faixa",D("p48"),"Barril +60% <b>não vira</b> gasolina +60%. Só uma parte do preço acompanha.")}
 {R("div","src","1.0","Fonte: Empresa de Pesquisa Energética (EPE), maio de 2026. Refinaria: cerca de 34%.")}</div>''')

cena(49, lambda D: f'''<div class="col c">{R("h2","h md","0.2","E em <b>1 litro de diesel</b>")}
 <div class="barras lg">
  <div class="lin r" data-d="0.6"><span class="rot">Refinaria e importador</span><div class="tr"><div class="bar" data-w="51" data-d="{D("w:metade do preço|-0.6")}" data-dur="1.2"></div></div><span class="val am">≈ metade</span></div>
 </div>
 {R("p","s lgs",D("w:então o diesel"),"O diesel <b>sente mais</b>.")}
 {R("div","faixa",D("w:é o combustível do brasil|-0.4"),"O diesel não é o combustível do seu carro. É o <b>combustível do Brasil</b>.")}
 {R("div","src","1.0","Fonte: EPE, maio de 2026. Refinaria e importador: cerca de 51%.")}</div>''')

cena(51, lambda D: f'''<div class="col c">{R("h2","h md","0.2","Do diesel <b>pra tudo</b>")}
 <div class="cards c5">
  {R("div","card",D("p52"),"<i>1</i><h3>🚚 Frete</h3><p>Quase tudo chegou de caminhão</p>")}
  {R("div","card",D("p53"),"<i>2</i><h3>🍅 Comida</h3><p>Sobe duas vezes: pra plantar e pra chegar</p>")}
  {R("div","card",D("p54"),"<i>3</i><h3>🚌 Passagem</h3><p>De ônibus e de avião</p>")}
  {R("div","card",D("p55"),"<i>4</i><h3>🔥 Gás</h3><p>O gás de cozinha também vem do petróleo</p>")}
  {R("div","card",D("p56"),"<i>5</i><h3>💳 Juros</h3><p>Inflação sobe, juro fica alto por mais tempo</p>")}
 </div>{R("div","faixa",D("p57"),"Você pode nem ter carro. O petróleo chega em você <b>do mesmo jeito</b>.")}</div>''')

cena(58, lambda D: f'''<div class="col e">{R("div","k","0.2","JUNTANDO AS PEÇAS")}
 <ul class="lista pq">{R("li","",D("w:um funil"),"Um funil de <b>33 km</b> entope")}{R("li","",D("w:o barril dispara"),"O barril dispara")}{R("li","",D("w:o brasil produz"),"O Brasil compra de fora <b>um terço do diesel</b>")}{R("li","",D("w:o diesel sobe"),"O diesel sobe")}{R("li","",D("w:o aumento escorre"),"E escorre pra tudo: frete, comida, passagem, gás e juros")}</ul>
 {R("div","faixa",D("p60"),"Uma fila de dominó. A primeira peça cai a <b>milhares de quilômetros</b> da sua casa.")}</div>''')

cena(61, lambda D: f'''<div class="col c">{R("h1","h xl","0.25","O que dá pra<br><b>tirar disso tudo</b>?")}
 {R("p","s lgs",D("w:entenda três coisas|-0.6"),"Três coisas pra você entender.")}
 {R("div","src",D("w:eu não estou"),"Conteúdo educativo. Não é recomendação de investimento.")}</div>''')

cena(63, lambda D: f'''<div class="col e">{R("div","k","0.15","TRÊS COISAS PRA GUARDAR")}
 <ol class="tres">{R("li","",D("p63"),"<i>1</i><span>O petróleo é o <b>primeiro preço a pular</b> numa crise</span>")}
 {R("li","",D("p64"),"<i>2</i><span>No Brasil, ele chega pelo <b>diesel e pelo dólar</b></span>")}
 {R("li","",D("p65"),"<i>3</i><span><b>O que sobe rápido também desce.</b> Reserva guardada atravessa o susto</span>")}</ol></div>''')

cena(66, lambda D: f'''<div class="col c">{R("div","k am","0.2","CALCULADORA GRÁTIS")}{R("h1","h lg","0.45","Quanto a inflação já comeu<br>do <b>seu dinheiro</b>?")}
 {R("div","url",D("w:o link está"),"termometrodecrise.com/ferramentas")}{R("p","s",D("w:o link está|0.4"),"O link está na descrição")}</div>''')

cena(67, lambda D: f'''<div class="col c">{R("h1","h lg","0.25","Onde você sentiu <b>primeiro</b>?")}
 <div class="chips g">{R("span","chip gr",D("w:no posto"),"⛽ Posto")}{R("span","chip gr",D("w:no mercado"),"🛒 Mercado")}{R("span","chip gr",D("w:no botijão"),"🔥 Botijão de gás")}</div>
 {R("p","s",D("w:no botijão|0.6"),"Conta aqui nos comentários")}</div>''')

LOGO = '''<svg viewBox="24 44 152 100"><g fill="none" stroke-width="18"><path d="M 38.06 117.3 A 62 62 0 0 1 48.3 85.78" stroke="#3B82C4"/><path d="M 51.48 81.4 A 62 62 0 0 1 78.29 61.93" stroke="#7CC3E0"/><path d="M 83.43 60.25 A 62 62 0 0 1 116.57 60.25" stroke="#F2C14E"/><path d="M 121.71 61.93 A 62 62 0 0 1 148.52 81.4" stroke="#EE8A3C"/><path d="M 151.7 85.78 A 62 62 0 0 1 161.94 117.3" stroke="#E5554A"/></g><line x1="100" y1="120" x2="120.44" y2="76.57" stroke="#EEF2F5" stroke-width="9" stroke-linecap="round"/><circle cx="100" cy="120" r="12" fill="#EEF2F5"/></svg>'''

cena(68, lambda D: f"""<div class="col c fim"><div class="lg2 r" data-d="0.2">{LOGO}</div>{R("h1","h lg","0.5","Termômetro de Crise")}
 {R("div","insc","0.9","INSCREVA-SE")}{R("p","s",D("w:segunda quarta"),"<b>Segunda, quarta e sexta</b>: o que acontece no mundo e o que muda no seu bolso")}
 {R("p","s pq",D("p69"),"Não recomendamos: só mostramos a temperatura do mundo.")}
 {R("div","bordao",D("p70"),"Sem alarde. Eu sou só o termômetro!")}</div>""")

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

CTA = [(caps[1]["b"] + 3.0, "Tá entendendo? Então", "INSCREVA-SE", "v"), (caps[3]["b"] + 3.0, "Curtiu até aqui?", "👍 DEIXA O LIKE", "a"),
       (caps[5]["b"] + 3.0, "Não perde o próximo:", "🔔 INSCREVA-SE", "v")]
dados = {"cta": [{"a": round(t, 2), "b": round(t + 5.2, 2), "tx": tx, "bt": bt, "cor": cor} for t, tx, bt, cor in CTA], "T": round(TOTAL, 2), "cenas": [{"a": c["a"], "b": c["b"]} for c in cenas], "caps": caps, "legs": legs}
tpl = (P / "modelo.html").read_text().replace("</style>", CSS_EXTRA + "</style>", 1)
saida = tpl.replace("/*DADOS*/", json.dumps(dados, ensure_ascii=False)).replace("<!--MAPA-->", MAPA_DEFS).replace("<!--LOGO-->", LOGO)
saida = saida.replace("<!--CENAS-->", "\n".join(f'<section class="cena" id="c{j}">{c["h"]}</section>' for j, c in enumerate(cenas)))
(P / "video.html").write_text(saida)
(P / "tempos.json").write_text(json.dumps({"cta": [round(t, 2) for t, *_ in CTA], "T": TOTAL, "cenas": [(c["a"], c["b"]) for c in cenas], "caps": caps, "paragrafos": [round(pt(i), 2) for i in range(71)]}, ensure_ascii=False, indent=1))
print(f"total {TOTAL:.1f}s = {int(TOTAL//60)}:{TOTAL%60:04.1f}; cenas {len(cenas)}; legendas {len(legs)}")

