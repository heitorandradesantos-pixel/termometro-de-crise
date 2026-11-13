"""Páginas de venda (LP) dos produtos do Termômetro, servidas pelo próprio site.

/manual/: o e-book "Manual do Investidor" (13/11/2026, pedido do Heitor: produto de R$ 19,90 na bio, checkout na
Kiwify). Conteúdo educativo: a página nunca promete ganho nem recomenda investimento.
"""

import shutil
from pathlib import Path

from . import config

PASTA = Path(__file__).resolve().parent.parent / "lp"
CHECKOUT_MANUAL = "https://pay.kiwify.com.br/0k8fopI"
PRECO_MANUAL = "19,90"

CSS = """
.lp{max-width:980px;margin:0 auto;padding:8px 18px 40px}
.lp h1{font-size:clamp(34px,6vw,54px);line-height:1.02;letter-spacing:-.02em;margin:10px 0 14px}
.lp h1 em{font-style:normal;color:#F2C14E}
.lp h2{font-size:clamp(24px,4vw,32px);letter-spacing:-.01em;margin:44px 0 14px}
.lp .heroi{display:grid;grid-template-columns:1.1fr .9fr;gap:30px;align-items:center;margin-top:10px}
.lp .heroi img{width:100%;border-radius:18px;box-shadow:0 24px 60px rgba(0,0,0,.35)}
.lp .sub{font-size:19px;line-height:1.45;opacity:.85;margin:0 0 18px}
.lp .preco{display:flex;align-items:baseline;gap:10px;margin:18px 0 6px}
.lp .preco b{font-size:44px;letter-spacing:-.02em}
.lp .preco span{opacity:.7;font-weight:600}
.lp .botao{display:inline-block;background:#F2C14E;color:#0E141B;font-weight:900;font-size:20px;text-decoration:none;
  padding:17px 30px;border-radius:14px;box-shadow:0 10px 30px rgba(242,193,78,.35)}
.lp .botao:hover{filter:brightness(1.05)}
.lp .miudo{font-size:13px;opacity:.7;margin-top:10px}
.lp .grade{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.lp .card{border:1px solid rgba(127,140,160,.3);border-radius:16px;padding:16px 18px}
.lp .card b{display:block;font-size:17px;margin-bottom:4px}
.lp .card p{margin:0;opacity:.85;line-height:1.45}
.lp .paginas{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.lp .paginas img{width:100%;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.25);background:#fff}
.lp .duas{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.lp .sim li,.lp .nao li{margin:8px 0;line-height:1.45}
.lp .sim{list-style:"✅  "} .lp .nao{list-style:"✋  "}
.lp .garantia{display:flex;gap:18px;align-items:center;border:2px solid #F2C14E;border-radius:18px;padding:18px 20px;margin-top:30px}
.lp .garantia .sel{flex:none;width:86px;height:86px;border-radius:999px;background:#F2C14E;color:#0E141B;font-weight:900;
  display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1}
.lp .garantia .sel b{font-size:30px}
.lp details{border-bottom:1px solid rgba(127,140,160,.3);padding:12px 0}
.lp summary{font-weight:800;cursor:pointer}
.lp details p{margin:8px 0 0;opacity:.85;line-height:1.5}
.lp .final{text-align:center;margin-top:44px}
@media (max-width:760px){.lp .heroi{grid-template-columns:1fr}.lp .heroi .foto{order:-1}.lp .paginas{grid-template-columns:1fr 1fr}
 .lp .paginas img:nth-child(3){display:none}.lp .duas{grid-template-columns:1fr}}
"""


