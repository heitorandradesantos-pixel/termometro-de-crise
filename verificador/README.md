# Verificador de Boleto e Pix (motor)

Triagem de risco antes de pagar: 🟢 verde, 🟡 amarelo ou 🔴 vermelho, sempre com os motivos. Não é garantia.

- `motor.mjs`: sem dependências, roda no navegador e na Cloudflare.
  - `lerBoleto`: linha digitável (47), conta de consumo/tributo (48) ou código de barras (44). Confere os dígitos e extrai banco, valor e vencimento.
  - `lerPix`: Pix copia e cola (BR Code). Confere o CRC e extrai chave, tipo de chave, recebedor, cidade e valor.
  - `avaliar(codigo, esperado, cnpjInfo, fornecedor)`: cruza tudo e devolve o nível de risco e os motivos.
- Testes: `node --test verificador/motor.test.mjs`. Usam boletos e Pix montados no teste, nunca dados reais de clientes.
- Próximos passos: consulta pública de CNPJ (proxy na Cloudflare), página `/boleto/`, leitura da foto por IA
  (a chave fica como segredo na Cloudflare, colocada pelo Heitor), memória de fornecedor e lote para empresas (B2B).
