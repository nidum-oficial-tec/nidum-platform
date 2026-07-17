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
# COMO USAR (a producao NAO precisa mudar - a sonda testa em isolamento):
#   1. No painel, configure so a CHAVE da candidata (ex.: TAVILY_API_KEY). NAO precisa
#      trocar o WEB_SEARCH_ENGINE global - a producao segue no DDGS, nao validada ainda.
#   2. Na valve ENGINE da sonda, ponha a engine a testar (default ja e 'tavily').
#   3. Publique esta sonda como Function (Pipe), NAO anexe a modelo nenhum.
#   4. Logue como COAUTOR NAO-ADMIN (o caso real - search_web sem gate). Manda qualquer
#      coisa; a sonda ignora o texto e roda as duas perguntas fixas.
#   5. Leia o resultado: os 3 primeiros resultados CRUS (titulo, link, snippet). VOCE
#      julga se o conteudo e de ontem/hoje.
#   6. Para comparar outra engine: muda a valve ENGINE (+ a chave dela), roda de novo.
#   7. SO DEPOIS de a sonda confirmar: troca o WEB_SEARCH_ENGINE global no painel. APAGAR
#      a sonda (e as outras duas, se vivas).
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
        # A ENGINE A TESTAR - default 'tavily'. Ponto IMPORTANTE: a sonda usa ESTA valve,
        # nao o WEB_SEARCH_ENGINE global. Assim voce testa o Tavily com a PRODUCAO INTACTA
        # no DDGS - basta configurar a TAVILY_API_KEY no painel; nao precisa trocar a
        # engine global (o que jogaria a producao para uma engine ainda nao validada). O
        # search_web despacha pela engine passada + le a chave dela; funciona mesmo com o
        # WEB_SEARCH_ENGINE ainda em 'duckduckgo'. Vazio = usa a global.
        # NOTA CRITICA: o wrapper do OWUI chama o Tavily em modo BASICO - so
        # {query, max_results}. NAO manda topic=news, days nem time_range, que sao a forca
        # do Tavily para recencia. Esta sonda mede o Tavily-COMO-O-OWUI-CHAMA, que e o que
        # a producao usaria. Se der velho, o problema nao e o Tavily - e o wrapper nao
        # pedir recencia, e o conserto seria um passo a mais (patch no tavily.py ou chamar
        # direto).
        ENGINE: str = Field(default="tavily")
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

        # --- engine a testar: a VALVE da sonda, nao o global (producao fica intacta) ----
        engine = (self.valves.ENGINE or "").strip()
        if not engine:
            try:
                engine = __request__.app.state.config.WEB_SEARCH_ENGINE or "duckduckgo"
                diz("[info] valve ENGINE vazia -> usando a global: %r" % engine)
            except Exception as e:
                diz("[FALHA] nao li WEB_SEARCH_ENGINE: %r" % e)
                return "\n".join(linhas)
        diz("ENGINE EM TESTE: %r  (valve da sonda; a producao segue no WEB_SEARCH_ENGINE "
            "global, intacta). Precisa da chave dela configurada no painel." % engine)
        if engine == "tavily":
            diz("[nota] Tavily via OWUI = modo basico (so query+max_results). Se vier "
                "velho, e o wrapper nao pedir recencia, nao o Tavily.")

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
