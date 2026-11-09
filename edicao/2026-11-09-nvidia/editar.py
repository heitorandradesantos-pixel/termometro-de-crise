"""Edição do Reel da Nvidia: corta pausas e as duas frases que saíram erradas, alterna o zoom nos cortes,
põe a legenda (2 a 3 palavras, com números e nomes em amarelo), os cartões com a fonte no terço de cima, o selo
da marca e trata o áudio. Uso: python editar.py"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
ORIGINAL = AQUI / "original.mov"
FIM = 57.20
REMOVER = [(4.27, 6.26), (16.93, 19.12)]  # "Essa investigação é contra você." / "Obviamente que a China vai negar."
LIMIAR_DB, MINIMO_PAUSA = -31, 0.16
FOLGA_ANTES, FOLGA_DEPOIS = 0.06, 0.04
ZOOM = 1.08
AMARELO = "&H4EC1F2&"  # #F2C14E em BGR
DESTAQUES = re.compile(r"\d|%|nvidia|nvdc|jensen|huang|bloomberg|new york|times|pânico|china", re.I)

CARTOES = [  # (início, fim) no vídeo original, texto (com *destaque*), fonte
    (0.00, 4.26, "Tem *Nvidia* na carteira?", ""),
    (9.96, 14.00, "Investigação *independente* sobre o CEO", "Fonte: CNBC"),
    (14.22, 16.95, "Fontes anônimas · *China nega*", "Fonte: The New York Times"),
    (19.14, 22.64, "Conselho: *sem motivo* para crer em vazamento", "Fonte: CNBC"),
    (22.80, 26.74, "Queda de cerca de *5%* antes da abertura", "Fonte: Bloomberg"),
    (26.90, 31.28, "≈ *US$ 225 bilhões* a menos em valor", "Fonte: Bloomberg"),
    (31.66, 35.34, "*NVDC34* = recibo em reais da Nvidia", "BDR negociado na B3"),
    (35.54, 38.44, "Ação lá fora *+* dólar", ""),
    (38.66, 45.00, "Sem prazo nem resultado: a investigação *mal começou*", ""),
    (45.24, 49.04, "*18/11*: reunião pedida pela Câmara dos EUA", "Fonte: South China Morning Post"),
    (49.10, 51.58, "Conteúdo educativo, *não é recomendação*", ""),
    (51.74, FIM, "Grupo no WhatsApp: *link na bio*", ""),
]
TROCAS = {"Conselho": "conselho", "NVIDIA": "Nvidia"}
LIGACOES = {"e", "o", "a", "os", "as", "da", "do", "de", "em", "que", "um", "uns", "com", "na", "no", "nem", "mas", "para",
            "se", "é", "sobre", "dos", "das", "pela", "tipo", "uma", "ter", "não", "já", "mal", "mesmo"}


def pausas() -> list[tuple[float, float]]:
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ORIGINAL), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                           check=True, capture_output=True).stdout
    a = np.frombuffer(bruto, dtype=np.int16).astype(np.float32) / 32768
    n = len(a) // 160
    db = 20 * np.log10(np.sqrt(np.mean(a[:n * 160].reshape(n, 160) ** 2, axis=1)) + 1e-9)
    db = np.convolve(db, np.ones(3) / 3, mode="same")
    saida, i = [], 0
    while i < n:
        if db[i] < LIMIAR_DB:
            j = i
            while j < n and db[j] < LIMIAR_DB:
                j += 1
            if (j - i) * 0.01 >= MINIMO_PAUSA:
                saida.append((i * 0.01 + FOLGA_ANTES, j * 0.01 - FOLGA_DEPOIS))
            i = j
        else:
            i += 1
    return saida


def trechos() -> list[tuple[float, float]]:
    cortes = sorted(REMOVER + [p for p in pausas() if p[1] - p[0] >= 0.08])
    juntos = []
    for a, b in cortes:
        if juntos and a <= juntos[-1][1]:
            juntos[-1] = (juntos[-1][0], max(b, juntos[-1][1]))
        else:
            juntos.append((a, b))
    manter, t = [], 0.0
    for a, b in juntos:
        if a > t + 0.05:
            manter.append((round(t, 3), round(min(a, FIM), 3)))
        t = max(t, b)
    if t < FIM:
        manter.append((round(t, 3), FIM))
    quadro = lambda x: round(round(x * 30) / 30, 4)  # noqa: E731
    return [(quadro(a), quadro(b)) for a, b in manter if quadro(b) - quadro(a) >= 2 / 30]


def mapa(manter):
    def novo(t: float) -> float:
        acc = 0.0
        for a, b in manter:
            if t < a:
                return acc
            if t <= b:
                return acc + (t - a)
            acc += b - a
        return acc
    return novo


def ts(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def legenda(manter, novo) -> str:
    segs = json.loads((AQUI / "transcricao.json").read_text())
    palavras = []
    for s in segs:
        for ini, fim, w, _ in s["palavras"]:
            meio = (ini + fim) / 2
            if any(a <= meio <= b for a, b in REMOVER) or meio > FIM:
                continue
            quebra = bool(re.search(r"[,.?!]$", w))
            w = TROCAS.get(w.strip(",."), w.strip(",."))
            if w == "%" and palavras:
                palavras[-1][2] += "%"
                continue
            palavras.append([novo(ini), novo(fim), w, quebra])
    for nome in (["New", "York", "Times"], ["Jensen", "Huang"]):  # nome próprio não se quebra
        i = 0
        while i <= len(palavras) - len(nome):
            if [w[2] for w in palavras[i:i + len(nome)]] == nome:
                bloco = palavras[i:i + len(nome)]
                palavras[i:i + len(nome)] = [[bloco[0][0], bloco[-1][1], " ".join(nome), bloco[-1][3]]]
            i += 1
    blocos, atual = [], []
    for i, p in enumerate(palavras):
        atual.append(p)
        texto = " ".join(x[2] for x in atual)
        cheio = len(atual) >= 3 or len(texto) >= 16
        solta = p[2].lower() in LIGACOES and i + 1 < len(palavras) and not p[3] and len(atual) < 4 and len(texto) < 22
        if p[3] or (cheio and not solta):
            blocos.append(atual)
            atual = []
    if atual:
        blocos.append(atual)
    linhas = []
    for i, b in enumerate(blocos):
        ini = b[0][0]
        fim = blocos[i + 1][0][0] if i + 1 < len(blocos) else b[-1][1] + 0.3
        fim = min(fim, b[-1][1] + 0.45)
        texto = " ".join((f"{{\\c{AMARELO}}}{w}{{\\c&HFFFFFF&}}" if DESTAQUES.search(w) else w) for _, _, w, _ in b)
        linhas.append(f"Dialogue: 0,{ts(ini)},{ts(fim)},Fala,,0,0,0,,{texto}")
    cab = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Fala,Inter Display Black,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,7,3,2,80,80,600,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return cab + "\n".join(linhas) + "\n"


CARTAO_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:transparent}
.c{display:inline-block;max-width:900px;background:rgba(14,20,27,.92);border:2px solid rgba(124,195,224,.55);border-radius:30px;
padding:26px 34px 24px;font-family:'Inter Display','Inter',sans-serif;color:#EEF2F5;box-shadow:0 12px 40px rgba(0,0,0,.35)}
.t{font-weight:800;font-size:60px;line-height:1.12;letter-spacing:-.01em}
.t em{font-style:normal;color:#F2C14E}
.f{margin-top:12px;font-weight:600;font-size:30px;color:#A9B4C4}
.selo{display:inline-flex;align-items:center;gap:14px;background:rgba(14,20,27,.78);border-radius:999px;padding:10px 22px 10px 14px;
font-family:'Inter Display','Inter',sans-serif;font-weight:800;font-size:28px;letter-spacing:.06em;color:#EEF2F5}
</style></head><body>__CORPO__</body></html>"""
SIMBOLO = ('<svg width="46" height="46" viewBox="0 0 200 200"><g transform="translate(0,6)">'
           '<path d="M 38.06 117.3 A 62 62 0 0 1 48.3 85.78" stroke="#3B82C4" stroke-width="18" fill="none"/>'
           '<path d="M 51.48 81.4 A 62 62 0 0 1 78.29 61.93" stroke="#7CC3E0" stroke-width="18" fill="none"/>'
           '<path d="M 83.43 60.25 A 62 62 0 0 1 116.57 60.25" stroke="#F2C14E" stroke-width="18" fill="none"/>'
           '<path d="M 121.71 61.93 A 62 62 0 0 1 148.52 81.4" stroke="#EE8A3C" stroke-width="18" fill="none"/>'
           '<path d="M 151.7 85.78 A 62 62 0 0 1 161.94 117.3" stroke="#E5554A" stroke-width="18" fill="none"/>'
           '<line x1="100" y1="120" x2="120.44" y2="76.57" stroke="#EEF2F5" stroke-width="10" stroke-linecap="round"/></g></svg>')


