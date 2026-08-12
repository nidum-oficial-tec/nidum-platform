# -*- coding: ascii -*-
"""
DEMO offline do dial (Fase 3) nos casos do baseline D8/D9/D10, com a FATIA REAL embutida
(_FATIA_FASE3). Mostra ANTES (ordem por score do reranker) x DEPOIS (ordem do dial).
Nao toca na base; usa pools sinteticos que imitam o baseline. Tambem VALIDA o efeito
esperado (sai != 0 se o dial nao corrigir).

USO: python _nidum_tools/demo_dial_d8_d9_d10.py
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

FATIA = C._FATIA_FASE3


def _src(chunks):
    return [{
        "document": [c[2] for c in chunks],
        "metadata": [{"name": c[0], "score": c[1]} for c in chunks],
        "distances": [c[1] for c in chunks],
    }]


def _rotulo(nome):
    return nome.split(" > ")[-1].replace(".md", "")


def mostrar(titulo, pergunta_assuntos, conceitual, chunks):
    print("\n== %s ==" % titulo)
    antes = sorted(chunks, key=lambda c: c[1], reverse=True)
    print("  ANTES (score):  " + " > ".join("%s(%.4f)" % (_rotulo(c[0]), c[1]) for c in antes))
    out = C._selecionar_e_ordenar(_src(chunks), pergunta_assuntos, FATIA, conceitual)
    print("  DEPOIS (dial):  " + " > ".join(
        "%s[%s/%s]" % (_rotulo(o["nome"]), o["colecao"][:3], o["tipo"][:4]) for o in out))
    return out


def main():
    ok = True

    # D8 (Academia): a convergencia de Academia estava enterrada (#7, nota baixa); o topo
    # tomado por convergencias de ecossistema ERRADO.
    d8 = [
        ("ACERVOS > Reunioes > Atas > ACA_Convergencia_2026-07-20.md", 0.0055, "x"),
        ("ACERVOS > Reunioes > Atas > FAN_Convergencia_2026-07-20.md", 0.10, "x"),
        ("ACERVOS > Reunioes > Atas > MKT_Convergencia_2026-07-20.md", 0.12, "x"),
        ("ACERVOS > Reunioes > Atas > MUN_Convergencia_2026-07-20.md", 0.11, "x"),
    ]
    out = mostrar("D8 Academia: 'quais as convergencias da Academia?'",
                  {"academia"}, False, d8)
    ok = ok and _rotulo(out[0]["nome"]).startswith("ACA_Convergencia")
    print("  -> ACA no topo? %s" % ("SIM" if _rotulo(out[0]["nome"]).startswith("ACA_") else "NAO"))

    # D9 (MKT/Amelia): a ata certa ja vinha em #1 - o dial NAO pode regredir.
    d9 = [
        ("ACERVOS > MKT > MKT_Reuniao_Amelia_2026-08-11.md", 0.31, "x"),
        ("FONTE > Empresas Vivas.md", 0.88, "x"),
        ("ACERVOS > Reunioes > Atas > GER_Semanal_27-07-2026.md", 0.15, "x"),
    ]
    out = mostrar("D9 Marketing: 'o que a Amelia trouxe na reuniao de MKT?'",
                  {"marketing"}, False, d9)
    ok = ok and _rotulo(out[0]["nome"]).startswith("MKT_Reuniao")
    print("  -> ata MKT no topo (nao regrediu)? %s"
          % ("SIM" if _rotulo(out[0]["nome"]).startswith("MKT_") else "NAO"))

    # D10 (Fazenda): o cronograma esta na base mas a FONTE conceitual ('Fazenda'/livros
    # a 0.8-0.9) domina o topo. O dial poe o cronograma (assunto fazenda) acima da FONTE.
    faz = ("ACERVOS > Financas e Gestao de Projetos > 3.1 EGP > 3.1.3 Portfolio de "
           "Projetos > 1. Projeto Fazenda Fortaleza > 1.1 Cronogramas > "
           "FAZ_Cronograma_31.07_v3.md")
    d10 = [
        (faz, 0.05, "conteudo do cronograma"),
        ("FONTE > Empresas Vivas.md", 0.90, "fala de fazenda no sentido conceitual"),
        ("FONTE > Documento Fundador v30.md", 0.85, "fazenda como metafora"),
    ]
    out = mostrar("D10 Fazenda: 'como esta o cronograma da Fazenda?'",
                  {"fazenda"}, False, d10)
    faz_i = [i for i, o in enumerate(out) if o["nome"] == faz][0]
    fonte_i = min(i for i, o in enumerate(out) if o["colecao"] == "FONTE")
    ok = ok and faz_i < fonte_i
    print("  -> cronograma ACIMA da FONTE conceitual? %s" % ("SIM" if faz_i < fonte_i else "NAO"))

    print("\n" + ("DEMO D8/D9/D10: dial corrige os tres" if ok
                  else "DEMO: ALGO NAO CORRIGIU"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
