// Envio do Termômetro de Crise para a comunidade do WhatsApp, com o Baileys (código aberto).
//
// O Baileys liga o número como um "aparelho conectado", igual ao WhatsApp Web. Aqui ele roda dentro do robô do
// GitHub: conecta, manda e desconecta. A sessão fica numa pasta (WA_SESSAO) que o robô guarda criptografada entre
// uma execução e outra; nada da sessão, do número ou dos grupos vai para o registro público do robô.
//
//   node enviar.mjs parear              liga o número (WA_NUMERO) com o código de 8 letras (WA_CODIGO)
//   node enviar.mjs teste <envio.json>  manda o envio para o próprio número (conversa "você")
//   node enviar.mjs enviar <envio.json> manda o envio para o grupo de avisos da comunidade
//   node enviar.mjs ouvir <saida.json>  lê os pedidos que o Heitor escreveu na conversa do próprio número
//                                       ("roteiro: tema") desde a última vez e responde que recebeu
//
// envio.json: {"imagem": "card.png", "legenda": "texto da imagem", "textos": ["mensagem 2", ...]}
// Saída: grava <envio.json>.resultado.json com {"ok", "ids", "destino"}.

import fs from 'node:fs'
import path from 'node:path'
import makeWASocket, {
  Browsers, DisconnectReason, delay, fetchLatestBaileysVersion, jidNormalizedUser, useMultiFileAuthState
} from 'baileys'
import pino from 'pino'

const PASTA = process.env.WA_SESSAO || path.resolve('sessao')
const ARQ_DESTINO = path.join(PASTA, 'destino.json')
const NOME_COMUNIDADE = process.env.WA_COMUNIDADE || 'termometro'
const silencio = pino({ level: 'silent' })

// O registro do robô é público. A biblioteca de criptografia escreve chaves da sessão no console: tudo que não for
// mensagem nossa é descartado, e as nossas saem por diga().
const diga = (m) => process.stdout.write(`${m}\n`)
for (const k of ['log', 'info', 'warn', 'error', 'debug', 'trace', 'dir']) console[k] = () => {}
process.stderr.write = () => true
for (const ev of ['uncaughtException', 'unhandledRejection']) {
  process.on(ev, (e) => { diga(`Erro: ${e?.message || e}`); process.exit(1) })
}