def imagens() -> list[Path]:
    import html as h
    pasta = AQUI / "cartoes"
    pasta.mkdir(exist_ok=True)
    paginas = []
    for i, (_, _, texto, fonte) in enumerate(CARTOES):
        t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", h.escape(texto))
        corpo = f'<div class="c"><div class="t">{t}</div>' + (f'<div class="f">{h.escape(fonte)}</div>' if fonte else "") + "</div>"
        (pasta / f"c{i:02d}.html").write_text(CARTAO_HTML.replace("__CORPO__", corpo))
        paginas.append(pasta / f"c{i:02d}")
    (pasta / "selo.html").write_text(CARTAO_HTML.replace("__CORPO__", f'<div class="selo">{SIMBOLO}TERMÔMETRO DE CRISE</div>'))
    paginas.append(pasta / "selo")
    js = """const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({viewport: {width: 1000, height: 600}});
  for (const n of process.argv.slice(2)) { await p.goto('file://' + n + '.html'); const e = await p.$('body > div');
    await e.screenshot({path: n + '.png', omitBackground: true}); }
  await b.close(); })();"""
    (pasta / "fotos.js").write_text(js)
    subprocess.run(["node", str(pasta / "fotos.js"), *map(str, paginas)], check=True, cwd=pasta)
    return [Path(str(p) + ".png") for p in paginas]


