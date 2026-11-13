"""Funil de venda do "Manual do Investidor", servido pelo próprio site.

/quiz/   : quiz de 8 perguntas (mais 1 de perfil) contraintuitivas ("o que o gerente não te conta") que termina na página de venda.
/manual/ : página de venda longa, SEM fugas (sem menu, rodapé ou links pro resto do site): o único caminho é o
           botão de compra (checkout na Kiwify). Pedido do Heitor (13/11/2026) para rodar anúncios.

Inimigo em comum: "o sistema que lucra com a sua confusão" (meta de venda, comissão, letra miúda). Nunca citamos
banco, corretora ou pessoa pelo nome. Conteúdo educativo: nada de promessa de ganho nem recomendação de investimento.
Números da conta de exemplo: Selic 13,75% (Copom de 04/11/2026), CDI ≈ Selic − 0,10, poupança 0,5% a.m. + TR.
"""

import html
import json
import shutil
from pathlib import Path

from . import config

PASTA = Path(__file__).resolve().parent.parent / "lp"
CHECKOUT_MANUAL = "https://pay.kiwify.com.br/0k8fopI"
PRECO_MANUAL = "19,90"

SIMBOLO = ('<svg width="26" height="26" viewBox="0 0 200 200" aria-hidden="true"><g transform="translate(0,6)">'
           '<path d="M 38.06 117.3 A 62 62 0 0 1 48.3 85.78" stroke="#3B82C4" stroke-width="18" fill="none"/>'
           '<path d="M 51.48 81.4 A 62 62 0 0 1 78.29 61.93" stroke="#7CC3E0" stroke-width="18" fill="none"/>'
           '<path d="M 83.43 60.25 A 62 62 0 0 1 116.57 60.25" stroke="#F2C14E" stroke-width="18" fill="none"/>'
           '<path d="M 121.71 61.93 A 62 62 0 0 1 148.52 81.4" stroke="#EE8A3C" stroke-width="18" fill="none"/>'
           '<path d="M 151.7 85.78 A 62 62 0 0 1 161.94 117.3" stroke="#E5554A" stroke-width="18" fill="none"/>'
           '<line x1="100" y1="120" x2="120.44" y2="76.57" stroke="#EEF2F5" stroke-width="10" stroke-linecap="round"/>'
           '<circle cx="100" cy="120" r="12" fill="#EEF2F5"/></g></svg>')

BASE_CSS = """
*{box-sizing:border-box}html,body{margin:0;padding:0}
body{background:#0B0F14;color:#EEF2F5;font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:18px;line-height:1.55;
 -webkit-font-smoothing:antialiased}
h1,h2,h3,.titulo{font-family:'Space Grotesk',system-ui,sans-serif;letter-spacing:-.02em;line-height:1.08;margin:0}
a{color:inherit}
.marca{display:flex;align-items:center;justify-content:center;gap:10px;padding:18px 16px 6px;font-family:'Space Grotesk',sans-serif;
 font-weight:700;font-size:13px;letter-spacing:.14em;color:#AEBAC7}
.amarelo{color:#F2C14E}.vermelho{color:#FF6B5E}
.botao{display:block;width:100%;max-width:520px;margin:0 auto;text-align:center;background:#F2C14E;color:#0E141B;font-weight:800;
 font-size:20px;text-decoration:none;padding:19px 22px;border-radius:14px;border:0;cursor:pointer;
 box-shadow:0 12px 34px rgba(242,193,78,.28);font-family:'Space Grotesk',sans-serif}
.botao:hover{filter:brightness(1.06)}
.legal{max-width:760px;margin:40px auto 0;padding:0 18px 40px;font-size:12px;color:#7D8B99;text-align:center;line-height:1.5}
"""