const normal = (t) => (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

class Falha extends Error {}

async function conectar ({ numero = '', codigo = '', esperaMs = 120000, aoCriar = null } = {}) {
  fs.mkdirSync(PASTA, { recursive: true })
  let versao
  try { ({ version: versao } = await fetchLatestBaileysVersion()) } catch { /* fica a versão que vem no Baileys */ }
  const fim = Date.now() + esperaMs
  let pedidos = 0
  while (Date.now() < fim) {
    const { state, saveCreds } = await useMultiFileAuthState(PASTA)
    if (!state.creds.registered && !numero) {
      throw new Falha('Este robô ainda não tem um número ligado: rode a ação "parear" primeiro.')
    }
    const sock = makeWASocket({
      auth: state,
      version: versao,
      logger: silencio,
      browser: Browsers.macOS('Chrome'),
      markOnlineOnConnect: false, // o celular continua recebendo as notificações normalmente
      syncFullHistory: false,
      shouldSyncHistoryMessage: () => false,
      generateHighQualityLinkPreview: false,
      getMessage: async () => undefined
    })
    sock.ev.on('creds.update', saveCreds)
    if (aoCriar) aoCriar(sock)
    let pediu = false
    const r = await new Promise((resolve) => {
      const relogio = setTimeout(() => resolve({ erro: 'tempo' }), Math.max(fim - Date.now(), 1000))
      sock.ev.on('connection.update', async (u) => {
        if (u.qr && !state.creds.registered && !pediu) {
          pediu = true
          try {
            await sock.requestPairingCode(numero, codigo || undefined)
            pedidos += 1
            diga(`Pedido de pareamento enviado ao celular (${pedidos}): digite o código em Aparelhos conectados.`)
          } catch (e) {
            diga(`O WhatsApp recusou o pedido de pareamento: ${e.message}`)
          }
        }
        if (u.connection === 'open') { clearTimeout(relogio); resolve({ sock }) }
        if (u.connection === 'close') {
          clearTimeout(relogio)
          resolve({ erro: u.lastDisconnect?.error?.output?.statusCode ?? 'desconhecido' })
        }
      })
    })
    if (r.sock) return r.sock
    try { sock.end(undefined) } catch { /* já fechou */ }
    if (r.erro === DisconnectReason.loggedOut) {
      fs.rmSync(PASTA, { recursive: true, force: true })
      throw new Falha('O WhatsApp desconectou este aparelho (alguém removeu em Aparelhos conectados): é preciso parear de novo.')
    }
    if (r.erro === 'tempo') break
    diga(r.erro === DisconnectReason.restartRequired ? 'Pareado; reconectando com a sessão nova.'
      : `A conexão fechou (código ${r.erro}); tentando de novo.`)
    await delay(2500) // dá tempo da sessão nova ir para o disco
  }
  throw new Falha(numero ? 'O código não foi digitado a tempo no celular.' : 'Não consegui conectar ao WhatsApp a tempo.')
}

function euMesmo (sock) {
  return [sock.user?.id, sock.user?.lid].filter(Boolean).map((j) => jidNormalizedUser(j))
}

async function acharDestino (sock) {
  // O grupo de avisos da comunidade cujo nome tem "termometro". O registro do robô é público: lá só vão contagens
  // e o nome da comunidade escolhida; a lista completa, se precisar, vai só para a conversa do próprio número.
  const grupos = Object.values(await sock.groupFetchAllParticipating())
  let comunidades = []
  try { comunidades = Object.values(await sock.communityFetchAllParticipating()) } catch (e) {
    diga(`Lista de comunidades indisponível (${e.message}).`)
  }
  const pais = new Map([...grupos.filter((g) => g.isCommunity), ...comunidades].map((g) => [g.id, g]))
  diga(`Este número está em ${grupos.length} grupos e ${pais.size} comunidades.`)
  const bate = (t) => normal(t).includes(normal(NOME_COMUNIDADE))
  let alvo = grupos.find((g) => g.isCommunityAnnounce && (bate(g.subject) || bate(pais.get(g.linkedParent)?.subject)))
  let comunidade = alvo ? pais.get(alvo.linkedParent) : [...pais.values()].find((c) => bate(c.subject))
  if (!alvo && comunidade) {
    // o grupo de avisos nem sempre vem na lista de grupos: procura entre os grupos ligados à comunidade
    try {
      const ligados = await sock.communityFetchLinkedGroups(comunidade.id)
      for (const g of ligados?.linkedGroups || []) {
        const meta = await sock.groupMetadata(g.id).catch(() => null)
        if (meta?.isCommunityAnnounce) { alvo = meta; break }
      }
    } catch (e) { diga(`Grupos da comunidade indisponíveis (${e.message}).`) }
    if (!alvo) {
      const meta = await sock.groupMetadata(comunidade.id).catch(() => null)
      if (meta) alvo = meta // a própria comunidade: o WhatsApp entrega no grupo de avisos
    }
  }
  if (!alvo) {
    const nomes = [...pais.values()].map((c) => `• ${c.subject}`).join('\n') || '(nenhuma)'
    await sock.sendMessage(euMesmo(sock)[0], {
      text: `⚠️ Termômetro de Crise: não achei a comunidade com "${NOME_COMUNIDADE}" no nome. Comunidades deste número:\n${nomes}`
    })
    throw new Falha(`Não achei a comunidade "${NOME_COMUNIDADE}" (mandei a lista de comunidades para a conversa do próprio número).`)
  }
  comunidade = comunidade || pais.get(alvo.linkedParent)
  const eu = euMesmo(sock)
  const admin = (alvo.participants || []).some((p) =>
    [p.id, p.lid, p.phoneNumber].filter(Boolean).some((j) => eu.includes(jidNormalizedUser(j))) && p.admin)
  const destino = { jid: alvo.id, nome: (comunidade?.subject || alvo.subject || '').trim(), admin }
  fs.writeFileSync(ARQ_DESTINO, JSON.stringify(destino))
  diga(`Comunidade encontrada: ${destino.nome} (${alvo.isCommunityAnnounce ? 'grupo de avisos' : 'comunidade'}` +
    `${admin ? ', este número é administrador' : ''}).`)
  if (!admin) diga('Atenção: não confirmei que este número é administrador do grupo de avisos.')
  return destino
}

async function mandar (sock, jid, envio) {
  const ids = []
  const confirmados = new Set()
  sock.ev.on('messages.update', (lista) => {
    for (const { key, update } of lista) if ((update?.status ?? 0) >= 2) confirmados.add(key.id) // 2 = servidor recebeu
  })
  if (envio.imagem) {
    const m = await sock.sendMessage(jid, { image: fs.readFileSync(envio.imagem), caption: envio.legenda || undefined })
    ids.push(m.key.id)
  } else if (envio.legenda) {
    ids.push((await sock.sendMessage(jid, { text: envio.legenda })).key.id)
  }
  for (const texto of envio.textos || []) {
    await delay(2000)
    ids.push((await sock.sendMessage(jid, { text: texto })).key.id)
  }
  for (let i = 0; i < 30 && !ids.every((id) => confirmados.has(id)); i++) await delay(1000)
  if (!ids.every((id) => confirmados.has(id))) diga('Aviso: o servidor não confirmou todas as mensagens em 30 s.')
  return ids
}

async function principal () {
  const [acao, arquivo] = process.argv.slice(2)
  const numero = (process.env.WA_NUMERO || '').replace(/\D/g, '')
  const codigo = (process.env.WA_CODIGO || '').toUpperCase().replace(/[^0-9A-Z]/g, '')
  if (codigo && codigo.length !== 8) throw new Falha('O código de pareamento precisa ter 8 letras ou números.')
  const resultado = { ok: false, ids: [], destino: '' }
  let sock
  try {
    if (acao === 'parear') {
      sock = await conectar({ numero, codigo, esperaMs: 9 * 60000 }) // já ligado: só procura a comunidade de novo
      await delay(5000)
      diga('Número ligado ao robô.')
      const d = await acharDestino(sock)
      await sock.sendMessage(euMesmo(sock)[0], {
        text: `✅ Termômetro de Crise conectado. Os envios automáticos vão para a comunidade "${d.nome}".`
      })
      resultado.destino = d.nome
    } else if (acao === 'foto') { // a logo vira a foto da comunidade e do grupo de avisos (o número do robô não muda)
      const img = fs.readFileSync(arquivo)
      sock = await conectar()
      await delay(4000)
      const d = await acharDestino(sock)
      const alvos = [d.jid]
      const meta = await sock.groupMetadata(d.jid).catch(() => null)
      if (meta?.linkedParent) alvos.unshift(meta.linkedParent)
      let feitos = 0
      for (const jid of alvos) {
        try { await sock.updateProfilePicture(jid, img); feitos++ } catch (e) { diga(`Não troquei uma das fotos (${e.message}).`) }
        await delay(2000)
      }
      resultado.ok = feitos > 0
      resultado.destino = d.nome
      diga(`Foto trocada em ${feitos} de ${alvos.length} (comunidade e grupo de avisos).`)
    } else if (acao === 'teste' || acao === 'enviar') {
      const envio = JSON.parse(fs.readFileSync(arquivo, 'utf8'))
      if (envio.imagem && !path.isAbsolute(envio.imagem)) envio.imagem = path.join(path.dirname(arquivo), envio.imagem)
      sock = await conectar()
      await delay(4000)
      let jid
      if (acao === 'teste' || envio.modo === 'teste') { // modo teste: a conversa do próprio número
        jid = euMesmo(sock)[0]
        resultado.destino = 'o próprio número'
      } else {
        const d = fs.existsSync(ARQ_DESTINO) ? JSON.parse(fs.readFileSync(ARQ_DESTINO, 'utf8')) : await acharDestino(sock)
        jid = d.jid
        resultado.destino = d.nome
      }
      resultado.ids = await mandar(sock, jid, envio)
      diga(`Enviado para ${resultado.destino}: ${resultado.ids.length} mensagem(ns).`)
    } else if (acao === 'ouvir') {
      // Os pedidos ficam na conversa "você" do próprio número; o aparelho conectado recebe o que chegou enquanto
      // estava desligado. Só conta mensagem que começa com "roteiro:" e que é mais nova que o último pedido lido.
      const ARQ_ULTIMO = path.join(PASTA, 'ultimo-pedido.json')
      const ultimo = fs.existsSync(ARQ_ULTIMO) ? JSON.parse(fs.readFileSync(ARQ_ULTIMO, 'utf8')).ts
        : Math.floor(Date.now() / 1000) - 6 * 3600
      const vistos = []
      sock = await conectar({
        aoCriar: (s) => s.ev.on('messages.upsert', ({ messages }) => {
          for (const m of messages || []) {
            const texto = m.message?.conversation || m.message?.extendedTextMessage?.text || ''
            const tema = texto.match(/^\s*roteiro\s*[:\-–]\s*(.+)$/is)?.[1]?.trim()
            const ts = Number(m.messageTimestamp || 0)
            if (m.key?.fromMe && tema && ts > ultimo) vistos.push({ ts, tema: tema.slice(0, 300), jid: m.key.remoteJid, id: m.key.id })
          }
        })
      })
      await delay(30000) // tempo para chegarem as mensagens de quando o robô estava desligado
      const eu = euMesmo(sock)
      const unicos = new Map()
      for (const v of vistos) if (eu.includes(jidNormalizedUser(v.jid))) unicos.set(v.id, v)
      const pedidos = [...unicos.values()].sort((a, b) => a.ts - b.ts).map(({ ts, tema }) => ({ ts, tema }))
      if (pedidos.length) {
        fs.writeFileSync(ARQ_ULTIMO, JSON.stringify({ ts: pedidos[pedidos.length - 1].ts }))
        const lista = pedidos.map((p) => `• ${p.tema}`).join('\n')
        await sock.sendMessage(eu[0], { text: `📝 Recebi ${pedidos.length > 1 ? 'os pedidos' : 'o pedido'} de roteiro:\n${lista}\n\nO Plantão confere as fontes e o roteiro chega aqui em uns 10 a 15 minutos.` })
      }
      fs.writeFileSync(arquivo, JSON.stringify({ pedidos }))
      diga(`Pedidos novos: ${pedidos.length}.`)
    } else {
      throw new Falha('Use: parear | teste <envio.json> | enviar <envio.json> | ouvir <saida.json>')
    }
    resultado.ok = true
  } finally {
    if (sock) {
      await delay(3000) // a sessão termina de ir para o disco antes de desconectar
      try { sock.end(undefined) } catch { /* já fechou */ }
    }
    if (arquivo) fs.writeFileSync(`${arquivo}.resultado.json`, JSON.stringify(resultado))
  }
}

principal().then(() => process.exit(0)).catch((e) => {
  diga(e instanceof Falha ? e.message : `Erro: ${e?.message || e}`)
  process.exit(1)
})
