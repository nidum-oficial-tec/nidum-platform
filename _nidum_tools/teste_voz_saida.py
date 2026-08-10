# -*- coding: utf-8 -*-
"""
Banco de provas da SAIDA DE VOZ (TTS no chat, 1.56.0). O teste OBRIGATORIO do dono:
com o TTS MORTO (sintese falha/None/excecao), o TEXTO chega INTEGRO e na ordem, o [DONE]
fecha no tempo normal, e entra um aviso discreto no lugar do audio. Sem ele passando, a
funcao nao e entregavel. Tambem: deteccao deterministica, remocao do gatilho, limpeza de
markdown, best-effort/A|texto, e sem regressao do caminho sem audio.
USO: python teste_voz_saida.py
"""
import ast
import asyncio
import json
import os
import re
import types

import teste_estrutura as E

_DIR = os.path.dirname(os.path.abspath(__file__))
CAM = os.path.join(_DIR, "chatnd.py")


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def _log():
    return types.SimpleNamespace(exception=lambda *a, **k: None, error=lambda *a, **k: None,
                                 warning=lambda *a, **k: None, info=lambda *a, **k: None)


def _fonte(fonte, nome):
    # Fonte (desindentada) de funcao OU metodo, via AST.
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            linhas = fonte.split("\n")[no.lineno - 1: no.end_lineno]
            # remove decoradores (ex.: @staticmethod) que ficaram fora do lineno? nao -
            # lineno aponta para o 'def'. desindenta pelo recuo da 1a linha.
            corte = len(linhas[0]) - len(linhas[0].lstrip())
            return "\n".join(l[corte:] if len(l) >= corte else l for l in linhas)
    return ""


def carregar():
    fonte = open(CAM, encoding="utf-8").read()
    ns = {"json": json, "asyncio": asyncio, "re": re,
          "unicodedata": __import__("unicodedata"), "log": _log()}
    # MENSAGEM_INSTABILIDADE (constante)
    m = re.search(r"^MENSAGEM_INSTABILIDADE = \(.*?\)", fonte, re.M | re.S)
    exec(m.group(0), ns)
    # constantes RE da limpeza
    for c in re.findall(r"^_RE_FALA_[A-Z]+ = re\.compile\([\s\S]*?\)\n", fonte, re.M):
        exec(c, ns)
    # constantes frozenset da deteccao
    for c in re.findall(r"^_(?:STOP_FALA|COLA_ANTES|COLA_DEPOIS) = frozenset\([\s\S]*?\)\)\n",
                        fonte, re.M):
        exec(c, ns)
    # helpers puros
    for nome in ("_normalizar_ascii", "_tem_conteudo_sse", "_texto_de_sse",
                 "_limpar_para_fala", "_norm_palavra", "_cfg_audio", "_audio_span",
                 "_pede_audio", "_sem_gatilho_audio"):
        exec(_fonte(fonte, nome), ns)
    # _pede_arquivo (+ constantes) para o ACEITE do reorder: a limpeza do gatilho NAO pode
    # mexer no roteamento de quem nao pede audio.
    for const in (r"_VERBO_PRODUZIR = \(.*?^\)", r"_SUBST_ARQUIVO = \(.*?^\)",
                  r"_RE_PEDE_ARQUIVO = re\.compile\(.*?^\)"):
        m = re.search(r"^" + const, fonte, re.M | re.S)
        exec(m.group(0), ns)
    exec(_fonte(fonte, "_pede_arquivo"), ns)
    # metodos sob teste (desindentados)
    for nome in ("_sse_conteudo", "_sintetizar_e_salvar", "_emitir_audio_final",
                 "_stream_resiliente"):
        exec(_fonte(fonte, nome), ns)
    return ns, fonte


def _stream_falso(chunks):
    async def gen():
        for c in chunks:
            yield c if isinstance(c, (bytes, bytearray)) else c.encode("utf-8")
    return gen()


def _sse(txt):
    return ("data: " + json.dumps({"choices": [{"delta": {"content": txt}}]}) + "\n\n")


async def _coletar(agen):
    return [c async for c in agen]


async def _prune_noop(self, user_id):   # o prune real importa open_webui - mock offline
    return None


