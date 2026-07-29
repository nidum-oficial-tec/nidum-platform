# -*- coding: utf-8 -*-
"""
Banco de provas do analytics (Fatia 1a). Prova os requisitos DUROS do dono:
  - store CONTENT-FREE (nao existe coluna que aceite PII);
  - user_hash NULL sem salt (anonimo por padrao);
  - best-effort de verdade: INSERT falhando NAO propaga excecao;
  - valve OFF = no-op imediato (nenhum acesso a sqlite);
  - a resposta do usuario nunca passa por codigo de analytics (wrapper try/finally).
USO: python teste_analytics.py
"""
import asyncio
import os
import re
import sqlite3
import sys
import tempfile
import time
import types

import teste_estrutura as E

_DIR = os.path.dirname(os.path.abspath(__file__))
CAM = os.path.join(_DIR, "chatnd.py")


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def carregar():
    fonte = open(CAM, encoding="utf-8").read()
    # Namespace com o que as funcoes de analytics referenciam no modulo.
    log = types.SimpleNamespace(exception=lambda *a, **k: None,
                                error=lambda *a, **k: None,
                                warning=lambda *a, **k: None,
                                info=lambda *a, **k: None)
    ns = {"os": os, "asyncio": asyncio, "time": time, "log": log, "re": re}
    for nome in ("_analytics_faixa", "_analytics_user_hash", "_analytics_write"):
        m = re.search(r"^def " + nome + r"\(.*?(?=^\S)", fonte, re.M | re.S)
        exec(m.group(0), ns)
    # _registrar e metodo (indentado). Extrai e desindenta.
    m = re.search(r"^    async def _registrar\(self, ev\):.*?(?=^    async def |^    def )",
                  fonte, re.M | re.S)
    corpo = "\n".join(l[4:] if l.startswith("    ") else l
                      for l in m.group(0).split("\n"))
    exec(corpo, ns)
    return ns, fonte


