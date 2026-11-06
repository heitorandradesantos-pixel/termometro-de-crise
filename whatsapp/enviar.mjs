// Envio do Termômetro de Crise para a comunidade do WhatsApp, com o Baileys (código aberto).
//
// O Baileys liga o número como um "aparelho conectado", igual ao WhatsApp Web. Aqui ele roda dentro do robô do
// GitHub: conecta, manda e desconecta. A sessão fica numa pasta (WA_SESSAO) que o robô guarda criptografada entre
// uma execução e outra; nada da sessão, do número ou dos grupos vai para o registro público do robô.
//
//   node enviar.mjs parear              liga o número (WA_NUMERO) com o código de 8 letras (WA_CODIGO)
//   node enviar.mjs teste <envio.json>  manda o envio para o próprio número (conversa "você")
//   node enviar.mjs enviar <envio.json> manda o envio para o grupo de avisos da comunidade
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

const normal = (t) => (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

class Falha extends Error {}

async function conectar ({ numero = '', codigo = '', esperaMs = 120000 } = {}) {
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
    let pediu = false
    const r = await new Promise((resolve) => {
      const relogio = setTimeout(() => resolve({ erro: 'tempo' }), Math.max(fim - Date.now(), 1000))
      sock.ev.on('connection.update', async (u) => {
        if (u.qr && !state.creds.registered && !pediu) {
          pediu = true
          try {
            await sock.requestPairingCode(numero, codigo || undefined)
            pedidos += 1
            console.log(`Pedido de pareamento enviado ao celular (${pedidos}): digite o código em Aparelhos conectados.`)
          } catch (e) {
            console.log(`O WhatsApp recusou o pedido de pareamento: ${e.message}`)
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
    console.log(r.erro === DisconnectReason.restartRequired ? 'Pareado; reconectando com a sessão nova.'
      : `A conexão fechou (código ${r.erro}); tentando de novo.`)
    await delay(2500) // dá tempo da sessão nova ir para o disco
  }
  throw new Falha(numero ? 'O código não foi digitado a tempo no celular.' : 'Não consegui conectar ao WhatsApp a tempo.')
}

function euMesmo (sock) {
  return [sock.user?.id, sock.user?.lid].filter(Boolean).map((j) => jidNormalizedUser(j))
}

async function acharDestino (sock) {
  // O grupo de avisos da comunidade cujo nome tem "termometro". Só nomes de comunidade vão para o registro.
  const grupos = Object.values(await sock.groupFetchAllParticipating())
  const pais = new Map(grupos.filter((g) => g.isCommunity).map((g) => [g.id, g]))
  const avisos = grupos.filter((g) => g.isCommunityAnnounce)
  const nomeDe = (g) => `${g.subject || ''} ${pais.get(g.linkedParent)?.subject || ''}`
  const alvo = avisos.find((g) => normal(nomeDe(g)).includes(normal(NOME_COMUNIDADE)))
  if (!alvo) {
    throw new Falha(`Não achei a comunidade "${NOME_COMUNIDADE}" neste número (${avisos.length} comunidades no total).`)
  }
  const eu = euMesmo(sock)
  const admin = (alvo.participants || []).some((p) =>
    [p.id, p.lid, p.phoneNumber].filter(Boolean).some((j) => eu.includes(jidNormalizedUser(j))) && p.admin)
  const destino = { jid: alvo.id, nome: (pais.get(alvo.linkedParent)?.subject || alvo.subject || '').trim(), admin }
  fs.writeFileSync(ARQ_DESTINO, JSON.stringify(destino))
  console.log(`Comunidade encontrada: ${destino.nome} (grupo de avisos${admin ? ', este número é administrador' : ''}).`)
  if (!admin) console.log('Atenção: só administrador posta no grupo de avisos; promova este número na comunidade.')
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
  if (!ids.every((id) => confirmados.has(id))) console.log('Aviso: o servidor não confirmou todas as mensagens em 30 s.')
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
      if (!numero) throw new Falha('Falta o número (com DDI 55 e DDD, só dígitos).')
      sock = await conectar({ numero, codigo, esperaMs: 9 * 60000 })
      await delay(5000)
      console.log('Número ligado ao robô.')
      const d = await acharDestino(sock)
      await sock.sendMessage(euMesmo(sock)[0], {
        text: `✅ Termômetro de Crise conectado. Os envios automáticos vão para a comunidade "${d.nome}".`
      })
      resultado.destino = d.nome
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
      console.log(`Enviado para ${resultado.destino}: ${resultado.ids.length} mensagem(ns).`)
    } else {
      throw new Falha('Use: parear | teste <envio.json> | enviar <envio.json>')
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
  console.log(e instanceof Falha ? e.message : `Erro: ${e?.message || e}`)
  process.exit(1)
})
