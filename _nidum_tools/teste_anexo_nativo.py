# -*- coding: ascii -*-
"""
Teste OFFLINE do ANEXO NATIVO da tool gerador_de_arquivos_nidum (2.8.0).

POR QUE ESTE TESTE EXISTE (03/09/2026): o frontend faz
    message.files = data.files            (Chat.svelte:523)
ou seja, SUBSTITUI a lista a cada evento. Um pedido como "entregue em HTML e
tambem em PPTX" - caso central da Fase D - emitiria dois eventos, e o segundo
apagaria o primeiro da mensagem. Trocar o 404 (visivel) por um arquivo que some
(invisivel) seria pior que o estado anterior.

O que este teste trava:
  1. ACUMULACAO: dois arquivos na MESMA mensagem -> o segundo evento carrega os
     DOIS. Este e o requisito, nao um caso de borda.
  2. ISOLAMENTO: mensagens diferentes nao se misturam.
  3. IDEMPOTENCIA: reemitir o mesmo arquivo nao duplica.
  4. FALLBACK DECLARADO: sem emitter, nada estoura e o chamador sabe (False).
  5. TETO DE MEMORIA: o cache por mensagem nao cresce sem limite.

USO:  py _nidum_tools/teste_anexo_nativo.py
"""

import ast
import asyncio
import contextvars
import io
import logging
import os
import sys

logging.basicConfig(level=logging.CRITICAL)

CAMINHO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "gerador_de_arquivos_nidum.py")


def carregar():
    # Carrega SO os helpers de anexo, sem importar o modulo inteiro (ele depende
    # do open_webui, que nao existe fora do servidor). Mesmo padrao das outras
    # suites offline da casa.
    fonte = io.open(CAMINHO, encoding="ascii").read()
    arvore = ast.parse(fonte)
    ns = {"log": logging.getLogger("t"), "inspect": __import__("inspect"),
          "contextvars": contextvars}
    alvos = {"_registrar_arquivo", "_emitir_arquivo", "_ctx_entrega"}
    globais = {"_ARQUIVOS_POR_MENSAGEM", "_MAX_MENSAGENS_EM_CACHE",
               "_CTX_EMITTER", "_CTX_MESSAGE_ID"}
    for no in arvore.body:
        if isinstance(no, ast.Assign):
            nomes = [t.id for t in no.targets if isinstance(t, ast.Name)]
            if any(n in globais for n in nomes):
                exec(compile(ast.Module([no], []), "<x>", "exec"), ns)
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name in alvos:
            exec(compile(ast.Module([no], []), "<x>", "exec"), ns)
    faltando = [a for a in alvos | globais if a not in ns]
    if faltando:
        print("ERRO: nao encontrei no fonte: %s" % ", ".join(sorted(faltando)))
        sys.exit(1)
    return ns


class EmitterFalso:
    def __init__(self):
        self.eventos = []

    async def __call__(self, ev):
        self.eventos.append(ev)

    @property
    def ultima_lista(self):
        return self.eventos[-1]["data"]["files"] if self.eventos else []


def nomes(lista):
    return [f.get("name") for f in lista]


