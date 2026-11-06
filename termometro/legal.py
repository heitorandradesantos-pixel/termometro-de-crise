"""Páginas de política de privacidade e termos de uso (links pequenos no rodapé de todas as páginas)."""

import html

from . import config

ATUALIZADO = "5 de novembro de 2026"


def _contato() -> str:
    email = html.escape(config.CONTATO_EMAIL)
    return f'<a href="mailto:{email}">{email}</a>'


def _responsavel() -> str:
    return html.escape(config.RESPONSAVEL) if config.RESPONSAVEL else f"os responsáveis pelo {config.NOME}"


def privacidade() -> str:
    return f"""<section class="edicao"><h1>Política de privacidade</h1>
<p class="suave">Última atualização: {ATUALIZADO}.</p>
<p>Esta política explica quais dados pessoais o {config.NOME} trata, para quê, com quem compartilha e como você exerce
os seus direitos, de acordo com a Lei Geral de Proteção de Dados (LGPD, Lei 13.709/2018).</p>

<h2>1. Quem é o responsável</h2>
<p>O controlador dos dados é {_responsavel()}. Para qualquer assunto sobre privacidade, inclusive para falar com o
encarregado (DPO), escreva para {_contato()}.</p>

<h2>2. Que dados tratamos</h2>
<ul>
<li><strong>Navegação no site.</strong> Hoje o site não usa cookies próprios nem ferramentas de rastreamento para
publicidade. A empresa que hospeda e protege o site (Cloudflare) registra dados técnicos de cada acesso, como endereço IP,
tipo de navegador, data, hora e página visitada, para manter o site no ar e seguro. As fontes do texto são carregadas dos
servidores do Google Fonts, o que faz o seu navegador informar o seu endereço IP ao Google.</li>
<li><strong>Newsletter.</strong> Se você se inscrever, tratamos o seu e-mail e os dados de entrega e leitura das mensagens
(por exemplo, se o e-mail foi aberto), por meio da plataforma de envio.</li>
<li><strong>WhatsApp.</strong> Quem segue um canal do WhatsApp não tem o número de telefone mostrado aos administradores.
Em grupos e comunidades, o seu número fica visível para administradores e participantes, conforme as regras do próprio
WhatsApp.</li>
<li><strong>Contato.</strong> Se você nos escrever, tratamos o seu nome, e-mail e o conteúdo da mensagem para responder.</li>
</ul>
<p>Não pedimos dados sensíveis e não tratamos dados de crianças e adolescentes de forma intencional: o site é destinado a
maiores de 18 anos.</p>

<h2>3. Para que usamos e com qual base legal</h2>
<ul>
<li>Manter o site funcionando, seguro e protegido contra abusos: legítimo interesse.</li>
<li>Enviar a newsletter e o panorama que você pediu: consentimento, que você pode retirar a qualquer momento.</li>
<li>Entender, de forma agregada, quais páginas são mais lidas, para melhorar o conteúdo: legítimo interesse, sempre com o
mínimo de dados possível.</li>
<li>Responder mensagens e pedidos sobre os seus direitos: execução do pedido e cumprimento de obrigação legal.</li>
<li>Guardar registros de acesso quando a lei exigir (Marco Civil da Internet): cumprimento de obrigação legal.</li>
</ul>

<h2>4. Com quem compartilhamos</h2>
<p>Não vendemos nem alugamos dados pessoais. Compartilhamos só o necessário com empresas que prestam serviço para nós
(operadores), como hospedagem e proteção do site (Cloudflare), envio da newsletter (plataforma de e-mail) e
armazenamento do código (GitHub). Os textos do site são escritos com ajuda de inteligência artificial a partir de dados
públicos de mercado e notícias; nenhum dado pessoal de leitores é enviado para isso. Também podemos compartilhar dados
quando uma autoridade exigir, nos termos da lei.</p>

<h2>5. Transferência para outros países</h2>
<p>Alguns desses prestadores guardam dados fora do Brasil, principalmente nos Estados Unidos. Nesses casos, usamos
prestadores que adotam garantias de proteção de dados compatíveis com a LGPD, como cláusulas contratuais.</p>

<h2>6. Por quanto tempo guardamos</h2>
<p>O e-mail da newsletter fica guardado enquanto você estiver inscrito; ao sair, ele é removido da lista de envio.
Registros técnicos seguem os prazos dos prestadores e, quando aplicável, o prazo mínimo de 6 meses do Marco Civil da
Internet. Mensagens de contato ficam guardadas pelo tempo necessário para responder e para eventual defesa de direitos.</p>

<h2>7. Seus direitos</h2>
<p>Você pode pedir, a qualquer momento: confirmação de que tratamos seus dados, acesso, correção, anonimização, bloqueio
ou eliminação de dados desnecessários, portabilidade, informação sobre com quem compartilhamos, revogação do
consentimento e revisão de decisões automatizadas. Escreva para {_contato()}. Você também pode reclamar à Autoridade
Nacional de Proteção de Dados (ANPD).</p>

<h2>8. Segurança</h2>
<p>O site é servido com conexão segura (HTTPS), não tem área de login e não guarda senhas. Os acessos às ferramentas que
administram o site são protegidos e restritos.</p>

<h2>9. Cookies e anúncios</h2>
<p>Hoje não usamos cookies de publicidade. Se passarmos a exibir anúncios (por exemplo, do Google AdSense, que usa cookies
para personalizar e medir anúncios) ou ferramentas de medição com cookies, esta política será atualizada antes, e você
poderá escolher, quando a lei exigir.</p>

<h2>10. Mudanças nesta política</h2>
<p>Quando esta política mudar, a nova versão será publicada aqui, com a data de atualização. Mudanças importantes também
serão avisadas na newsletter.</p>
</section>"""


