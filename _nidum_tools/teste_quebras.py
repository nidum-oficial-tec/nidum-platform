# -*- coding: utf-8 -*-
"""
Prova de `_quebras` - separador de paragrafo virando quebra normal.

O DEFEITO ERA MUDO, que e o pior tipo. Texto vindo de documento (Word,
PowerPoint, PDF convertido) usa VT (0x0B) onde o autor apertou Shift+Enter, e FF
(0x0C) na quebra de pagina. O Word chama os dois de "quebra"; o Python nao -
str.split() so conhece \n. Resultado: o bloco inteiro virava UMA linha, o
separador sobrava dentro do texto como caractere de controle, e o PowerPoint
desenhava um retangulo vazio no meio da frase. Sem erro, sem log.

DOIS CAMINHOS, E O TESTE COBRE OS DOIS. O texto chega ao slide de duas formas:
como string solta (_texto_para_slide) e como campo de dict (o modelo escreve
'texto'/'bullets' direto). Consertar so o primeiro deixaria de pe justamente a
metade que aparece no slide, porque o laco agentico usa o segundo.

USO: python _nidum_tools/teste_quebras.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerador_de_arquivos_nidum as G  # noqa: E402

VT = chr(11)
FF = chr(12)
CR = chr(13)
LF = chr(10)
falhas = []


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    if not cond:
        falhas.append(nome)


def main():
    print("== os separadores que o Word chama de quebra ==")
    for bruto, rotulo in [(VT, "VT 0x0B (Shift+Enter)"), (FF, "FF 0x0C (pagina)"),
                          (CR + LF, "CRLF (Windows)"), (CR, "CR (Mac antigo)"),
                          (chr(8232), "LS U+2028 (PDF)"), (chr(8233), "PS U+2029")]:
        check("%-24s -> quebra normal" % rotulo,
              G._quebras("linha1" + bruto + "linha2") == "linha1" + LF + "linha2")

    print("\n== o que NAO pode mudar ==")
    check("texto sem separador passa intacto",
          G._quebras("Uma frase normal, com virgula.") == "Uma frase normal, com virgula.")
    check("quebra que ja era \n continua uma so",
          G._quebras("a" + LF + "b") == "a" + LF + "b")
    check("tab horizontal NAO e quebra (indentacao legitima)",
          G._quebras("a" + chr(9) + "b") == "a" + chr(9) + "b")
    check("vazio", G._quebras("") == "")
    check("None vira string vazia, nao 'None'", G._quebras(None) == "")

    print("\n== CAMINHO 1: string solta -> slide ==")
    s = G._texto_para_slide("Titulo" + VT + "- um" + VT + "- dois" + VT + "corpo")
    check("VT separa titulo, bullets e corpo", s.get("titulo") == "Titulo")
    check("os dois bullets aparecem", s.get("bullets") == ["um", "dois"])
    check("o corpo aparece", s.get("texto") == "corpo")
    check("nenhum caractere de controle sobra no slide",
          not any(c in repr(s) for c in ("x0b", "x0c")))

    print("\n== CAMINHO 2: dict do modelo (o do laco agentico) ==")
    slides = [{"tipo": "conteudo", "titulo": "T" + VT + "sub",
               "texto": "primeira" + VT + "segunda",
               "bullets": ["a" + FF + "b", "normal"]}]
    slides, erro = G._normalizar_corpo_slides(slides, "gerar_pptx")
    check("normalizacao nao rejeita o slide", erro is None)
    check("titulo limpo", VT not in slides[0]["titulo"])
    check("texto limpo", slides[0]["texto"] == "primeira" + LF + "segunda")
    check("bullet limpo", slides[0]["bullets"][0] == "a" + LF + "b")
    check("bullet sem separador intacto", slides[0]["bullets"][1] == "normal")

    print("")
    if falhas:
        print("QUEBRAS: %d FALHA(S)" % len(falhas))
        return 1
    print("QUEBRAS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
