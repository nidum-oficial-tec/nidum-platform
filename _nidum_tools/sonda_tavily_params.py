"""
title: SONDA 3 - PARAMS do Tavily direto (DESCARTAVEL)
author: Nidum
version: 0.2.0
description: SONDA DESCARTAVEL. Nao e produto. Roda o par Santos/dolar contra o Tavily DIRETO em varias COMBINACOES de params (basic; advanced+days; +news; +raw) e mostra o conteudo cru de cada, para VOCE escolher a janela/topic/raw que a producao vai usar. Roda com usuario NAO-ADMIN. APAGAR quando os params estiverem escolhidos.
"""

# =============================================================================
# O QUE MUDOU DA SONDA ANTERIOR
#
# A sonda 2 media UMA engine no modo basico. Esta chama o Tavily DIRETO (o mesmo
# _tavily_buscar da 1.39.0) e varia os PARAMS, porque a decisao agora nao e "qual
# engine" - e "quais parametros de recencia". Tres perguntas em aberto, todas medidas
# aqui, nenhuma chutada:
#   1. days (a janela): 1 acerta o dolar mas erra o jogo de ontem? Testa 1, 3, 7.
#   2. topic='news': ajuda o Santos (jogo E noticia) e ATRAPALHA o dolar (cotacao NAO e
#      noticia)? Testa com e sem.
#   3. raw_content (pagina inteira vs snippet): vale o peso de tokens? Mostra o tamanho.
#
# O PAR DE PERGUNTAS (o Davi definiu o criterio):
#   - "quem ganhou o jogo do Santos ontem?" = O VEREDITO. Verificavel (ontem foi contra o
#     Botafogo), o modelo nao sabe de cabeca, o DDGS e o Tavily-basico JA ERRARAM.
#   - "qual a cotacao do dolar hoje?"        = O CONTROLE. Muda todo dia.
# A janela boa acerta OS DOIS. Se um combo acerta o dolar e erra o Santos, a janela e
# pequena - ou o topic='news' esta cortando fontes de cotacao.
#
# COMO USAR (producao intacta):
#   1. TAVILY_API_KEY configurada no painel. NAO precisa trocar o WEB_SEARCH_ENGINE.
#   2. Publique como Function (Pipe), NAO anexe a modelo.
#   3. Logue como COAUTOR NAO-ADMIN. Manda qualquer coisa; roda o par fixo em N combos.
#   4. Leia: para cada pergunta e cada combo, os resultados crus + o tamanho. VOCE julga
#      qual combo traz o dado de ontem/hoje com fonte boa e sem sobrepeso.
#   5. Diga ao Code os params vencedores; ele fixa as valves WEB_RECENTE_*.
#   6. APAGAR esta sonda e as outras.
#
# NAO responde: preco/creditos (externo, voce confere na Tavily); "o Tavily e bom em
# geral" (mede so este par - amostra pequena de proposito, para comparar combos).
# =============================================================================

import logging
import traceback

log = logging.getLogger(__name__)

from pydantic import BaseModel, Field

PERGUNTAS = [
    "quem ganhou o jogo do Santos ontem?",   # VEREDITO
    "qual a cotacao do dolar hoje?",          # CONTROLE
]

# Cada combo e uma chamada -> creditos (basic/fast=1, advanced=2; confirmado na doc).
# A PERGUNTA DECISIVA vem primeiro: 'general + days' (sem topic) ja resolve OS DOIS? Se
# sim, nao precisa de topic nem do classificador escolher topico - o mais simples ganha.
# So se general falhar e que news/finance entram - e ai o par pode ser news para o Santos,
# finance para o dolar (o Tavily tem 3 topicos: general/news/finance).
COMBOS = [
    ("basico (controle = producao hoje)", dict(search_depth="basic")),
    ("DECISIVO: advanced + days=2 (general, SEM topic)", dict(search_depth="advanced", days=2)),
    ("advanced + days=7 (general)", dict(search_depth="advanced", days=7)),
    ("advanced + days=7 + topic=news (aposta do Santos)", dict(search_depth="advanced", days=7, topic="news")),
    ("advanced + days=7 + topic=finance (aposta do dolar)", dict(search_depth="advanced", days=7, topic="finance")),
    ("advanced + days=7 + raw_content (mede o peso)", dict(search_depth="advanced", days=7, raw_content=True)),
    # EXPLORATORIO - a doc menciona fast; se a API nao aceitar, sai [VAZIO]/[FALHA] e a
    # resposta e essa. Nao chuto que existe - meco.
    ("exploratorio: search_depth=fast", dict(search_depth="fast")),
]


