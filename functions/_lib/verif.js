// Armazenamento do piloto do Verificador (15/11/2026), no KV do Cloudflare ligado como VERIF.
// Chaves: cli:<codigo> = cadastro da empresa · mes:<codigo>:<AAAA-MM> = conferências do mês.
// Do boleto/Pix guardamos só: resumo do código (hash, para não contar duas vezes), data, nível, valor,
// empresa esperada e o motivo principal. O código completo NÃO é guardado.

export const json = (corpo, status = 200) => new Response(JSON.stringify(corpo), {
  status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }
})

export const semKV = () => json({ ok: false, erro: 'Cadastro ainda não ligado. Use sem cadastro por enquanto.' }, 503)

export const limpo = (s, max = 120) => String(s ?? '').replace(/[\u0000-\u001f<>]/g, '').trim().slice(0, max)

export function novoCodigo () {
  const letras = 'abcdefghjkmnpqrstuvwxyz23456789'
  const b = crypto.getRandomValues(new Uint8Array(10))
  return Array.from(b, (x) => letras[x % letras.length]).join('')
}

export const codigoValido = (c) => /^[a-z2-9]{10}$/.test(String(c || ''))

export async function lerJSON (kv, chave, padrao) {
  const v = await kv.get(chave)
  if (!v) return padrao
  try { return JSON.parse(v) } catch { return padrao }
}

export function iguais (a, b) {
  a = String(a || ''); b = String(b || '')
  if (!a || a.length !== b.length) return false
  let d = 0
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i)
  return d === 0
}