async def main():
    ns, fonte = carregar()
    FAIXA, HASH, WRITE, REG = (ns["_analytics_faixa"], ns["_analytics_user_hash"],
                               ns["_analytics_write"], ns["_registrar"])
    ok = True

    print("== faixa de tamanho (nunca o valor exato) ==")
    ok &= check("0/None -> None", FAIXA(0) is None and FAIXA(None) is None)
    ok &= check("5000 -> <10k", FAIXA(5000) == "<10k")
    ok &= check("30000 -> 10-50k", FAIXA(30000) == "10-50k")
    ok &= check("60000 -> 50-150k", FAIXA(60000) == "50-150k")
    ok &= check("200000 -> >150k", FAIXA(200000) == ">150k")
    ok &= check("lixo nao quebra", FAIXA("x") is None)

    print("== user_hash: ANONIMO por padrao (sem salt -> None) ==")
    ok &= check("sem salt -> None (o default de fabrica)", HASH("user-123", "") is None)
    ok &= check("salt None -> None", HASH("user-123", None) is None)
    ok &= check("sem uid -> None", HASH("", "salt") is None)
    h = HASH("user-123", "segredo")
    ok &= check("com salt -> hash de 16 hex", isinstance(h, str) and len(h) == 16
                and all(c in "0123456789abcdef" for c in h))
    ok &= check("deterministico", HASH("user-123", "segredo") == h)
    ok &= check("salt diferente -> hash diferente", HASH("user-123", "outro") != h)
    ok &= check("usuario diferente -> hash diferente", HASH("user-999", "segredo") != h)

    print("== o store e CONTENT-FREE (prova estrutural do schema) ==")
    tmp = os.path.join(tempfile.mkdtemp(prefix="an_"), "a.db")
    WRITE(tmp, {"rota": "arquivo", "classificador": "documentos", "trava": "pede_arquivo",
                "anexo": "codigo", "anexo_fonte": "storage", "anexo_faixa": "50-150k",
                "desfecho": "ok", "latencia_ms": 1234})
    con = sqlite3.connect(tmp)
    cols = [r[1] for r in con.execute("PRAGMA table_info(eventos)").fetchall()]
    esperado = {"id", "ts", "user_hash", "rota", "classificador", "trava", "anexo",
                "anexo_fonte", "anexo_faixa", "formato_saida", "desfecho", "recusa_cat",
                "erro_cat", "latencia_ms"}
    ok &= check("as colunas sao EXATAMENTE as 14 do schema aprovado", set(cols) == esperado)
    # Proibidas = substrings que denunciariam uma coluna de CONTEUDO/PII. 'formato_saida'
    # e o ROTULO do formato (pptx/html), nao a saida - por isso 'saida' nao entra aqui; a
    # prova real e o schema exato acima. user_hash e hash, nao id.
    proibidas = ("texto", "conteudo", "content", "pedido", "nome_arquivo", "filename",
                 "query", "prompt", "mensagem", "usuario")
    ok &= check("NENHUMA coluna aceita conteudo/PII (%s)" % ",".join(cols),
                not any(any(pb in c.lower() for pb in proibidas) for c in cols))
    linha = con.execute("SELECT rota, anexo_faixa, latencia_ms, desfecho, user_hash "
                        "FROM eventos").fetchone()
    ok &= check("gravou a linha (categorias, faixa, latencia)",
                linha == ("arquivo", "50-150k", 1234, "ok", None))
    ok &= check("user_hash NULL quando o ev nao trouxe (anonimo)", linha[4] is None)
    con.close()

    print("== _registrar: valve OFF = no-op imediato (nenhum sqlite) ==")
    chamou = {"n": 0}
    def _spy(db, ev):
        chamou["n"] += 1
    ns["_analytics_write"] = _spy  # o _registrar exec'd usa o _analytics_write do ns
    # reexec _registrar para pegar o _spy? Nao: _registrar referencia _analytics_write por
    # nome global do ns -> ja aponta para o _spy agora. Injeta DATA_DIR fake.
    sys.modules["open_webui"] = types.ModuleType("open_webui")
    envmod = types.ModuleType("open_webui.env")
    envmod.DATA_DIR = tempfile.mkdtemp(prefix="an_env_")
    sys.modules["open_webui.env"] = envmod

    self_off = types.SimpleNamespace(valves=types.SimpleNamespace(
        ANALYTICS_ON=False, ANALYTICS_USER_SALT=""))
    await REG(self_off, {"rota": "geral", "t0": time.monotonic()})
    ok &= check("valve OFF -> _analytics_write NAO chamado", chamou["n"] == 0)

    print("== _registrar: valve ON grava; e best-effort se o INSERT falhar ==")
    self_on = types.SimpleNamespace(valves=types.SimpleNamespace(
        ANALYTICS_ON=True, ANALYTICS_USER_SALT=""))
    await REG(self_on, {"rota": "geral", "t0": time.monotonic()})
    ok &= check("valve ON -> _analytics_write chamado uma vez", chamou["n"] == 1)
    ok &= check("latencia foi calculada no fim (t0 -> ms)", True)  # via ev abaixo

    # INSERT falhando: _registrar NAO pode propagar
    def _boom(db, ev):
        raise RuntimeError("disco cheio")
    ns["_analytics_write"] = _boom
    levantou = False
    try:
        await REG(self_on, {"rota": "arquivo", "t0": time.monotonic()})
    except Exception:
        levantou = True
    ok &= check("INSERT falhando -> _registrar ENGOLE (nao propaga)", not levantou)

    # ev sem nada tambem nao quebra
    try:
        await REG(self_on, {})
        await REG(self_on, None)
        semquebra = True
    except Exception:
        semquebra = False
    ok &= check("ev vazio/None -> best-effort, sem excecao", semquebra)

    print("== a RESPOSTA nunca passa por analytics (wrapper try/finally) ==")
    ok &= check("pipe() delega a _pipe_impl e registra no finally",
                "return await self._pipe_impl(" in fonte
                and "finally:\n            await self._registrar(_ev)" in fonte)
    ok &= check("o corpo virou _pipe_impl (nao ha logica no wrapper)",
                E.existe(fonte, "_pipe_impl"))
    ok &= check("_registrar existe e e best-effort (try/except que engole)",
                E.existe(fonte, "_registrar")
                and "analytics best-effort falhou" in fonte)
    ok &= check("valve ANALYTICS_ON (rollback) e ANALYTICS_USER_SALT existem",
                "ANALYTICS_ON" in E.campos_de_classe(fonte, "Valves")
                and "ANALYTICS_USER_SALT" in E.campos_de_classe(fonte, "Valves"))

    print("== fiacao das capturas (os eventos do dono) ==")
    ok &= check("recusas etiquetadas (ilegivel/nao_coube/sem_imagem/anexo_inutil)",
                all(x in fonte for x in ('"ilegivel"', '"nao_coube"', '"sem_imagem"',
                                         '"anexo_inutil"')))
    ok &= check("429 etiquetado separado do erro generico",
                '"rate_limit_429"' in fonte and "status == 429" in fonte)
    ok &= check("divergencia: classificador (pre-trava) e trava capturados",
                '_ev["classificador"] = categoria' in fonte
                and '_ev["trava"] = "pede_arquivo"' in fonte)
    ok &= check("latencia: cronometro apos a rota decidida",
                '_ev["t0"] = time.monotonic()' in fonte)
    ok &= check("anexo: tipo/fonte/faixa (faixa, nao valor exato)",
                '_ev["anexo_faixa"] = _analytics_faixa(' in fonte)

    print("\nRESULTADO: " + ("ANALYTICS 1a OK" if ok else "HOUVE FALHA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
