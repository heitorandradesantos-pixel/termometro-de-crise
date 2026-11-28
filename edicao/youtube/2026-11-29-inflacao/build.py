#!/usr/bin/env python3
"""Monta o HTML animado do vídeo 4 (inflação) e o áudio final com pausas entre capítulos."""
import json, re, subprocess, unicodedata, html
from difflib import SequenceMatcher
from pathlib import Path

P = Path(__file__).resolve().parent
REPO = Path("/home/claude/termometro-de-crise")
LEAD, PAUSA, CAUDA = 0.8, 1.5, 8.0
CAPS = [(7, "O que é inflação"), (14, "Quando era 82% ao mês"), (20, "Quem mede"), (32, "A sua inflação não é a oficial"),
        (38, "Por que os preços sobem"), (46, "Quem segura"), (52, "O que ela faz com o seu dinheiro"), (67, "O que tirar disso")]

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))

# ---------- texto e alinhamento ----------
texto = (P.parent / "v4-tts1.txt").read_text().strip().split("\n\n")
t2 = (P.parent / "v4-tts2.txt").read_text().strip().split("\n\n")
# a divisão automática deixou "Ou seja..." no começo da parte 2; na geração ele foi para o fim da parte 1 (não muda a ordem)
paras = texto + t2
assert len(paras) == 77, len(paras)

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
#leg span{font-size:56px;padding:14px 38px;max-width:1640px}
.cards.c3{grid-template-columns:repeat(3,1fr);width:1620px}.cards.c3 .card{min-height:300px}.cards.c3 h3{font-size:46px}.cards.c3 p{font-size:34px}
.duo{display:grid;grid-template-columns:auto 1fr;gap:70px;align-items:center;width:1660px}.duo .tx{display:flex;flex-direction:column;gap:24px;align-items:flex-start;text-align:left}
.emo{font-size:260px;line-height:1}.emo.g{font-size:360px}.emo.m{font-size:170px}
.emj{display:flex;gap:34px;align-items:flex-end;justify-content:center;flex-wrap:wrap}.emj span{font-size:130px;line-height:1;display:flex;flex-direction:column;align-items:center;gap:8px}.emj small{font-size:30px;font-weight:700;color:#C9D3DE}
.nota{display:inline-flex;flex-direction:column;align-items:center;justify-content:center;width:520px;height:240px;border-radius:18px;background:linear-gradient(135deg,#1F8A5B,#2FB07A 55%,#1A7550);border:5px solid #8FF0C0;color:#EFFFF6;font-weight:900;box-shadow:0 18px 50px rgba(0,0,0,.45)}
.nota b{font-size:120px;line-height:.95;color:#fff}.nota i{font-style:normal;font-size:30px;letter-spacing:6px}
.nota.m{width:380px;height:176px}.nota.m b{font-size:86px}.nota.m i{font-size:22px}
.nota.p{width:250px;height:116px;border-width:3px;border-radius:12px}.nota.p b{font-size:56px}.nota.p i{font-size:15px;letter-spacing:3px}
.nota.pp{width:158px;height:76px;border-width:3px;border-radius:9px}.nota.pp b{font-size:38px}.nota.pp i{display:none}
.notas{display:flex;gap:16px;flex-wrap:wrap;justify-content:center;max-width:1640px;align-items:center}
.tv{width:1180px;border-radius:34px;border:14px solid #2A3A4D;background:#0B1118;box-shadow:0 30px 80px rgba(0,0,0,.6);overflow:hidden}
.tv .tvb{background:#C8322B;color:#fff;font-weight:900;font-size:34px;letter-spacing:5px;padding:14px 34px;text-align:left}
.tv .man{padding:60px 50px 70px;font-size:86px;font-weight:900;line-height:1.08;color:#fff;text-align:left}.tv .man b{color:#F2C14E}
.pac{display:inline-flex;flex-direction:column;align-items:center;justify-content:center;border-radius:20px;background:linear-gradient(160deg,#E2A63A,#B8791F);color:#2A1A05;font-weight:900;box-shadow:0 16px 40px rgba(0,0,0,.45);width:270px;height:320px;font-size:66px}.pac small{font-size:30px}
.pac.p{width:226px;height:268px;font-size:54px}
.etq{display:inline-block;background:#F2C14E;color:#0E141B;font-weight:900;font-size:44px;padding:10px 26px;border-radius:12px}
.vs{font-size:90px;font-weight:900;color:#8A98A8}
.bigt{font-size:150px;font-weight:900;color:#F2C14E;line-height:1;letter-spacing:-4px}
.conta{display:flex;gap:26px;align-items:center;justify-content:center;flex-wrap:wrap}.conta .op{font-size:90px;font-weight:900;color:#F2C14E}
.bar.vmb{background:linear-gradient(90deg,#B93B32,#F0776C)!important}.vmt{color:#F0776C!important}
.fx{display:flex;gap:22px;align-items:center;justify-content:center;flex-wrap:wrap;max-width:1700px}.fx .st{font-size:70px;font-weight:900;color:#F2C14E}
"""
NOTA = lambda c="": f'<span class="nota {c}"><b>100</b><i>REAIS</i></span>'

CENAS = []
def cena(p, corpo):
    CENAS.append([p, corpo])

cena(0, lambda D: f'''<div class="col c"><div class="duo">{R("div","emo g","0.15","🛒")}
 <div class="tx">{R("div","k","0.2","O MESMO CARRINHO DE MERCADO")}
 {R("h2","h lg","0.4","2020: <b>R$ 300</b>")}
 {R("div","bigt",D("w:hoje|-0.1"),cnt(300,502,0,D("w:hoje"),1.5,"R$ ",""))}
 {R("p","s lgs",D("w:passa de"),"hoje ele <b>passa de R$ 500</b>")}</div></div>
 {R("div","src","1.0","Fonte: FGV IBRE com dados do IBGE (alimentação no domicílio: +67,5% de janeiro de 2020 a junho de 2026)")}</div>''')

cena(1, lambda D: f'''<div class="col c"><div class="tv r" data-d="0.15"><div class="tvb">📺 NO JORNAL DA TELEVISÃO</div>
 <div class="man">Inflação sobe<br><b>menos de 5%</b><br>em um ano</div></div></div>''')

cena(2, lambda D: f'''<div class="col c">{R("h1","h xl","0.2","Quem está <b>mentindo</b>?")}
 <div class="fx">{R("span","emo","0.5","📺")}{R("span","vs","0.9","ou")}{R("span","emo",D("w:ou o seu carrinho"),"🛒")}</div>
 {R("div","faixa",D("p3"),"<b>Nenhum dos dois.</b> E você nunca mais vai olhar pra etiqueta do mesmo jeito.")}</div>''')

cena(4, lambda D: f'''<div class="col c fim"><div class="lg2 r" data-d="0.15">{LOGO}</div>{R("h1","h lg","0.3","Termômetro de Crise")}
 <div class="fx">{R("span","chip gr",D("w:deixa o like"),"👍 Deixa o like")}{R("span","insc",D("w:se inscreve"),"🔔 INSCREVA-SE")}</div>
 {R("p","s lgs",D("w:pra que mais gente"),"pra mais gente ter acesso à <b>temperatura do Brasil</b>")}</div>''')

cena(5, lambda D: f'''<div class="col e">{R("div","k","0.2","NESTE VÍDEO")}
 <ul class="lista">{R("li","",D("w:o que é inflação"),"🏷️ O que é inflação de verdade")}{R("li","",D("w:quem faz essa conta"),"🧮 Quem faz essa conta")}{R("li","",D("w:por que no seu bolso"),"🛒 Por que no seu bolso ela é diferente")}{R("li","",D("w:e o que ela faz"),"💵 O que ela faz com o dinheiro parado")}</ul>
 {R("span","chip am",D("p6"),"⏱️ No final: uma conta de 30 segundos com o seu salário")}</div>''')

cena(7, lambda D: f'''<div class="col c">{R("h1","h xl","0.25","O que é <b>inflação</b>?")}
 {R("p","s lgs",D("p8"),"Não é <b>uma</b> coisa ficar cara.")}
 {R("div","faixa",D("w:é quase tudo"),"É quase <b>tudo</b> ficar caro ao mesmo tempo. E continuar ficando.")}</div>''')

cena(9, lambda D: f'''<div class="col c"><div class="fx">{R("span","emo m","0.2","🍅")}{R("span","chip gr","0.6","só o tomate = problema do tomate")}</div>
 <div class="emj">{R("span","",D("w:se sobe o tomate"),"🍅<small>tomate</small>")}{R("span","",D("w:o aluguel"),"🏠<small>aluguel</small>")}{R("span","",D("w:a luz"),"💡<small>luz</small>")}{R("span","",D("w:o ônibus"),"🚌<small>ônibus</small>")}{R("span","",D("w:e a escola"),"🎒<small>escola</small>")}</div>
 {R("span","chip vm",D("w:aí é inflação"),"TUDO JUNTO = INFLAÇÃO")}</div>''')

cena(10, lambda D: f'''<div class="col c">{R("h2","h lg","0.2","Não é o preço que sobe.<br>É o <b>dinheiro que encolhe</b>.")}
 <div class="notas">{R("span","","0.5",NOTA())}{R("span","st",D("w:é o dinheiro"),"<span class=vs>→</span>")}{R("span","",D("w:é o dinheiro|0.3"),NOTA("m"))}{R("span","",D("p11"),"<span class=vs>→</span>")}{R("span","",D("p11|0.3"),NOTA("p"))}</div>
 {R("p","s lgs",D("w:só que ela compra"),"Continua escrito 100. Só que <b>compra menos</b>.")}</div>''')

cena(12, lambda D: f'''<div class="col c">{R("div","k","0.2","DESDE QUE O REAL NASCEU · JULHO DE 1994")}
 {R("div","num vmn",D("w:mais de setecentos|-0.8"),cnt(0,790,0,D("w:mais de setecentos|-0.6"),1.6,"+","%"))}
 <div class="notas r" data-d="{D("p13")}">{"".join(R("span","",D(f"p13|{0.3+j*0.28:.2f}"),NOTA("pp")) for j in range(9))}</div>
 {R("p","s",D("w:quase nove notas"),"<b>Quase 9 notas</b> de 100 pra comprar o que 1 comprava em 1994")}
 {R("div","src","1.0","Fonte: IBGE (IPCA de julho de 1994 a setembro de 2026: 797,7%)")}</div>''')

cena(14, lambda D: f'''<div class="col c">{R("p","s lgs","0.2","E isso é o Brasil que <b>deu certo</b>.")}
 {R("h1","h xl",D("w:antes do real"),"Antes do real era<br><b>muito pior</b>.")}</div>''')

cena(15, lambda D: f'''<div class="col c">{R("div","k vm","0.2","MARÇO DE 1990")}
 {R("div","num vmn",D("w:oitenta e dois|-0.8"),cnt(0,82,0,D("w:oitenta e dois|-0.6"),1.3,"+","%"))}
 {R("h2","h lg",D("w:em um mês"),"em <b>um mês</b>")}
 {R("div","src","1.0","Fonte: IBGE (IPCA de março de 1990: 82,39%)")}</div>''')

cena(16, lambda D: f'''<div class="col c"><div class="fx">{R("span","emo","0.2","💵")}{R("span","st",D("w:e corria"),"→")}{R("span","emo",D("w:e corria"),"🏃")}{R("span","st",D("w:pro mercado"),"→")}{R("span","emo",D("w:pro mercado"),"🛒")}</div>
 {R("h2","h md",D("w:no mesmo dia"),"Salário recebido, mercado <b>no mesmo dia</b>")}
 {R("span","chip gr",D("w:as máquinas"),"🏷️ Preço remarcado o dia inteiro")}</div>''')

cena(17, lambda D: f'''<div class="col c">{R("div","k","0.2","DE 1980 ATÉ A CHEGADA DO REAL")}
 {R("div","bigt",D("w:treze trilhões|-0.3"),"+13 trilhões %")}
 <div class="fx">{R("span","chip",D("p18"),"Cruzeiro")}{R("span","chip",D("p18|0.4"),"Cruzado")}{R("span","chip",D("p18|0.8"),"Cruzado Novo")}{R("span","chip",D("p18|1.2"),"Cruzeiro")}{R("span","chip",D("p18|1.6"),"Cruzeiro Real")}{R("span","chip am",D("w:só parou"),"REAL")}</div>
 {R("div","faixa",D("p19"),"Por isso o Banco Central tem <b>tanto medo</b> de inflação.")}
 {R("div","src","1.0","Fonte: IBGE (IPCA acumulado de 1980 a junho de 1994)")}</div>''')

cena(20, lambda D: f'''<div class="col c">{R("h2","h lg","0.2","Quem mede isso hoje?")}
 {R("div","bigt",D("p21"),"IBGE")}{R("span","chip",D("w:o mesmo instituto"),"o mesmo do censo")}
 {R("h2","h lg",D("w:ipca|-0.2"),"A inflação oficial se chama <b>IPCA</b>")}</div>''')

cena(22, lambda D: f'''<div class="col c">{R("div","k","0.2","TODO MÊS, O IBGE ANOTA O PREÇO DE")}
 {R("div","num md",D("w:quase quatrocentos|-0.6"),cnt(0,377,0,D("w:quase quatrocentos|-0.4"),1.3,""," itens"))}
 <div class="emj">{R("span","",D("w:arroz"),"🍚<small>arroz</small>")}{R("span","",D("w:gasolina"),"⛽<small>gasolina</small>")}{R("span","",D("w:aluguel"),"🏠<small>aluguel</small>")}{R("span","",D("w:plano de saúde"),"🩺<small>plano de saúde</small>")}{R("span","",D("w:corte de cabelo"),"💇<small>corte de cabelo</small>")}</div>
 {R("div","src","1.0","Fonte: IBGE (377 produtos e serviços pesquisados no IPCA)")}</div>''')

cena(23, lambda D: f'''<div class="col c">{R("h2","h lg","0.2","Nem tudo <b>conta igual</b>")}
 <div class="fx">{R("span","chip gr",D("w:comida e transporte"),"🍽️ Comida")}{R("span","chip gr",D("w:comida e transporte|0.5"),"🚌 Transporte")}</div>
 {R("p","s lgs",D("w:contam mais"),"contam mais, porque é onde as famílias <b>mais gastam</b>")}</div>''')

cena(24, lambda D: f'''<div class="col c"><div class="duo">{R("div","emo g","0.2","🛒")}
 <div class="tx">{R("h2","h lg","0.4","O <b>carrinho gigante</b> do IBGE")}
 {R("p","s lgs",D("w:com o gasto médio"),"O gasto <b>médio</b> das famílias: de 1 a 40 salários mínimos")}
 {R("span","chip am",D("p25"),"🔑 Repara na palavra: MÉDIO")}</div></div></div>''')

cena(26, lambda D: f'''<div class="col c">{R("div","k","0.2","O CARRINHO DO IBGE, EM UM ANO")}
 {R("div","num",D("w:quatro vírgula|-0.6"),cnt(0,4.63,2,D("w:quatro vírgula|-0.4"),1.4,"+","%"))}
 {R("span","chip vm",D("w:é mais do que"),"acima do limite de 4,5%")}
 {R("div","src","1.0","Fonte: IBGE (IPCA de outubro de 2026, acumulado em 12 meses)")}</div>''')

cena(27, lambda D: f'''<div class="col c">{R("h2","h md","0.2","Dentro da média <b>tem de tudo</b>")}
 <div class="cards c3">
  {R("div","card vm",D("w:o tomate"),"<h3>🍅 Tomate</h3><div class=big>+90%</div><p>neste ano</p>")}
  {R("div","card vm",D("w:a cebola"),"<h3>🧅 Cebola</h3><div class=big>+108%</div><p>em 12 meses</p>")}
  {R("div","card vm",D("w:a carne"),"<h3>🥩 Carnes</h3><div class=big>+12%</div><p>em 12 meses</p>")}
 </div>
 <div class="fx">{R("span","chip",D("p28"),"💡 Conta de luz ▼")}{R("span","chip",D("w:passagem aérea"),"✈️ Passagem aérea ▼")}</div>
 {R("div","src","1.0","Fonte: IBGE (IPCA de outubro de 2026)")}</div>''')

cena(29, lambda D: f'''<div class="col c">{R("div","num md","0.2","4,63%")}
 {R("h1","h xl",D("w:mas ninguém"),"Mas ninguém<br>compra a <b>média</b>.")}</div>''')

cena(30, lambda D: f'''<div class="col c">{R("div","k vm","0.2","O AUMENTO QUE NÃO APARECE NA ETIQUETA")}
 <div class="fx">{R("span","pac",D("w:duzentos gramas|-0.4"),"200 g<small>biscoito</small>")}{R("span","vs",D("w:e agora tem"),"→")}{R("span","pac p",D("w:e agora tem|0.2"),"170 g<small>biscoito</small>")}{R("span","etq",D("w:o preço é o mesmo"),"mesmo preço")}</div>
 {R("span","chip vm",D("p31"),"Isso também é inflação. Só que disfarçada.")}
 {R("span","chip am",D("w:por isso vale"),"🔎 Olha o preço por quilo ou por litro")}</div>''')

cena(32, lambda D: f'''<div class="col c"><div class="fx">{R("span","emo","0.2","🛒")}{R("span","vs","0.5","≠")}{R("span","emo","0.7","🛒")}</div>
 {R("h1","h xl",D("w:o seu carrinho"),"O seu carrinho não é<br>o carrinho do <b>IBGE</b>.")}</div>''')

cena(33, lambda D: f'''<div class="col c">{R("div","k","0.2","SE METADE DO SEU SALÁRIO VAI EM COMIDA")}
 <div class="barras lg"><div class="lin r" data-d="0.5"><span class="rot">🍽️ Comida</span><div class="tr"><div class="bar vmb" data-w="50" data-d="0.7" data-dur="1.2"></div></div><span class="val vmt">metade</span></div></div>
 {R("div","faixa",D("w:a inflação da sua casa"),"Comida subiu mais que a média? A inflação <b>da sua casa</b> é maior que a do IBGE.")}</div>''')

cena(34, lambda D: f'''<div class="col c">{R("h2","h md","0.2","Cada casa sente <b>num lugar</b>")}
 <div class="cards c3">
  {R("div","card",D("w:se você tem carro"),"<h3>⛽ Tem carro</h3><p>Sente a gasolina</p>")}
  {R("div","card",D("w:se paga aluguel"),"<h3>🏠 Paga aluguel</h3><p>Sente o reajuste</p>")}
  {R("div","card",D("w:se tem filho"),"<h3>🎒 Filho na escola</h3><p>Sente a mensalidade</p>")}
 </div>{R("div","faixa",D("p35"),"Quem ganha menos <b>sente mais</b>: gasta uma fatia maior com comida, gás e transporte.")}</div>''')

cena(36, lambda D: f'''<div class="col c">{R("h2","h md","0.2","A prova: de <b>2020 pra cá</b>")}
 <div class="barras lg">
  <div class="lin r" data-d="{D("w:a inflação oficial|-0.3")}"><span class="rot">📺 Inflação oficial</span><div class="tr"><div class="bar cz" data-w="64" data-d="{D("w:a inflação oficial")}" data-dur="1.2"></div></div><span class="val">+43%</span></div>
  <div class="lin r" data-d="{D("w:a comida de casa|-0.3")}"><span class="rot">🛒 Comida de casa</span><div class="tr"><div class="bar vmb" data-w="100" data-d="{D("w:a comida de casa")}" data-dur="1.2"></div></div><span class="val vmt">+67%</span></div>
 </div>
 {R("div","faixa",D("p37"),"O número oficial não é mentira. Ele só <b>não é o seu</b>.")}
 {R("div","src","1.0","Fonte: FGV IBRE com dados do IBGE (janeiro de 2020 a junho de 2026: IPCA +43,3%; alimentação no domicílio +67,5%)")}</div>''')

cena(38, lambda D: f'''<div class="col c">{R("div","k am","0.2","A PERGUNTA DE UM MILHÃO")}{R("h1","h xl","0.4","Por que os preços<br><b>sobem</b>?")}
 {R("span","chip gr",D("p39"),"4 motivos")}</div>''')

cena(40, lambda D: f'''<div class="col c">{R("div","k","0.2","MOTIVO 1")}
 <div class="fx">{R("span","emo m","0.4","🧍🧍🧍🧍🧍")}{R("span","vs",D("w:e pouca coisa"),"→")}{R("span","emo m",D("w:e pouca coisa"),"📦")}</div>
 {R("h2","h lg","0.6","Muita gente querendo,<br><b>pouca coisa pra vender</b>")}
 {R("span","chip vm",D("w:o vendedor percebe"),"O vendedor sobe o preço")}</div>''')

cena(41, lambda D: f'''<div class="col c">{R("div","k","0.2","MOTIVO 2")}{R("h2","h lg","0.4","Ficou mais caro <b>produzir</b>")}
 <div class="fx">{R("span","chip gr",D("w:subiu o petróleo"),"🛢️ Petróleo → 🚚 frete")}{R("span","chip gr",D("w:faltou chuva"),"🌧️ Faltou chuva → 🥬 comida")}</div>
 <div class="fx">{R("span","chip am",D("w:e o dólar"),"💵 Dólar sobe")}{R("span","st",D("w:sobe o trigo"),"→")}<div class="emj">{R("span","",D("w:sobe o trigo"),"🍞<small>pão</small>")}{R("span","",D("w:o adubo"),"🌱<small>adubo</small>")}{R("span","",D("w:o remédio"),"💊<small>remédio</small>")}{R("span","",D("w:o celular"),"📱<small>celular</small>")}</div></div></div>''')

cena(42, lambda D: f'''<div class="col c">{R("div","k","0.2","MOTIVO 3")}{R("h2","h lg","0.4","O aumento que <b>já vem no contrato</b>")}
 <div class="fx">{R("span","chip gr",D("w:aluguel"),"🏠 Aluguel")}{R("span","chip gr",D("w:plano de saúde"),"🩺 Plano de saúde")}{R("span","chip gr",D("w:e mensalidade"),"🎒 Mensalidade")}</div>
 {R("div","faixa",D("w:a inflação de ontem"),"A inflação de ontem vira <b>a de amanhã</b>.")}</div>''')

cena(43, lambda D: f'''<div class="col c"><div class="duo">{R("div","emo g","0.4","😨")}
 <div class="tx">{R("div","k vm","0.2","MOTIVO 4")}{R("h1","h xl","0.5","O <b>medo</b>")}
 <ul class="lista pq">{R("li","",D("w:o comerciante"),"O comerciante remarca antes")}{R("li","",D("w:o trabalhador"),"O trabalhador pede aumento antes")}{R("li","",D("w:e aí sobe"),"<b>E aí sobe mesmo</b>")}</ul></div></div>
 {R("div","faixa",D("p44"),"A inflação se alimenta do <b>medo dela mesma</b>.")}</div>''')

cena(45, lambda D: f'''<div class="col c">{R("div","k","0.2","FOI ASSIM NOS ANOS 80")}
 <div class="fx">{R("span","emo m","0.4","🏷️")}{R("span","emo m","0.7","🏷️")}{R("span","emo m","1.0","🏷️")}{R("span","emo m","1.3","🏷️")}</div>
 {R("h2","h lg",D("w:todo mundo remarcava"),"Todo mundo remarcava porque<br><b>todo mundo remarcava</b>")}</div>''')

cena(46, lambda D: f'''<div class="col c">{R("h2","h lg","0.2","Quem segura isso?")}
 <div class="duo">{R("div","emo",D("w:ele tem um alvo"),"🎯")}
 <div class="tx">{R("div","k",D("p47"),"BANCO CENTRAL · O ALVO")}{R("div","bigt",D("w:três por cento|-0.3"),"3% ao ano")}
 <div class="fx">{R("span","chip",D("w:pode passar"),"pode ir até 4,5%")}{R("span","chip vm",D("w:mais do que isso"),"🚨 passou: alerta")}</div></div></div>
 {R("div","src","1.0","Fonte: Conselho Monetário Nacional (meta de inflação) e Banco Central")}</div>''')

cena(48, lambda D: f'''<div class="col c">{R("div","k","0.2","A FERRAMENTA: O JURO")}{R("h2","h lg",D("w:a famosa selic"),"A famosa <b>Selic</b>")}
 <div class="fx">{R("span","chip gr",D("p49"),"💳 Prestação mais cara")}{R("span","st",D("w:o povo compra"),"→")}{R("span","chip gr",D("w:o povo compra"),"🛍️ Povo compra menos")}</div>
 <div class="fx">{R("span","st",D("w:as lojas seguram"),"→")}{R("span","chip gr",D("w:as lojas seguram"),"🏪 Lojas seguram o preço")}{R("span","st",D("w:e a inflação esfria"),"→")}{R("span","chip am",D("w:e a inflação esfria"),"❄️ Inflação esfria")}</div></div>''')

cena(50, lambda D: f'''<div class="col c"><div class="duo">{R("div","emo","0.2","💊")}
 <div class="tx">{R("h2","h lg","0.4","Só que o remédio é <b>amargo</b>")}
 <div class="fx">{R("span","chip vm",D("w:encarece a sua dívida"),"Encarece a sua dívida")}{R("span","chip vm",D("w:e freia o emprego"),"Freia o emprego")}</div>
 {R("span","chip",D("w:é por isso que a selic"),"Selic hoje: <b>13,75%</b>")}</div></div>
 {R("div","faixa",D("p51"),"Inflação baixa não é preço caindo. É preço subindo <b>mais devagar</b>.")}</div>''')

cena(52, lambda D: f'''<div class="col c">{R("div","k","0.2","AGORA, O SEU BOLSO")}{R("h1","h xl","0.4","O que a inflação faz com<br>o <b>seu dinheiro</b>?")}</div>''')

cena(53, lambda D: f'''<div class="col c">{R("div","k vm","0.2","1 · O DINHEIRO PARADO")}
 <div class="dea r" data-d="{D("p54")}"><span class="de">R$ 1.000</span><span class="seta">→</span><span class="ate">{cnt(1000,956,0,D("w:novecentos e cinquenta|-0.6"),1.4,"R$ ","")}</span></div>
 {R("p","s lgs",D("w:mas compram"),"um ano parado: compra o que <b>R$ 956</b> compravam")}
 {R("span","chip vm",D("w:quarenta e quatro reais"),"−R$ 44, sem sair da sua conta")}
 {R("div","src","1.0","Conta própria com o IPCA de 12 meses (4,63%)")}</div>''')

cena(56, lambda D: f'''<div class="col c">{R("div","k","0.2","PARECE POUCO. MAS ACUMULA.")}
 <div class="duo">{R("div","bigt",D("w:os preços dobram|-0.2"),"×2")}
 <div class="tx">{R("h2","h lg",D("w:os preços dobram"),"Os preços <b>dobram</b> em uns 15 anos")}{R("p","s",D("w:nesse ritmo"),"no ritmo de 4,6% ao ano")}</div></div>
 <div class="fx">{R("span","emo m",D("p57"),"🛏️")}{R("span","chip gr",D("w:compra só a metade"),"Dinheiro no colchão: compra só <b>a metade</b>")}</div>
 {R("div","src","1.0","Conta própria (juros compostos a 4,6% ao ano)")}</div>''')

cena(58, lambda D: f'''<div class="col c">{R("div","k vm","0.2","2 · O SEU SALÁRIO")}
 <div class="barras lg">
  <div class="lin r" data-d="{D("p59")}"><span class="rot">Seu aumento</span><div class="tr"><div class="bar cz" data-w="65" data-d="{D("p59|0.3")}" data-dur="1.0"></div></div><span class="val">+3%</span></div>
  <div class="lin r" data-d="{D("w:e a inflação foi|-0.3")}"><span class="rot">Inflação</span><div class="tr"><div class="bar vmb" data-w="100" data-d="{D("w:e a inflação foi")}" data-dur="1.0"></div></div><span class="val vmt">+4,63%</span></div>
 </div>
 {R("div","faixa",D("w:você ganhou um corte"),"Não foi aumento. Foi um <b>corte disfarçado</b>.")}
 {R("span","chip am",D("p60"),"⏱️ A conta de 30 segundos: seu reajuste × a inflação do período")}</div>''')

cena(61, lambda D: f'''<div class="col c">{R("div","k vm","0.2","3 · O SEU INVESTIMENTO")}
 <div class="conta">{R("span","chip gr",D("p62"),"Rendimento")}{R("span","op",D("w:a mais que a inflação"),"−")}{R("span","chip gr",D("w:a mais que a inflação"),"Inflação")}{R("span","op",D("w:ganho real"),"=")}{R("span","chip am",D("w:ganho real"),"GANHO REAL")}</div>
 <div class="conta">{R("span","chip",D("p63"),"5%")}{R("span","op",D("p63|0.6"),"−")}{R("span","chip",D("w:com inflação de"),"4,63%")}{R("span","op",D("w:praticamente"),"=")}{R("span","chip vm",D("w:praticamente"),"só empatou")}</div></div>''')

cena(64, lambda D: f'''<div class="col c"><div class="duo">{R("div","emo","0.2","🛡️")}
 <div class="tx">{R("h2","h lg","0.4","Investimentos que pagam<br><b>inflação + um pouco</b>")}
 {R("p","s lgs",D("w:eles foram feitos"),"pra o seu dinheiro <b>comprar a mesma coisa</b> lá na frente")}</div></div>
 {R("div","src","1.0","Exemplo educativo. Não é recomendação de investimento.")}</div>''')

cena(65, lambda D: f'''<div class="col c">{R("h2","h md","0.2","Quem <b>ganha</b> e quem <b>perde</b> com a inflação")}
 <div class="cards c2">
  {R("div","card vd",D("w:quem deve uma parcela"),"<h3>📄 Quem deve parcela fixa</h3><p>A parcela fica igual. Salário e preços sobem em volta.</p>")}
  {R("div","card vm",D("p66"),"<h3>💤 Quem não acompanha</h3><p>Dinheiro sem render, salário sem reajuste, aluguel sem correção, aposentadoria apertada.</p>")}
 </div></div>''')

cena(67, lambda D: f'''<div class="col c">{R("h1","h xl","0.25","O que dá pra<br><b>tirar disso tudo</b>?")}
 {R("p","s lgs",D("w:mas guarda"),"Guarda três coisas.")}
 {R("div","src",D("p68"),"Conteúdo educativo. Não é recomendação de investimento.")}</div>''')

cena(69, lambda D: f'''<div class="col e">{R("div","k","0.15","TRÊS COISAS PRA GUARDAR")}
 <ol class="tres">{R("li","",D("p69"),"<i>1</i><span>Inflação é o <b>dinheiro encolhendo</b>. E a sua pode ser maior que a oficial</span>")}
 {R("li","",D("p70"),"<i>2</i><span><b>Dinheiro parado</b> perde valor todo dia</span>")}
 {R("li","",D("p71"),"<i>3</i><span>Antes de comemorar, <b>tira a inflação da conta</b></span>")}</ol></div>''')

cena(72, lambda D: f'''<div class="col c">{R("div","k am","0.2","CALCULADORA GRÁTIS")}{R("h1","h lg","0.45","Quanto a inflação já comeu<br>do <b>seu dinheiro</b>?")}
 {R("div","url",D("w:o link está"),"termometrodecrise.com/ferramentas")}{R("p","s",D("w:o link está|0.4"),"O link está na descrição")}</div>''')

cena(73, lambda D: f'''<div class="col c">{R("h1","h lg","0.25","O que mais subiu<br>no <b>seu mercado</b>?")}
 <div class="emj">{R("span","","0.6","🍅")}{R("span","","0.9","🥩")}{R("span","","1.2","☕")}{R("span","","1.5","🥛")}{R("span","","1.8","🍚")}</div>
 {R("p","s","2.2","Conta aqui nos comentários 👇")}</div>''')

LOGO = '''<svg viewBox="24 44 152 100"><g fill="none" stroke-width="18"><path d="M 38.06 117.3 A 62 62 0 0 1 48.3 85.78" stroke="#3B82C4"/><path d="M 51.48 81.4 A 62 62 0 0 1 78.29 61.93" stroke="#7CC3E0"/><path d="M 83.43 60.25 A 62 62 0 0 1 116.57 60.25" stroke="#F2C14E"/><path d="M 121.71 61.93 A 62 62 0 0 1 148.52 81.4" stroke="#EE8A3C"/><path d="M 151.7 85.78 A 62 62 0 0 1 161.94 117.3" stroke="#E5554A"/></g><line x1="100" y1="120" x2="120.44" y2="76.57" stroke="#EEF2F5" stroke-width="9" stroke-linecap="round"/><circle cx="100" cy="120" r="12" fill="#EEF2F5"/></svg>'''

cena(74, lambda D: f"""<div class="col c fim"><div class="lg2 r" data-d="0.2">{LOGO}</div>{R("h1","h lg","0.5","Termômetro de Crise")}
 {R("div","insc","0.9","INSCREVA-SE")}{R("p","s",D("w:segunda quarta"),"Vídeo novo toda <b>segunda, quarta, sexta e domingo</b>")}
 {R("p","s pq",D("p75"),"Não recomendamos: só mostramos a temperatura do mundo.")}
 {R("div","bordao",D("p76"),"Sem alarde. Eu sou só o termômetro!")}</div>""")

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
(P / "tempos.json").write_text(json.dumps({"cta": [round(t, 2) for t, *_ in CTA], "T": TOTAL, "cenas": [(c["a"], c["b"]) for c in cenas], "caps": caps, "paragrafos": [round(pt(i), 2) for i in range(77)]}, ensure_ascii=False, indent=1))
print(f"total {TOTAL:.1f}s = {int(TOTAL//60)}:{TOTAL%60:04.1f}; cenas {len(cenas)}; legendas {len(legs)}")



