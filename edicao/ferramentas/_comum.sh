#!/bin/bash
# Funções comuns das ferramentas do editor. O repositório é público: áudio e vídeo só sobem criptografados,
# num ramo temporário que o próprio robô apaga.
REPO=heitorandradesantos-pixel/termometro-de-crise
API=repos/$REPO
CLONE=${CLONE:-/tmp/termometro-ramos}

clone_ramos() {  # um clone separado, só para empurrar ramos temporários
  [ -d "$CLONE/.git" ] || git clone -q --depth 1 "https://github.com/$REPO.git" "$CLONE"
}

empurrar_cifrado() {  # $1 arquivo, $2 nome no ramo, $3 prefixo do ramo, $4 chave → imprime o nome do ramo
  clone_ramos
  local ramo="$3-$(date +%s%N | cut -c1-13)"
  ( cd "$CLONE" && git checkout -q --orphan "$ramo" && git rm -rq --cached . 2>/dev/null
    openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in "$1" -out "$2" -pass "pass:$4"
    git add "$2" && git commit -qm "temporário (apagado pelo robô) [CF-Pages-Skip]" && git push -q origin "$ramo" 2>&1 | grep -vE "remote|warning|fatal" ; rm -f "$2" ) >&2
  echo "$ramo"
}

disparar_e_esperar() {  # $1 workflow, $2 json dos inputs → imprime o id da execução quando termina
  echo "{\"ref\":\"main\",\"inputs\":$2}" | gh api -X POST "$API/actions/workflows/$1/dispatches" --input - >&2
  sleep 8
  local r; r=$(gh api "$API/actions/workflows/$1/runs?per_page=1" --jq '.workflow_runs[0].id')
  until [ "$(gh api "$API/actions/runs/$r" --jq .status)" = completed ]; do sleep 15; done
  echo "$r"
}

log_execucao() {  # $1 id da execução → log do primeiro job
  local j; j=$(gh api "$API/actions/runs/$1/jobs" --jq '.jobs[0].id')
  gh api "$API/actions/jobs/$j/logs"
}
