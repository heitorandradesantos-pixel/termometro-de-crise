#!/usr/bin/env python3
"""Cama de som do vídeo: efeitos nos eventos da tela + trilha CC0 que troca a cada capítulo. Gera audio-completo.m4a."""
import re, json, subprocess, numpy as np
from pathlib import Path

P = Path(__file__).resolve().parent
SR = 44100
S = "/home/claude/termometro-de-crise/edicao/remotion/sfx/"
M = "/home/claude/termometro-de-crise/edicao/remotion/musica/"
G = 0.66  # ganho da cama (trilha + efeitos) em relação à voz

def carrega(p, ch=1):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", p, "-f", "s16le", "-ac", str(ch), "-ar", str(SR), "-"])
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    return a.reshape(-1, ch) if ch > 1 else a

t = json.loads((P / "tempos.json").read_text()); T = t["T"]; cenas = t["cenas"]; caps = t["caps"]; N = int(T * SR)
sons = {n: carrega(S + n + ".wav") for n in ["bordao-hit", "bordao-whoosh", "cartao", "choque", "destaque", "gancho", "impacto", "seguir", "subida", "tick"]}
html = (P / "video.html").read_text()
secs = re.findall(r'<section class="cena" id="c(\d+)">(.*?)</section>', html, flags=re.S)
ev = [(0.25, "gancho", .5)]; capfim = [c["b"] for c in caps]
for c in caps:
    ev += [(c["a"] + 0.02, "bordao-whoosh", .5), (c["a"] + 0.55, "impacto", .28)]
for x in t.get("cta", []):
    ev += [(x + 0.05, "cartao", .5), (x + 1.6, "seguir", .5)]
for j, corpo in secs:
    a = cenas[int(j)][0]
    if not any(abs(a - b) < 0.3 for b in capfim) and int(j) > 0: ev.append((a + 0.08, "cartao", .45))
    for cls, d in re.findall(r'class="((?:chip|card|faixa|num|dea|url|insc|bordao)[^"]*?) r" data-d="([\d.]+)"', corpo):
        d = float(d); k = cls.split()[0]
        if k in ("chip", "card"): ev.append((a + d, "tick", .5))
        elif k == "faixa": ev.append((a + d, "destaque", .36))
        elif k in ("num", "dea"): ev.append((a + d + 0.1, "subida", .24))
        elif k == "url": ev.append((a + d, "destaque", .38))
        elif k == "insc": ev.append((a + d, "seguir", .45))
        elif k == "bordao": ev += [(a + d - 0.15, "bordao-whoosh", .45), (a + d + 0.35, "bordao-hit", .5)]
    for d in re.findall(r'<li class=" r" data-d="([\d.]+)"', corpo): ev.append((a + float(d), "tick", .5))
    for d, dur in re.findall(r'class="cnt"[^>]*data-d="([\d.]+)" data-dur="([\d.]+)"', corpo): ev.append((a + float(d) + float(dur) * 0.9, "choque", .36))
    arcs = re.findall(r'class="arc"[^>]*data-draw="([\d.]+):', corpo)
    if arcs: ev.append((a + min(map(float, arcs)), "subida", .3))
    if "lgraf" in corpo: ev.append((a + 0.6, "subida", .24))
sfx = np.zeros(N + SR, dtype=np.float32)
for tt, n, v in ev:
    s = sons[n]; i = int(max(0, tt) * SR); sfx[i:i + len(s)] += s[:len(sfx) - i] * v
sfx = np.stack([sfx[:N], sfx[:N]], 1)

def faixa(nome):
    a = carrega(M + nome, 2)
    return a / (np.sqrt(np.mean(a ** 2)) + 1e-9) * 10 ** (-30 / 20)
tr = {"h": faixa("suspense-holizna-tension-in-the-air.mp3"), "k": faixa("tensao-komiku-tension.mp3"), "b": faixa("suspense-bartmann-broken-suspense.mp3")}
def trecho(a, n, xf=int(3 * SR)):
    out = a.copy()
    while len(out) < n + xf:
        r = np.linspace(0, 1, xf)[:, None]
        out = np.concatenate([out[:-xf], out[-xf:] * (1 - r) + a[:xf] * r, a[xf:]])
    return out[:n]
cb = [c["a"] for c in caps]
lim = [0] + cb + [T]; blocos = [(lim[i], lim[i + 1], "hkb"[i % 3]) for i in range(len(lim) - 1)]
mus = np.zeros((N, 2), dtype=np.float32); XF = int(2.0 * SR)
for a, b, k in blocos:
    i0 = max(0, int(a * SR) - XF // 2); i1 = min(N, int(b * SR) + XF // 2); seg = trecho(tr[k], i1 - i0).copy()
    r = np.linspace(0, 1, XF)[:, None]
    if i0 > 0: seg[:XF] *= r
    if i1 < N: seg[-XF:] *= (1 - r)
    mus[i0:i1] += seg
env = np.ones(N, dtype=np.float32)
def sobe(a, b, g, rampa=0.35):
    i0, i1, rr = int(a * SR), min(N, int(b * SR)), int(rampa * SR)
    env[i0:i1] = np.maximum(env[i0:i1], g)
    j0 = max(0, i0 - rr); env[j0:i0] = np.maximum(env[j0:i0], np.linspace(1, g, i0 - j0))
    j1 = min(N, i1 + rr); env[i1:j1] = np.maximum(env[i1:j1], np.linspace(g, 1, j1 - i1))
for c in caps: sobe(c["a"], c["b"], 2.6)
sobe(T - 7.2, T, 2.4, 0.8)
mus *= env[:, None]
mus[:int(1.2 * SR)] *= np.linspace(0, 1, int(1.2 * SR))[:, None]; mus[-int(3.5 * SR):] *= np.linspace(1, 0, int(3.5 * SR))[:, None]
cama = np.clip((mus + sfx) * G, -1, 1).astype(np.float32)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", str(P / "cama.wav")], input=cama.tobytes(), check=True)
subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", str(P / "audio-final.m4a"), "-i", str(P / "cama.wav"), "-filter_complex",
                       "[0:a][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]", "-map", "[a]", "-c:a", "aac", "-b:a", "192k", str(P / "audio-completo.m4a")])
(P / "cama.wav").unlink()
print(len(ev), "efeitos; trilha em", len(blocos), "blocos")
