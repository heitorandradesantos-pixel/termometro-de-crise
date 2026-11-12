"""Envio automático para a comunidade do WhatsApp.

Quem conecta e manda é o whatsapp/enviar.mjs, com o Baileys (código aberto que liga o número como um "aparelho
conectado", igual ao WhatsApp Web). Este módulo prepara o que vai (o card do fechamento, o texto do balanço e o
panorama do dia) e guarda o registro de cada envio, para um horário de reserva nunca mandar duas vezes.

Modo do envio: a variável WHATSAPP_ENVIO do GitHub, se existir; senão, o arquivo whatsapp/modo.txt.
- "nao": não envia;
- "teste": manda para o próprio número ligado (conversa "você"), para conferir;
- "sim": manda para o grupo de avisos da comunidade.

Recomendação: poucos envios por dia, sempre para a própria comunidade (o WhatsApp não autoriza oficialmente esse
tipo de conexão; envio em massa para desconhecidos é o que leva a bloqueio).
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ARQ_MODO = RAIZ / "whatsapp" / "modo.txt"


def modo() -> str:
    m = (os.environ.get("WHATSAPP_ENVIO") or "").strip().lower()
    if not m and ARQ_MODO.exists():
        m = ARQ_MODO.read_text().strip().lower()
    return m if m in ("nao", "teste", "sim") else "nao"


def ja_enviado(pasta_dia: Path, o_que: str, como: str | None = None) -> bool:
    arq = pasta_dia / "whatsapp.json"
    como = como or modo()
    return arq.exists() and any(e.get("o_que") == o_que and e.get("modo") == como and e.get("ok", True)
                                for e in json.loads(arq.read_text()))


def registrar(pasta_dia: Path, o_que: str, resultado: dict, como: str | None = None) -> None:
    pasta_dia.mkdir(parents=True, exist_ok=True)  # de manhã a pasta do dia ainda não existe
    arq = pasta_dia / "whatsapp.json"
    lista = json.loads(arq.read_text()) if arq.exists() else []
    lista.append({"o_que": o_que, "modo": como or modo(), "ok": bool(resultado.get("ok")),
                  "quando": pd.Timestamp.now(tz="America/Sao_Paulo").isoformat(),
                  "mensagens": len(resultado.get("ids") or [])})
    arq.write_text(json.dumps(lista, ensure_ascii=False, indent=1))


def sem_link_do_site(texto: str) -> str:
    """Tira a linha "o porquê de cada número... <link>" dos panoramas gravados antes dessa mudança."""
    linhas = [li for li in texto.strip().splitlines() if "porquê de cada número" not in li]
    saida = "\n".join(linhas)
    while "\n\n\n" in saida:
        saida = saida.replace("\n\n\n", "\n\n")
    return saida


def mensagens(pasta_diario: Path, dia: str, pasta_trabalho: Path) -> dict | None:
    """O envio do fechamento: o card com o texto do balanço e, depois, o panorama do dia."""
    from . import fechamento as fch
    gerado = fch.gerar(pasta_trabalho, pasta_diario, dia)
    panorama = pasta_diario / dia / "panorama.txt"
    if not gerado and not panorama.exists():
        return None
    envio = {"dia": dia, "textos": []}
    if gerado:
        envio["imagem"] = str((pasta_trabalho / gerado["imagem"]).resolve())
        envio["legenda"] = gerado["legenda"]
    if panorama.exists():
        envio["textos"].append(sem_link_do_site(panorama.read_text()))
    return envio


def mensagens_abertura(pasta_diario: Path, pasta_trabalho: Path) -> dict | None:
    """A abertura: o card com o texto inteiro na legenda (se couber) ou o card e o texto em seguida."""
    from . import abertura
    gerado = abertura.gerar(pasta_diario, pasta_trabalho)
    if not gerado:
        return None
    envio = {"dia": gerado["dia"], "textos": []}
    if gerado["imagem"] and len(gerado["texto"]) <= LEGENDA_MAXIMA:
        envio.update(imagem=gerado["imagem"], legenda=gerado["texto"])
    elif gerado["imagem"]:
        envio.update(imagem=gerado["imagem"], legenda=gerado["texto"].splitlines()[0], textos=[gerado["texto"]])
    else:
        envio["legenda"] = gerado["texto"]
    return envio


LEGENDA_MAXIMA = 1000  # o WhatsApp corta legendas de imagem perto de 1.024 caracteres
NOMES = {"fechamento": "O fechamento", "abertura": "A abertura", "roteiros": "Os roteiros",
         "fimdesemana": "A edição de domingo", "ideias": "As ideias de Reels", "ranking": "O ranking da semana"}


def preparar(pasta_diario: Path, dia: str, pasta_saida: Path, teste: bool = False, tipo: str = "fechamento") -> str:
    """Grava pasta_saida/envio.json quando há o que mandar. Devolve o que aconteceu, em uma frase."""
    como = "teste" if teste else modo()
    if como == "nao":
        return "Envio ao WhatsApp desligado (whatsapp/modo.txt ou variável WHATSAPP_ENVIO)."
    if tipo == "abertura":
        dia = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
    if not dia:
        return "Sem fechamento no diário: nada a enviar."
    if not teste and ja_enviado(pasta_diario / dia, tipo, como):
        return f"{NOMES[tipo]} de {dia} já foi enviada ({como})." if tipo == "abertura" else \
            f"O fechamento de {dia} já foi enviado ({como})."
    if pasta_saida.exists():
        shutil.rmtree(pasta_saida)
    pasta_saida.mkdir(parents=True)
    envio = mensagens_abertura(pasta_diario, pasta_saida) if tipo == "abertura" else mensagens(pasta_diario, dia, pasta_saida)
    if not envio:
        shutil.rmtree(pasta_saida)
        return (f"Sem abertura hoje ({dia}): a B3 não abriu." if tipo == "abertura"
                else f"Sem card nem panorama de {dia}: nada enviado.")
    envio["modo"], envio["tipo"] = como, tipo
    (pasta_saida / "envio.json").write_text(json.dumps(envio, ensure_ascii=False, indent=1))
    return f"{NOMES[tipo]} de {dia} pronta para enviar ({como})." if tipo == "abertura" else \
        f"Fechamento de {dia} pronto para enviar ({como})."


def concluir(pasta_diario: Path, pasta_saida: Path) -> str:
    """Lê o resultado do enviar.mjs e guarda no registro do dia."""
    arq, res = pasta_saida / "envio.json", pasta_saida / "envio.json.resultado.json"
    if not arq.exists():
        return "Nada foi preparado para enviar."
    envio = json.loads(arq.read_text())
    tipo = envio.get("tipo", "fechamento")
    resultado = json.loads(res.read_text()) if res.exists() else {"ok": False}
    if tipo == "roteiros":
        return concluir_roteiros(envio, resultado)
    if tipo == "ideias":
        if not resultado.get("ok"):
            return "Ideias de Reels: o envio falhou."
        from . import referencias
        referencias.marcar_ideias(pasta_diario / "referencias", envio.get("ideias", []))
        return f"Ideias de Reels: {len(envio.get('ideias', []))} enviada(s) para a conversa do próprio número."
    if tipo == "ranking":
        return "Ranking da semana: " + ("enviado para a conversa do próprio número." if resultado.get("ok") else "o envio falhou.")
    if envio.get("modo") == "sim" or resultado.get("ok"):
        registrar(pasta_diario / envio["dia"], tipo, resultado, envio.get("modo"))
    return (f"{NOMES[tipo]} de {envio['dia']}: enviado ({envio.get('modo')})." if resultado.get("ok")
            else f"{NOMES[tipo]} de {envio['dia']}: o envio falhou.")


# ---------------------------------------------------------------- roteiros para gravar

ROTEIROS_TIPOS = tuple(t.strip() for t in (os.environ.get("ROTEIROS_WHATSAPP")
                                          or "explica,fixado,abertura,fechamento").split(",") if t.strip())
ROTEIROS_DESDE = os.environ.get("ROTEIROS_DESDE") or "2026-11-09"  # o Heitor começa a gravar na segunda


def _titulo_roteiro(pasta_diario: Path, dia: str, arq: Path) -> str:
    tipo = arq.stem.split("-")[0]
    titulo = json.loads(arq.read_text()).get("titulo")
    if titulo:
        return titulo
    if tipo == "explica":
        artigo = pasta_diario / "plantao" / f"{dia}-{arq.stem[len('explica-'):]}.json"
        if artigo.exists():
            return json.loads(artigo.read_text()).get("titulo", arq.stem)
    return f"{tipo.capitalize()} de {dia[8:10]}/{dia[5:7]}"


RAIZ = Path(__file__).resolve().parent.parent
FOTOS_CAPA = RAIZ / "edicao" / "capa" / "fotos"
REMOTION = RAIZ / "edicao" / "remotion"


def texto_capa(roteiro: dict) -> str:
    """O texto da capa: o cartão do gancho (até 6 palavras), com o primeiro número em amarelo."""
    tela = next((t["texto"] for t in roteiro.get("na_tela") or [] if t.get("fala") == 0 and t.get("texto")), "")
    tela = tela or roteiro["linhas"][0]
    if "*" not in tela:
        tela = re.sub(r"((?:R\$|US\$)\s?[\d.,]+(?:\s(?:mil|milhões|bilhões))?|[\d.,]*\d%?)", r"*\1*", tela, count=1)
    return tela


def capa_roteiro(roteiro: dict, nome: str, saida: Path) -> Path | None:
    """Capa com texto gigante (Remotion). Só roda onde a Remotion está instalada (CAPAS=1 no robô); se falhar, segue sem."""
    if os.environ.get("CAPAS") != "1" or not (REMOTION / "node_modules").exists():
        return None
    fotos = sorted(FOTOS_CAPA.glob("*.jpg"))
    if not fotos:
        return None
    foto = fotos[sum(map(ord, nome)) % len(fotos)].name
    props = json.dumps({"foto": foto, "texto": texto_capa(roteiro)}, ensure_ascii=False)
    try:
        cmd = ["npx", "remotion", "still", "Capa", str(saida.resolve()), f"--props={props}",
               f"--public-dir={FOTOS_CAPA}", "--log=error"]
        navegador = os.environ.get("REMOTION_NAVEGADOR") or next((str(x) for x in Path("/opt/pw-browsers").glob(
            "chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell")), "")
        if navegador:  # onde a rede não deixa a Remotion baixar o navegador dela
            cmd.append(f"--browser-executable={navegador}")
        subprocess.run(cmd, check=True, cwd=REMOTION, timeout=300)
        return saida if saida.exists() else None
    except (subprocess.SubprocessError, OSError) as erro:
        print(f"  capa não saiu ({erro}); segue sem")
        return None


def preparar_roteiros(pasta_diario: Path, dia: str, pasta_saida: Path) -> str:
    """Os roteiros aprovados do dia que ainda não foram para a conversa do próprio número (para o Heitor gravar)."""
    from . import roteirista
    if dia < ROTEIROS_DESDE:
        return f"Os roteiros para gravar começam em {ROTEIROS_DESDE}; nada enviado."
    pasta = pasta_diario / dia / "roteiros"
    novos = []
    for arq in sorted(pasta.glob("*.json")) if pasta.is_dir() else []:
        r = json.loads(arq.read_text())
        if arq.stem.split("-")[0] in ROTEIROS_TIPOS and r.get("aprovado") and r.get("teleprompter") \
                and not r.get("enviado_whatsapp"):
            novos.append((arq, r))
    if not novos:
        return f"Nenhum roteiro novo de {dia} para mandar."
    if pasta_saida.exists():
        shutil.rmtree(pasta_saida)
    pasta_saida.mkdir(parents=True)
    textos = []
    for n, (arq, r) in enumerate(novos, 1):
        pacote = roteirista.pacote_whatsapp(r, _titulo_roteiro(pasta_diario, dia, arq), n, len(novos))
        if capa := capa_roteiro(r, arq.stem, pasta_saida / f"capa-{n}.png"):
            pacote.insert(1, {"imagem": capa.name, "legenda": "🖼️ Capa sugerida: na hora de postar, Editar capa > "
                                                          "Adicionar da galeria (Instagram e TikTok)."})
        textos += pacote
    if aviso := (os.environ.get("AVISO_ROTEIROS") or "").strip():  # ex.: "GRAVAR A PARTIR DAQUI", antes de tudo
        textos.insert(0, aviso)
    envio = {"modo": "teste", "dia": dia, "tipo": "roteiros", "textos": textos, "roteiros": [str(a) for a, _ in novos]}
    (pasta_saida / "envio.json").write_text(json.dumps(envio, ensure_ascii=False, indent=1))
    return f"{len(novos)} roteiro(s) de {dia} prontos para mandar (conversa do próprio número)."


def concluir_roteiros(envio: dict, resultado: dict) -> str:
    if not resultado.get("ok"):
        return f"Roteiros de {envio['dia']}: o envio falhou."
    quando = pd.Timestamp.now(tz="America/Sao_Paulo").isoformat()
    for caminho in envio.get("roteiros", []):
        arq = Path(caminho)
        if arq.exists():
            r = json.loads(arq.read_text())
            arq.write_text(json.dumps({**r, "enviado_whatsapp": quando}, ensure_ascii=False, indent=1))
    return f"Roteiros de {envio['dia']}: {len(envio.get('roteiros', []))} enviado(s) para a conversa do próprio número."


# ---------------------------------------------------------------- ranking da semana (painel de desempenho)

def preparar_ranking(pasta_saida: Path) -> str:
    """Sábado de manhã, na conversa do próprio número: os 3 posts da semana que mais aguentam anúncio."""
    from . import painel
    senha = os.environ.get("PAINEL_SENHA", "")
    if not senha or not painel.ARQ.exists():
        return "Ranking: o painel ainda não tem dados (falta PAINEL_SENHA ou a primeira atualização)."
    dados, _ = painel.ler(senha)
    if not dados:
        return "Ranking: não deu para abrir os dados do painel."
    if pasta_saida.exists():
        shutil.rmtree(pasta_saida)
    pasta_saida.mkdir(parents=True)
    dia = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
    envio = {"modo": "teste", "dia": dia, "tipo": "ranking", "textos": [painel.ranking(dados)]}
    (pasta_saida / "envio.json").write_text(json.dumps(envio, ensure_ascii=False, indent=1))
    return "Ranking da semana pronto para mandar (conversa do próprio número)."


# ---------------------------------------------------------------- ideias de Reels (das referências)

def preparar_ideias(pasta_diario: Path, pasta_saida: Path, maximo: int = 6) -> str:
    """Um resumo por dia, na conversa do próprio número, com os assuntos das referências que viram Reel nosso."""
    from . import referencias
    itens, descartadas = referencias.selecionar_ideias(referencias.ideias_pendentes(pasta_diario / "referencias"),
                                                       maximo)
    if descartadas:  # repetidas ou sem ângulo de bolso: não voltam amanhã
        referencias.marcar_ideias(pasta_diario / "referencias", descartadas)
    if not itens:
        return "Nenhuma ideia de Reel nova."
    if pasta_saida.exists():
        shutil.rmtree(pasta_saida)
    pasta_saida.mkdir(parents=True)
    dia = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d")
    envio = {"modo": "teste", "dia": dia, "tipo": "ideias", "textos": [referencias.mensagem_ideias(itens, maximo)],
             "ideias": [k for k, _ in itens]}
    (pasta_saida / "envio.json").write_text(json.dumps(envio, ensure_ascii=False, indent=1))
    return f"{len(itens)} ideia(s) de Reel prontas para mandar (conversa do próprio número)."
