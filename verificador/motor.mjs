// Motor do Verificador de Boleto e Pix (15/11/2026). Roda no navegador e na Cloudflare (sem dependências).
// Faz só conferências objetivas: dígitos verificadores, banco emissor, valor/vencimento escondidos no código,
// leitura do Pix "copia e cola" (BR Code) com CRC, e cruzamento com o que a pessoa diz esperar.
// O resultado é uma TRIAGEM DE RISCO (verde/amarelo/vermelho com motivos), nunca garantia de que é seguro.

export const BANCOS = {
  "001": "Banco do Brasil", "033": "Santander", "041": "Banrisul", "070": "BRB", "077": "Banco Inter",
  "085": "Ailos", "104": "Caixa Econômica Federal", "136": "Unicred", "197": "Stone", "208": "BTG Pactual",
  "212": "Banco Original", "237": "Bradesco", "260": "Nubank", "290": "PagBank (PagSeguro)", "323": "Mercado Pago",
  "336": "C6 Bank", "341": "Itaú", "380": "PicPay", "389": "Mercantil do Brasil", "399": "HSBC", "422": "Safra",
  "403": "Cora", "633": "Rendimento", "655": "Votorantim (BV)", "707": "Daycoval", "735": "Neon", "745": "Citibank",
  "746": "Modal", "748": "Sicredi", "756": "Sicoob", "102": "XP", "364": "Efí (Gerencianet)", "301": "Dock (BPP)",
  "332": "Acesso", "348": "XP (Banco XP)", "450": "Fitbank", "461": "Asaas", "536": "Neon (Pagamentos)",
};

const SEGMENTOS = { 1: "Prefeituras", 2: "Saneamento (água e esgoto)", 3: "Energia elétrica e gás", 4: "Telecomunicações",
  5: "Órgãos governamentais", 6: "Carnês e assemelhados", 7: "Multas de trânsito", 9: "Uso exclusivo do banco" };

const so = (s) => String(s || "").replace(/\D/g, "");

export function mod10(num) {
  let soma = 0, peso = 2;
  for (let i = num.length - 1; i >= 0; i--) {
    let p = Number(num[i]) * peso;
    if (p > 9) p = Math.floor(p / 10) + (p % 10);
    soma += p; peso = peso === 2 ? 1 : 2;
  }
  return (10 - (soma % 10)) % 10;
}

function mod11(num, { boleto = true } = {}) {
  let soma = 0, peso = 2;
  for (let i = num.length - 1; i >= 0; i--) { soma += Number(num[i]) * peso; peso = peso === 9 ? 2 : peso + 1; }
  const resto = soma % 11;
  if (boleto) { const dv = 11 - resto; return dv === 0 || dv === 10 || dv === 11 ? 1 : dv; }
  if (resto === 0 || resto === 1) return 0; // arrecadação
  if (resto === 10) return 1;
  return 11 - resto;
}

// Fator de vencimento: dias desde 07/10/1997; ao chegar em 9999 (21/02/2025) voltou para 1000 (22/02/2025).
function dataDoFator(fator, hoje = new Date()) {
  if (!fator) return null;
  const dia = 86400000;
  const antigo = new Date(Date.UTC(1997, 9, 7) + fator * dia);
  const novo = new Date(Date.UTC(2025, 1, 22) + (fator - 1000) * dia);
  return Math.abs(novo - hoje) < Math.abs(antigo - hoje) ? novo : antigo;
}
const iso = (d) => (d ? d.toISOString().slice(0, 10) : null);