def _cabeca(titulo: str, descricao: str, caminho: str, css: str, imagem: str = "manual/produto.webp") -> str:
    url = config.url_publica(caminho) if config.SITE_URL else ""
    og = f"{config.SITE_URL}/{imagem}" if config.SITE_URL else ""
    t, d = html.escape(titulo), html.escape(descricao)
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t}</title><meta name="description" content="{d}">
<meta property="og:title" content="{t}"><meta property="og:description" content="{d}"><meta property="og:type" content="website">
{f'<meta property="og:url" content="{url}"><link rel="canonical" href="{url}">' if url else ''}
{f'<meta property="og:image" content="{og}"><meta name="twitter:card" content="summary_large_image">' if og else ''}
<link rel="icon" href="../favicon.svg" type="image/svg+xml"><meta name="theme-color" content="#0B0F14">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>{BASE_CSS}{css}</style></head>"""


def _legal() -> str:
    # único link fora do funil: a política de privacidade (exigida para anúncios), em nova aba
    return (f'<p class="legal">{html.escape(config.AVISO)}<br>Termômetro de Crise · @termometrodecrise · '
            f'<a href="../privacidade.html" target="_blank" rel="noopener">Política de privacidade</a></p>')


# ===================================================================================== PÁGINA DE VENDA
CSS_LP = """
.lp{max-width:760px;margin:0 auto;padding:0 18px}
.topo-alerta{background:#3A1414;color:#FFD9D4;text-align:center;font-size:14px;font-weight:600;padding:9px 14px}
.heroi{text-align:center;padding:26px 0 8px}
.heroi h1{font-size:clamp(34px,7.4vw,56px);font-weight:700}
.heroi .sub{font-size:20px;color:#C9D3DE;margin:18px auto 22px;max-width:640px}
.preco{display:flex;align-items:baseline;justify-content:center;gap:10px;margin:0 0 14px}
.preco b{font-size:44px;font-family:'Space Grotesk',sans-serif}.preco span{color:#AEBAC7;font-weight:600}
.miudo{font-size:14px;color:#9AA7B4;text-align:center;margin-top:10px}
.carta{margin-top:46px}
.carta h2{font-size:clamp(28px,5.6vw,40px);margin:46px 0 14px}
.carta p{margin:0 0 16px;color:#D6DEE6}
.carta p b{color:#fff}
.inimigos{display:grid;gap:14px;margin:22px 0}
.inimigo{border:1px solid rgba(255,107,94,.35);background:rgba(255,107,94,.06);border-radius:16px;padding:18px 20px}
.inimigo h3{font-size:22px;margin-bottom:6px}
.inimigo p{margin:0;font-size:17px}
.conta{border-radius:18px;background:#121A22;border:1px solid rgba(255,255,255,.08);padding:22px;margin:22px 0}
.conta .linha{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px dashed rgba(255,255,255,.12)}
.conta .linha:last-of-type{border:0}
.conta .linha b{white-space:nowrap;font-family:'Space Grotesk',sans-serif;font-size:22px}
.conta .dif{margin-top:12px;text-align:center;font-family:'Space Grotesk',sans-serif;font-size:26px;font-weight:700}
.conta small{display:block;margin-top:10px;color:#8796A5;font-size:13px;text-align:center}
.lista{list-style:none;padding:0;margin:18px 0;display:grid;gap:10px}
.lista li{background:rgba(255,255,255,.04);border-radius:12px;padding:12px 14px 12px 46px;position:relative}
.lista li:before{content:"✓";position:absolute;left:14px;top:11px;width:22px;height:22px;border-radius:99px;background:#F2C14E;color:#0E141B;
 font-weight:900;text-align:center;line-height:22px;font-size:14px}
.paginas{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}
.paginas img{width:100%;border-radius:8px;background:#fff}
.nao{list-style:none;padding:0;margin:14px 0}.nao li{padding:6px 0 6px 32px;position:relative;color:#D6DEE6}
.nao li:before{content:"✋";position:absolute;left:0}
.garantia{display:flex;gap:16px;align-items:center;border:2px solid #F2C14E;border-radius:18px;padding:18px;margin:26px 0}
.garantia .sel{flex:none;width:84px;height:84px;border-radius:99px;background:#F2C14E;color:#0E141B;font-weight:800;display:flex;
 flex-direction:column;align-items:center;justify-content:center;line-height:1;font-family:'Space Grotesk',sans-serif}
.garantia .sel b{font-size:30px}.garantia p{margin:0}
details{border-bottom:1px solid rgba(255,255,255,.1);padding:14px 0}
summary{font-weight:700;cursor:pointer}details p{margin:8px 0 0;color:#C9D3DE}
.cta-bloco{text-align:center;margin:30px 0}
.fixo{position:fixed;left:0;right:0;bottom:0;padding:10px 14px calc(10px + env(safe-area-inset-bottom));background:rgba(11,15,20,.94);
 backdrop-filter:blur(8px);border-top:1px solid rgba(255,255,255,.08);transform:translateY(110%);transition:transform .25s}
.fixo.on{transform:none}.fixo .botao{font-size:18px;padding:15px}
body{padding-bottom:84px}

.kicker{display:inline-block;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:13px;letter-spacing:.14em;
 color:#F2C14E;border:1px solid rgba(242,193,78,.45);border-radius:99px;padding:6px 14px;margin:6px 0 16px}
.heroi .sub b{color:#fff}
.extrato{max-width:560px;margin:4px auto 20px;text-align:left;background:#F4F1EA;color:#14181D;border-radius:16px;
 padding:16px 18px 12px;box-shadow:0 24px 60px rgba(0,0,0,.45);font-size:16px;transform:rotate(-1deg)}
.ext-topo{display:flex;justify-content:space-between;align-items:center;font-weight:700;font-family:'Space Grotesk',sans-serif;
 border-bottom:2px solid #14181D;padding-bottom:8px;margin-bottom:4px}
.ext-topo .tag{font-size:11px;letter-spacing:.1em;text-transform:uppercase;background:#14181D;color:#F4F1EA;border-radius:6px;padding:3px 7px}
.ext-linha{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px dashed #BFB8A8}
.ext-linha b{white-space:nowrap;font-family:'Space Grotesk',sans-serif;font-size:19px}
.extrato .amarelo{color:#B07A00}.extrato .vermelho{color:#C0392B}
.ext-linha small{color:#6B6458}
.ext-linha.perda{border:0;font-weight:700}
.ext-fonte{display:block;font-size:11px;color:#6B6458;margin-top:6px;line-height:1.35}
.sub2{font-size:18px;color:#C9D3DE;max-width:620px;margin:6px auto 18px}.sub2 b{color:#fff}
.compra{display:grid;grid-template-columns:200px 1fr;gap:18px;align-items:center;max-width:620px;margin:0 auto;text-align:left}
.capa3d{position:relative}.capa3d:before{content:"";position:absolute;inset:8% 6%;border-radius:50%;background:radial-gradient(closest-side,rgba(242,193,78,.38),rgba(242,193,78,0));filter:blur(18px)}.capa3d img{position:relative;width:100%;height:auto;display:block;filter:drop-shadow(0 18px 30px rgba(0,0,0,.55))}
.compra .preco{justify-content:flex-start;margin-bottom:10px}
.selos{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.selos span{font-size:13px;color:#C9D3DE;background:rgba(255,255,255,.06);
 border-radius:99px;padding:5px 10px}
@media (max-width:560px){.compra{grid-template-columns:1fr;text-align:center}.capa3d{max-width:230px;margin:0 auto}
 .compra .preco{justify-content:center}.selos{justify-content:center}}
@media (max-width:560px){.paginas{grid-template-columns:1fr 1fr}.paginas img:nth-child(3){display:none}}
"""


def _botao(texto: str = f"Quero o Manual por R$ {PRECO_MANUAL}") -> str:
    return f'<a class="botao" href="{CHECKOUT_MANUAL}" rel="nofollow">{texto}</a>'


def pagina_manual() -> str:
    corpo = f"""<body>
<div class="topo-alerta">⚠️ Se você já assinou alguma coisa no banco sem entender direito, leia até o fim.</div>
<div class="marca">{SIMBOLO}TERMÔMETRO DE CRISE</div>
<main class="lp">
<section class="heroi">
 <div class="kicker" id="kicker">CARTA ABERTA A QUEM GUARDA DINHEIRO NO BANCO</div>
 <h1>Já saiu do banco achando que fez um bom negócio… <span class="amarelo">e depois descobriu que não?</span></h1>
 <p class="sub">Não foi burrice. Foi falta de informação. E do outro lado do balcão tem gente que <b>ganha</b> com ela:
 o mesmo banco que te paga <b>8% ao ano</b> na poupança cobra até <b class="vermelho">451% ao ano</b> no rotativo do cartão.</p>
 <div class="extrato" aria-label="Comparação de rendimento">
  <div class="ext-topo"><span>R$ 10 mil guardados por 1 ano</span><span class="tag">simulação</span></div>
  <div class="ext-linha"><span>🏦 Na poupança</span><b>+ R$ 834</b></div>
  <div class="ext-linha"><span>📄 Num CDB a 100% do CDI <small>(já sem o IR)</small></span><b class="amarelo">+ R$ 1.126</b></div>
  <div class="ext-linha perda"><span>Deixou na mesa, só por não saber</span><b class="vermelho">− R$ 292</b></div>
  <small class="ext-fonte">Selic 13,75% (Copom, 04/11/2026). Rotativo: média de 451,7% ao ano em set/2026 (Banco Central).
  Não é promessa de rendimento.</small>
 </div>
 <p class="sub2">O <b>Manual do Investidor</b> te ensina em uma tarde o que o gerente e o assessor não explicam: onde o seu
 dinheiro está, quanto rende de verdade e <b>quem ganha em cima dele</b>. Pra você nunca mais assinar nada no escuro.</p>
 <div class="compra">
  <div class="capa3d"><img src="mockup.webp" alt="E-book Manual do Investidor" width="705" height="719"></div>
  <div>
   <div class="preco"><b>R$ {PRECO_MANUAL}</b><span>pagamento único</span></div>
   {_botao()}
   <div class="selos"><span>📘 20 páginas</span><span>⏱ 1 tarde de leitura</span><span>🛡 7 dias de garantia</span></div>
  </div>
 </div>
</section>

<section class="carta">
<h2>Deixa eu te contar como funciona do outro lado do balcão.</h2>
<p>Quando você senta na frente de um gerente, parece uma conversa entre você e alguém que quer te ajudar. Mas tem uma terceira
pessoa na mesa que você não vê: <b>a meta do mês</b>.</p>
<p>Gerente de banco é vendedor. Na maioria das vezes, um vendedor honesto, mas que tem metas de produto pra bater. E os produtos
que mais aparecem na sua frente nem sempre são os que mais rendem pra você. Muitas vezes são os que mais rendem <b>pra quem
vende</b>.</p>
<p>O mesmo vale pro assessor que liga com "uma oportunidade exclusiva", pro "especialista" do Instagram que promete 5% ao mês, pro aplicativo que te empurra o cartão com limite novo
e pro contrato de 14 páginas que ninguém lê.</p>
<p><b>O inimigo não é uma pessoa.</b> É um sistema inteiro que lucra com a sua confusão. E ele tem três caras:</p>
<div class="inimigos">
 <div class="inimigo"><h3>1. O produto com letra miúda</h3><p>Título de capitalização vendido como "investimento". Previdência com
 taxa que come o rendimento. CDB pagando bem menos que o CDI quando existe opção melhor no mesmo banco.</p></div>
 <div class="inimigo"><h3>2. A comissão que você não vê</h3><p>"Esse aqui é o melhor pra você." Será? Gerente tem meta. Assessor
 pode ganhar por produto vendido. A regra da CVM obriga quem distribui investimento a mostrar quanto ganha com ele. Você já
 perguntou? Quase ninguém pergunta, porque não sabe que pode.</p></div>
 <div class="inimigo"><h3>3. A promessa boa demais</h3><p>Rendimento "garantido" de 3%, 5%, 10% ao mês. Robô de trader. "Chama mais
 gente e ganha bônus." É assim que o golpe começa, e ele pega gente esperta.</p></div>
</div>

<h2>Quanto custa não saber?</h2>
<p>Vamos fazer uma conta simples, com <b>R$ 10 mil parados por 1 ano</b>:</p>
<div class="conta">
 <div class="linha"><span>Na poupança</span><b>+ R$ 834</b></div>
 <div class="linha"><span>Num CDB que paga 100% do CDI<br><small style="display:inline;margin:0">já descontado o Imposto de Renda</small></span><b class="amarelo">+ R$ 1.126</b></div>
 <div class="dif">Diferença: <span class="amarelo">R$ 292</span> no ano.<br>Só por não saber.</div>
 <small>Simulação com a Selic em 13,75% ao ano (Copom, 04/11/2026), CDI de 13,65%, IR de 17,5% e poupança a 0,5% ao mês + TR.
 Não é promessa de rendimento: taxas mudam e cada produto tem regras.</small>
</div>
<p>E isso é o caso <b>bom</b>, de quem pelo menos guardou. O caso ruim é o de quem assinou um produto que nem entende, ou caiu
numa promessa que nunca devolveu o dinheiro.</p>

<h2>O Manual do Investidor existe pra virar esse jogo.</h2>
<p>Ele <b>não vai te dizer onde investir</b>. Isso é de propósito: quem promete "o investimento certo pra todo mundo" está
vendendo outra coisa. Ele te ensina a <b>entender</b>, pra você nunca mais assinar nada sem saber o que é.</p>
<ul class="lista">
 <li><b>Por onde começar:</b> dívida cara primeiro, depois a reserva de emergência. Quanto guardar e onde ela costuma ficar.</li>
 <li><b>Selic, CDI e IPCA:</b> as três palavras que mandam no seu dinheiro, e o juro real, o único número que importa.</li>
 <li><b>Poupança × Tesouro × CDB:</b> quanto cada um rende de verdade, depois do imposto e da inflação.</li>
 <li><b>LCI, LCA e o FGC:</b> até onde o seguro dos bancos protege, e o que ele não cobre.</li>
 <li><b>Imposto de Renda sem susto:</b> a tabela regressiva pronta e o que é isento.</li>
 <li><b>Ações e fundos imobiliários:</b> o que é ser sócio de uma empresa e os erros de quem começa.</li>
 <li><b>Os golpes que mais pegam gente:</b> os sinais e o que fazer se cair num golpe do Pix.</li>
 <li><b>Seu plano em 5 passos:</b> uma página pra preencher e sair com o próximo passo definido.</li>
</ul>
<div class="paginas">
 <img src="pag-juro.webp" alt="Página sobre juro real" loading="lazy">
 <img src="pag-fgc.webp" alt="Página sobre o FGC" loading="lazy">
 <img src="pag-golpe.webp" alt="Página sobre golpes" loading="lazy">
</div>
<div class="cta-bloco">{_botao()}<p class="miudo">Leva uma tarde pra ler. Serve pro resto da vida.</p></div>

<h2>Pra quem NÃO é</h2>
<ul class="nao">
 <li>Quem procura dica de ação ou "a próxima que vai explodir".</li>
 <li>Quem quer ficar rico rápido.</li>
 <li>Quem já investe há anos e domina renda fixa e variável.</li>
</ul>

<h2>Quem escreve</h2>
<p>Eu sou o Heitor, do <b>Termômetro de Crise</b> (@termometrodecrise). Todo dia eu mostro, com fonte, o que mexeu no bolso de
quem vive no Brasil. Sem alarde, sem lado político e sem vender promessa. O manual junta o que mais me perguntam, do jeito que
eu explico nos vídeos.</p>

<div class="garantia"><div class="sel"><b>7</b>dias</div>
<p>Leia com calma. Se em até 7 dias achar que não valeu, peça o reembolso pela própria Kiwify e recebe o valor de volta, sem
burocracia.</p></div>

<h2>Perguntas rápidas</h2>
<details><summary>Como recebo o e-book?</summary><p>Logo depois do pagamento aprovado, chega no seu e-mail o acesso à área de
membros da Kiwify, onde está o PDF. No Pix e no cartão a aprovação costuma ser na hora.</p></details>
<details><summary>Dá pra ler no celular?</summary><p>Sim. São 20 páginas em formato de livro de bolso, feitas pra ler no celular
ou imprimir.</p></details>
<details><summary>Tem recomendação de investimento?</summary><p>Não. É conteúdo educativo: explica como cada investimento funciona,
quanto rende e qual o risco. A decisão é sempre sua.</p></details>
<details><summary>As regras estão atualizadas?</summary><p>Conferidas em novembro de 2026 nas fontes oficiais (Receita, Banco
Central, Tesouro, FGC, CVM e B3). Regras mudam: o manual mostra onde conferir.</p></details>
<details><summary>Tem mais alguma coisa no checkout?</summary><p>Tem três complementos opcionais, que você marca se quiser: a
Planilha do Investidor, o Kit Anti-Golpe e o Guia Sair do Vermelho. O Manual funciona sozinho.</p></details>

<div class="cta-bloco" style="margin-top:40px">
 <h2 style="margin:0 0 18px">Entender o seu dinheiro custa menos que uma pizza.</h2>
 {_botao()}
 <p class="miudo">Conteúdo educativo. Não é recomendação de investimento.</p>
</div>
</section>
</main>
{_legal()}
<div class="fixo" id="fixo">{_botao(f"Quero o Manual · R$ {PRECO_MANUAL}")}</div>
<script>
(function(){{try{{var q=new URLSearchParams(location.search),e=parseInt(q.get('erros'),10);
 if(q.get('origem')==='quiz'&&e>=0){{var k=document.getElementById('kicker');
 var tt=parseInt(q.get('total'),10)||8;k.textContent=e>0?('VOCÊ CAIU EM '+e+' DE '+tt+' NO TESTE. É EXATAMENTE AÍ QUE O SISTEMA GANHA.'):'VOCÊ GABARITOU O TESTE. AGORA AJUDE QUEM ESTÁ PERTO.';}}}}catch(x){{}}}})();
(function(){{var f=document.getElementById('fixo'),h=document.querySelector('.heroi');
 function v(){{try{{f.classList.toggle('on',h.getBoundingClientRect().bottom<0)}}catch(e){{}}}}
 window.addEventListener('scroll',v,{{passive:true}});v();}})();
</script>
</body></html>"""
    return _cabeca(f"Manual do Investidor · {config.NOME}",
                   "O sistema ganha quando você não entende. Em 20 páginas, entenda onde está o seu dinheiro, quanto rende "
                   "de verdade e quem ganha em cima dele. Conteúdo educativo.", "manual/", CSS_LP) + corpo


# ===================================================================================== QUIZ
PERGUNTAS = [
    {"p": "A poupança é o investimento mais seguro do Brasil.", "certa": False, "tema": "Poupança × Tesouro",
     "e": "Mito. O Tesouro Direto é garantido pelo Tesouro Nacional, considerado o menor risco do país. A poupança tem a "
          "garantia do FGC (até R$ 250 mil por banco). E hoje ela rende bem menos que o Tesouro Selic."},
    {"p": "Se o gerente ofereceu, é porque é o melhor pra você.", "certa": False, "tema": "Metas do banco",
     "e": "Mito. Gerente de banco é vendedor e costuma ter metas de produtos. Pode ser um ótimo produto, ou só o que ajuda a "
          "bater a meta do mês. Quem decide bem é quem entende."},
    {"p": "Se o assessor diz que o produto não tem taxa, ele não ganha nada com isso.", "certa": False, "tema": "Comissões",
     "e": "Mito. Em muitos produtos, quem distribui é remunerado pelo emissor ou pela diferença de taxa, mesmo sem cobrar "
          "nada direto de você. Por isso a CVM obriga a mostrar essa remuneração. Pergunte sempre."},
    {"p": "Título de capitalização é um tipo de investimento.", "certa": False, "tema": "Capitalização",
     "e": "Mito. A própria Susep, que fiscaliza o setor, diz que capitalização não é investimento. É um sorteio com "
          "devolução, e você pode receber menos do que pagou se resgatar antes."},
    {"p": "Hoje, um CDB que paga 100% do CDI rende mais que a poupança, mesmo pagando Imposto de Renda.", "certa": True,
     "tema": "CDB e CDI",
     "e": "Verdade. Com a Selic em 13,75%, R$ 10 mil por 1 ano rendem cerca de R$ 1.126 líquidos no CDB contra R$ 834 na "
          "poupança. E o FGC protege os dois."},
    {"p": "O FGC protege qualquer dinheiro que você coloca no banco.", "certa": False, "tema": "FGC",
     "e": "Mito. Ele cobre poupança, CDB, LCI e LCA até R$ 250 mil por CPF em cada instituição. Não cobre ações, fundos, "
          "previdência nem capitalização."},
    {"p": "Previdência privada sempre vale a pena pra quem é CLT.", "certa": False, "tema": "Previdência",
     "e": "Mito. Depende. Taxa de administração alta pode comer o rendimento, e o benefício do PGBL no Imposto de Renda só "
          "vale pra quem faz a declaração completa."},
    {"p": "Existe investimento sério com rendimento garantido de 5% ao mês.", "certa": False, "tema": "Golpes",
     "e": "Mito. 5% ao mês dá quase 80% ao ano, mais de 5 vezes a Selic. Promessa assim é o sinal número 1 de golpe ou "
          "pirâmide."},
]

PERFIS = [
    {"r": "Na poupança", "m": "Seu dinheiro está no lugar que a maioria escolhe por costume, não por conta. Com R$ 20 mil, a "
     "diferença pra um CDB a 100% do CDI passa de R$ 580 por ano."},
    {"r": "Parado na conta corrente", "m": "Dinheiro parado na conta corrente não rende nada e a inflação come um pedaço todo mês. "
     "É o cenário que mais custa."},
    {"r": "Em CDB, Tesouro ou outros", "m": "Você já saiu do básico. O risco agora é a taxa escondida, a comissão que você não vê "
     "e o produto que parece bom mas não é pra você."},
    {"r": "Não tenho nada guardado", "m": "O primeiro passo não é investir: é sair da dívida cara e montar uma reserva. O Manual "
     "começa exatamente por aí."},
]

CSS_QUIZ = """
.q{max-width:640px;margin:0 auto;padding:0 18px 30px}
.abre{text-align:center;padding:24px 0 10px}
.abre .kicker{display:inline-block;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:12px;letter-spacing:.14em;color:#FF6B5E;
 border:1px solid rgba(255,107,94,.5);border-radius:99px;padding:6px 12px;margin-bottom:14px}
.abre h1{font-size:clamp(32px,7.6vw,50px)}
.abre p{font-size:19px;color:#C9D3DE;margin:16px 0 22px}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:0 0 24px}
.chips span{background:rgba(255,255,255,.07);border-radius:99px;padding:6px 12px;font-size:14px;color:#C9D3DE}
.topo-jogo{display:flex;align-items:center;gap:14px;margin:14px 0 18px}
.barra{flex:1;height:8px;border-radius:99px;background:rgba(255,255,255,.08);overflow:hidden}
.barra i{display:block;height:100%;width:0;background:#F2C14E;transition:width .35s}
.termo{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:#C9D3DE;white-space:nowrap}
.termo .bulbo{width:74px;height:12px;border-radius:99px;background:linear-gradient(90deg,#3B82C4,#7CC3E0,#F2C14E,#EE8A3C,#E5554A);
 position:relative;overflow:hidden}
.termo .bulbo i{position:absolute;right:0;top:0;bottom:0;background:#1A222C;transition:width .4s}
.num{font-size:14px;color:#9AA7B4;font-weight:600;letter-spacing:.08em}
.pergunta{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:clamp(26px,6vw,34px);line-height:1.15;margin:10px 0 24px}
.opcoes{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.opcoes.lista{grid-template-columns:1fr}
.op{font:inherit;font-weight:800;font-size:20px;padding:20px 12px;border-radius:16px;border:2px solid rgba(255,255,255,.14);
 background:rgba(255,255,255,.05);color:#EEF2F5;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:transform .1s}
.op:active{transform:scale(.98)}
.op:hover{border-color:#F2C14E}
.op.certo{background:#173A2A;border-color:#4CC38A}.op.errado{background:#3A1414;border-color:#FF6B5E;animation:treme .35s}
@keyframes treme{0%,100%{transform:translateX(0)}25%{transform:translateX(-6px)}75%{transform:translateX(6px)}}
.resp{margin-top:16px;border-radius:16px;padding:16px 18px;background:#121A22;display:none}
.resp b{display:block;font-family:'Space Grotesk',sans-serif;font-size:20px;margin-bottom:6px}
.resp.on{display:block;animation:sobe .3s}
@keyframes sobe{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.prox{margin-top:16px;display:none}.prox.on{display:block}
.fim{text-align:center;display:none;padding-top:10px}.fim.on{display:block;animation:sobe .4s}
.nota{font-family:'Space Grotesk',sans-serif;font-size:92px;font-weight:700;line-height:1;margin:6px 0}
.fim h2{font-size:clamp(26px,6vw,36px);margin:8px 0 12px}
.fim p{color:#C9D3DE;margin:0 0 16px}
.temp{height:16px;border-radius:99px;background:linear-gradient(90deg,#3B82C4,#7CC3E0,#F2C14E,#EE8A3C,#E5554A);position:relative;margin:14px 0 6px}
.temp i{position:absolute;top:-6px;width:6px;height:28px;border-radius:4px;background:#fff;box-shadow:0 0 0 3px #0B0F14;transform:translateX(-50%)}
.temp-rot{display:flex;justify-content:space-between;font-size:12px;color:#8796A5;margin-bottom:18px}
.furos{text-align:left;background:#121A22;border-radius:16px;padding:16px 18px;margin:0 0 16px}
.furos b{font-family:'Space Grotesk',sans-serif}
.furos ul{margin:8px 0 0;padding-left:20px}.furos li{margin:4px 0;color:#FFD9D4}
.perfil{text-align:left;border-left:4px solid #F2C14E;background:rgba(242,193,78,.08);border-radius:10px;padding:12px 14px;margin:0 0 20px;
 color:#EEF2F5;font-size:17px}
.refazer{background:none;border:0;color:#8796A5;text-decoration:underline;font:inherit;font-size:14px;margin-top:14px;cursor:pointer}
"""


def pagina_quiz() -> str:
    dados = json.dumps(PERGUNTAS, ensure_ascii=False)
    perfis = json.dumps(PERFIS, ensure_ascii=False)
    n = len(PERGUNTAS)
    corpo = f"""<body>
<div class="marca">{SIMBOLO}TERMÔMETRO DE CRISE</div>
<main class="q">
<section class="abre" id="abre">
 <div class="kicker">TESTE DE 1 MINUTO</div>
 <h1>Seu gerente torce pra você <span class="vermelho">errar</span> estas {n} perguntas.</h1>
 <p>Gerente tem meta. Assessor tem comissão. E quem não entende, paga. Descubra quanto do seu dinheiro está no escuro.</p>
 <div class="chips"><span>⏱ 1 minuto</span><span>🔒 sem cadastro</span><span>✅ resposta na hora</span></div>
 <button class="botao" id="comecar">Fazer o teste agora</button>
</section>
<section id="jogo" style="display:none">
 <div class="topo-jogo"><div class="barra"><i id="progresso"></i></div>
  <div class="termo">🌡️ seu bolso <span class="bulbo"><i id="calor" style="width:100%"></i></span></div></div>
 <div class="num" id="num"></div>
 <div class="pergunta" id="pergunta"></div>
 <div class="opcoes" id="opcoes"></div>
 <div class="resp" id="resp"><b id="veredito"></b><span id="explica"></span></div>
 <div class="prox" id="prox"><button class="botao" id="seguir">Próxima</button></div>
</section>
<section class="fim" id="fim">
 <div class="num">SEU RESULTADO</div>
 <div class="nota"><span id="acertos"></span><span style="font-size:42px;color:#9AA7B4">/{n}</span></div>
 <div class="temp"><i id="ponteiro"></i></div>
 <div class="temp-rot"><span>bolso protegido</span><span>bolso pegando fogo</span></div>
 <h2 id="titulo-fim"></h2>
 <p id="texto-fim"></p>
 <div class="furos" id="furos"><b>Os furos no seu bolso:</b><ul id="lista-furos"></ul></div>
 <div class="perfil" id="perfil"></div>
 <a class="botao" id="cta" href="../manual/?origem=quiz">Quero tapar esses furos</a>
 <p style="font-size:13px;color:#8796A5;margin-top:12px">Manual do Investidor · R$ {PRECO_MANUAL} · 7 dias de garantia</p>
 <button class="refazer" id="refazer">Refazer o teste</button>
</section>
</main>
{_legal()}
<script>
(function(){{
var P={dados},PF={perfis},i=-1,ok=0,perfil=null,respondeu=false,erros=[],$=function(x){{return document.getElementById(x)}};
function calor(){{var e=erros.length;$('calor').style.width=Math.max(0,100-(e/P.length)*100-8)+'%';}}
function botoes(lista,cls){{var o=$('opcoes');o.className='opcoes'+(cls?' '+cls:'');o.innerHTML='';
 lista.forEach(function(t,k){{var b=document.createElement('button');b.className='op';b.textContent=t;b.onclick=function(){{clique(k,b)}};o.appendChild(b)}});}}
function mostra(){{respondeu=false;$('resp').className='resp';$('prox').className='prox';
 if(i<0){{$('num').textContent='ANTES DE COMEÇAR';$('pergunta').textContent='Onde está a maior parte do seu dinheiro hoje?';
  botoes(PF.map(function(x){{return x.r}}),'lista');$('progresso').style.width='0%';return}}
 $('num').textContent='PERGUNTA '+(i+1)+' DE '+P.length;$('pergunta').textContent=P[i].p;
 $('progresso').style.width=(i/P.length*100)+'%';botoes(['VERDADE','MITO']);}}
function clique(k,b){{if(respondeu)return;
 if(i<0){{perfil=PF[k];i=0;mostra();return}}
 respondeu=true;var v=k===0,certo=v===P[i].certa;if(certo)ok++;else erros.push(P[i].tema);calor();
 var bs=document.querySelectorAll('.op');bs.forEach(function(o,n){{o.disabled=true;if((n===0)===P[i].certa)o.classList.add('certo')}});
 if(!certo){{b.classList.add('errado');try{{navigator.vibrate&&navigator.vibrate(60)}}catch(x){{}}}}
 $('veredito').textContent=certo?'Acertou. ✅':'Caiu nessa. 🔥';$('veredito').style.color=certo?'#4CC38A':'#FF6B5E';
 $('explica').textContent=P[i].e;$('resp').className='resp on';$('prox').className='prox on';
 $('seguir').textContent=i<P.length-1?'Próxima':'Ver meu resultado';}}
$('comecar').onclick=function(){{$('abre').style.display='none';$('jogo').style.display='block';mostra();window.scrollTo(0,0)}};
$('seguir').onclick=function(){{i++;if(i<P.length){{mostra();window.scrollTo(0,0);return}}fim()}};
function fim(){{$('progresso').style.width='100%';$('jogo').style.display='none';$('fim').className='fim on';
 var e=P.length-ok;$('acertos').textContent=ok;$('ponteiro').style.left=Math.min(96,Math.max(4,e/P.length*100))+'%';
 var t,x;if(e>=4){{t='Seu bolso está pegando fogo.';x='Você caiu em '+e+' de '+P.length+'. São exatamente os pontos onde o sistema ganha em cima de quem não sabe.'}}
 else if(e>=2){{t='Você sabe mais que a média. Mas tem furo.';x='Caiu em '+e+' de '+P.length+'. Um furo desses pode estar custando dinheiro todo mês sem você perceber.'}}
 else if(e===1){{t='Quase lá.';x='Só 1 furo. Mas é justamente o que alguém do outro lado do balcão adoraria que você não soubesse.'}}
 else{{t='Gabaritou. 🏆';x='Você está à frente da maioria. Agora use isso pra proteger quem está perto: pais, avós, parceiro.'}}
 $('titulo-fim').textContent=t;$('texto-fim').textContent=x;
 var l=$('lista-furos');l.innerHTML='';erros.forEach(function(z){{var li=document.createElement('li');li.textContent=z;l.appendChild(li)}});
 $('furos').style.display=erros.length?'block':'none';
 $('perfil').textContent=perfil?perfil.m:'';$('perfil').style.display=perfil?'block':'none';
 $('cta').textContent=e?'Quero tapar esses furos':'Quero o Manual pra ajudar minha família';
 $('cta').href='../manual/?origem=quiz&erros='+e+'&total='+P.length;window.scrollTo(0,0);}}
$('refazer').onclick=function(){{i=-1;ok=0;erros=[];perfil=null;calor();$('fim').className='fim';$('jogo').style.display='block';mostra();window.scrollTo(0,0)}};
}})();
</script>
</body></html>"""
    return _cabeca(f"Teste: o que o gerente não te conta · {config.NOME}",
                   f"{n} perguntas rápidas sobre poupança, CDB, FGC, comissões e golpes. Descubra quanto do seu dinheiro está "
                   "no escuro.", "quiz/", CSS_QUIZ) + corpo


def gerar(saida: Path, pagina=None) -> list[str]:
    """Gera /manual/ e /quiz/ como páginas soltas (sem o menu do site e sem anúncios). `pagina` não é usada."""
    pasta = saida / "manual"
    pasta.mkdir(parents=True, exist_ok=True)
    for arq in (PASTA / "manual").glob("*"):
        shutil.copy(arq, pasta / arq.name)
    (pasta / "index.html").write_text(pagina_manual())
    quiz = saida / "quiz"
    quiz.mkdir(parents=True, exist_ok=True)
    (quiz / "index.html").write_text(pagina_quiz())
    return ["manual/", "quiz/"]
