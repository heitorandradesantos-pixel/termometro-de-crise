#!/usr/bin/env python3
"""Filma video.html quadro a quadro. uso: render.py parte total_partes [fps] | render.py foto t1 t2 ..."""
import sys, json, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

P = Path(__file__).resolve().parent
T = json.loads((P / "tempos.json").read_text())["T"]

def pagina(p):
    b = p.chromium.launch(args=["--disable-gpu", "--force-color-profile=srgb"])
    pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    pg.goto(f"file://{P}/video.html"); pg.wait_for_timeout(800)
    pg.evaluate("document.fonts.ready")
    return b, pg

with sync_playwright() as p:
    if sys.argv[1] == "foto":
        b, pg = pagina(p)
        for t in sys.argv[2:]:
            pg.evaluate(f"seek({float(t)})")
            pg.screenshot(path=str(P / f"foto-{float(t):07.2f}.jpg"), type="jpeg", quality=70)
        b.close(); sys.exit()
    parte, partes = int(sys.argv[1]), int(sys.argv[2]); fps = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    total = int(T * fps); a, z = total * parte // partes, total * (parte + 1) // partes
    tmp, fin = P / f"seg-{parte}.tmp.mp4", P / f"seg-{parte}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(fps), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(fps), str(tmp)], stdin=subprocess.PIPE)
    b, pg = pagina(p)
    for f in range(a, z):
        pg.evaluate(f"seek({f / fps})")
        ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
        if (f - a) % 240 == 0:
            print(f"parte {parte}: {f - a}/{z - a}", flush=True)
    ff.stdin.close(); rc = ff.wait(); b.close()
    if rc == 0: tmp.rename(fin)
    print(f"parte {parte} fim rc={rc}", flush=True)