def atraso_audio() -> float:
    """O iPhone grava o áudio começando um pouco depois do vídeo (aqui, 0,142 s)."""
    saida = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=start_time",
                            "-of", "csv=p=0", str(ORIGINAL)], check=True, capture_output=True, text=True).stdout
    return float(saida.strip() or 0)


def audio_cortado(manter) -> str:
    """Cortes no áudio contados em amostras (exatos), não em blocos: o som fica preso à imagem do começo ao fim."""
    atraso = round(atraso_audio() * 48000)
    partes = [f"[0:a]aresample=48000,adelay=delays={atraso}S:all=1,asplit={len(manter)}" + "".join(f"[s{i}]" for i in range(len(manter)))]
    for i, (a, b) in enumerate(manter):
        ini, fim = round(a * 48000), round(b * 48000)
        d = (fim - ini) / 48000
        partes.append(f"[s{i}]atrim=start_sample={ini}:end_sample={fim},asetpts=PTS-STARTPTS,"
                      f"afade=t=in:d=0.006,afade=t=out:st={d - 0.006:.4f}:d=0.006[p{i}]")
    return ";".join(partes) + ";" + "".join(f"[p{i}]" for i in range(len(manter))) + f"concat=n={len(manter)}:v=0:a=1[a]"


def montar():
    manter = trechos()
    novo = mapa(manter)
    total = sum(b - a for a, b in manter)
    (AQUI / "legenda.ass").write_text(legenda(manter, novo))
    pngs = imagens()
    # 1) um passe só: o vídeo e o áudio saem dos mesmos trechos (presos ao quadro de 1/30 s), sem acumular atraso
    sel = "+".join(f"between(t,{a:.4f},{b - 0.0005:.4f})" for a, b in manter)
    zooms, t, zoom, primeiro = [], 0.0, False, True
    for a, b in manter:
        if not primeiro and (b - a) >= 0.6:
            zoom = not zoom
        primeiro = False
        if zoom:
            zooms.append((t, t + (b - a)))
        t += b - a
    cw, ch = round(1080 / ZOOM / 2) * 2, round(1920 / ZOOM / 2) * 2
    quando = "+".join(f"between(t,{a:.4f},{b - 0.0005:.4f})" for a, b in zooms) or "0"
    f1 = (f"[0:v]select='{sel}',setpts=N/30/TB,setsar=1,split[base][z];"
          f"[z]crop={cw}:{ch}:{(1080 - cw) // 2}:{int((1920 - ch) * 0.35)},scale=1080:1920,setsar=1[zz];"
          f"[base][zz]overlay=0:0:enable='{quando}'[v];"
          + audio_cortado(manter))
    (AQUI / "filtro1.txt").write_text(f1)
    junto = AQUI / "junto.mov"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ORIGINAL), "-filter_complex_script", str(AQUI / "filtro1.txt"),
                    "-map", "[v]", "-map", "[a]", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                    "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ac", "2", str(junto)], check=True)
    # 2) cartões, selo, legenda e áudio por cima do vídeo já cortado
    entradas, filtro, atual = ["-i", str(junto)], "", "0:v"
    for k, ((ini, fim, _, _), png) in enumerate(zip(CARTOES, pngs[:-1]), start=1):
        a, b = novo(ini), min(novo(fim), total)
        dur = max(0.3, b - a)
        entradas += ["-loop", "1", "-t", f"{dur:.3f}", "-i", str(png)]
        filtro += (f"[{k}:v]format=rgba,fade=t=in:st=0:d=0.18:alpha=1,fade=t=out:st={dur - 0.18:.3f}:d=0.18:alpha=1,"
                   f"setpts=PTS-STARTPTS+{a:.3f}/TB[c{k}];[{atual}][c{k}]overlay=x=(W-w)/2:y=245:eof_action=pass[o{k}];")
        atual = f"o{k}"
    k = len(CARTOES) + 1
    entradas += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(pngs[-1])]
    filtro += (f"[{k}:v]format=rgba,colorchannelmixer=aa=0.9[selo];[{atual}][selo]overlay=x=48:y=150:eof_action=pass[os];"
               f"[os]ass={AQUI / 'legenda.ass'}:fontsdir=/usr/share/fonts/opentype/inter[vf];"
               "[0:a]highpass=f=80,afftdn=nr=8:nf=-42,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,"
               "loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000,"
               "atrim=start=0.025,asetpts=PTS-STARTPTS,apad=pad_dur=0.025[af]")  # os filtros atrasam o som 25 ms: compensa
    (AQUI / "filtro.txt").write_text(filtro)
    cmd = ["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex_script", str(AQUI / "filtro.txt"),
           "-map", "[vf]", "-map", "[af]", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
           "-t", f"{total:.3f}", str(AQUI / "nvidia-editado.mp4")]
    subprocess.run(cmd, check=True)
    print(f"{len(manter)} trechos, {FIM:.1f}s → {total:.1f}s")


if __name__ == "__main__":
    montar()
