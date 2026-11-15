// Consulta pública de CNPJ para o Verificador de Boleto e Pix (15/11/2026).
// GET /api/cnpj?cnpj=00000000000191 → {cnpj, razao_social, nome_fantasia, situacao, abertura, atividade, municipio, uf}
// Fonte: BrasilAPI (dados abertos da Receita Federal); se falhar, publica.cnpj.ws. Resposta guardada 1 dia no cache
// do Cloudflare. Só dado público de empresa: nenhum dado do usuário é enviado ou guardado.

const DIA = 86400;
const so = (s) => String(s || "").replace(/\D/g, "");

export function validaCNPJ(c) {
  c = so(c);
  if (c.length !== 14 || /^(\d)\1+$/.test(c)) return false;
  const dv = (n) => {
    const p = n === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    let s = 0;
    for (let i = 0; i < n; i++) s += Number(c[i]) * p[i];
    const r = s % 11;
    return r < 2 ? 0 : 11 - r;
  };
  return dv(12) === Number(c[12]) && dv(13) === Number(c[13]);
}

export async function consultar(cnpj, buscar = fetch) {
  const ua = { headers: { "User-Agent": "termometro-de-crise/1.0 (verificador)", Accept: "application/json" } };
  try {
    const r = await buscar(`https://brasilapi.com.br/api/cnpj/v1/${cnpj}`, ua);
    if (r.status === 404) return { cnpj, encontrado: false };
    if (r.ok) {
      const d = await r.json();
      return { cnpj, encontrado: true, razao_social: d.razao_social || null, nome_fantasia: d.nome_fantasia || null,
        situacao: d.descricao_situacao_cadastral || null, abertura: d.data_inicio_atividade || null,
        atividade: d.cnae_fiscal_descricao || null, municipio: d.municipio || null, uf: d.uf || null };
    }
  } catch (e) { /* tenta a reserva */ }
  const r = await buscar(`https://publica.cnpj.ws/cnpj/${cnpj}`, ua);
  if (r.status === 404) return { cnpj, encontrado: false };
  if (!r.ok) throw new Error(`consulta indisponível (${r.status})`);
  const d = await r.json(), e = d.estabelecimento || {};
  return { cnpj, encontrado: true, razao_social: d.razao_social || null, nome_fantasia: e.nome_fantasia || null,
    situacao: e.situacao_cadastral || null, abertura: e.data_inicio_atividade || null,
    atividade: e.atividade_principal?.descricao || null, municipio: e.cidade?.nome || null, uf: e.estado?.sigla || null };
}

const json = (corpo, status = 200, cache = 0) => new Response(JSON.stringify(corpo), {
  status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": cache ? `public, max-age=${cache}` : "no-store" },
});

export async function onRequestGet(context) {
  const cnpj = so(new URL(context.request.url).searchParams.get("cnpj"));
  if (!validaCNPJ(cnpj)) return json({ erro: "CNPJ inválido" }, 400);
  const cache = caches.default;
  const chave = new Request(`https://cache.termometrodecrise.com/cnpj/${cnpj}`);
  const guardado = await cache.match(chave);
  if (guardado) return guardado;
  try {
    const resp = json(await consultar(cnpj), 200, DIA);
    context.waitUntil(cache.put(chave, resp.clone()));
    return resp;
  } catch (e) {
    return json({ erro: "Consulta de CNPJ fora do ar agora. Tente de novo em alguns minutos." }, 502);
  }
}
