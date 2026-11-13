"""Funil de venda do "Manual do Investidor", servido pelo próprio site.

/quiz/   : quiz de 7 perguntas contraintuitivas ("o que o gerente não te conta") que termina na página de venda.
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
.heroi img{width:100%;max-width:520px;border-radius:18px;margin:6px auto 22px;display:block;box-shadow:0 24px 60px rgba(0,0,0,.45)}
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
@media (max-width:560px){.paginas{grid-template-columns:1fr 1fr}.paginas img:nth-child(3){display:none}}
"""


def _botao(texto: str = f"Quero o Manual por R$ {PRECO_MANUAL}") -> str:
    return f'<a class="botao" href="{CHECKOUT_MANUAL}" rel="nofollow">{texto}</a>'


def pagina_manual() -> str:
    corpo = f"""<body>
<div class="topo-alerta">Conteúdo educativo. Ninguém aqui vai te dizer onde investir.</div>
<div class="marca">{SIMBOLO}TERMÔMETRO DE CRISE</div>
<main class="lp">
<section class="heroi">
 <h1>O sistema <span class="vermelho">ganha</span> quando você não entende.<br><span class="amarelo">Por isso ninguém te explica.</span></h1>
 <p class="sub">Em 20 páginas, você aprende o que o gerente não tem tempo (nem interesse) de te contar: onde o seu dinheiro está,
 quanto ele rende de verdade e quem ganha em cima dele.</p>
 <img src="produto.webp" alt="E-book Manual do Investidor" width="600" height="500">
 <div class="preco"><b>R$ {PRECO_MANUAL}</b><span>pagamento único</span></div>
 {_botao()}
 <p class="miudo">Pix, cartão ou boleto · acesso imediato · 7 dias de garantia</p>
</section>

<section class="carta">
<h2>Deixa eu te contar como funciona do outro lado do balcão.</h2>
<p>Quando você senta na frente de um gerente, parece uma conversa entre você e alguém que quer te ajudar. Mas tem uma terceira
pessoa na mesa que você não vê: <b>a meta do mês</b>.</p>
<p>Gerente de banco é vendedor. Na maioria das vezes, um vendedor honesto, mas que tem metas de produto pra bater. E os produtos
que mais aparecem na sua frente nem sempre são os que mais rendem pra você. Muitas vezes são os que mais rendem <b>pra quem
vende</b>.</p>
<p>O mesmo vale pro "especialista" do Instagram que promete 5% ao mês, pro aplicativo que te empurra o cartão com limite novo
e pro contrato de 14 páginas que ninguém lê.</p>
<p><b>O inimigo não é uma pessoa.</b> É um sistema inteiro que lucra com a sua confusão. E ele tem três caras:</p>
<div class="inimigos">
 <div class="inimigo"><h3>1. O produto com letra miúda</h3><p>Título de capitalização vendido como "investimento". Previdência com
 taxa que come o rendimento. CDB pagando bem menos que o CDI quando existe opção melhor no mesmo banco.</p></div>
 <div class="inimigo"><h3>2. A meta que não é sua</h3><p>"Esse aqui é o melhor pra você." Será? Quem te ofereceu ganha comissão ou
 bate meta com isso? Você nunca pergunta, porque não sabe que pode.</p></div>
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
    {"p": "A poupança é o investimento mais seguro do Brasil.", "certa": False,
     "e": "Não. O Tesouro Direto é garantido pelo Tesouro Nacional, considerado o menor risco do país. A poupança tem a "
          "garantia do FGC (até R$ 250 mil por banco). E hoje ela rende bem menos que o Tesouro Selic."},
    {"p": "Se o gerente ofereceu, é porque é o melhor pra você.", "certa": False,
     "e": "Gerente de banco é vendedor e costuma ter metas de produtos. Pode ser um ótimo produto, ou só o que ajuda a bater "
          "a meta. Quem decide é quem entende."},
    {"p": "Título de capitalização é um tipo de investimento.", "certa": False,
     "e": "Não é. A própria Susep, que fiscaliza o setor, diz que capitalização não é investimento. É um sorteio com "
          "devolução, e você pode receber menos do que pagou se resgatar antes."},
    {"p": "Hoje, um CDB que paga 100% do CDI rende mais que a poupança, mesmo pagando Imposto de Renda.", "certa": True,
     "e": "Verdade. Com a Selic em 13,75%, R$ 10 mil por 1 ano rendem cerca de R$ 1.126 líquidos no CDB contra R$ 834 na "
          "poupança. Com o FGC protegendo os dois."},
    {"p": "O FGC protege qualquer dinheiro que você coloca no banco.", "certa": False,
     "e": "Não. Ele cobre poupança, CDB, LCI e LCA até R$ 250 mil por CPF em cada instituição. Não cobre ações, fundos, "
          "previdência nem capitalização."},
    {"p": "Previdência privada sempre vale a pena pra quem é CLT.", "certa": False,
     "e": "Depende. Taxa de administração alta pode comer o rendimento, e o benefício do PGBL no Imposto de Renda só vale "
          "pra quem faz a declaração completa."},
    {"p": "Existe investimento sério com rendimento garantido de 5% ao mês.", "certa": False,
     "e": "Não existe. 5% ao mês dá quase 80% ao ano, mais de 5 vezes a Selic. Promessa assim é o sinal número 1 de golpe "
          "ou pirâmide."},
]

CSS_QUIZ = """
.q{max-width:640px;margin:0 auto;padding:0 18px 30px;min-height:calc(100vh - 60px);display:flex;flex-direction:column}
.abre{text-align:center;padding:30px 0 10px}
.abre h1{font-size:clamp(32px,7.6vw,50px)}
.abre p{font-size:19px;color:#C9D3DE;margin:16px 0 26px}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:0 0 26px}
.chips span{background:rgba(255,255,255,.07);border-radius:99px;padding:6px 12px;font-size:14px;color:#C9D3DE}
.barra{height:8px;border-radius:99px;background:rgba(255,255,255,.08);overflow:hidden;margin:18px 0 22px}
.barra i{display:block;height:100%;width:0;background:#F2C14E;transition:width .35s}
.num{font-size:14px;color:#9AA7B4;font-weight:600;letter-spacing:.08em}
.pergunta{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:clamp(26px,6vw,34px);line-height:1.15;margin:10px 0 26px}
.opcoes{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.op{font:inherit;font-weight:800;font-size:20px;padding:22px 10px;border-radius:16px;border:2px solid rgba(255,255,255,.14);
 background:rgba(255,255,255,.05);color:#EEF2F5;cursor:pointer;font-family:'Space Grotesk',sans-serif}
.op:hover{border-color:#F2C14E}
.op.certo{background:#173A2A;border-color:#4CC38A}.op.errado{background:#3A1414;border-color:#FF6B5E}
.resp{margin-top:18px;border-radius:16px;padding:16px 18px;background:#121A22;display:none}
.resp b{display:block;font-family:'Space Grotesk',sans-serif;font-size:20px;margin-bottom:6px}
.resp.on{display:block}
.prox{margin-top:16px;display:none}.prox.on{display:block}
.fim{text-align:center;display:none;padding-top:16px}.fim.on{display:block}
.nota{font-family:'Space Grotesk',sans-serif;font-size:96px;font-weight:700;line-height:1;margin:10px 0}
.fim h2{font-size:clamp(26px,6vw,36px);margin:8px 0 14px}
.fim p{color:#C9D3DE;margin:0 0 22px}
"""


def pagina_quiz() -> str:
    dados = json.dumps(PERGUNTAS, ensure_ascii=False)
    corpo = f"""<body>
<div class="marca">{SIMBOLO}TERMÔMETRO DE CRISE</div>
<main class="q">
<section class="abre" id="abre">
 <h1>Cansado de assinar coisa no banco <span class="amarelo">sem entender?</span></h1>
 <p>7 perguntas rápidas que o gerente não faz questão de te explicar. Veja quanto do seu dinheiro está no escuro.</p>
 <div class="chips"><span>⏱ 1 minuto</span><span>🔒 sem cadastro</span><span>✅ resposta na hora</span></div>
 <button class="botao" id="comecar">Começar o teste</button>
</section>
<section id="jogo" style="display:none">
 <div class="barra"><i id="progresso"></i></div>
 <div class="num" id="num"></div>
 <div class="pergunta" id="pergunta"></div>
 <div class="opcoes"><button class="op" data-v="1">VERDADE</button><button class="op" data-v="0">MITO</button></div>
 <div class="resp" id="resp"><b id="veredito"></b><span id="explica"></span></div>
 <div class="prox" id="prox"><button class="botao" id="seguir">Próxima</button></div>
</section>
<section class="fim" id="fim">
 <div class="num">SEU RESULTADO</div>
 <div class="nota"><span id="acertos"></span><span style="font-size:44px;color:#9AA7B4">/7</span></div>
 <h2 id="titulo-fim"></h2>
 <p id="texto-fim"></p>
 <a class="botao" href="../manual/?origem=quiz">Quero entender o meu dinheiro</a>
 <p style="font-size:13px;color:#8796A5;margin-top:12px">Conteúdo educativo. Não é recomendação de investimento.</p>
</section>
</main>
{_legal()}
<script>
(function(){{
var P={dados},i=0,ok=0,respondeu=false,$=function(x){{return document.getElementById(x)}};
function mostra(){{respondeu=false;$('num').textContent='PERGUNTA '+(i+1)+' DE '+P.length;$('pergunta').textContent=P[i].p;
 $('progresso').style.width=(i/P.length*100)+'%';$('resp').className='resp';$('prox').className='prox';
 document.querySelectorAll('.op').forEach(function(b){{b.className='op';b.disabled=false}});}}
$('comecar').onclick=function(){{$('abre').style.display='none';$('jogo').style.display='block';mostra();window.scrollTo(0,0)}};
document.querySelectorAll('.op').forEach(function(b){{b.onclick=function(){{if(respondeu)return;respondeu=true;
 var v=b.getAttribute('data-v')==='1',certo=v===P[i].certa;if(certo)ok++;
 document.querySelectorAll('.op').forEach(function(o){{o.disabled=true;if((o.getAttribute('data-v')==='1')===P[i].certa)o.classList.add('certo')}});
 if(!certo)b.classList.add('errado');
 $('veredito').textContent=certo?'Acertou.':'Muita gente erra essa.';$('veredito').style.color=certo?'#4CC38A':'#FF6B5E';
 $('explica').textContent=P[i].e;$('resp').className='resp on';$('prox').className='prox on';
 $('seguir').textContent=i<P.length-1?'Próxima':'Ver meu resultado';}}}});
$('seguir').onclick=function(){{i++;if(i<P.length){{mostra();window.scrollTo(0,0);return}}
 $('progresso').style.width='100%';$('jogo').style.display='none';$('fim').className='fim on';$('acertos').textContent=ok;
 var t,x;if(ok<=3){{t='Seu dinheiro está no escuro.';x='Você errou '+(7-ok)+' de 7. São exatamente os pontos onde o sistema ganha em cima de quem não sabe. Dá pra virar isso em uma tarde.'}}
 else if(ok<=5){{t='Você sabe mais que a média, mas ainda tem buraco.';x='Errou '+(7-ok)+' de 7. Um desses erros pode estar custando dinheiro todo mês sem você perceber.'}}
 else{{t='Mandou bem.';x='Você está à frente da maioria. O Manual organiza o resto e serve pra você ajudar quem está perto.'}}
 $('titulo-fim').textContent=t;$('texto-fim').textContent=x;window.scrollTo(0,0);}};
}})();
</script>
</body></html>"""
    return _cabeca(f"Teste: o que o gerente não te conta · {config.NOME}",
                   "7 perguntas rápidas sobre poupança, CDB, FGC, previdência e golpes. Descubra quanto do seu dinheiro está "
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
