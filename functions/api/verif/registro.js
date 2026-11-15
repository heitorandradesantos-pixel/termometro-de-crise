// POST /api/verif/registro {c, itens: [{h, nivel, valor, empresa, motivo}]} → guarda as conferências do mês.
// GET /api/verif/registro?c=... → {empresa} (para a página mostrar de quem é a conta)
import { json, semKV, limpo, codigoValido, lerJSON } from '../../_lib/verif.js'

const NIVEIS = new Set(['verde', 'amarelo', 'vermelho'])

export async function onRequestGet ({ request, env }) {
  if (!env.VERIF) return semKV()
  const c = new URL(request.url).searchParams.get('c')
  if (!codigoValido(c)) return json({ ok: false }, 404)
  const cli = await lerJSON(env.VERIF, `cli:${c}`, null)
  return cli ? json({ ok: true, empresa: cli.empresa }) : json({ ok: false }, 404)
}

export async function onRequestPost ({ request, env }) {
  if (!env.VERIF) return semKV()
  let d
  try { d = await request.json() } catch { return json({ ok: false }, 400) }
  if (!codigoValido(d.c) || !Array.isArray(d.itens)) return json({ ok: false }, 400)
  if (!(await env.VERIF.get(`cli:${d.c}`))) return json({ ok: false, erro: 'Cadastro não encontrado.' }, 404)
  const agora = new Date().toISOString(), chave = `mes:${d.c}:${agora.slice(0, 7)}`
  const lista = await lerJSON(env.VERIF, chave, [])
  for (const x of d.itens.slice(0, 200)) {
    const h = String(x.h || '').slice(0, 64)
    if (!/^[0-9a-f]{16,64}$/.test(h) || !NIVEIS.has(x.nivel)) continue
    const item = { h, data: agora, nivel: x.nivel, valor: Math.max(0, Math.min(Number(x.valor) || 0, 1e9)),
      empresa: limpo(x.empresa, 100), motivo: limpo(x.motivo, 240) }
    const i = lista.findIndex((y) => y.h === h)
    if (i >= 0) lista[i] = item; else lista.push(item)
  }
  await env.VERIF.put(chave, JSON.stringify(lista.slice(-3000)))
  return json({ ok: true, total: lista.length })
}
