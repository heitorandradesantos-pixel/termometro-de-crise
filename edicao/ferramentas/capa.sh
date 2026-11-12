#!/bin/bash
# Capa de Reel com texto gigante (Remotion). Uso: capa.sh foto.jpg "Texto com *destaque*" saida.png
# A foto é um quadro do vídeo (1080x1920); o editor escurece (70%) e põe o selo.
set -e
D=$(cd "$(dirname "$0")/../remotion" && pwd); P=$(mktemp -d)
ffmpeg -v error -y -i "$1" -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" -q:v 2 "$P/foto.jpg"
NAV=$(ls /opt/pw-browsers/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell 2>/dev/null | head -1)
( cd "$D" && [ -d node_modules ] || npm ci --silent
  npx remotion still Capa "$(realpath -m "$3")" --props="$(jq -n --arg t "$2" '{foto:"foto.jpg",texto:$t}')" \
    --public-dir="$P" ${NAV:+--browser-executable=$NAV} --log=error )
rm -rf "$P"; echo "$3"
