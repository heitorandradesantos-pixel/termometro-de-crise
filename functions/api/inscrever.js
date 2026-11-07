// Inscrição na newsletter "O Termômetro da Semana".
// Recebe o e-mail do formulário do site e repassa ao formulário do Kit, que manda o e-mail de confirmação
// (dupla confirmação: só vira inscrito quem clica no link). Nada fica guardado aqui. O campo "site" é uma isca
// invisível: quem o preenche é robô, e recebe um "deu certo" sem que nada seja enviado.
const FORMULARIO = '10157338'
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

function resposta (pedido, ok, mensagem, status = 200) {
  if ((pedido.headers.get('accept') || '').includes('application/json')) {
    return new Response(JSON.stringify({ ok, mensagem }), {
      status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }
    })
  }
  const destino = ok ? '/newsletter/obrigado.html' : '/newsletter/?erro=1'
  return Response.redirect(new URL(destino, pedido.url).toString(), 303)
}

export async function onRequestPost ({ request, env }) {
  let dados
  try { dados = await request.formData() } catch { dados = new FormData() }
  const email = String(dados.get('email') || '').trim().toLowerCase()
  if (String(dados.get('site') || '')) return resposta(request, true, 'Quase lá! Abra o seu e-mail e confirme a inscrição.')
  if (email.length > 200 || !EMAIL.test(email)) {
    return resposta(request, false, 'Esse e-mail não parece certo. Confira e tente de novo.', 400)
  }
  const formulario = (env && env.KIT_FORM_ID) || FORMULARIO
  try {
    const r = await fetch(`https://app.kit.com/forms/${formulario}/subscriptions`, {
      method: 'POST',
      headers: { accept: 'application/json', 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ email_address: email }).toString()
    })
    // o Kit responde 200 mesmo quando recusa: o resultado vem em "status"
    const j = await r.json().catch(() => ({}))
    if (j.status !== 'success') {
      const msg = ((j.errors || {}).messages || []).join(' ')
      console.log(`inscrever: Kit recusou (${r.status}): ${msg || JSON.stringify(j).slice(0, 200)}`)
      if (/invalid/i.test(msg)) return resposta(request, false, 'Esse e-mail não parece certo. Confira e tente de novo.', 400)
      return resposta(request, false, 'Não deu certo agora. Tente de novo em alguns minutos.', 502)
    }
    return resposta(request, true, 'Quase lá! Abra o seu e-mail e clique em "Confirmar inscrição".')
  } catch (erro) {
    console.log(`inscrever: ${erro.message}`)
    return resposta(request, false, 'Não deu certo agora. Tente de novo em alguns minutos.', 502)
  }
}

export function onRequestGet ({ request }) {
  return Response.redirect(new URL('/newsletter/', request.url).toString(), 302)
}
