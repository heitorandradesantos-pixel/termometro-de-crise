#!/usr/bin/env bash
# Abre e guarda a sessão do WhatsApp. No cache do GitHub fica só o arquivo criptografado (.sessao-wa.enc);
# a chave é o segredo WA_CHAVE ou, sem ele, uma derivada do segredo da IA (nunca aparece no registro).
set -euo pipefail
ARQ="${WA_ARQ:-.sessao-wa.enc}"
PASTA="${WA_SESSAO:?defina WA_SESSAO}"
if [ -n "${WA_CHAVE:-}" ]; then
  CHAVE="$WA_CHAVE"
elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  CHAVE=$(printf 'termometro-wa-sessao:%s' "$ANTHROPIC_API_KEY" | sha256sum | cut -d' ' -f1)
else
  echo "Sem chave para a sessão (segredo WA_CHAVE ou ANTHROPIC_API_KEY)."
  exit 1
fi
export CHAVE
case "${1:-}" in
  abrir)
    mkdir -p "$PASTA"
    if [ ! -f "$ARQ" ]; then echo "Ainda não há sessão guardada."; exit 0; fi
    if openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:CHAVE -in "$ARQ" | tar -xz -C "$PASTA"; then
      echo "Sessão do WhatsApp aberta."
    else
      rm -rf "$PASTA"; mkdir -p "$PASTA"
      echo "Não consegui abrir a sessão guardada (a chave mudou?): é preciso parear de novo."
    fi
    ;;
  guardar)
    if [ -f "$PASTA/creds.json" ]; then
      tar -cz -C "$PASTA" . | openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:CHAVE -out "$ARQ"
      echo "Sessão guardada (criptografada)."
    else
      rm -f "$ARQ"
      echo "Sem sessão para guardar."
    fi
    ;;
  *) echo "Use: sessao.sh abrir|guardar"; exit 1 ;;
esac