def termos() -> str:
    return f"""<section class="edicao"><h1>Termos de uso</h1>
<p class="suave">Última atualização: {ATUALIZADO}.</p>
<p>Ao usar o {config.NOME} (o site, a newsletter, o panorama diário e os canais oficiais), você concorda com estes termos.
Se não concordar, não use o serviço.</p>

<h2>1. O que é o serviço</h2>
<p>O {config.NOME} mede, de 0 a 100, o estresse dos mercados no mundo, em regiões e em países, e explica as leituras em
linguagem simples, com notícias e fontes. É um conteúdo <strong>educativo e informativo</strong>.</p>

<h2>2. Não é recomendação de investimento</h2>
<p>Nada no serviço é recomendação de compra, venda ou manutenção de qualquer ativo, análise de valor mobiliário,
consultoria ou planejamento financeiro personalizado. O conteúdo não considera a sua situação, os seus objetivos ou o seu
perfil. As decisões sobre o seu dinheiro são suas; se precisar, procure um profissional certificado e registrado na
Comissão de Valores Mobiliários (CVM), quando for o caso.</p>

<h2>3. Limites dos indicadores e dos dados</h2>
<ul>
<li>Os termômetros mostram o que já aconteceu nos mercados. Não preveem crises nem resultados futuros, e um bom
desempenho histórico do método não garante o mesmo comportamento no futuro.</li>
<li>Os dados vêm de fontes de terceiros (como FRED, datahub.io e Yahoo Finance) e podem ter atrasos, falhas ou
revisões. As cotações exibidas são de fechamento, não em tempo real.</li>
<li>Podemos corrigir números e textos a qualquer momento, quando encontrarmos erros.</li>
</ul>

<h2>4. Conteúdo produzido com inteligência artificial</h2>
<p>Parte dos textos é escrita por agentes de inteligência artificial e passa por conferências automáticas (números,
fontes, datas e linguagem). Mesmo assim, pode conter erros. As fontes ficam sempre linkadas para você conferir. Se
encontrar um erro, avise em {_contato()}.</p>

<h2>5. Propriedade intelectual</h2>
<p>A marca, o método, os textos e as imagens do {config.NOME} são protegidos. Você pode compartilhar trechos e os números
com link e citação da fonte. Não é permitido copiar o conteúdo em massa, revender ou apresentar como próprio. Notícias,
dados e marcas de terceiros pertencem aos respectivos titulares; os links externos levam a sites que não controlamos.</p>

<h2>6. Uso adequado</h2>
<p>Não use o serviço para fins ilegais, não tente invadir, sobrecarregar ou copiar o site de forma automatizada em grande
volume, e não use o nome do {config.NOME} para enganar outras pessoas.</p>

<h2>7. Newsletter, panorama e canais</h2>
<p>A inscrição é gratuita e você pode sair a qualquer momento, pelo link no fim de cada e-mail ou deixando de seguir o
canal. O tratamento dos seus dados segue a <a href="privacidade.html">política de privacidade</a>.</p>

<h2>8. Produtos pagos</h2>
<p>Se oferecermos cursos, assinaturas ou outros produtos pagos, eles terão condições próprias, informadas antes da compra.
Compras feitas pela internet têm direito de arrependimento em até 7 dias (art. 49 do Código de Defesa do Consumidor).</p>

<h2>9. Publicidade e parcerias</h2>
<p>Conteúdo patrocinado, anúncios e parcerias comerciais serão sempre identificados como publicidade.</p>

<h2>10. Responsabilidade</h2>
<p>Fazemos o possível para manter o serviço correto e disponível, mas ele é oferecido como está, sem garantia de que
estará sempre no ar ou livre de erros. Dentro do permitido pela lei, não respondemos por decisões de investimento ou
financeiras tomadas com base no conteúdo. Nada nestes termos limita os direitos garantidos pelo Código de Defesa do
Consumidor.</p>

<h2>11. Mudanças nestes termos</h2>
<p>Podemos atualizar estes termos. A versão em vigor é sempre a publicada aqui, com a data de atualização.</p>

<h2>12. Lei aplicável e contato</h2>
<p>Estes termos seguem as leis do Brasil. Para consumidores, vale o foro do seu domicílio. Dúvidas: {_contato()}.</p>
</section>"""


