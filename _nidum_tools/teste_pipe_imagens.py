# -*- coding: utf-8 -*-
"""
Teste 5 (o critico): o prompt que vai ao GERADOR NAO pode conter base64.
Testa as funcoes puras do pipe sem subir o Open WebUI.
USO: python teste_pipe_imagens.py
"""
import os
import re
import sys

import teste_estrutura as E

_DIR = os.path.dirname(os.path.abspath(__file__))
CAM = os.path.join(_DIR, "chatnd.py")


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def carregar_funcoes():
    # O pipe importa open_webui no topo; para testar as funcoes PURAS, extraimos os
    # trechos das funcoes que nos interessam e executamos num namespace proprio.
    fonte = open(CAM, encoding="utf-8").read()
    ns = {}
    for nome in ("_msgs_sem_imagem", "_nota_imagens", "_tem_anexo_imagem",
                 "_extrair_imagens_anexo"):
        m = re.search(r"^def " + nome + r"\(.*?(?=^\S)", fonte, re.M | re.S)
        exec(m.group(0), ns)
    return ns, fonte


def main():
    ok = True
    ns, fonte = carregar_funcoes()
    _msgs_sem_imagem = ns["_msgs_sem_imagem"]
    _nota_imagens = ns["_nota_imagens"]
    _tem_anexo = ns["_tem_anexo_imagem"]
    _extrair = ns["_extrair_imagens_anexo"]

    B64 = "data:image/jpeg;base64," + ("A" * 40000)   # uma "foto" grande
    msg_com_anexo = {
        "role": "user",
        "content": [
            {"type": "text", "text": "monte um deck com esta foto"},
            {"type": "image_url", "image_url": {"url": B64}},
        ],
    }
    msgs = [{"role": "user", "content": "ola"}, msg_com_anexo]

    print("== deteccao e extracao (reuso, nao reimplementacao) ==")
    ok &= check("detecta o anexo de imagem", _tem_anexo(msg_com_anexo) is True)
    ok &= check("extrai a data-URL do anexo", _extrair(msg_com_anexo) == [B64])

    print("== 5. o prompt do GERADOR nao leva base64 ==")
    limpas = _msgs_sem_imagem(msgs)
    txt = str(limpas)
    ok &= check("base64 NAO sobrevive a sanitizacao", "base64," not in txt)
    ok &= check("os 40k chars sumiram (prompt %d chars)" % len(txt), len(txt) < 500)
    ok &= check("o TEXTO do pedido foi preservado", "monte um deck com esta foto" in txt)
    ok &= check("mensagens anteriores intactas", limpas[0]["content"] == "ola")
    ok &= check("'files' removido junto (outra via de vazamento)",
                all("files" not in m for m in limpas))

    print("== sem anexo: caminho identico ao de antes (sem regressao) ==")
    simples = [{"role": "user", "content": "faca um pdf"}]
    ok &= check("mensagem de texto puro atravessa inalterada",
                _msgs_sem_imagem(simples) == simples)

    print("== instrucao dinamica de marcadores ==")
    nota = _nota_imagens(2)
    ok &= check("cita IMAGEM_1 e IMAGEM_2", "IMAGEM_1" in nota and "IMAGEM_2" in nota)
    ok &= check("nao cita IMAGEM_3", "IMAGEM_3" not in nota)
    ok &= check("proibe placeholder de texto", "inserir imagem aqui" in nota)
    ok &= check("a nota NAO contem base64", "base64" not in nota)

    print("== fiacao no codigo (o que a leitura estatica garante) ==")
    ok &= check("a rota de arquivo agora extrai anexo de imagem",
                E.chamada_com(fonte, "_extrair_imagens_anexo", "_mu"))
    ok &= check("_gerar_arquivo recebe imagens",
                "imagens" in E.assinatura(fonte, "_gerar_arquivo"))
    ok &= check("sanitiza so quando ha anexo",
                E.chamada_com(fonte, "_msgs_sem_imagem", "messages"))
    # Os 5 metodos que aceitam imagem sao chamados com o argumento NOMEADO; o xlsx nao.
    com_img = [m for m in ("gerar_pptx", "gerar_docx", "gerar_pdf", "gerar_html",
                           "gerar_apresentacao_html")
               if "imagens" in E.nomeados(fonte, "tool." + m)]
    ok &= check("os 5 metodos recebem imagens= (nomeado): %s" % len(com_img),
                len(com_img) == 5)
    ok &= check("gerar_xlsx NAO recebe imagens",
                "imagens" not in E.nomeados(fonte, "tool.gerar_xlsx"))

    print("\nRESULTADO: " + ("PIPE OK" if ok else "HOUVE FALHA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
