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
    S = C._colecoes_para_busca

    # ---- parse ----
    ok = check("parse: json valido", P('{"atas":"A"}') == {"atas": "A"}) and ok
    ok = check("parse: vazio -> {}", P("") == {}) and ok
    ok = check("parse: espacos -> {}", P("   ") == {}) and ok
    ok = check("parse: json invalido -> {}", P("{nao eh json") == {}) and ok
    ok = check("parse: lista (nao-dict) -> {}", P('["a","b"]') == {}) and ok
    ok = check("parse: key minuscula, dropa vazio/nao-str",
               P('{"Atas":"A","x":"","y":123}') == {"atas": "A"}) and ok

    # ---- selecao / fallback ----
    ok = check("mapa vazio -> (None,None) = comportamento atual",
               S({}, False, False) == (None, None)) and ok

    sel, todas = S(MAPA, True, False)   # conceitual
    ok = check("conceitual -> fonte+normas", sel == ["F", "N"]) and ok
    ok = check("conceitual: todas = as 7", todas == TODAS) and ok

    sel, _ = S(MAPA, False, True)       # temporal
    ok = check("temporal -> atas+projetos", sel == ["A", "P"]) and ok

    sel, _ = S(MAPA, False, False)      # default
    ok = check("default -> todas as 7", sel == TODAS) and ok

    # conceitual vence temporal quando ambos
    sel, _ = S(MAPA, True, True)
    ok = check("conceitual vence temporal", sel == ["F", "N"]) and ok

    # parcial: papel ausente e filtrado, nunca devolve vazio
    sel, todas = S({"atas": "A", "fonte": "F"}, True, False)
    ok = check("parcial conceitual: so o que existe (fonte)", sel == ["F"]) and ok
    ok = check("parcial: todas = os presentes", todas == ["A", "F"]) and ok

    # parcial onde os selecionados somem -> cai em todas (nunca vazio)
    sel, _ = S({"marca": "M"}, True, False)
    ok = check("parcial sem os papeis alvo -> cai em todas (nao vazio)",
               sel == ["M"]) and ok

    print("\n" + ("MAPA_COLECOES OK" if ok else "HOUVE FALHA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
