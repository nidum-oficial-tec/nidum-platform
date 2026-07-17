"""
title: SONDA 3 - RECENCIA da engine de busca (DESCARTAVEL)
author: Nidum
version: 0.1.0
description: SONDA DESCARTAVEL. Nao e produto. Mede se a engine configurada devolve o resultado CERTO para pergunta sobre ONTEM/HOJE - nao so "se devolve data". Rode UMA engine por vez (configure no painel, rode, troque, rode). Roda com usuario NAO-ADMIN. APAGAR quando a engine estiver escolhida.
"""

# =============================================================================
# POR QUE ESTA SONDA E DIFERENTE - o criterio que o Davi corrigiu
#
# A tentacao e medir "a engine devolve a data do resultado?". ERRADO - o caso Santos
# mostrou por que: "quem ganhou o jogo do Santos ontem?" -> o DDGS devolveu um jogo
# ANTIGO (Santos x Bahia; ontem foi contra o Botafogo). O problema nao foi falta de data;
# foi o resultado ERRADO com cara de atual. Uma engine pode devolver data e ainda assim
# trazer o jogo errado.
#
# ENTAO O QUE ESTA SONDA MEDE: o CONTEUDO CRU que a engine devolve para duas perguntas
# verificaveis-por-humano sobre o agora. Voce (humano) le e julga: "esse resultado e
# mesmo de ontem/hoje, ou e velho?". A sonda nao decide - ela EXPOE o material exato que o
# modelo veria, para voce comparar engine A vs engine B com o mesmo criterio.
#
# AS DUAS PERGUNTAS (as que o Davi escolheu, e o porque):
#   1. "quem ganhou o jogo do Santos ontem?"  - o teste-ouro: verificavel, o modelo NAO
#      sabe de cabeca, e o DDGS JA ERROU aqui. Se a nova engine tambem trouxer jogo velho,
#      ela nao resolve o problema, so troca a fonte fraca.
#   2. "qual a cotacao do dolar hoje?"        - muda todo dia; o DDGS trouxe 22/01.
#
# COMO USAR:
#   1. Configure UMA engine candidata no painel (WEB_SEARCH_ENGINE + a chave dela).
#   2. Publique esta sonda como Function (Pipe), NAO anexe a modelo nenhum.
#   3. Logue como COAUTOR NAO-ADMIN (o caso real - search_web sem gate). Manda qualquer
#      coisa; a sonda ignora o texto e roda as duas perguntas fixas.
#   4. Leia o resultado: para cada pergunta, os 3 primeiros resultados CRUS (titulo, link,
#      snippet). VOCE julga se o conteudo e de ontem/hoje.
#   5. Troque a engine no painel, rode de novo, compare.
#   6. APAGAR a sonda quando escolher. (E as outras duas, se ainda vivas.)
#
# O QUE ELA NAO RESPONDE (nem tente concluir):
#   - preco: e externo, voce pesquisa.
#   - "a engine e boa em geral": mede so estas duas perguntas. Amostra pequena de
#     PROPOSITO - o ponto e comparar engines no MESMO caso, nao certificar uma.
# =============================================================================

import logging
import traceback

log = logging.getLogger(__name__)

from pydantic import BaseModel, Field

PERGUNTAS = [
    "quem ganhou o jogo do Santos ontem?",
    "qual a cotacao do dolar hoje?",
]


class Pipe:
    class Valves(BaseModel):
        # Quantos resultados mostrar por pergunta. 3 = o que a fatia 3 injeta.
        TOP: int = Field(default=3)

    def __init__(self):
        self.type = "pipe"
        self.id = "sonda_recencia"
        self.name = "SONDA 3 - recencia da engine (descartavel)"
        self.valves = self.Valves()

    def _campo(self, r, nome):
        v = getattr(r, nome, None)
        if v is None and isinstance(r, dict):
            v = r.get(nome)
        return v or ""

    async def pipe(self, body: dict, __user__=None, __request__=None):
        linhas = []

        def diz(txt):
            log.info("sonda3: %s", txt)
            linhas.append(txt)

        papel = (__user__ or {}).get("role", "?") if isinstance(__user__, dict) else "?"
        diz("usuario role=%r" % papel)
        if papel == "admin":
            diz("[ATENCAO] rode como COAUTOR nao-admin (o caso real). Como admin, o "
                "search_web ainda roda, mas nao e o caminho de producao.")

        # --- engine configurada -----------------------------------------------
        engine = None
        try:
            engine = __request__.app.state.config.WEB_SEARCH_ENGINE
        except Exception as e:
            diz("[FALHA] nao li WEB_SEARCH_ENGINE: %r" % e)
            return "\n".join(linhas)
        diz("ENGINE EM TESTE: %r  (configure outra no painel e rode de novo para comparar)"
            % engine)

        try:
            from open_webui.routers.retrieval import search_web
        except Exception as e:
            diz("[FALHA] import de search_web: %r" % e)
            diz(traceback.format_exc()[:800])
            return "\n".join(linhas)

        # --- roda as duas perguntas fixas ------------------------------------
        for pergunta in PERGUNTAS:
            diz("")
            diz("=" * 60)
            diz("PERGUNTA: %s" % pergunta)
            diz("=" * 60)
            try:
                resultados = await search_web(__request__, engine or "duckduckgo",
                                              pergunta, __user__)
            except Exception as e:
                diz("[FALHA] search_web levantou: %r" % e)
                diz(traceback.format_exc()[:800])
                continue

            n = len(resultados or [])
            if n == 0:
                diz("[VAZIO] 0 resultados. Rate-limit da engine, ou ela nao respondeu. "
                    "Numa engine seria de estranhar para estas perguntas.")
                continue

            diz("%d resultado(s). Os %d primeiros (o que o modelo veria) - VOCE julga se "
                "o conteudo e de ontem/hoje:" % (n, min(n, self.valves.TOP)))
            for i, r in enumerate(resultados[: self.valves.TOP], 1):
                titulo = str(self._campo(r, "title")).strip()
                link = str(self._campo(r, "link")).strip()
                trecho = str(self._campo(r, "snippet")).strip()
                diz("")
                diz("  [%d] %s" % (i, titulo or "(sem titulo)"))
                diz("      %s" % (link or "(sem link)"))
                diz("      %s" % ((trecho or "(sem snippet)")[:400]))

        diz("")
        diz("=" * 60)
        diz("COMO LER: para o Santos, o resultado tem que trazer o jogo de ONTEM (o "
            "adversario e o placar certos). Se vier jogo antigo - como o DDGS trouxe - "
            "esta engine NAO resolve o problema. Para o dolar, a cotacao tem que ser de "
            "hoje. Compare com a proxima engine no MESMO criterio.")
        return "\n".join(linhas)
