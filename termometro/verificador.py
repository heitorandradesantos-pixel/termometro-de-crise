"""Página /verificar/: conferência em lote de boletos e Pix para pequenas empresas (piloto, 15/11/2026).

Roda tudo no navegador com `verificador/motor.mjs`; só o CNPJ (dado público de empresa) vai para /api/cnpj.
Sem Pixel do Meta e sem anúncios: aqui a pessoa cola dado de pagamento. A memória dos fornecedores fica só
no navegador da pessoa (piloto); a versão paga terá conta e banco de dados.
"""
from __future__ import annotations

import html
import shutil
from pathlib import Path

from . import config
from .lp import BASE_CSS

RAIZ = Path(__file__).resolve().parent.parent
MOTOR = RAIZ / "verificador" / "motor.mjs"

CSS = """
.v{max-width:900px;margin:0 auto;padding:22px 16px 60px}
.v h1{font-size:clamp(28px,6vw,42px);margin:8px 0 10px}
.v .sub{color:#C9D3DE;margin:0 0 20px}
.cx{background:#121922;border:1px solid #243140;border-radius:14px;padding:16px;margin:0 0 18px}
.cx h2{font-size:20px;margin:0 0 8px}
.cx p,.cx li{color:#C9D3DE;font-size:16px}
textarea{width:100%;min-height:190px;background:#0B0F14;color:#EEF2F5;border:1px solid #33465A;border-radius:10px;
 padding:12px;font:15px/1.5 ui-monospace,Menlo,monospace}
.bt{display:inline-block;background:#E8473B;color:#fff;border:0;border-radius:10px;padding:13px 22px;font-weight:700;
 font-size:17px;cursor:pointer;margin:12px 8px 0 0}
.bt.cz{background:#243140}
code{background:#0B0F14;padding:2px 6px;border-radius:6px;font-size:14px}
.resumo{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 14px}
.resumo div{flex:1 1 140px;background:#121922;border:1px solid #243140;border-radius:12px;padding:12px}
.resumo b{display:block;font-size:26px;font-family:'Space Grotesk',sans-serif}
.item{border-left:6px solid #888;background:#121922;border-radius:10px;padding:12px 14px;margin:0 0 12px}
.item.verde{border-color:#2FBF71}.item.amarelo{border-color:#F2B233}.item.vermelho{border-color:#E8473B}
.item h3{margin:0 0 4px;font-size:18px}.item .dd{color:#9AA7B4;font-size:14px;margin:0 0 6px;word-break:break-all}
.item ul{margin:6px 0 0;padding-left:20px}.item li{font-size:15px;margin:3px 0;color:#D6DEE6}.item h3{color:#EEF2F5}
.item .mini{font-size:14px;background:#243140;color:#EEF2F5;border:0;border-radius:8px;padding:7px 12px;margin-top:8px;cursor:pointer}
.aviso{font-size:14px;color:#9AA7B4}
"""