// ------------------------------------------------------------------ BOLETO BANCÁRIO (47 dígitos / 44 no código)
function boletoBancario(dig) {
  let barra, camposOk = true;
  if (dig.length === 47) {
    const c1 = dig.slice(0, 9), c2 = dig.slice(10, 20), c3 = dig.slice(21, 31);
    camposOk = mod10(c1) === Number(dig[9]) && mod10(c2) === Number(dig[20]) && mod10(c3) === Number(dig[31]);
    barra = dig.slice(0, 4) + dig[32] + dig.slice(33, 47) + c1.slice(4) + c2 + c3;
  } else barra = dig;
  const geralOk = mod11(barra.slice(0, 4) + barra.slice(5)) === Number(barra[4]);
  const codBanco = barra.slice(0, 3);
  const fator = Number(barra.slice(5, 9));
  const valor = Number(barra.slice(9, 19)) / 100;
  return { tipo: "boleto_bancario", codigo_barras: barra, digitos_ok: camposOk && geralOk, campos_ok: camposOk, dv_geral_ok: geralOk,
    banco_codigo: codBanco, banco: BANCOS[codBanco] || null, moeda_ok: barra[3] === "9",
    vencimento: iso(dataDoFator(fator)), valor: valor || null };
}

// ------------------------------------------------------------------ ARRECADAÇÃO (contas de consumo, tributos: 48 / 44)
function arrecadacao(dig) {
  let barra, blocosOk = true;
  const ref = dig[2];
  const fn = ref === "6" || ref === "7" ? (s) => mod10(s) : (s) => mod11(s, { boleto: false });
  if (dig.length === 48) {
    const blocos = [0, 1, 2, 3].map((k) => dig.slice(k * 12, k * 12 + 12));
    blocosOk = blocos.every((b) => fn(b.slice(0, 11)) === Number(b[11]));
    barra = blocos.map((b) => b.slice(0, 11)).join("");
  } else barra = dig;
  const geralOk = fn(barra.slice(0, 3) + barra.slice(4)) === Number(barra[3]);
  const valorEfetivo = ref === "6" || ref === "8";
  return { tipo: "arrecadacao", codigo_barras: barra, digitos_ok: blocosOk && geralOk, segmento: SEGMENTOS[Number(barra[1])] || "Outro",
    valor: valorEfetivo ? Number(barra.slice(4, 15)) / 100 || null : null, empresa_codigo: barra.slice(15, 19) };
}

export function lerBoleto(texto) {
  const dig = so(texto);
  if (dig.length === 48 || (dig.length === 44 && dig[0] === "8")) return arrecadacao(dig);
  if (dig.length === 47 || dig.length === 44) return boletoBancario(dig);
  return { tipo: "desconhecido", erro: `O código tem ${dig.length} números. Boleto tem 47 (ou 48 em conta de consumo).` };
}

// ------------------------------------------------------------------ PIX (BR Code / "copia e cola")
export function crc16(str) {
  let crc = 0xffff;
  for (let i = 0; i < str.length; i++) {
    crc ^= str.charCodeAt(i) << 8;
    for (let b = 0; b < 8; b++) crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff;
  }
  return crc.toString(16).toUpperCase().padStart(4, "0");
}

function tlv(s) {
  const out = {}; let i = 0;
  while (i + 4 <= s.length) {
    const id = s.slice(i, i + 2), n = Number(s.slice(i + 2, i + 4));
    if (Number.isNaN(n)) break;
    out[id] = s.slice(i + 4, i + 4 + n); i += 4 + n;
  }
  return out;
}

export function tipoChave(chave) {
  if (!chave) return null;
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(chave)) return "aleatoria";
  if (chave.includes("@")) return "email";
  if (/^\+55\d{10,11}$/.test(chave)) return "telefone";
  if (/^\d{11}$/.test(chave)) return validaCPF(chave) ? "cpf" : "telefone_ou_cpf_invalido";
  if (/^\d{14}$/.test(chave)) return validaCNPJ(chave) ? "cnpj" : "cnpj_invalido";
  return "outra";
}

