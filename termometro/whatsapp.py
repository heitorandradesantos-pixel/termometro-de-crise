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
import shutil
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
NOMES = {"fechamento": "O fechamento", "abertura": "A abertura"}


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
    if envio.get("modo") == "sim" or resultado.get("ok"):
        registrar(pasta_diario / envio["dia"], tipo, resultado, envio.get("modo"))
    return (f"{NOMES[tipo]} de {envio['dia']}: enviado ({envio.get('modo')})." if resultado.get("ok")
            else f"{NOMES[tipo]} de {envio['dia']}: o envio falhou.")
