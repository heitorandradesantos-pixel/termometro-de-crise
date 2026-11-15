// O verificador virou produto próprio (15/11/2026): quem tiver o link antigo vai para overificador.com.br.
export function onRequest () {
  return Response.redirect('https://overificador.com.br/app/', 301)
}