def quem_somos() -> str:
    responsavel = f" O responsável pelo projeto é {html.escape(config.RESPONSAVEL)}." if config.RESPONSAVEL else ""
    return f"""<section class="edicao"><h1>Quem somos</h1>
<p>O {config.NOME} é um projeto brasileiro independente que mede, de 0 a 100, o estresse dos mercados no mundo, em 6
regiões e em 19 países, e explica cada leitura em português simples, com as notícias que mexem com ela e a fonte de cada
fato.{responsavel}</p>
<h2>Como funciona</h2>
<p>Os números saem de um método aberto, descrito na <a href="metodologia.html">metodologia</a>: cada sinal (bolsa, sobe e
desce do mercado e moeda) é comparado com a história do próprio país. Uma equipe de agentes de inteligência artificial
coleta os dados, pesquisa as notícias, escreve os textos e confere tudo antes de publicar; as pessoas do projeto definem o
método, as regras e revisam o trabalho. Como fazemos isso está na <a href="politica-editorial.html">política editorial</a>.</p>
<h2>O que o {config.NOME} não é</h2>
<p>Não é uma corretora, não vende investimentos, não recomenda ativos e não faz consultoria. É conteúdo educativo e
informativo, para você entender o que está acontecendo e conversar melhor com quem cuida do seu dinheiro.</p>
<h2>Fale com a gente</h2>
<p>Sugestões, correções e parcerias: {_contato()}.</p>
</section>"""


def editorial() -> str:
    return f"""<section class="edicao"><h1>Política editorial</h1>
<p class="suave">Última atualização: {ATUALIZADO}.</p>
<h2>1. Fontes</h2>
<p>Damos preferência a fontes primárias (bancos centrais, governos, bolsas, organismos internacionais) e a agências e
jornais de referência. Fatos controversos precisam de duas fontes independentes. Toda notícia publicada traz o link da
fonte e a data em que o fato aconteceu.</p>
<h2>2. Status do fato</h2>
<p>Cada notícia é marcada como fato confirmado, operação em curso, ameaça ou declaração, negociação, ou hipótese e cenário.
Rumor nunca é tratado como fato.</p>
<h2>3. Uso de inteligência artificial</h2>
<p>Agentes de IA pesquisam, escrevem e conferem o conteúdo. Antes de publicar, um conjunto de conferências automáticas
verifica se os números batem com o cálculo, se cada link veio de uma busca real, se as datas são recentes e se o texto
evita recomendação, promessa e alarmismo. O que não passa não é publicado. Mesmo assim, erros podem acontecer.</p>
<h2>4. Correções</h2>
<p>Quando encontramos ou recebemos o aviso de um erro, corrigimos o mais rápido possível. Avise em {_contato()}.</p>
<h2>5. Neutralidade</h2>
<p>Descrevemos o que governos, partidos e empresas fizeram e disseram, sem opinar e com o mesmo tratamento para todos.</p>
<h2>6. Independência</h2>
<p>Nenhum patrocinador ou parceiro decide o que publicamos nem altera os números. Publicidade e parcerias, quando
existirem, serão sempre identificadas. Não recomendamos ativos nem recebemos por indicação de investimentos.</p>
<h2>7. Limites</h2>
<p>Os termômetros mostram o que já aconteceu; não preveem o futuro. Os dados de mercado vêm de terceiros e podem ter atrasos.</p>
</section>"""


CORRECOES: list[tuple[str, str, str]] = []  # (data, página, o que foi corrigido), mais recentes primeiro


def correcoes() -> str:
    itens = "".join(f"<li><strong>{html.escape(d)}</strong> · {html.escape(p)}: {html.escape(o)}</li>" for d, p, o in CORRECOES)
    lista = f"<ul>{itens}</ul>" if itens else "<p>Nenhuma correção registrada até agora.</p>"
    return f"""<section class="edicao"><h1>Correções</h1>
<p>Erros acontecem, inclusive em textos escritos com ajuda de inteligência artificial. Quando encontramos ou recebemos o
aviso de um erro, corrigimos a página o mais rápido possível (a meta é em até 48 horas), registramos aqui e deixamos na
própria página uma nota "Corrigido em…".</p>
<p>Viu algo errado? Escreva para {_contato()} com o endereço da página e o que está errado.</p>
<h2>Correções publicadas</h2>
{lista}
</section>"""
