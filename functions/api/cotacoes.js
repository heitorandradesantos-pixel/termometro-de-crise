// Cotações quase ao vivo para a faixa do topo (Cloudflare Pages Functions).
// O navegador pede /api/cotacoes a cada 30 segundos; esta função busca os preços no Yahoo Finance
// e guarda a resposta por 30 segundos no cache do Cloudflare, então o Yahoo recebe no máximo
// duas consultas por minuto por região do Cloudflare, não uma por visitante.
// Para trocar de fornecedor (com licença), basta reescrever a função `um`.

export const ITENS = [
  ["Ibovespa", "^BVSP", "pontos"], ["Dólar", "BRL=X", "brl"], ["Euro", "EURBRL=X", "brl"],
  ["Dow Jones", "^DJI", "pontos"], ["S&P 500", "^GSPC", "pontos"], ["Nasdaq", "^IXIC", "pontos"],
  ["Bitcoin", "BTC-USD", "usd"], ["Petróleo Brent", "BZ=F", "usd"], ["Ouro", "GC=F", "usd"],
  ["DAX", "^GDAXI", "pontos"], ["Nikkei", "^N225", "pontos"], ["Merval", "^MERV", "pontos"],
];
const TTL = 30;

export async function um(nome, simbolo, tipo, buscar = fetch) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(simbolo)}?range=1d&interval=5m`;
  const r = await buscar(url, { headers: { "User-Agent": "Mozilla/5.0 (compatible; termometro-de-crise/1.0)" } });
  if (!r.ok) throw new Error(`${simbolo}: ${r.status}`);
  const meta = (await r.json())?.chart?.result?.[0]?.meta || {};
  const ultimo = meta.regularMarketPrice, antes = meta.chartPreviousClose ?? meta.previousClose;
  if (!(ultimo > 0) || !(antes > 0)) throw new Error(`${simbolo}: sem preço`);
  const periodo = meta.currentTradingPeriod?.regular, agora = Date.now() / 1000;
  // preço parado há mais de 4 dias (a fonte deixou de atualizar): melhor sumir da faixa do que enganar
  if (meta.regularMarketTime && agora - meta.regularMarketTime > 4 * 86400) throw new Error(`${simbolo}: parado`);
  return {
    nome, tipo, ultimo, variacao_pct: (ultimo / antes - 1) * 100, hora: meta.regularMarketTime || null,
    aberto: Boolean(periodo && agora >= periodo.start && agora <= periodo.end),
  };
}

export async function montar(buscar = fetch) {
  const respostas = await Promise.allSettled(ITENS.map(([nome, simbolo, tipo]) => um(nome, simbolo, tipo, buscar)));
  const itens = respostas.filter((x) => x.status === "fulfilled").map((x) => x.value);
  return { fonte: "Yahoo Finance", gerado: Math.floor(Date.now() / 1000), itens, falhas: respostas.length - itens.length };
}

export async function onRequestGet(context) {
  const cache = caches.default;
  const chave = new Request(new URL("/api/cotacoes", context.request.url).toString());
  const guardada = await cache.match(chave);
  if (guardada) return guardada;
  const dados = await montar();
  const resposta = new Response(JSON.stringify(dados), {
    status: dados.itens.length ? 200 : 502,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": `public, max-age=${TTL}` },
  });
  if (dados.itens.length) context.waitUntil(cache.put(chave, resposta.clone()));
  return resposta;
}