class Pipe:
    class Valves(BaseModel):
        MAX_RESULTADOS: int = Field(default=3)

    def __init__(self):
        self.type = "pipe"
        self.id = "sonda_tavily_params"
        self.name = "SONDA 3 - params do Tavily (descartavel)"
        self.valves = self.Valves()

    async def pipe(self, body: dict, __user__=None, __request__=None):
        linhas = []

        def diz(txt):
            log.info("sonda3: %s", txt)
            linhas.append(txt)

        papel = (__user__ or {}).get("role", "?") if isinstance(__user__, dict) else "?"
        diz("usuario role=%r" % papel)
        if papel == "admin":
            diz("[ATENCAO] rode como COAUTOR nao-admin (o caminho real). Como admin roda, "
                "mas nao e producao.")

        api_key = ""
        try:
            api_key = getattr(__request__.app.state.config, "TAVILY_API_KEY", "") or ""
        except Exception as e:
            diz("[FALHA] nao li a config: %r" % e)
            return "\n".join(linhas)
        if not api_key:
            diz("[FALHA] TAVILY_API_KEY vazia no painel. Configure a chave e rode de novo.")
            return "\n".join(linhas)

        # Usa a MESMA funcao da producao - a sonda mede o codigo real, nao um paralelo.
        _tavily = None
        for mod in ("chatnd", "function_chatnd"):
            try:
                _tavily = __import__(mod, fromlist=["_tavily_buscar"])._tavily_buscar
                break
            except Exception:
                continue
        if _tavily is None:
            diz("[FALHA] nao achei _tavily_buscar do chatnd. A sonda precisa do pipe "
                "chatnd 1.39.0+ publicado no mesmo servidor.")
            return "\n".join(linhas)

        for pergunta in PERGUNTAS:
            diz("")
            diz("#" * 64)
            diz("PERGUNTA: %s" % pergunta)
            diz("#" * 64)
            for rotulo, kw in COMBOS:
                diz("")
                diz(">>> COMBO: %s" % rotulo)
                try:
                    res = await _tavily(api_key, pergunta,
                                        max_results=self.valves.MAX_RESULTADOS, **kw)
                except Exception as e:
                    diz("    [FALHA] %r" % e)
                    diz(traceback.format_exc()[:500])
                    continue
                if not res:
                    diz("    [VAZIO] 0 resultados neste combo.")
                    continue
                total = sum(len(str(r.get("snippet") or "")) for r in res)
                diz("    %d resultado(s), %d chars de conteudo:" % (len(res), total))
                for i, r in enumerate(res[: self.valves.MAX_RESULTADOS], 1):
                    diz("      [%d] %s" % (i, (r.get("title") or "(sem titulo)")[:80]))
                    diz("          %s" % (r.get("link") or ""))
                    diz("          %s" % ((r.get("snippet") or "")[:260]))

        diz("")
        diz("#" * 64)
        diz("COMO ESCOLHER: o combo bom traz, para o SANTOS, o jogo de ONTEM (adversario "
            "certo) e, para o DOLAR, a cotacao de HOJE. Repare se 'news' AJUDA o jogo mas "
            "ESVAZIA o dolar. E no tamanho: raw_content da muito mais chars - vale se o "
            "snippet faltava o dado, sobrepeso se nao. Diga ao Code days/topic/raw "
            "vencedores.")
        return "\n".join(linhas)