export function lerPix(texto) {
  const s = String(texto || "").trim();
  if (!s.startsWith("000201")) return { tipo: "desconhecido", erro: "Isso não parece um Pix copia e cola (começa com 000201)." };
  const crcOk = s.length > 8 && crc16(s.slice(0, -4)) === s.slice(-4).toUpperCase();
  const t = tlv(s);
  const conta = tlv(t["26"] || "");
  const extra = tlv(t["62"] || "");
  const chave = conta["01"] || null;
  return { tipo: "pix", crc_ok: crcOk, gui_ok: (conta["00"] || "").toLowerCase() === "br.gov.bcb.pix",
    chave, tipo_chave: tipoChave(chave), dinamico: !!conta["25"], url: conta["25"] || null,
    recebedor: t["59"] || null, cidade: t["60"] || null, valor: t["54"] ? Number(t["54"]) : null,
    descricao: conta["02"] || null, txid: extra["05"] || null };
}

// ------------------------------------------------------------------ CPF / CNPJ
export function validaCPF(c) {
  c = so(c); if (c.length !== 11 || /^(\d)\1+$/.test(c)) return false;
  const dv = (n) => { let s = 0; for (let i = 0; i < n; i++) s += Number(c[i]) * (n + 1 - i); const r = (s * 10) % 11; return r === 10 ? 0 : r; };
  return dv(9) === Number(c[9]) && dv(10) === Number(c[10]);
}
export function validaCNPJ(c) {
  c = so(c); if (c.length !== 14 || /^(\d)\1+$/.test(c)) return false;
  const dv = (n) => { const p = n === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    let s = 0; for (let i = 0; i < n; i++) s += Number(c[i]) * p[i]; const r = s % 11; return r < 2 ? 0 : 11 - r; };
  return dv(12) === Number(c[12]) && dv(13) === Number(c[13]);
}

// ------------------------------------------------------------------ AVALIAÇÃO DE RISCO
const norm = (t) => String(t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9 ]/g, " ")
  .replace(/\b(ltda|sa|s a|me|epp|eireli|cia|companhia|de|da|do|das|dos)\b/g, " ").replace(/\s+/g, " ").trim();
function parecido(a, b) {
  const A = new Set(norm(a).split(" ").filter((x) => x.length > 2)), B = new Set(norm(b).split(" ").filter((x) => x.length > 2));
  if (!A.size || !B.size) return null;
  let comum = 0; for (const x of A) if (B.has(x)) comum++;
  return comum / Math.min(A.size, B.size);
}

/**
 * Avalia um boleto ou Pix.
 * @param {string} codigo  linha digitável, código de barras ou Pix copia e cola
 * @param {object} esperado  o que a pessoa espera: {empresa, valor, vencimento, banco, cnpj}
 * @param {object} cnpjInfo  dados públicos do CNPJ do beneficiário (opcional): {razao_social, nome_fantasia, situacao, abertura}
 * @param {object} fornecedor memória do fornecedor (B2B, opcional): {banco_codigo, chave, recebedor}
 */
