import test from "node:test";
import assert from "node:assert/strict";
import { avaliar, lerBoleto, lerPix, crc16, mod10, validaCNPJ } from "./motor.mjs";

// monta um boleto bancário válido a partir dos campos (para testar sem usar boleto real de ninguém)
function mod11b(n) { let s = 0, p = 2; for (let i = n.length - 1; i >= 0; i--) { s += Number(n[i]) * p; p = p === 9 ? 2 : p + 1; }
  const dv = 11 - (s % 11); return dv === 0 || dv === 10 || dv === 11 ? 1 : dv; }
function montar(banco, fator, valorCent, livre) {
  const sem = banco + "9" + String(fator).padStart(4, "0") + String(valorCent).padStart(10, "0") + livre;
  const barra = sem.slice(0, 4) + mod11b(sem) + sem.slice(4);
  const c1 = barra.slice(0, 4) + barra.slice(19, 24), c2 = barra.slice(24, 34), c3 = barra.slice(34, 44);
  return c1 + mod10(c1) + c2 + mod10(c2) + c3 + mod10(c3) + barra[4] + barra.slice(5, 19);
}
const HOJE = new Date("2026-11-15T12:00:00Z");
// fator 1000 = 22/02/2025; 15/12/2026 = 1000 + 661
const LINHA = montar("341", 1661, 125090, "1234567890123456789012345");

test("lê boleto válido: banco, valor e vencimento", () => {
  const b = lerBoleto(LINHA);
  assert.equal(b.digitos_ok, true); assert.equal(b.banco, "Itaú"); assert.equal(b.valor, 1250.9); assert.equal(b.vencimento, "2026-12-15");
});
test("número trocado na linha digitável → vermelho", () => {
  const ruim = LINHA.slice(0, 12) + ((Number(LINHA[12]) + 1) % 10) + LINHA.slice(13);
  assert.equal(avaliar(ruim, {}, null, null, HOJE).nivel, "vermelho");
});
test("valor impresso diferente do código → vermelho", () => {
  assert.equal(avaliar(LINHA, { valor: 1500 }, null, null, HOJE).nivel, "vermelho");
});
test("boleto ok e valor batendo → verde", () => {
  const r = avaliar(LINHA, { valor: 1250.9, vencimento: "2026-12-15" }, null, null, HOJE);
  assert.equal(r.nivel, "verde", JSON.stringify(r.motivos));
});
test("fornecedor trocou de banco → vermelho", () => {
  assert.equal(avaliar(LINHA, {}, null, { banco_codigo: "237" }, HOJE).nivel, "vermelho");
});
test("CNPJ inativo ou nome diferente → vermelho; aberto há pouco → amarelo", () => {
  assert.equal(avaliar(LINHA, { empresa: "Claro" }, { razao_social: "JOAO DA SILVA 12345678900", situacao: "ATIVA", abertura: "2020-01-01" }, null, HOJE).nivel, "vermelho");
  assert.equal(avaliar(LINHA, {}, { razao_social: "X", situacao: "BAIXADA" }, null, HOJE).nivel, "vermelho");
  assert.equal(avaliar(LINHA, {}, { razao_social: "X", situacao: "ATIVA", abertura: "2026-09-01" }, null, HOJE).nivel, "amarelo");
});

function pix({ chave, nome, cidade, valor }) {
  const f = (id, v) => id + String(v.length).padStart(2, "0") + v;
  const conta = f("00", "br.gov.bcb.pix") + f("01", chave);
  let p = f("00", "01") + f("26", conta) + f("52", "0000") + f("53", "986") + (valor ? f("54", valor) : "") + f("58", "BR") + f("59", nome) + f("60", cidade) + f("62", f("05", "***")) + "6304";
  return p + crc16(p);
}
test("Pix válido de empresa (chave CNPJ) com nome certo → verde", () => {
  const p = pix({ chave: "11222333000181", nome: "CLARO SA", cidade: "SAO PAULO", valor: "99.90" });
  assert.equal(validaCNPJ("11222333000181"), true);
  const r = avaliar(p, { empresa: "Claro" }, null, null, HOJE);
  assert.equal(lerPix(p).valor, 99.9); assert.equal(r.nivel, "verde", JSON.stringify(r.motivos));
});
test("Pix alterado (CRC) → vermelho; chave CPF → amarelo; nome errado → vermelho", () => {
  const p = pix({ chave: "11222333000181", nome: "CLARO SA", cidade: "SAO PAULO" });
  assert.equal(avaliar(p.replace("CLARO SA", "CLARA SA"), {}, null, null, HOJE).nivel, "vermelho");
  assert.equal(avaliar(pix({ chave: "52998224725", nome: "MARIA SOUZA", cidade: "RECIFE" }), {}, null, null, HOJE).nivel, "amarelo");
  assert.equal(avaliar(pix({ chave: "11222333000181", nome: "MARIA SOUZA", cidade: "RECIFE" }), { empresa: "Claro" }, null, null, HOJE).nivel, "vermelho");
});
test("código com tamanho errado → amarelo com explicação", () => {
  const r = avaliar("123", {}, null, null, HOJE);
  assert.equal(r.nivel, "amarelo"); assert.match(r.motivos[0].texto, /47/);
});
