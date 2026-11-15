// GET /api/verif/admin?mes=AAAA-MM com o cabeçalho X-Chave = VERIF_ADMIN (variável secreta no Cloudflare,
// colocada pelo Heitor). Devolve cada empresa cadastrada com o fechamento do mês.
import { json, semKV, lerJSON, iguais } from '../../_lib/verif.js'

export async function onRequestGet ({ request, env }) {
  if (!env.VERIF) return semKV()
  if (!env.VERIF_ADMIN || !iguais(request.headers.get('x-chave'), env.VERIF_ADMIN)) return json({ ok: false, erro: 'Chave errada.' }, 401)
  const pedido = new URL(request.url).searchParams.get('mes')
  const mes = /^\d{4}-\d{2}$/.test(pedido || '') ? pedido : new Date().toISOString().slice(0, 7)
  const clientes = []
  let cursor
  do {
    const r = await env.VERIF.list({ prefix: 'cli:', cursor })
    for (const k of r.keys) {
      const cli = await lerJSON(env.VERIF, k.name, null)
      if (!cli) continue
      cli.itens = await lerJSON(env.VERIF, `mes:${cli.codigo}:${mes}`, [])
      clientes.push(cli)
    }
    cursor = r.list_complete ? null : r.cursor
  } while (cursor)
  return json({ ok: true, mes, clientes })
}