CORPO = """<body><main class="v">
<p class="aviso">TERMÔMETRO DE CRISE · VERIFICADOR (versão de teste)</p>
<h1>Confira os boletos e Pix do mês antes de pagar</h1>
<p class="sub">Cole todos de uma vez. Em segundos você vê quais estão 🟢 ok, 🟡 pedem atenção ou 🔴 têm sinal de golpe,
e o motivo de cada um.</p>

<div class="cx"><h2>1. Cole aqui, um por linha</h2>
<p>Formato: <code>código ; empresa que você espera ; valor ; CNPJ ; vencimento</code>. Só o código é obrigatório,
mas quanto mais você preenche, mais a conferência pega.</p>
<textarea id="entrada" spellcheck="false" placeholder="23793381286000000000300000000400100000001000 ; Distribuidora Silva ; 1.250,00 ; 12.345.678/0001-90 ; 10/12/2026
00020126...6304ABCD ; Contabilidade Souza ; 480,00"></textarea>
<button class="bt" id="conferir">Conferir tudo</button><button class="bt cz" id="exemplo">Ver um exemplo</button>
</div>

<div id="saida"></div>

<div class="cx" id="fech"><h2>Fechamento do mês</h2>
<p>Tudo que você confere fica somado aqui (só neste aparelho). No fim do mês, copie o resumo e guarde ou mande no WhatsApp.</p>
<p><label>Nome da empresa: <input id="nomeEmp" style="background:#0B0F14;color:#EEF2F5;border:1px solid #33465A;border-radius:8px;padding:8px;font-size:16px;width:100%;max-width:320px"></label></p>
<div id="mes"></div>
<button class="bt" id="copiar">Copiar resumo pro WhatsApp</button><button class="bt cz" id="zerar">Apagar histórico</button>
<pre id="previa" style="white-space:pre-wrap;background:#0B0F14;border-radius:10px;padding:12px;font-size:15px;color:#D6DEE6"></pre>
</div>

<div class="cx"><h2>O que a gente confere</h2><ul>
<li>Se os dígitos de segurança do código batem (boleto adulterado não bate).</li>
<li>O banco, o valor e o vencimento que ficam escondidos no código, comparados com o que você espera.</li>
<li>No Pix copia e cola: o código de conferência, o tipo de chave e o nome de quem recebe.</li>
<li>O CNPJ de quem recebe na base pública da Receita: se está ativo, desde quando existe e se o nome combina.</li>
<li>Se o fornecedor mudou de banco ou de chave Pix desde a última vez (sinal nº 1 do golpe do e-mail invadido).</li>
</ul></div>

<div class="cx"><h2>Importante</h2>
<p>Isto é uma triagem de risco, não garantia. 🟢 quer dizer que não achamos sinal de problema, não que é 100% seguro.
Antes de pagar, confira no app do seu banco o NOME de quem vai receber.</p>
<p>Os códigos são conferidos no seu próprio navegador e não são guardados por nós. Só o CNPJ, que é dado público,
é consultado na base da Receita. A memória dos fornecedores fica salva apenas neste aparelho.</p>
<p class="aviso">Ferramenta de apoio. Não substitui a conferência no seu banco. · <a href="../privacidade.html" target="_blank" rel="noopener" style="color:#9AA7B4">Política de privacidade</a></p>
</div>
</main>
<script type="module">
import { avaliar, validaCNPJ } from "./motor.mjs";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const so = (s) => String(s || "").replace(/\\D/g, "");
const chaveForn = (n) => "tc_forn_" + String(n || "").normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const lerMem = (n) => { try { return JSON.parse(localStorage.getItem(chaveForn(n)) || "null"); } catch (e) { return null; } };
const gravarMem = (n, v) => { try { localStorage.setItem(chaveForn(n), JSON.stringify(v)); return true; } catch (e) { return false; } };
const valorBR = (s) => { s = String(s || "").replace(/[R$\\s]/g, ""); if (!s) return null;
  if (s.includes(",")) s = s.replace(/\\./g, "").replace(",", "."); const n = Number(s); return isFinite(n) && n > 0 ? n : null; };
const dataBR = (s) => { const m = String(s || "").trim().match(/^(\\d{2})\\/(\\d{2})\\/(\\d{4})$/); return m ? `${m[3]}-${m[2]}-${m[1]}` : null; };
const brl = (n) => n == null ? "-" : n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const cacheCnpj = {};
async function cnpj(c) {
  if (!validaCNPJ(c)) return null;
  if (!(c in cacheCnpj)) cacheCnpj[c] = fetch("/api/cnpj?cnpj=" + c).then((r) => r.ok ? r.json() : null).catch(() => null);
  const d = await cacheCnpj[c]; return d && d.encontrado ? d : null;
}
const ICONE = { verde: "🟢", amarelo: "🟡", vermelho: "🔴" };
const MESES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
const ler = (k, d) => { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } };
const gravar = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
function registrar(res) {
  const h = ler("tc_hist", []), agora = new Date().toISOString();
  res.forEach(({ codigo, empresa, r }) => {
    const id = so(codigo) || codigo;  // o mesmo código conferido duas vezes conta uma vez só
    const i = h.findIndex((x) => x.id === id && x.data.slice(0, 7) === agora.slice(0, 7));
    const item = { id, data: agora, empresa: empresa || "", nivel: r.nivel, valor: r.dados.valor || 0,
      motivo: (r.motivos.find((m) => m.nivel === r.nivel) || {}).texto || "" };
    if (i >= 0) h[i] = item; else h.push(item);
  });
  gravar("tc_hist", h.slice(-2000));
  fechamento();
}
function fechamento() {
  const h = ler("tc_hist", []), mes = new Date().toISOString().slice(0, 7);
  const doMes = h.filter((x) => x.data.slice(0, 7) === mes);
  const n = { verde: 0, amarelo: 0, vermelho: 0 }; let total = 0;
  doMes.forEach((x) => { n[x.nivel]++; total += x.valor; });
  const nome = $("#nomeEmp").value.trim(), m = MESES[Number(mes.slice(5)) - 1];
  let t = `📊 *Fechamento de ${m}${nome ? " – " + nome : ""}*\\n${doMes.length} pagamento(s) conferido(s) · ${brl(total)}\\n` +
    `🟢 ${n.verde} ok · 🟡 ${n.amarelo} atenção · 🔴 ${n.vermelho} barrado(s)`;
  const verm = doMes.filter((x) => x.nivel === "vermelho");
  if (verm.length) t += `\\n\\n🔴 Pediram confirmação antes de pagar (${brl(verm.reduce((a, x) => a + x.valor, 0))}):\\n` +
    verm.slice(0, 5).map((x) => `• ${x.empresa || "Sem nome"} ${x.valor ? brl(x.valor) : ""}: ${x.motivo}`).join("\\n");
  t += "\\n\\nConferido pelo Verificador do Termômetro de Crise. Triagem de risco, não garantia.";
  $("#mes").innerHTML = doMes.length ? "" : "<p>Nada conferido neste mês ainda.</p>";
  $("#previa").textContent = doMes.length ? t : "";
  return doMes.length ? t : "";
}
const TITULO = { verde: "Sem sinal de problema", amarelo: "Pede atenção", vermelho: "Não pague antes de confirmar" };

let exemploAtivo = false;
async function conferir() {
  const linhas = $("#entrada").value.split(/\\n+/).map((l) => l.trim()).filter(Boolean);
  if (!linhas.length) { $("#saida").innerHTML = '<div class="cx"><p>Cole pelo menos um código.</p></div>'; return; }
  $("#saida").innerHTML = '<div class="cx"><p>Conferindo ' + linhas.length + ' código(s)...</p></div>';
  const res = [];
  for (const l of linhas.slice(0, 200)) {
    const [codigo, empresa, valor, doc, venc] = l.split(";").map((x) => (x || "").trim());
    const esperado = { empresa: empresa || null, valor: valorBR(valor), vencimento: dataBR(venc) };
    const mem = empresa ? lerMem(empresa) : null;
    let r = avaliar(codigo, esperado, null, mem);
    let c = so(doc);
    if (!c && r.dados.tipo === "pix" && /^\\d{14}$/.test(so(r.dados.chave)) && validaCNPJ(r.dados.chave)) c = so(r.dados.chave);
    if (doc && !validaCNPJ(c)) r.motivos.push({ nivel: "amarelo", texto: "O CNPJ que você digitou é inválido (dígitos não batem)." });
    const info = c ? await cnpj(c) : null;
    if (info) r = avaliar(codigo, esperado, info, mem);
    if (doc && validaCNPJ(c) && !info) r.motivos.push({ nivel: "amarelo", texto: "Não conseguimos consultar este CNPJ agora (ou ele não existe na Receita)." });
    if (r.motivos.some((m) => m.nivel === "amarelo") && r.nivel === "verde") r.nivel = "amarelo";
    res.push({ codigo, empresa, r, info });
  }
  mostrar(res);
  if (!exemploAtivo) registrar(res);
  exemploAtivo = false;
}

function mostrar(res) {
  const conta = { verde: 0, amarelo: 0, vermelho: 0 }, soma = { verde: 0, amarelo: 0, vermelho: 0 };
  res.forEach(({ r }) => { conta[r.nivel]++; soma[r.nivel] += r.dados.valor || 0; });
  let h = '<div class="resumo">' + ["verde", "amarelo", "vermelho"].map((n) =>
    `<div>${ICONE[n]} ${TITULO[n]}<b>${conta[n]}</b>${brl(soma[n])}</div>`).join("") + "</div>";
  const ordem = { vermelho: 0, amarelo: 1, verde: 2 };
  res.map((x, i) => ({ ...x, i })).sort((a, b) => ordem[a.r.nivel] - ordem[b.r.nivel]).forEach(({ codigo, empresa, r, info, i }) => {
    const d = r.dados, partes = [];
    if (d.tipo === "pix") partes.push("Pix", d.recebedor && "para " + d.recebedor, d.chave && "chave " + d.chave);
    else partes.push(d.tipo === "arrecadacao" ? "Conta/tributo" : "Boleto", d.banco || d.banco_codigo, d.vencimento && "vence " + d.vencimento.split("-").reverse().join("/"));
    partes.push(d.valor && brl(d.valor), info && "CNPJ: " + (info.razao_social || ""));
    h += `<div class="item ${r.nivel}"><h3>${ICONE[r.nivel]} ${esc(empresa || "Pagamento " + (i + 1))}: ${TITULO[r.nivel]}</h3>
      <p class="dd">${esc(partes.filter(Boolean).join(" · "))}</p><ul>${r.motivos.map((m) => `<li>${ICONE[m.nivel]} ${esc(m.texto)}</li>`).join("")}</ul>`;
    if (empresa && r.nivel !== "vermelho" && (d.banco_codigo || d.chave))
      h += `<button class="mini" data-i="${i}">Já confirmei: guardar como padrão de ${esc(empresa)}</button>`;
    h += "</div>";
  });
  h += '<div class="cx"><p><b>Último passo:</b> ' + esc(res[0]?.r.conferencia_final || "") + "</p></div>";
  $("#saida").innerHTML = h;
  $("#saida").querySelectorAll(".mini").forEach((b) => b.onclick = () => {
    const { empresa, r } = res[Number(b.dataset.i)];
    const ok = gravarMem(empresa, { banco_codigo: r.dados.banco_codigo || null, chave: r.dados.chave || null, recebedor: r.dados.recebedor || null });
    b.textContent = ok ? "Guardado neste aparelho ✓" : "Não deu para guardar neste navegador";
    b.disabled = true;
  });
  $("#saida").scrollIntoView({ behavior: "smooth" });
}

$("#conferir").onclick = conferir;
try { $("#nomeEmp").value = localStorage.getItem("tc_nome") || ""; } catch (e) {}
$("#nomeEmp").oninput = () => { try { localStorage.setItem("tc_nome", $("#nomeEmp").value); } catch (e) {} fechamento(); };
$("#copiar").onclick = async () => { const t = fechamento(); if (!t) return;
  try { await navigator.clipboard.writeText(t); $("#copiar").textContent = "Copiado ✓"; }
  catch (e) { $("#copiar").textContent = "Selecione o texto abaixo e copie"; }
  setTimeout(() => $("#copiar").textContent = "Copiar resumo pro WhatsApp", 2500); };
$("#zerar").onclick = () => { gravar("tc_hist", []); fechamento(); };
fechamento();
$("#exemplo").onclick = () => {
  // códigos fictícios, montados só para demonstração
  $("#entrada").value = "34191112282333444555066677788896116610000370000 ; Distribuidora Exemplo ; 3.700,00 ; ; 15/12/2026\\n" +
    "34191112282333444555066677788896116610000370000 ; Gráfica Exemplo ; 2.900,00\\n" +
    "00020126440014br.gov.bcb.pix0122joao.exemplo@email.com5204000053039865406480.005802BR5913JOAO DA SILVA6009SAO PAULO62070503***6304D721 ; Contabilidade Souza ; 480,00";
  exemploAtivo = true;
  conferir();
};
</script></body></html>"""


def pagina() -> str:
    t = "Verificador de boleto e Pix · Termômetro de Crise"
    d = "Cole os boletos e Pix do mês e veja quais têm sinal de golpe antes de pagar."
    url = config.url_publica("verificar/") if config.SITE_URL else ""
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(t)}</title>'
            f'<meta name="description" content="{html.escape(d)}"><meta name="robots" content="noindex">'
            f'{f"<link rel=canonical href={url}>" if url else ""}'
            '<link rel="icon" href="../favicon.svg" type="image/svg+xml"><meta name="theme-color" content="#0B0F14">'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700'
            '&family=IBM+Plex+Sans:wght@400;600;700&display=swap">'
            f'<style>{BASE_CSS}{CSS}</style></head>' + CORPO)


def gerar(saida: Path) -> list[str]:
    """Gera /verificar/ (fora do menu e do Google enquanto é piloto). Não entra no sitemap."""
    pasta = saida / "verificar"
    pasta.mkdir(parents=True, exist_ok=True)
    shutil.copy(MOTOR, pasta / "motor.mjs")
    (pasta / "index.html").write_text(pagina())
    return []
