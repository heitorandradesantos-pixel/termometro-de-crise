"""Roda o motor mundial com dados reais e imprime o teste histórico (usado pelo robô do GitHub)."""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from termometro import mundo  # noqa: E402

dados_dir, saida = RAIZ / "dados" / "mundo", RAIZ / "saida_mundo"
mundo.coletar(dados_dir)
dados = mundo.rodar(dados_dir, saida)

print("\n== Leitura mais recente por região")
for r in dados["regioes"]:
    print(f"{r['nome']:18s} {r.get('valor')!s:>4} {r.get('nivel', '')!s:9s} {r.get('referencia', '')}  "
          + ", ".join(f"{p['nome']} {p.get('valor')}" for p in r["paises"]))
print(f"Mundo (média)       {dados['mundo']}")
print(f"Brasil              {dados['brasil']}")
print("\n== Teste histórico (pico do termômetro no episódio)")
for linha in dados["teste_historico"]:
    print(f"{linha['episodio']:30s} {linha['maximo']!s:>5}  {linha['mes']}")
print("\n" + json.dumps(dados["teste_historico"], ensure_ascii=False))