def corpo_manual() -> str:
    botao = (f'<a class="botao" href="{CHECKOUT_MANUAL}" rel="nofollow">Quero o Manual por R$ {PRECO_MANUAL}</a>')
    return f"""<section class="lp">
<div class="heroi">
 <div>
  <p class="rotulo">E-BOOK EM PDF · TERMÔMETRO DE CRISE</p>
  <h1>Entenda o seu dinheiro <em>em uma tarde.</em></h1>
  <p class="sub">Selic, CDI, poupança, Tesouro, CDB, LCI/LCA, FGC, Imposto de Renda, ações, fundos imobiliários e como
  fugir de golpe. Em linguagem de gente, com exemplos em reais.</p>
  <div class="preco"><b>R$ {PRECO_MANUAL}</b><span>pagamento único · acesso imediato</span></div>
  {botao}
  <p class="miudo">Pix, cartão ou boleto pela Kiwify. 7 dias de garantia.</p>
 </div>
 <div class="foto"><img src="produto.webp" alt="Capa do e-book Manual do Investidor" width="600" height="500"></div>
</div>

<h2>Este manual não vai te dizer onde investir.</h2>
<p class="sub">E isso é de propósito. Quem promete "o investimento certo" pra todo mundo está vendendo outra coisa.
O manual te ensina a <b>entender</b> cada opção, pra você nunca mais assinar nada no banco sem saber o que é.</p>

<h2>O que você aprende</h2>
<div class="grade">
 <div class="card"><b>Por onde começar</b><p>Dívida cara primeiro, depois a reserva de emergência. Quanto guardar e onde ela costuma ficar.</p></div>
 <div class="card"><b>Selic, CDI e IPCA</b><p>As três palavras que mandam no seu dinheiro, e o juro real: o único número que importa.</p></div>
 <div class="card"><b>Poupança × Tesouro × CDB</b><p>Quanto cada um rende de verdade, depois do imposto e da inflação.</p></div>
 <div class="card"><b>LCI, LCA e o FGC</b><p>Até onde o seguro dos bancos protege e por que dividir valores grandes.</p></div>
 <div class="card"><b>Imposto de Renda sem susto</b><p>A tabela regressiva pronta, o que é isento e o que mudou nos dividendos em 2026.</p></div>
 <div class="card"><b>Ações e fundos imobiliários</b><p>O que é ser sócio de uma empresa, dividendos e os erros de quem começa.</p></div>
 <div class="card"><b>Os golpes que mais pegam gente</b><p>Os 5 sinais e o que fazer se cair num golpe do Pix.</p></div>
 <div class="card"><b>Seu plano em 5 passos</b><p>Uma página pra preencher e sair com o próximo passo definido.</p></div>
</div>

<h2>Uma olhada por dentro</h2>
<div class="paginas">
 <img src="pag-juro.webp" alt="Página sobre juro real e juros compostos" loading="lazy">
 <img src="pag-fgc.webp" alt="Página sobre o FGC" loading="lazy">
 <img src="pag-golpe.webp" alt="Página sobre golpes" loading="lazy">
</div>

<div class="duas">
 <div><h2>É pra você se…</h2><ul class="sim">
  <li>tem dinheiro na poupança e quer saber se está perdendo;</li>
  <li>o gerente te oferece coisas que você não entende;</li>
  <li>quer começar a investir sem cair em promessa milagrosa;</li>
  <li>quer ajudar os pais ou o parceiro a cuidar do dinheiro.</li></ul></div>
 <div><h2>Não é pra você se…</h2><ul class="nao">
  <li>procura dica de ação ou "a próxima que vai explodir";</li>
  <li>quer ficar rico rápido;</li>
  <li>já investe há anos e domina renda fixa e variável.</li></ul></div>
</div>

<h2>Quem escreve</h2>
<p class="sub">Eu sou o Heitor, do <b>Termômetro de Crise</b> (@termometrodecrise). Todo dia eu mostro, com fonte, o que
mexeu no bolso de quem vive no Brasil. O manual junta o que mais me perguntam, do jeito que eu explico nos vídeos.</p>

<div class="garantia"><div class="sel"><b>7</b>dias</div>
<p style="margin:0">Leia com calma. Se em até 7 dias achar que não valeu, peça o reembolso pela própria Kiwify e recebe
o valor de volta, sem burocracia.</p></div>

<h2>Perguntas rápidas</h2>
<details><summary>Como recebo o e-book?</summary><p>Logo depois do pagamento aprovado, chega no seu e-mail o acesso à área de
membros da Kiwify, onde está o PDF para baixar. No Pix e no cartão a aprovação costuma ser na hora.</p></details>
<details><summary>Dá pra ler no celular?</summary><p>Sim. São 20 páginas em formato de livro de bolso, feitas pra ler no
celular ou imprimir.</p></details>
<details><summary>Tem recomendação de investimento?</summary><p>Não. É conteúdo educativo: explica como cada investimento
funciona, quanto rende e qual o risco. A decisão é sempre sua.</p></details>
<details><summary>As regras estão atualizadas?</summary><p>Conferidas em novembro de 2026 nas fontes oficiais (Receita, Banco
Central, Tesouro, FGC, CVM e B3). Regras mudam: o manual mostra onde conferir.</p></details>

<div class="final">
 <h2>Comece hoje.</h2>
 {botao}
 <p class="miudo">Conteúdo educativo. Não é recomendação de investimento.</p>
</div>
</section>"""


def gerar(saida: Path, pagina) -> list[str]:
    pasta = saida / "manual"
    pasta.mkdir(parents=True, exist_ok=True)
    for arq in (PASTA / "manual").glob("*"):
        shutil.copy(arq, pasta / arq.name)
    (pasta / "index.html").write_text(pagina(
        f"Manual do Investidor · {config.NOME}",
        "E-book de R$ 19,90: entenda Selic, CDI, poupança, Tesouro, CDB, LCI/LCA, FGC, IR, ações e FIIs em uma tarde. "
        "Linguagem simples, sem recomendação de investimento.",
        corpo_manual(), raiz="../", imagem="manual/produto.webp", caminho="manual/", extra_css=CSS, sem_anuncio=True))  # página de venda nunca mostra anúncio
    return ["manual/"]