def _eh_keepalive(s):
    # chunk de keepalive = _sse_conteudo("") -> delta.content == "" (nada visivel).
    if not s.startswith("data: ") or "[DONE]" in s:
        return False
    try:
        d = json.loads(s[6:].strip())
        return d["choices"][0]["delta"].get("content", "X") == ""
    except Exception:
        return False


def _novo_self(ns, **valves):
    v = dict(TTS_ON=True, TTS_KEY="k", TTS_BASE_URL="https://api.openai.com/v1",
             TTS_MODEL="tts-1", TTS_VOZ="echo", TTS_SPEED=1.0, TTS_KEEPALIVE_SEG=2.0,
             TTS_TIMEOUT=60, TTS_RETER_DIAS=30)
    v.update(valves)
    S = types.SimpleNamespace()
    S.valves = types.SimpleNamespace(**v)
    S._sse_conteudo = ns["_sse_conteudo"]                       # staticmethod-like
    S._sintetizar_e_salvar = types.MethodType(ns["_sintetizar_e_salvar"], S)
    S._prune_audios = types.MethodType(_prune_noop, S)          # mock (offline)
    S._emitir_audio_final = types.MethodType(ns["_emitir_audio_final"], S)
    S._stream_resiliente = types.MethodType(ns["_stream_resiliente"], S)
    return S


