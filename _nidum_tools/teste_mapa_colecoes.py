# -*- coding: ascii -*-
"""Testa os helpers puros do MAPA_COLECOES (Fase 1): _parse_mapa_colecoes e
_colecoes_para_busca. Sem tocar em rede/retrieval - so a logica de selecao e o
fallback (valve vazia = comportamento atual).

USO: python _nidum_tools/teste_mapa_colecoes.py
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

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)
import chatnd as C  # noqa: E402

MAPA = {"atas": "A", "projetos": "P", "fonte": "F", "normas": "N",
        "marca": "M", "contratos": "C", "externo": "E"}
TODAS = ["A", "P", "F", "N", "M", "C", "E"]  # ordem de _PAPEIS_MAPA


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def main():
    ok = True
    P = C._parse_mapa_colecoes
    # ---- parse ----
    ok = check("parse: json valido", P('{"atas":"A"}') == {"atas": "A"}) and ok
    ok = check("parse: vazio -> {}", P("") == {}) and ok
    ok = check("parse: espacos -> {}", P("   ") == {}) and ok
    ok = check("parse: json invalido -> {}", P("{nao eh json") == {}) and ok
    ok = check("parse: lista (nao-dict) -> {}", P('["a","b"]') == {}) and ok
    ok = check("parse: key minuscula, dropa vazio/nao-str",
               P('{"Atas":"A","x":"","y":123}') == {"atas": "A"}) and ok

    # ---- MAPA ativo -> TODAS as ids (nunca filtra por tema; a busca da 1.64.1 usa todas) ----
    ids = list(dict.fromkeys(P(
        '{"atas":"A","projetos":"P","fonte":"F","normas":"N","marca":"M",'
        '"contratos":"C","externo":"E"}').values()))
    ok = check("MAPA ativo -> todas as 7 ids (sem filtro por tema)", ids == TODAS) and ok
    ok = check("MAPA vazio -> sem ids (comportamento atual)",
               list(P("").values()) == []) and ok

    # ---- etiquetas do contexto injetado (entrega C) ----
    E = C._etiquetas_trecho
    ok = check("etiqueta EXTERNA: IPPUL -> PROCEDENCIA EXTERNA",
               any("PROCEDENCIA EXTERNA" in x
                   for x in E("ACERVOS > Produtos > IPPUL > LEI_13542.md"))) and ok
    ok = check("etiqueta RASCUNHO: v31",
               any("RASCUNHO" in x
                   for x in E("FONTE > Nidum Documento Fundador - v31 (rascunho).md"))) and ok
    ok = check("etiqueta convergencia (fold de acento)",
               any("convergencia" in x
                   for x in E("ACERVOS > Reunioes > Atas > CTE_Convergencia_27062026.md"))) and ok
    ok = check("arquivo comum -> sem etiqueta",
               E("MKT > MKT_BrandbookNidum_10072026_V1.md") == []) and ok

    print("\n" + ("MAPA_COLECOES OK" if ok else "HOUVE FALHA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
