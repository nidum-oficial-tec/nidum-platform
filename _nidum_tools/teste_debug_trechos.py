# -*- coding: utf-8 -*-
"""
Prova AUTOMATICA e SEM RISCO do relatorio de observabilidade de ranking
(_relatorio_trechos do chatnd.py, valve DEBUG_TRECHOS). Exercita so a funcao PURA -
nao faz rede, nao busca, nao toca na base, nao emite nada. Sai != 0 se falhar.

O QUE GARANTE:
  - ORDEM preservada: o relatorio lista os trechos na ordem em que a busca os devolveu
    (que ja e a ordem do reranker) - numeracao 1..N na mesma sequencia.
  - NOTA: usa metadata['score'] quando existe (rotulo 'score='); cai para a distancia
    (rotulo 'dist=') quando o score falta; e 'nota=n/d' quando nenhum dos dois serve.
  - PASTA: extrai o campo 'pasta' do cabecalho da esteira quando o trecho o traz.
  - BUSCA VAZIA: sources vazio -> mensagem explicita de RAG vazio (nao string em branco).

USO: python _nidum_tools/teste_debug_trechos.py

Por que stubar o open_webui: o chatnd.py importa modulos do app no topo. A funcao
testada e PURA e nao toca em nada disto - o stub so permite importar o modulo offline,
igual ao teste_datas.py.
"""

import os
import sys
from unittest.mock import MagicMock

for _m in [
    "open_webui", "open_webui.utils", "open_webui.utils.chat", "open_webui.models",
    "open_webui.models.users", "open_webui.models.knowledge", "open_webui.retrieval",
    "open_webui.retrieval.utils", "open_webui.utils.plugin",
]:
    sys.modules[_m] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chatnd as C  # noqa: E402


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def tem(texto, *partes):
    return all(p in texto for p in partes)


# Cabecalho REAL da esteira, para exercitar a extracao da 'pasta'.
_CAB = (
    "<!-- origem: sharepoint:Nidum/3 - Acervos Institucionais/Juridico/x.docx | "
    "pasta: 3 - Acervos Institucionais/Juridico | modificado: 2026-08-03T21:32:13Z | "
    "convertido: 2026-08-07 | esteira v1 -->"
)


def main():
    ok = True

    # Caso 1: dois trechos, ambos com score em metadata, ordem A->B preservada, pasta.
    sources = [{
        "source": {"name": "Base institucional Nidum"},
        "document": [_CAB + "\nAlfa conteudo", "Beta conteudo sem cabecalho"],
        "metadata": [
            {"name": "ACERVOS > Juridico > x.docx.md", "score": 0.8123},
            {"name": "FONTE > v30.md", "score": 0.4010},
        ],
        "distances": [0.8123, 0.4010],
    }]
    rel = C._relatorio_trechos(sources)
    ok = check("caso1: cabecalho conta 2 trechos", tem(rel, "2 trecho(s)")) and ok
    ok = check("caso1: usa score (nao dist)", tem(rel, "score=0.8123", "score=0.4010")) and ok
    ok = check("caso1: ordem A antes de B",
               rel.find("x.docx.md") < rel.find("v30.md")) and ok
    ok = check("caso1: numeracao 1 e 2", tem(rel, " 1. ", " 2. ")) and ok
    ok = check("caso1: extrai a pasta (sem prefixo numerico)",
               tem(rel, "pasta: Acervos Institucionais/Juridico")) and ok

    # Caso 2: sem score em metadata -> cai para a distancia (rotulo 'dist=').
    sources2 = [{
        "document": ["trecho sem score"],
        "metadata": [{"name": "doc.md"}],
        "distances": [0.55],
    }]
    rel2 = C._relatorio_trechos(sources2)
    ok = check("caso2: fallback para distancia", tem(rel2, "dist=0.5500")) and ok
    ok = check("caso2: nao inventa 'score='", "score=" not in rel2) and ok

    # Caso 3: sem score e sem distancia utilizavel -> nota=n/d, nao quebra.
    sources3 = [{"document": ["x"], "metadata": [{"name": "d.md"}], "distances": []}]
    rel3 = C._relatorio_trechos(sources3)
    ok = check("caso3: nota=n/d quando nao ha nota", tem(rel3, "nota=n/d")) and ok

    # Caso 4: busca vazia -> mensagem explicita, nunca string em branco.
    for vazio in ([], None, [{"document": [], "metadata": [], "distances": []}]):
        relv = C._relatorio_trechos(vazio)
        ok = check("caso4: RAG vazio explicito (%r)" % (vazio,),
                   tem(relv, "ZERO trechos")) and ok

    print("\n" + ("TODOS OS CASOS PASSARAM" if ok else "HOUVE FALHA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
