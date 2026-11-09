// Lista de espera da ferramenta para criadores (rascunho em /metricas/).
// Repassa o e-mail a um formulário próprio do Kit (KIT_FORM_METRICAS, nas variáveis do Cloudflare), separado da
// newsletter do Termômetro: quem entra aqui não recebe o Termômetro da Semana. O Kit manda o e-mail de confirmação.
// Sem o formulário configurado, avisa que a lista ainda não abriu (e não guarda nada).
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

function resposta (ok, mensagem, status = 200) {
  return new Response(JSON.stringify({ ok, mensagem }), {
    status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }
  })
}

export async function onRequestPost ({ request, env }) {
  let dados
  try { dados = await request.formData() } catch { dados = new FormData() }
  const email = String(dados.get('email') || '').trim().toLowerCase()
  if (String(dados.get('site') || '')) return resposta(true, 'Pronto! Confira o seu e-mail.')
  if (email.length > 200 || !EMAIL.test(email)) return resposta(false, 'Esse e-mail não parece certo. Confira e tente de novo.', 400)
  const formulario = env && env.KIT_FORM_METRICAS
  if (!formulario) return resposta(false, 'A lista de espera abre em breve. Volte em alguns dias!', 503)
  try {
    const r = await fetch(`https://app.kit.com/forms/${formulario}/subscriptions`, {
      method: 'POST',
      headers: { accept: 'application/json', 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ email_address: email }).toString()
    })
    const j = await r.json().catch(() => ({}))
    if (j.status !== 'success') {
      console.log(`lista-espera: Kit recusou (${r.status})`)
      return resposta(false, 'Não deu certo agora. Tente de novo em alguns minutos.', 502)
    }
    return resposta(true, 'Quase lá! Abra o seu e-mail e confirme a entrada na lista.')
  } catch (erro) {
    console.log(`lista-espera: ${erro.message}`)
    return resposta(false, 'Não deu certo agora. Tente de novo em alguns minutos.', 502)
  }
}

export function onRequestGet ({ request }) {
  return Response.redirect(new URL('/metricas/', request.url).toString(), 302)
}
