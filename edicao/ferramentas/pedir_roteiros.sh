#!/bin/bash
# Pede roteiros ao Plantão, um de cada vez (o Plantão divide a fila com o Panorama: dois juntos cancelam um).
# Uso: pedir_roteiros.sh temas.txt   (um tema por linha)
#   Notícia: o robô exige fato dos últimos 3 dias.  Assunto do dia a dia sem notícia: comece com "Explicativo: ".
#   Cite a fonte oficial no tema (gov.br, bcb.gov.br, IBGE, FGV...) quando souber: sem fonte de primeira linha, não passa.
#   Cada roteiro aprovado vai sozinho para o WhatsApp do Heitor, com capa. No fim, mostra o motivo de quem não passou.
source "$(dirname "$0")/_comum.sh"
while IFS= read -r tema; do
  [ -z "$tema" ] && continue
  while [ "$(gh api "$API/actions/runs?status=in_progress&per_page=20" --jq '[.workflow_runs[]|select(.path|test("plantao|diario"))]|length')" != "0" ]; do sleep 20; done
  R=$(disparar_e_esperar plantao.yml "$(jq -n --arg t "$tema" '{tema:$t}')")
  MOTIVO=$(log_execucao "$R" | cut -c30- | sed -n '/Plantão (/,/Post job/p' | grep -E "publicado:|·" | head -3 | tr '\n' ' ')
  echo "$(gh api "$API/actions/runs/$R" --jq .conclusion) $R | ${tema:0:60} | $MOTIVO"
done < "$1"
echo FIM
