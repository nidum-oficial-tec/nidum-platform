# -*- coding: ascii -*-
"""
Lado PIPE do contrato de TIPO (Fase 3). Roda as MESMAS fixtures do canonico da esteira
(via a fatia embutida _nidum_tools/fatia_assunto_pipe.json, que a esteira gera de
mapa_assuntos.json) atraves da derivacao do pipe (_f3_tipo/_f3_assuntos por meta_name).

Espelha _scripts/teste_tipo_contrato.py da esteira: se a logica de tipo/assunto dos dois
lados divergir das MESMAS fixtures, um dos testes falha. E a "fonte unica + guarda, nao
copia a mao" que o Davi pediu, aplicada ao tipo.

USO: python _nidum_tools/teste_tipo_contrato_pipe.py
"""

import json
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


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def main():
    with open(os.path.join(_DIR, "fatia_assunto_pipe.json"), encoding="ascii") as f:
        fatia = json.load(f)
    casos = (fatia.get("_fixtures_tipo") or {}).get("casos") or []
    ok = True

    ok = check("fatia embutida tem _tipo_regras e _fixtures_tipo",
               bool(fatia.get("_tipo_regras")) and len(casos) >= 6) and ok

    # TIPO: cada fixture pela derivacao do pipe (por meta_name) == tipo esperado.
    for f in casos:
        got = C._f3_tipo(f["meta_name"], fatia)
        ok = check("pipe _f3_tipo: %-34s -> %s" % (f["stem"][:34], f["tipo"]),
                   got == f["tipo"]) and ok

    # ASSUNTO por meta_name: FAZ -> fazenda (por pasta); ACA_Convergencia -> academia (sigla).
    faz = ("ACERVOS > Financas e Gestao de Projetos > 3.1 EGP > 3.1.3 Portfolio de "
           "Projetos > 1. Projeto Fazenda Fortaleza > 1.1 Cronogramas > "
           "FAZ_Cronograma_31.07_v3.md")
    ok = check("pipe _f3_assuntos: FAZ -> fazenda",
               "fazenda" in C._f3_assuntos(faz, fatia)) and ok
    ok = check("pipe _f3_assuntos: ACA_Convergencia -> academia (sigla)",
               C._f3_assuntos("ACA > ACA_Convergencia_10062026_v1.md", fatia)
               == {"academia"}) and ok

    print("\n" + ("CONTRATO DE TIPO (PIPE) OK" if ok else "HOUVE FALHA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
