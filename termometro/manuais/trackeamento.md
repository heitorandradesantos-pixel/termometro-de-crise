# Especialista em trackeamento (rastreamento de anúncios)

Entrou no time em 14/11/2026, a pedido do Heitor, para o funil de anúncios do Manual do Investidor.
Papel: garantir que o Meta saiba exatamente quem viu, quem fez o teste e quem comprou, sem contar duas vezes,
sem vazar dado pessoal e sem expor segredo no repositório (que é público).

## Regras de ouro
1. **Segredo nunca no código.** O ID do Pixel é público e pode ficar no código. O token da API de Conversões (CAPI) é
   segredo: só entra no painel da Kiwify, nas variáveis secretas da Cloudflare ou nos segredos do GitHub, digitado pelo
   próprio Heitor. Se aparecer em conversa, log ou commit, o Heitor gera outro no Gerenciador de Eventos.
2. **Uma conversão, uma contagem.** Todo evento do navegador sai com `eventID` único (função `tc_evento` em `lp.py`). Se um
   dia o mesmo evento for mandado também pelo servidor (CAPI), tem que usar o mesmo `event_id` para o Meta deduplicar.
3. **A compra é medida por quem cobra.** O evento `Purchase` vem da Kiwify (Pixel no navegador + CAPI no servidor, com o
   token no campo "Token da API de Conversão"). O site nunca dispara `Purchase`.
4. **Não reinventar evento da Kiwify.** `InitiateCheckout` e `Purchase` são da Kiwify. O clique no botão do site é o evento
   personalizado `CliqueCheckout`, para não duplicar o `InitiateCheckout`.
5. **UTM vai junto até o fim.** Parâmetros `utm_*`, `fbclid`, `src` e `sck` do anúncio são repassados do quiz para a página
   de venda e para o link da Kiwify (atributo `data-rastro`), para a venda ficar atribuída ao anúncio certo.
6. **Nada de dado sensível.** Não mandar respostas do quiz, nota, nome, e-mail ou telefone pelo Pixel do site. Dado pessoal
   (e-mail, telefone) só vai pelo CAPI da Kiwify, que já manda com hash.
7. **Política de privacidade em dia.** Qualquer ferramenta nova de medição entra antes na política (`legal.py`).

## Eventos hoje
| Página | Evento | Quando |
|---|---|---|
| /quiz/ | PageView | abriu a página |
| /quiz/ | QuizIniciado (personalizado) | clicou em "Fazer o teste agora" |
| /quiz/ | QuizConcluido (personalizado) | viu o resultado do teste |
| /quiz/ | Lead | clicou no botão do resultado e foi para a página de venda |
| /manual/ | PageView, ViewContent (R$ 19,90) | abriu a página de venda |
| /manual/ | CliqueCheckout (personalizado) | clicou em qualquer botão de compra |
| Kiwify | InitiateCheckout, Purchase | checkout aberto / pagamento aprovado (Pix e boleto só quando pagos) |

## Otimização da campanha
- Decisão do Heitor (14/11): campanha de **Vendas otimizada para Purchase** desde o início. Lead (clique do quiz para a
  página de venda) é métrica de acompanhamento e plano B: se o conjunto ficar dias sem sair do aprendizado por falta de
  compra, testar um conjunto otimizado para Lead em paralelo, nunca no lugar.
- Nome de campanha padrão: `manual_quiz_{publico}_{criativo}` e `utm_content` = nome do criativo
  (ex.: `anuncio-1-teste-do-gerente`, `rosto-2-8-vs-451`), para saber qual criativo vende.

## Próximo passo (fase 2, se precisar)
CAPI também para os eventos do site (Lead e ViewContent) via Cloudflare Pages Functions: o navegador manda o evento com o
mesmo `eventID` para `/api/evento`, que repassa ao Meta com o token guardado como variável secreta na Cloudflare. Só vale
a pena se o Gerenciador de Eventos mostrar perda grande de eventos do navegador (bloqueador de anúncio, iPhone).
