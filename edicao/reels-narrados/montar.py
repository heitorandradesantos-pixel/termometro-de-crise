#!/usr/bin/env python3
"""Monta a pasta de um Reel narrado (vertical 1080x1920) a partir de tts.txt + cenas.py. uso: montar.py pasta"""
import sys, re
from pathlib import Path
D = Path(sys.argv[1]).resolve(); B = Path("/home/claude/yt/v3")
src = (B / "build.py").read_text().split("\n")
head = "\n".join(src[:158])
i0 = head.index("CAPS = ["); i1 = head.index("def norm")
head = head[:i0] + "CAPS = []\n\n" + head[i1:]
head = head.replace("LEAD, PAUSA, CAUDA = 0.8, 1.5, 8.0", "LEAD, PAUSA, CAUDA = 0.25, 1.5, 2.6")
a = head.index('texto = (P.parent'); b = head.index('pal = []')
head = head[:a] + 'paras = (P / "tts.txt").read_text().strip().split("\\n\\n")\n' + head[b:]
logo = next(l for l in src if l.startswith("LOGO = "))
k = next(i for i, l in enumerate(src) if l.startswith("# monta as cenas"))
tail = "\n".join(src[k:])
a = tail.index("CTA = ["); b = tail.index("dados = {")
tail = tail[:a] + "CTA = []\n" + tail[b:]
tail = tail.replace("range(83)", "range(len(paras))")
CSS = r'''
CSS_EXTRA = """
html,body{width:1080px;height:1920px}
#topo{top:150px;left:60px;right:60px}#cap{display:none}#cta{display:none!important}
.cena{top:240px;width:1080px;height:1180px}
.col,.col.c,.col.e{padding:0 58px;gap:30px;height:100%;box-sizing:border-box;zoom:1.1}
.k{font-size:32px;letter-spacing:4px}
.h{font-size:64px}.h.md{font-size:60px}.h.lg{font-size:80px;line-height:1.08}.h.xl{font-size:98px;letter-spacing:-2.5px}.h.xxl{font-size:170px}
.s{font-size:46px;max-width:940px}.s.lgs{font-size:54px}.s.pq{font-size:34px}
.src{font-size:26px;max-width:900px;line-height:1.3}
.num{font-size:250px;letter-spacing:-8px}.num.md{font-size:176px;letter-spacing:-6px}.num.pqn{font-size:120px;letter-spacing:-3px;color:#8A98A8}
.chip{font-size:42px;padding:18px 36px}.chip.gr{font-size:58px;padding:26px 46px}
.chip.am{background:#F2C14E;color:#0E141B;border-color:#F2C14E}.chip.vm{background:#E5554A;border-color:#E5554A}
.faixa{font-size:48px;padding:26px 36px;max-width:900px}
.lista li{font-size:50px}
.tres{gap:40px}.tres li{font-size:50px;gap:28px;text-align:left}.tres i{width:96px;height:96px;font-size:60px}
.barras,.barras.lg{width:940px;gap:34px}.lin{flex-wrap:wrap;gap:12px 24px;font-size:50px}
.lin .rot,.barras.lg .rot{width:940px;text-align:left;font-size:40px;font-weight:700;color:#EEF2F5}
.lin .tr{height:92px}.lin .val,.barras.lg .val{width:250px;font-size:56px}
.bar.vmb{background:linear-gradient(90deg,#B93B32,#F0776C)!important}
.seta2{font-size:110px;font-weight:900;color:#F2C14E;line-height:.8}
.emo{font-size:190px;line-height:1}
.vmt{color:#F0776C!important}
.fim{gap:26px}.lg2 svg{width:380px;height:250px}.bordao{font-size:60px}.insc{font-size:46px}
#leg{bottom:395px}#leg span{max-width:920px;font-size:52px;padding:14px 30px}
"""
'''
cenas = (D / "cenas.py").read_text()
fim = '''
cena(len(paras) - 1, lambda D: f"""<div class="col c fim"><div class="lg2 r" data-d="0.15">{LOGO}</div>{R("h1","h lg","0.3","Termômetro de Crise")}
 {R("div","insc","0.6","SIGA @termometrodecrise")}{R("p","s pq","0.8","Conteúdo educativo. Não é recomendação de investimento.")}
 {R("div","bordao","0.5","Sem alarde.<br>Eu sou só o termômetro!")}</div>""")
'''
(D / "build.py").write_text(head + "\n" + CSS + "\nCENAS = []\ndef cena(p, corpo):\n    CENAS.append([p, corpo])\n\n" + cenas + "\n" + logo + "\n" + fim + "\n" + tail + "\n")
(D / "modelo.html").write_text((B / "modelo.html").read_text())
r = (B / "render.py").read_text().replace('"width": 1920, "height": 1080', '"width": 1080, "height": 1920')
(D / "render.py").write_text(r)
s = (B / "som.py").read_text().replace("sobe(T - 7.2, T, 2.4, 0.8)", "sobe(T - 3.0, T, 1.8, 0.6)")
(D / "som.py").write_text(s)
print("ok", D)
