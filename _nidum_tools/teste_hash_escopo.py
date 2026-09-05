# -*- coding: ascii -*-
"""
Prova de que a selecao por "#" ESCOPA as ferramentas em Native.

O DEFEITO, medido em producao (05/09/2026): selecionar a base "Reunioes" pelo #
mostrava o chip na mensagem e injetava o contexto certo - e o agente chamava
query_knowledge_files SEM knowledge_ids, trazendo fontes de Gestao de Projetos e
ACA, bases que o usuario nao selecionou. O # nao escopava nada.

A CAUSA: get_builtin_tools le EXATAMENTE DUAS fontes de escopo -
model.info.meta.knowledge e metadata['folder_knowledge']. O # nao entra em
nenhuma: poe o item em form_data['files'], que alimenta o retrieval pre-pipe e
para ai. Contexto injetado, ferramenta desescopada - e o modelo decide pela
ferramenta.

O QUE ESTE TESTE GUARDA, e que nenhuma leitura pega:

1. Que o item selecionado CHEGA ao lugar que get_builtin_tools le. Um teste que
   so verificasse "o middleware nao quebrou" ficaria verde com o defeito de pe -
   ele estava verde ontem.

2. Que o item SAI de form_data['files']. Se ficar nos dois lugares, o retrieval
   pre-pipe roda E a ferramenta busca: o mesmo documento entra duas vezes e o
   orcamento e pago em dobro. E o sintoma seria "funciona", que e o pior.

3. O CASO INVERSO: sem #, nada e escopado e list_knowledge_bases continua
   disponivel. Sem esta metade, um conserto que escopasse SEMPRE passaria - e
   quebraria o Modo 1, que e o uso normal.

USO: python _nidum_tools/teste_hash_escopo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ID_REUNIOES = "52c794ea-caa8-4f58-a343-d08a79f8110c"
ID_PRODUTOS = "afa53a66-f0cf-4c61-a741-e25b5ced479e"

falhas = []


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    if not cond:
        falhas.append(nome)


def aplicar(form_data, metadata):
    """Reproduz o bloco do middleware, na mesma ordem e com as mesmas condicoes.

    E copia deliberada: o middleware e async e carrega o mundo inteiro do OWUI,
    entao importa-lo aqui custaria mais do que prova. A guarda contra a copia
    divergir e o proprio teste no fim do arquivo, que le o middleware REAL e
    falha se as condicoes mudarem la sem mudar aqui.
    """
    if metadata.get("params", {}).get("function_calling") == "native":
        sel = [
            f for f in (form_data.get("files") or [])
            if isinstance(f, dict) and f.get("type") in ("collection", "file", "note")
            and f.get("id")
        ]
        if sel:
            metadata["folder_knowledge"] = [
                *(metadata.get("folder_knowledge") or []),
                *sel,
            ]
            ids = {id(f) for f in sel}
            form_data["files"] = [
                f for f in (form_data.get("files") or []) if id(f) not in ids
            ]
    return form_data, metadata


def ferramentas(model_knowledge):
    """As duas listas de get_builtin_tools (utils/tools.py), sem o resto do OWUI."""
    if model_knowledge:
        return ["list_knowledge", "search_knowledge_files", "grep_knowledge_files",
                "query_knowledge_files", "view_knowledge_file"]
    return ["list_knowledge_bases", "search_knowledge_bases", "query_knowledge_bases",
            "grep_knowledge_files", "search_knowledge_files", "query_knowledge_files",
            "view_knowledge_file"]


def main():
    print("== COM # em Reunioes, modo Native ==")
    fd = {"messages": [], "files": [{"type": "collection", "id": ID_REUNIOES,
                                     "name": "Reunioes"}]}
    md = {"params": {"function_calling": "native"}}
    fd, md = aplicar(fd, md)
    fk = md.get("folder_knowledge") or []
    check("a selecao chega em metadata['folder_knowledge']", len(fk) == 1)
    check("com o id certo, e SO ele",
          [f["id"] for f in fk] == [ID_REUNIOES])
    check("saiu de form_data['files'] (nao busca duas vezes)", fd["files"] == [])
    ts = ferramentas(fk)
    check("query_knowledge_files continua disponivel", "query_knowledge_files" in ts)
    check("list_knowledge_bases some (o agente perde as outras bases)",
          "list_knowledge_bases" not in ts)
    check("e list_knowledge escopado entra no lugar", "list_knowledge" in ts)

    print("\n== SEM #, modo Native (o Modo 1, uso normal) ==")
    fd2 = {"messages": [], "files": []}
    md2 = {"params": {"function_calling": "native"}}
    fd2, md2 = aplicar(fd2, md2)
    check("nada e escopado", not md2.get("folder_knowledge"))
    ts2 = ferramentas(md2.get("folder_knowledge") or [])
    check("list_knowledge_bases DISPONIVEL (descobre as bases sozinho)",
          "list_knowledge_bases" in ts2)
    check("query_knowledge_files sem escopo", "query_knowledge_files" in ts2)

    print("\n== duas bases pelo #: compoe ==")
    fd3 = {"messages": [], "files": [
        {"type": "collection", "id": ID_REUNIOES, "name": "Reunioes"},
        {"type": "collection", "id": ID_PRODUTOS, "name": "Produtos"}]}
    md3 = {"params": {"function_calling": "native"}}
    fd3, md3 = aplicar(fd3, md3)
    check("as duas chegam ao escopo",
          sorted(f["id"] for f in md3["folder_knowledge"]) ==
          sorted([ID_REUNIOES, ID_PRODUTOS]))

    print("\n== o que NAO pode mudar ==")
    fd4 = {"messages": [], "files": [{"type": "collection", "id": ID_REUNIOES}]}
    md4 = {"params": {"function_calling": "default"}}
    fd4, md4 = aplicar(fd4, md4)
    check("FORA do Native, nada muda (o caminho antigo e o unico que existe)",
          not md4.get("folder_knowledge") and len(fd4["files"]) == 1)

    fd5 = {"messages": [], "files": [{"type": "image", "url": "x"}]}
    md5 = {"params": {"function_calling": "native"}}
    fd5, md5 = aplicar(fd5, md5)
    check("anexo que nao e conhecimento nao vira escopo",
          not md5.get("folder_knowledge") and len(fd5["files"]) == 1)

    fd6 = {"messages": [], "files": [{"type": "collection", "name": "sem id"}]}
    md6 = {"params": {"function_calling": "native"}}
    fd6, md6 = aplicar(fd6, md6)
    check("item sem id e ignorado (nao vira escopo vazio)",
          not md6.get("folder_knowledge"))

    fd7 = {"messages": [], "files": [{"type": "collection", "id": ID_REUNIOES}]}
    md7 = {"params": {"function_calling": "native"},
           "folder_knowledge": [{"type": "collection", "id": ID_PRODUTOS}]}
    fd7, md7 = aplicar(fd7, md7)
    check("pasta E # somam, o # nao apaga a pasta",
          sorted(f["id"] for f in md7["folder_knowledge"]) ==
          sorted([ID_REUNIOES, ID_PRODUTOS]))

    print("\n== a copia acima nao divergiu do middleware real ==")
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "backend", "open_webui", "utils", "middleware.py")
    try:
        with open(caminho, encoding="utf-8") as f:
            fonte = f.read()
    except OSError:
        print("  (middleware nao encontrado - guarda pulada)")
        fonte = ""
    if fonte:
        check("o middleware ainda entrega em metadata['folder_knowledge']",
              "metadata['folder_knowledge'] = [" in fonte)
        check("ainda condicionado a function_calling == 'native'",
              "metadata.get('params', {}).get('function_calling') == 'native'" in fonte)
        check("ainda filtra por collection/file/note",
              "('collection', 'file', 'note')" in fonte)

    print("")
    if falhas:
        print("HASH ESCOPO: %d FALHA(S)" % len(falhas))
        return 1
    print("HASH ESCOPO OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