export function avaliar(codigo, esperado = {}, cnpjInfo = null, fornecedor = null, hoje = new Date()) {
  const s = String(codigo || "").trim();
  const dados = s.startsWith("000201") ? lerPix(s) : lerBoleto(s);
  const motivos = []; // {nivel: "vermelho"|"amarelo"|"verde", texto}
  const add = (nivel, texto) => motivos.push({ nivel, texto });
  if (dados.tipo === "desconhecido") return { nivel: "amarelo", dados, motivos: [{ nivel: "amarelo", texto: dados.erro }] };

  if (dados.tipo === "pix") {
    if (!dados.crc_ok) add("vermelho", "O código do Pix não fecha a conta de conferência (CRC): foi alterado ou copiado errado.");
    if (!dados.gui_ok) add("vermelho", "O código não segue o padrão Pix do Banco Central.");
    if (dados.tipo_chave === "cpf" || dados.tipo_chave === "telefone" || dados.tipo_chave === "email")
      add("amarelo", `O dinheiro vai para uma chave de ${dados.tipo_chave === "cpf" ? "CPF (pessoa física)" : dados.tipo_chave}. Empresa costuma receber em chave de CNPJ ou aleatória.`);
    if (dados.tipo_chave === "cnpj_invalido" || dados.tipo_chave === "telefone_ou_cpf_invalido") add("vermelho", "A chave Pix tem número de documento inválido.");
    if (esperado.empresa && dados.recebedor) {
      const p = parecido(esperado.empresa, dados.recebedor);
      if (p !== null && p < 0.5) add("vermelho", `Quem recebe é "${dados.recebedor}", não "${esperado.empresa}".`);
      else if (p !== null) add("verde", `O nome de quem recebe (${dados.recebedor}) combina com ${esperado.empresa}.`);
    }
    if (fornecedor?.chave && dados.chave && fornecedor.chave !== dados.chave)
      add("vermelho", "Este fornecedor costumava receber em OUTRA chave Pix. Troca de conta é o sinal nº 1 do golpe do e-mail invadido: confirme por telefone antes de pagar.");
  } else {
    if (!dados.digitos_ok) add("vermelho", "Os dígitos de segurança do código não batem: o boleto foi adulterado ou o número foi digitado errado.");
    if (dados.tipo === "boleto_bancario") {
      if (!dados.banco) add("amarelo", `Banco emissor de código ${dados.banco_codigo} fora da nossa lista: confira no app do seu banco.`);
      if (esperado.banco && dados.banco && parecido(esperado.banco, dados.banco) === 0)
        add("vermelho", `O código diz que o boleto é do ${dados.banco}, mas o impresso diz ${esperado.banco}.`);
      if (dados.vencimento) {
        const dias = (new Date(dados.vencimento) - hoje) / 86400000;
        if (dias < -60) add("amarelo", `Vencimento escondido no código: ${dados.vencimento}, muito antigo. Boleto velho reaproveitado é tática comum.`);
        if (esperado.vencimento && dados.vencimento !== esperado.vencimento)
          add("vermelho", `O vencimento no código (${dados.vencimento}) é diferente do impresso (${esperado.vencimento}).`);
      }
      if (fornecedor?.banco_codigo && fornecedor.banco_codigo !== dados.banco_codigo)
        add("vermelho", `Este fornecedor sempre usou o ${BANCOS[fornecedor.banco_codigo] || fornecedor.banco_codigo}; agora o boleto é do ${dados.banco || dados.banco_codigo}. Confirme por telefone antes de pagar.`);
    }
    if (esperado.valor && dados.valor && Math.abs(Number(esperado.valor) - dados.valor) > 0.009)
      add("vermelho", `O valor escondido no código (R$ ${dados.valor.toFixed(2)}) é diferente do impresso (R$ ${Number(esperado.valor).toFixed(2)}).`);
    if (dados.digitos_ok) add("verde", "Os dígitos de segurança do código conferem.");
  }

  if (cnpjInfo) {
    const sit = norm(cnpjInfo.situacao);
    if (sit && sit !== "ativa") add("vermelho", `O CNPJ de quem recebe está "${cnpjInfo.situacao}" na Receita.`);
    if (cnpjInfo.abertura) {
      const meses = (hoje - new Date(cnpjInfo.abertura)) / (86400000 * 30.4);
      if (meses < 6) add("amarelo", `A empresa que recebe foi aberta há menos de 6 meses (${cnpjInfo.abertura}).`);
    }
    if (esperado.empresa) {
      const p = Math.max(parecido(esperado.empresa, cnpjInfo.razao_social) || 0, parecido(esperado.empresa, cnpjInfo.nome_fantasia) || 0);
      if (p < 0.5) add("vermelho", `Quem recebe é "${cnpjInfo.razao_social}", não "${esperado.empresa}".`);
    }
  }

  const nivel = motivos.some((m) => m.nivel === "vermelho") ? "vermelho" : motivos.some((m) => m.nivel === "amarelo") ? "amarelo" : "verde";
  return { nivel, dados, motivos,
    conferencia_final: "Antes de pagar, veja no app do seu banco o NOME de quem vai receber. Se não for quem você espera, não pague." };
}