async def principal():
    ns = carregar()
    emitir = ns["_emitir_arquivo"]
    cache = ns["_ARQUIVOS_POR_MENSAGEM"]
    falhas = []

    def checar(rotulo, condicao, detalhe=""):
        if condicao:
            print("  OK   %s" % rotulo)
        else:
            print("  FALHA %s %s" % (rotulo, detalhe))
            falhas.append(rotulo)

    # ---- 1. ACUMULACAO: o caso "HTML e tambem PPTX" -------------------------
    cache.clear()
    em = EmitterFalso()
    ok1 = await emitir(em, "msg-1", "id-html", "REL.html", "text/html", "/a/html")
    ok2 = await emitir(em, "msg-1", "id-pptx", "DECK.pptx", "application/x", "/a/pptx")
    checar("dois arquivos: os dois eventos foram entregues", ok1 and ok2)
    checar("dois arquivos: o 2o evento carrega OS DOIS (acumulou)",
           nomes(em.ultima_lista) == ["REL.html", "DECK.pptx"],
           repr(nomes(em.ultima_lista)))
    checar("dois arquivos: o 1o evento carregava so o primeiro",
           nomes(em.eventos[0]["data"]["files"]) == ["REL.html"])

    # ---- 2. ISOLAMENTO entre mensagens --------------------------------------
    em2 = EmitterFalso()
    await emitir(em2, "msg-2", "id-outro", "OUTRO.pdf", "application/pdf", "/a/pdf")
    checar("mensagem nova nao herda arquivo da anterior",
           nomes(em2.ultima_lista) == ["OUTRO.pdf"], repr(nomes(em2.ultima_lista)))

    # ---- 3. IDEMPOTENCIA -----------------------------------------------------
    em3 = EmitterFalso()
    await emitir(em3, "msg-1", "id-html", "REL.html", "text/html", "/a/html")
    checar("reemitir o mesmo id nao duplica",
           nomes(em3.ultima_lista) == ["REL.html", "DECK.pptx"],
           repr(nomes(em3.ultima_lista)))

    # ---- 3b. REGERAR O MESMO NOME SUBSTITUI (medido em producao) -----------
    # O modelo chamou gerar_html duas vezes na mesma resposta: dois uuid, um nome so.
    # Dedupe por id nao pegava e o usuario via tres cards (HTML, PPTX, HTML).
    cache.clear()
    em4 = EmitterFalso()
    await emitir(em4, "msg-r", "id-h1", "REL.html", "text/html", "/a/h1")
    await emitir(em4, "msg-r", "id-pptx", "DECK.pptx", "application/x", "/a/pptx")
    await emitir(em4, "msg-r", "id-h2", "REL.html", "text/html", "/a/h2")
    checar("regerar o mesmo NOME substitui, nao duplica",
           nomes(em4.ultima_lista) == ["REL.html", "DECK.pptx"],
           repr(nomes(em4.ultima_lista)))
    checar("substituicao mantem a POSICAO original",
           em4.ultima_lista[0]["name"] == "REL.html", repr(em4.ultima_lista))
    checar("substituicao usa a VERSAO NOVA do arquivo",
           em4.ultima_lista[0]["id"] == "id-h2", repr(em4.ultima_lista[0]))

    # ---- 4. FALLBACK: sem emitter, devolve False e nao estoura --------------
    resultado = await emitir(None, "msg-3", "id-x", "X.docx", "application/x", "/a/x")
    checar("sem emitter -> False (chamador cai no link declarado)",
           resultado is False, repr(resultado))

    # ---- 4b. emitter que EXPLODE nao derruba a geracao ----------------------
    async def emitter_quebrado(ev):
        raise RuntimeError("socket morreu")

    resultado = await emitir(emitter_quebrado, "msg-4", "id-y", "Y.pdf", "a/b", "/a/y")
    checar("emitter com erro -> False, sem propagar excecao", resultado is False)

    # ---- 4c. sem message_id (fora de um chat) -------------------------------
    em5 = EmitterFalso()
    await emitir(em5, None, "id-z", "Z.xlsx", "a/b", "/a/z")
    checar("sem message_id -> entrega so o item, sem quebrar",
           nomes(em5.ultima_lista) == ["Z.xlsx"])

    # ---- 5. TETO DE MEMORIA --------------------------------------------------
    cache.clear()
    teto = ns["_MAX_MENSAGENS_EM_CACHE"]
    em6 = EmitterFalso()
    for i in range(teto + 25):
        await emitir(em6, "m%d" % i, "f%d" % i, "F%d.pdf" % i, "a/b", "/a/%d" % i)
    checar("cache por mensagem respeita o teto (%d)" % teto,
           len(cache) <= teto, "tamanho=%d" % len(cache))

    print("")
    if falhas:
        print("ANEXO NATIVO: %d FALHA(S) - %s" % (len(falhas), "; ".join(falhas)))
        sys.exit(1)
    print("ANEXO NATIVO OK")


if __name__ == "__main__":
    asyncio.run(principal())
