# -*- coding: utf-8 -*-
"""
Prova do gerar_codigo (modo preservacao, tool 2.6.0): grava o codigo VERBATIM, sem
injetar marca nem editor. O ponto do conserto do HTML do Guilherme e que <script> e
handlers SOBREVIVEM byte a byte.
USO: python teste_codigo_tool.py
"""
import asyncio
import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)
import gerador_de_arquivos_nidum as G  # noqa: E402

_gravados = {}


async def _fake(data, nome, ct, uid):
    _gravados[nome] = (data, ct)
    return "/local/" + nome


G._salvar_e_linkar = _fake


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


async def main():
    ok = True
    t = G.Tools()

    # um app real: script + handlers, exatamente o que o caso do Guilherme perdia
    APP = (
        "<!DOCTYPE html><html><body>\n"
        "<button class=\"btn\" onclick=\"baixar()\">Baixar Relatorio</button>\n"
        "<input id=\"nota\" type=\"range\" min=\"1\" max=\"5\" step=\"0.1\">\n"
        "<div id=\"regua\"></div>\n"
        "<script>\n"
        "function baixar(){ /* logica real */ return true; }\n"
        "document.getElementById('nota').addEventListener('input', function(e){\n"
        "  var v=parseFloat(e.target.value);\n"
        "  document.getElementById('regua').style.background =\n"
        "    'hsl('+((v-1)/4*120)+',80%,50%)';\n"
        "});\n"
        "</script></body></html>"
    )

    print("== gerar_codigo grava o codigo VERBATIM ==")
    r = await t.gerar_codigo("Vistoria", APP, "html", None)
    ok &= check("devolve link", "Link para download" in r)
    nome = [n for n in _gravados if n.endswith(".html")][0]
    data, ct = _gravados[nome]
    saida = data.decode("utf-8")
    ok &= check("byte a byte identico ao original", saida == APP)
    ok &= check("content-type text/html", ct == "text/html")
    ok &= check("nome no padrao de governanca (.html)", nome.endswith(".html"))

    print("== o que o modo preservacao NAO faz (o conserto do meio-conserto) ==")
    ok &= check("NAO injeta marca Nidum (nao repinta o CSS do app)",
                "Maxima Nouva" not in saida and "nidum-" not in saida.lower())
    ok &= check("NAO injeta a barra de edicao (nao briga com o formulario)",
                "ndbar" not in saida and "NIDUM_EDITOR" not in saida)
    ok &= check("os <script> SObrevivem (o bug do Guilherme)", "<script>" in saida)
    ok &= check("os handlers SObrevivem (onclick)", "onclick=\"baixar()\"" in saida)
    ok &= check("o addEventListener SObrevive", "addEventListener('input'" in saida)
    ok &= check("a logica real NAO virou placeholder",
                "logica ilustrativa" not in saida.lower()
                and "parseFloat" in saida)

    print("== contagem de handlers: original vs gerado (nao pode cair) ==")
    import re
    n_orig = len(re.findall(r"onclick|addEventListener", APP))
    n_ger = len(re.findall(r"onclick|addEventListener", saida))
    ok &= check("handlers preservados (%d == %d)" % (n_orig, n_ger), n_ger == n_orig)

    print("== outras extensoes da familia (round-trip generico) ==")
    for conteudo, ext, ct_esp in (
        ("body{color:red}", "css", "text/css"),
        ("const x = 1;", "js", "text/javascript"),
        ('{"a": 1}', "json", "application/json"),
        ("# Titulo\n\ntexto", "md", "text/markdown"),
    ):
        _gravados.clear()
        await t.gerar_codigo("T", conteudo, ext, None)
        n = [x for x in _gravados if x.endswith("." + ext)]
        ok &= check("gera .%s verbatim" % ext,
                    bool(n) and _gravados[n[0]][0].decode() == conteudo
                    and _gravados[n[0]][1] == ct_esp)

    print("== degradacao segura ==")
    ok &= check("conteudo vazio -> diagnostico, nao link",
                "Link para download" not in await t.gerar_codigo("T", "   ", "html", None))
    _gravados.clear()
    await t.gerar_codigo("T", "x", "exe", None)   # ext fora da familia
    n = list(_gravados)
    ok &= check("ext fora da familia -> cai para .txt (nao quebra)",
                bool(n) and n[0].endswith(".txt"))

    print("\nRESULTADO: " + ("GERAR_CODIGO OK" if ok else "HOUVE FALHA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