def main():
    ns, fonte = carregar()
    ok = True
    run = asyncio.run

    TEXTO = [_sse("Ola "), _sse("mundo"), "data: [DONE]\n\n"]
    ctx = {"user_id": "u1"}

    print("== OBRIGATORIO: TTS MORTO -> texto INTEGRO + [DONE] + aviso discreto ==")
    async def _synth_none(self, texto):   # sintese morta (None)
        return None
    S = _novo_self(ns)
    S._sintetizar_openai = types.MethodType(_synth_none, S)
    S._salvar_audio = types.MethodType(lambda self, d, u: None, S)  # nem chamado
    out = run(_coletar(S._stream_resiliente(_stream_falso(TEXTO), ctx)))
    txt = [c.decode("utf-8") for c in out]
    ok &= check("texto passou INTEGRO e na ordem (Ola  + mundo)",
                out[0] == TEXTO[0].encode() and out[1] == TEXTO[1].encode())
    ok &= check("[DONE] fecha por ultimo", "[DONE]" in txt[-1])
    ok &= check("aviso discreto no lugar do audio",
                any("nao consegui gerar o audio" in t.lower() for t in txt))
    ok &= check("NAO emitiu player quando TTS morto",
                not any("<audio>" in t for t in txt))

    print("== TTS MORTO por EXCECAO -> mesmo assim texto integro, sem crash ==")
    async def _synth_raise(self, texto):
        raise RuntimeError("URL morta")
    S = _novo_self(ns)
    S._sintetizar_openai = types.MethodType(_synth_raise, S)
    S._salvar_audio = types.MethodType(lambda self, d, u: None, S)
    out = run(_coletar(S._stream_resiliente(_stream_falso(TEXTO), ctx)))
    txt = [c.decode("utf-8") for c in out]
    ok &= check("texto integro mesmo com excecao na sintese",
                out[0] == TEXTO[0].encode() and out[1] == TEXTO[1].encode()
                and "[DONE]" in txt[-1])

    print("== TTS OK -> player <div><audio>URL</audio></div> ANTES do [DONE] ==")
    async def _synth_ok(self, texto):
        return b"mp3-bytes"
    async def _save_ok(self, d, u):
        return "/api/v1/files/AUD/content"
    S = _novo_self(ns)
    S._sintetizar_openai = types.MethodType(_synth_ok, S)
    S._salvar_audio = types.MethodType(_save_ok, S)
    out = run(_coletar(S._stream_resiliente(_stream_falso(TEXTO), ctx)))
    txt = [c.decode("utf-8") for c in out]
    ok &= check("texto ainda integro e primeiro",
                out[0] == TEXTO[0].encode() and out[1] == TEXTO[1].encode())
    ok &= check("player no formato provado (<div><audio>URL</audio></div>)",
                any("<div><audio>/api/v1/files/AUD/content</audio></div>" in t for t in txt))
    ok &= check("link de download presente (requisito 3)",
                any("/api/v1/files/AUD/content" in t and "Baixar" in t for t in txt))
    ok &= check("audio vem ANTES do [DONE]",
                max(i for i, t in enumerate(txt) if "<audio>" in t)
                < max(i for i, t in enumerate(txt) if "[DONE]" in t))

    print("== SEM CAP (1.60.0): resposta LONGA ainda gera audio (nunca recusa por tamanho) ==")
    chamou = {"n": 0}
    async def _synth_conta(self, texto):
        chamou["n"] += 1
        return b"x"
    S = _novo_self(ns, TTS_KEEPALIVE_SEG=0)   # sem keepalive: caminho direto
    S._sintetizar_openai = types.MethodType(_synth_conta, S)
    S._salvar_audio = types.MethodType(_save_ok, S)
    _longo = "palavra " * 2000   # ~16000 chars, muito acima do antigo cap de 3000
    out = run(_coletar(S._stream_resiliente(
        _stream_falso([_sse(_longo), "data: [DONE]\n\n"]), ctx)))
    txt = [c.decode("utf-8") for c in out]
    ok &= check("resposta longa AINDA chama o TTS (sem cap)", chamou["n"] == 1)
    ok &= check("resposta longa -> player emitido (usuario sempre recebe o audio)",
                any("<audio>" in t for t in txt))
    ok &= check("NENHUM aviso de 'longa demais' (o cap nao existe mais)",
                not any("longa demais" in t.lower() for t in txt))

    print("== KEEPALIVE: save lento -> chunks vazios saem, player aparece LOGO que salva ==")
    async def _save_lento(self, d, u):
        await asyncio.sleep(0.12)
        return "/api/v1/files/AUD/content"
    async def _keepalive_caso():
        S = _novo_self(ns, TTS_KEEPALIVE_SEG=0.02)
        S._sintetizar_openai = types.MethodType(_synth_ok, S)
        S._salvar_audio = types.MethodType(_save_lento, S)
        return [c.decode("utf-8") async for c in S._emitir_audio_final(ctx, "Ola mundo")]
    ka = run(_keepalive_caso())
    _idx_player = [i for i, t in enumerate(ka) if "<audio>" in t]
    _idx_keep = [i for i, t in enumerate(ka) if _eh_keepalive(t)]
    ok &= check("saiu keepalive (chunk vazio) enquanto o save nao voltava", len(_idx_keep) >= 1)
    ok &= check("o player apareceu (assim que o save terminou)", len(_idx_player) == 1)
    ok &= check("os keepalives vieram ANTES do player",
                bool(_idx_keep) and bool(_idx_player) and max(_idx_keep) < _idx_player[0])
    ok &= check("keepalive nao adiciona nada visivel (content vazio)",
                all(json.loads(ka[i][6:].strip())["choices"][0]["delta"]["content"] == ""
                    for i in _idx_keep))

    print("== CANCELAMENTO: cliente fecha DURANTE a sintese -> loga, cancela, nunca MUDO ==")
    reg = []
    rec = types.SimpleNamespace(
        exception=lambda *a, **k: reg.append(("exception",) + tuple(str(x) for x in a)),
        error=lambda *a, **k: reg.append(("error",) + tuple(str(x) for x in a)),
        warning=lambda *a, **k: reg.append(("warning",) + tuple(str(x) for x in a)),
        info=lambda *a, **k: None)
    cancelado = {"save": False}
    async def _save_travado(self, d, u):
        try:
            await asyncio.sleep(5)               # save "eterno": o cliente fecha antes
            return "/api/v1/files/AUD/content"
        except asyncio.CancelledError:
            cancelado["save"] = True             # prova que a task foi CANCELADA
            raise
    async def _cancel_caso():
        log_bak = ns["log"]
        ns["log"] = rec
        try:
            S = _novo_self(ns, TTS_KEEPALIVE_SEG=0.02)
            S._sintetizar_openai = types.MethodType(_synth_ok, S)
            S._salvar_audio = types.MethodType(_save_travado, S)
            agen = S._emitir_audio_final(ctx, "Ola mundo")
            primeiro = (await agen.__anext__()).decode("utf-8")   # 1o yield = keepalive
            erro = None
            try:
                await agen.aclose()              # cliente fecha a conexao no meio
            except BaseException as e:
                erro = e
            for _ in range(6):                   # deixa a cancelacao propagar para a task
                await asyncio.sleep(0)
            return primeiro, erro
        finally:
            ns["log"] = log_bak
    primeiro, erro = run(_cancel_caso())
    ok &= check("enquanto salvava, saiu keepalive (nao ociosidade)", _eh_keepalive(primeiro))
    ok &= check("aclose() encerrou LIMPO (nao vazou outra excecao)", erro is None)
    ok &= check("LOGOU o cancelamento (nunca morre MUDO)",
                any(any("CANCELADO" in x for x in r) for r in reg))
    ok &= check("a task de sintese/save foi CANCELADA (nao ficou rodando solta)",
                cancelado["save"] is True)

    print("== SEM audio (audio_ctx=None) -> comportamento IDENTICO ao de antes ==")
    S = _novo_self(ns)
    S._sintetizar_openai = types.MethodType(_synth_ok, S)
    out = run(_coletar(S._stream_resiliente(_stream_falso(TEXTO), None)))
    txt = [c.decode("utf-8") for c in out]
    ok &= check("texto passa e [DONE] fecha, sem nada de audio",
                out[0] == TEXTO[0].encode() and "[DONE]" in txt[-1]
                and not any("<audio>" in t for t in txt))

    print("== SEM conteudo (motor vazio) -> instabilidade (regressao) ==")
    S = _novo_self(ns)
    S._sintetizar_openai = types.MethodType(_synth_ok, S)
    out = run(_coletar(S._stream_resiliente(_stream_falso(["data: [DONE]\n\n"]), ctx)))
    txt = [c.decode("utf-8") for c in out]
    ok &= check("motor vazio -> MENSAGEM_INSTABILIDADE",
                any("Instabilidade" in t for t in txt))

    print("== DETECCAO por PROXIMIDADE + POSICAO (os casos do dono) ==")
    PEDE = ns["_pede_audio"]
    SEM = ns["_sem_gatilho_audio"]
    LIMP = ns["_limpar_para_fala"]
    # valves com os defaults (as mesmas listas do codigo)
    _v = types.SimpleNamespace(
        TTS_VERBOS="responde;responda;responder;manda;mande;mandar;envia;envie;enviar;"
                   "quero;queria;passa;passe",
        TTS_TERMOS_AUDIO="audio;audios;voz", TTS_VERBOS_FALA="fala;falar;narra;narrar;le;leia;ler",
        TTS_DEIXIS="isso;isto;aquilo;resposta;texto;esse;essa;este;esta;tudo",
        TTS_JANELA=4, TTS_DIST_PONTA=6, TTS_MAX_PALAVRAS=30)
    cfg = ns["_cfg_audio"](_v)
    ok &= check("'me responde em audio' -> DISPARA", PEDE("me responde em audio", cfg))
    ok &= check("'opa, me manda isso em audio por favor' -> DISPARA",
                PEDE("opa, me manda isso em audio por favor", cfg))
    ok &= check("'pode falar isso' -> DISPARA", PEDE("pode falar isso", cfg))
    ok &= check("e-mail + audio distantes no meio -> NAO dispara",
                PEDE("responda o e-mail do cliente; ele reclamou que o audio da reuniao "
                     "estava ruim e sem contexto nenhum", cfg) is False)
    ok &= check("'esse audio que voce gerou ficou ruim, pode refazer?' -> NAO dispara",
                PEDE("esse audio que voce gerou ontem ficou ruim, pode refazer?", cfg) is False)
    ok &= check("'vamos falar sobre isso' (assunto) -> NAO dispara",
                PEDE("vamos falar sobre isso amanha", cfg) is False)
    ok &= check("pedido na PONTA FINAL de msg longa -> dispara",
                PEDE("preciso entender o balanco patrimonial e o fluxo de caixa da empresa "
                     "toda com muito detalhe " * 2 + "e me responde em audio", cfg))
    ok &= check("co-ocorrencia solta no MEIO de msg longa -> NAO dispara",
                PEDE("me manda o resumo agora " + "palavra " * 30
                     + "o audio da call estava ruim", cfg) is False)
    ok &= check("remove o span do pedido (modelo nao comenta o audio)",
                "audio" not in SEM("o que e SPE? me responde em audio", cfg).lower()
                and "SPE" in SEM("o que e SPE? me responde em audio", cfg))
    ok &= check("limpeza tira codigo/tabela/link/etiqueta/marca",
                LIMP("# T\n**b** [x](http://y) `c`\n| a |\n[Fonte] real") == "T\nb x \nreal")

    print("== ACEITE DO REORDER: a limpeza do gatilho NAO muda quem NAO pede audio ==")
    NORM = ns["_normalizar_ascii"]
    PARQ = ns["_pede_arquivo"]   # trava deterministica de arquivo (o sinal real de rota)
    # Caso 1 (dono): pedido de arquivo SEM audio -> deteccao NAO dispara -> texto intacto ->
    # a trava de arquivo segue valendo -> continua roteando para arquivo.
    ok &= check("'gera um pdf sobre holding' -> audio NAO dispara",
                PEDE("gera um pdf sobre holding", cfg) is False)
    ok &= check("'gera um pdf sobre holding' -> ainda e pedido de ARQUIVO (rota intacta)",
                PARQ("gera um pdf sobre holding") is True)
    # Caso 2 (dono): pergunta comum -> audio NAO dispara -> intacto -> nao vira arquivo.
    ok &= check("'o que e uma holding?' -> audio NAO dispara",
                PEDE("o que e uma holding?", cfg) is False)
    ok &= check("'o que e uma holding?' -> NAO e pedido de arquivo (segue conversa)",
                PARQ("o que e uma holding?") is False)
    # Caso 3 (dono): pergunta + audio -> DISPARA; a limpeza deixa a PERGUNTA, e a pergunta
    # limpa NAO vira pedido de arquivo -> o classificador veria conversa, nao arquivo.
    _p3 = "o que e uma holding? me responde em audio"
    ok &= check("'...me responde em audio' -> audio DISPARA", PEDE(_p3, cfg) is True)
    _limpo3 = SEM(_p3, cfg)
    ok &= check("limpeza PRESERVA a pergunta e remove o gatilho",
                "holding" in NORM(_limpo3) and "audio" not in NORM(_limpo3))
    ok &= check("a pergunta LIMPA NAO vira pedido de arquivo (o bug do log)",
                PARQ(_limpo3) is False)
    ok &= check("deteccao roda ANTES do classificador (fonte)",
                fonte.index("_pede_audio(texto, _cfg_aud)")
                < fonte.index("saida = await self._classificar("))

    print("== A|TEXTO (estrutural): o texto passa ANTES de qualquer logica de audio ==")
    fs = _fonte(fonte, "_stream_resiliente")
    ok &= check("o yield do chunk de texto vem ANTES do _emitir_audio_final no fonte",
                fs.index("yield chunk") < fs.index("_emitir_audio_final"))
    ok &= check("a injecao de audio esta protegida por try/except (best-effort)",
                "injecao de audio falhou" in fs)
    ok &= check("_stream_resiliente CAPTURA cancelamento (BaseException, nao so Exception)",
                "GeneratorExit" in fs and "CancelledError" in fs and "CANCELADO" in fs)
    fe = _fonte(fonte, "_emitir_audio_final")
    ok &= check("_emitir_audio_final e best-effort (except Exception -> nunca levanta)",
                "except Exception:" in fe)
    ok &= check("_emitir_audio_final CAPTURA cancelamento e CANCELA a task",
                "GeneratorExit" in fe and "CancelledError" in fe and "tarefa.cancel()" in fe)
    ok &= check("_emitir_audio_final NAO tem mais cap de tamanho (TTS_MAX_CHARS sumiu)",
                "TTS_MAX_CHARS" not in fe)
    ok &= check("_emitir_audio_final faz KEEPALIVE (chunk vazio enquanto a task nao volta)",
                "TTS_KEEPALIVE_SEG" in fe and 'self._sse_conteudo("")' in fe)

    print("== ESCOPO: sem nome indefinido nas funcoes novas ==")
    for fn in ("_stream_resiliente", "_emitir_audio_final", "_sintetizar_e_salvar",
               "_prune_audios", "_sintetizar_openai", "_salvar_audio", "_pede_audio",
               "_sem_gatilho_audio", "_audio_span", "_cfg_audio", "_norm_palavra",
               "_limpar_para_fala", "_texto_de_sse", "_sse_conteudo"):
        u = E.nomes_indefinidos(fonte, fn)
        ok &= check("%s: sem nome indefinido" % fn, not u)

    print("\nRESULTADO: " + ("SAIDA DE VOZ OK" if ok else "HOUVE FALHA"))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
