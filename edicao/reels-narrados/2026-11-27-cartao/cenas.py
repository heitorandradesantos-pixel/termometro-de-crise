cena(0, lambda D: f'''<div class="col c">{R("div","k vm","0.15","DÍVIDA NO CARTÃO")}
 {R("div","num md","0.25","R$ 1.000")}
 {R("h2","h lg",D("w:quanto isso"),"Quanto isso vira<br>em <b>um ano</b>?")}
 {R("div","faixa",D("w:e uma regra"),"E tem uma regra que <b>quase ninguém conhece</b>.")}
 {R("span","chip am",D("p1"),"Faz a conta comigo")}</div>''')

cena(2, lambda D: f'''<div class="col c">{R("div","k vm","0.15","JURO DO ROTATIVO DO CARTÃO")}
 {R("div","num vmn",D("w:passa de|-0.2"),cnt(0,450,0,D("w:passa de"),1.5,"+","%"))}
 {R("p","s lgs",D("w:por cento ao ano"),"<b>ao ano</b>")}
 {R("span","chip gr",D("w:uns quinze"),"≈ 15% ao mês")}
 {R("div","src","1.0","Fonte: Banco Central (taxa média do rotativo: 451,7% ao ano em setembro de 2026)")}</div>''')

cena(3, lambda D: f'''<div class="col c">{R("div","k","0.15","PRIMEIRO MÊS")}
 {R("div","num pqn","0.3","R$ 1.000")}{R("div","seta2","0.6","↓")}
 {R("div","num md",D("w:viram|-0.3"),cnt(1000,1150,0,D("w:viram"),1.2,"R$ ",""))}
 {R("span","chip am",D("p4|0.8"),"📌 R$ 150 de juro em 30 dias")}</div>''')

cena(5, lambda D: f'''<div class="col c">{R("div","k","0.15","AGORA COMPARA: R$ 1.000")}
 <div class="barras">
  <div class="lin r" data-d="0.5"><span class="rot">💳 Juro do cartão em <b>1 mês</b></span><div class="tr"><div class="bar vmb" data-w="100" data-d="0.7" data-dur="1.0"></div></div><span class="val vmt">R$ 153</span></div>
  <div class="lin r" data-d="{D("w:rendem|-0.6")}"><span class="rot">💰 Rendimento a 100% do CDI em <b>1 ano</b></span><div class="tr"><div class="bar" data-w="89" data-d="{D("w:rendem|-0.3")}" data-dur="1.0"></div></div><span class="val am">R$ 136</span></div>
 </div>
 {R("div","faixa",D("p6"),"O cartão cobra em <b>1 mês</b> mais do que o seu dinheiro rende em <b>1 ano</b>.")}
 {R("div","src","1.0","Simulação: 15,3% ao mês no rotativo; CDI de 13,65% ao ano, antes do imposto.")}</div>''')

cena(7, lambda D: f'''<div class="col c">{R("div","k vm","0.15","SE ESSA CONTA RODASSE SOLTA POR 12 MESES")}
 {R("div","num pqn","0.3","R$ 1.000")}{R("div","seta2","0.6","↓")}
 {R("div","num md vmn",D("w:virariam|-0.3"),cnt(1000,5500,0,D("w:virariam"),1.5,"R$ ",""))}
 {R("p","s lgs",D("w:virariam|1.2"),"mais de <b>5 vezes</b> a dívida")}</div>''')

cena(8, lambda D: f'''<div class="col c">{R("h1","h xl","0.2","Mas existe<br>um <b>teto</b>.")}
 {R("div","k",D("p9"),"DESDE JANEIRO DE 2024")}
 {R("div","faixa",D("w:os juros e encargos"),"Juros e encargos do rotativo e do parcelamento da fatura: no máximo <b>100% da dívida original</b>.")}
 {R("div","src","1.0","Fonte: Lei 14.690/2023 e Resolução CMN 5.112/2023")}</div>''')

cena(10, lambda D: f'''<div class="col c">{R("div","k","0.15","NA PRÁTICA")}
 {R("div","num pqn","0.3","Deve R$ 1.000")}
 {R("p","s lgs",D("w:paga"),"paga, no máximo:")}
 {R("div","num md",D("w:dois mil|-0.2"),"R$ 2.000")}
 {R("span","chip",D("w:mais o imposto"),"+ imposto (IOF)")}
 {R("div","faixa",D("p11"),"É um alívio? É. Mas é <b>pagar o dobro</b>.")}</div>''')

cena(12, lambda D: f'''<div class="col e">{R("div","k","0.15","GUARDA 3 COISAS")}
 <ol class="tres">{R("li","",D("p13"),"<i>1</i><span>Pagar só o <b>mínimo da fatura</b> é entrar nessa conta</span>")}
 {R("li","",D("p14"),"<i>2</i><span>Dívida de cartão vem <b>antes de qualquer investimento</b></span>")}
 {R("li","",D("p15"),"<i>3</i><span>Passou do dobro? <b>Confere a fatura</b> e questiona o banco</span>")}</ol></div>''')

cena(16, lambda D: f'''<div class="col c">{R("h1","h xl","0.2","Você sabia<br>desse <b>teto</b>?")}
 <div class="chips g">{R("span","chip gr",D("w:sim"),"SIM")}{R("span","chip gr",D("w:não"),"NÃO")}</div>
 {R("p","s","0.8","Comenta aqui 👇")}</div>''')
