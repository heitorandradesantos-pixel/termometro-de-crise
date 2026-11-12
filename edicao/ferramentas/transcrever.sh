#!/bin/bash
# Transcreve um ou mais vídeos/áudios de uma vez (faster-whisper no robô, com tempo por palavra).
# Uso: transcrever.sh [-m large-v3|medium] [-p "nomes próprios"] pasta1 [pasta2 ...]
#   cada pasta tem original.mov (ou edite: um .mp4 qualquer com -e) e recebe transcricao.json
#   -e  transcreve o vídeo EDITADO da pasta (*-editado.mp4) e grava qa.json (conferência depois da edição)
set -e
source "$(dirname "$0")/_comum.sh"
MODELO=large-v3; PROMPT=""; EDITADO=0
while getopts "m:p:e" o; do case $o in m) MODELO=$OPTARG ;; p) PROMPT=$OPTARG ;; e) EDITADO=1 ;; esac; done
shift $((OPTIND-1))
TMP=$(mktemp -d); ffmpeg -v error -y -f lavfi -t 2 -i anullsrc=r=16000:cl=mono "$TMP/s.wav"
ENTRADAS=(); FILTRO=""; i=0; DURS=()
for p in "$@"; do
  if [ $EDITADO = 1 ]; then f=$(ls "$p"/*-editado.mp4 | head -1); else f="$p/original.mov"; fi
  ffmpeg -v error -y -i "$f" -vn -ac 1 -ar 16000 "$TMP/a$i.wav"
  DURS+=("$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMP/a$i.wav")")
  ENTRADAS+=(-i "$TMP/a$i.wav"); [ $i -gt 0 ] && { ENTRADAS+=(-i "$TMP/s.wav"); }
  i=$((i+1))
done
n=$(( ${#ENTRADAS[@]} / 2 )); FILTRO=""; for k in $(seq 0 $((n-1))); do FILTRO+="[$k]"; done
ffmpeg -v error -y "${ENTRADAS[@]}" -filter_complex "${FILTRO}concat=n=$n:v=0:a=1" -c:a libopus -b:a 48k "$TMP/juntos.ogg"
CHAVE=$(openssl rand -hex 24)
RAMO=$(empurrar_cifrado "$TMP/juntos.ogg" audio.enc tmp-transcricao "$CHAVE")
R=$(disparar_e_esperar transcrever.yml "$(jq -n --arg r "$RAMO" --arg c "$CHAVE" --arg m "$MODELO" --arg t "$PROMPT" '{ramo:$r,chave:$c,modelo:$m,texto:$t}')")
log_execucao "$R" | sed -n '/TRANSCRICAO_INICIO/,/TRANSCRICAO_FIM/p' | sed '1d;$d' | sed 's/^[0-9T:.Z-]* //' > "$TMP/juntos.json"
python3 - "$TMP/juntos.json" "$EDITADO" "${DURS[*]}" "$@" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); editado = sys.argv[2] == "1"; durs = [float(x) for x in sys.argv[3].split()]
a = 0
for pasta, dur in zip(sys.argv[4:], durs):
    t = lambda x: round(x - a, 2)
    segs = [{"ini": t(s["ini"]), "fim": t(s["fim"]), "texto": s["texto"],
             "palavras": [[t(w[0]), t(w[1]), w[2], w[3]] for w in s["palavras"]]}
            for s in d if a - 0.5 <= (s["ini"] + s["fim"]) / 2 < a + dur + 0.5]
    json.dump(segs, open(f"{pasta}/{'qa' if editado else 'transcricao'}.json", "w"), ensure_ascii=False)
    print(f"=== {pasta}")
    for s in segs:
        print(" ".join(f"{w[2]}[{w[0]:.2f}{'?' + str(round(w[3], 2)) if w[3] < 0.6 else ''}]" for w in s["palavras"])
              if not editado else f"{s['ini']:.1f} {s['texto']}")
    a += dur + 2
PY
rm -rf "$TMP"
