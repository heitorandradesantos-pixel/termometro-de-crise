// POST /api/verif/cadastro {nome, empresa, whatsapp, cnpj?, aceite: true} → {ok, codigo}
import { json, semKV, limpo, novoCodigo } from '../../_lib/verif.js'

export async function onRequestPost ({ request, env }) {
  if (!env.VERIF) return semKV()
  let d
  try { d = await request.json() } catch { return json({ ok: false, erro: 'Dados inválidos.' }, 400) }
  if (d.site) return json({ ok: true, codigo: 'aaaaaaaaaa' }) // armadilha para robô
  const nome = limpo(d.nome, 80), empresa = limpo(d.empresa, 100)
  const whatsapp = String(d.whatsapp || '').replace(/\D/g, '').slice(0, 13)
  const cnpj = String(d.cnpj || '').replace(/\D/g, '').slice(0, 14)
  if (!nome || !empresa) return json({ ok: false, erro: 'Preencha seu nome e o nome da empresa.' }, 400)
  if (whatsapp.length < 10) return json({ ok: false, erro: 'Confira o WhatsApp com DDD.' }, 400)
  if (d.aceite !== true) return json({ ok: false, erro: 'Para continuar, aceite os termos.' }, 400)
  const codigo = novoCodigo()
  await env.VERIF.put(`cli:${codigo}`, JSON.stringify({
    codigo, nome, empresa, whatsapp: whatsapp.length <= 11 ? '55' + whatsapp : whatsapp, cnpj,
    aceite: { termos: true, whatsapp: true, em: new Date().toISOString() }, criado: new Date().toISOString()
  }))
  return json({ ok: true, codigo })
}
