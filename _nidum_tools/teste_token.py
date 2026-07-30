# -*- coding: utf-8 -*-
"""
Banco de provas da AUDITORIA DE TOKEN - Fatia 2a (1.55.0). Prova os requisitos DUROS:
  - _extrair_usage le os DOIS provedores (OpenAI prompt/completion, Anthropic input/output)
    e deriva o provedor do formato; nunca levanta;
  - decomposicao de chars (historico exclui o pedido atual; content = str ou partes);
  - CONTENT-FREE: o log de orcamento so imprime METRICAS (ev.get), nunca teor (prova AST);
  - A|B: a medicao nao referencia analytics; o write so no _analytics_write (via _registrar);
  - fiacao: classificador grava usage+provedor; gerador SOMA sobre o retry; arquivo mede
    sistema/anexo; _pipe_impl mede origem_modelo (do model_id) e historico;
  - sem nome indefinido nas funcoes novas.
USO: python teste_token.py
"""
import ast
import json
import os
import re

import teste_estrutura as E

_DIR = os.path.dirname(os.path.abspath(__file__))
CAM = os.path.join(_DIR, "chatnd.py")


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def carregar():
    fonte = open(CAM, encoding="utf-8").read()
    ns = {"json": json}
    for nome in ("_extrair_usage", "_len_conteudo", "_chars_historico"):
        m = re.search(r"^def " + nome + r"\(.*?(?=^\S)", fonte, re.M | re.S)
        exec(m.group(0), ns)
    return ns, fonte


class _Corpo:
    # imita o objeto-com-.body que generate_chat_completion pode devolver (nao-dict).
    def __init__(self, d):
        self.body = json.dumps(d)


def _fn_node(fonte, nome):
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return no
    return None


def _src(fonte, nome):
    # SOURCE (codigo) da funcao, nao os literais - para checar a fiacao por substring.
    no = _fn_node(fonte, nome)
    if no is None:
        return ""
    linhas = fonte.split("\n")[no.lineno - 1: no.end_lineno]
    return "\n".join(linhas)


def _nomes_usados(fonte, nome):
    no = _fn_node(fonte, nome)
    s = set()
    if no is None:
        return s
    for x in ast.walk(no):
        if isinstance(x, ast.Name):
            s.add(x.id)
        elif isinstance(x, ast.Attribute):
            s.add(x.attr)
    return s


def _orcamento_so_metricas(fonte):
    # O log de 'orcamento' em _registrar so pode receber CONSTANTES e ev.get("<chave>") -
    # nunca uma variavel de conteudo. Prova estrutural de content-free do log de medicao.
    no = _fn_node(fonte, "_registrar")
    if no is None:
        return False
    achou = False
    for c in ast.walk(no):
        if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and c.func.attr == "info"):
            continue
        # a chamada cujo 1o arg (constante) contem 'orcamento'
        if not (c.args and isinstance(c.args[0], ast.Constant)
                and "orcamento" in str(c.args[0].value)):
            continue
        achou = True
        for arg in c.args[1:]:
            if isinstance(arg, ast.Constant):
                continue
            # so aceita ev.get("<literal>")
            ok_arg = (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute)
                      and arg.func.attr == "get"
                      and isinstance(arg.func.value, ast.Name) and arg.func.value.id == "ev"
                      and len(arg.args) == 1 and isinstance(arg.args[0], ast.Constant))
            if not ok_arg:
                return False
    return achou


def main():
    ns, fonte = carregar()
    ok = True
    USG = ns["_extrair_usage"]
    LEN = ns["_len_conteudo"]
    HIS = ns["_chars_historico"]

    print("== _extrair_usage: dois provedores, nomes de campo diferentes ==")
    ok &= check("OpenAI: prompt_tokens/completion_tokens -> openai",
                USG({"usage": {"prompt_tokens": 100, "completion_tokens": 20}})
                == (100, 20, "openai"))
    ok &= check("Anthropic: input_tokens/output_tokens -> anthropic",
                USG({"usage": {"input_tokens": 80, "output_tokens": 10}})
                == (80, 10, "anthropic"))
    ok &= check("sem usage -> (None,None,None)", USG({"choices": []}) == (None, None, None))
    ok &= check("usage nao-dict -> vazio", USG({"usage": 5}) == (None, None, None))
    ok &= check("objeto-com-body (nao-dict) tambem le",
                USG(_Corpo({"usage": {"prompt_tokens": 7, "completion_tokens": 3}}))
                == (7, 3, "openai"))
    ok &= check("lixo nao levanta", USG(None) == (None, None, None) and USG(42) == (None, None, None))
    ok &= check("so prompt presente ainda classifica provedor",
                USG({"usage": {"prompt_tokens": 5}}) == (5, None, "openai"))

    print("== _len_conteudo: string, partes, e nao-texto ==")
    ok &= check("string -> len", LEN("abcde") == 5)
    ok &= check("partes com text -> soma so o texto",
                LEN([{"type": "text", "text": "abc"}, {"type": "image_url"}]) == 3)
    ok &= check("None/num -> 0", LEN(None) == 0 and LEN(5) == 0)

    print("== _chars_historico: exclui o PEDIDO atual (ultima do usuario) ==")
    msgs = [{"role": "user", "content": "oi"},           # 2
            {"role": "assistant", "content": "ola tudo"},  # 8
            {"role": "user", "content": "pergunta atual longa"}]  # excluida
    ok &= check("conta anteriores, exclui a ultima do usuario", HIS(msgs) == 2 + 8)
    ok &= check("so um turno do usuario -> historico 0",
                HIS([{"role": "user", "content": "unica"}]) == 0)
    ok &= check("historico com partes de conteudo",
                HIS([{"role": "assistant", "content": [{"type": "text", "text": "xy"}]},
                     {"role": "user", "content": "q"}]) == 2)
    ok &= check("vazio/lixo -> 0", HIS([]) == 0 and HIS(None) == 0)

    print("== CONTENT-FREE (AST): o log de orcamento so imprime metricas ==")
    ok &= check("log de orcamento so recebe ev.get(<chave>) e constantes",
                _orcamento_so_metricas(fonte))

    print("== A|B (estrutural): a medicao nao toca analytics ==")
    for fn in ("_extrair_usage", "_len_conteudo", "_chars_historico"):
        u = _nomes_usados(fonte, fn)
        ok &= check("%s nao referencia analytics" % fn,
                    not (u & {"_analytics_write", "_registrar", "_analytics_agregar"}))
    for fn in ("_pipe_impl", "_classificar", "_gerar_arquivo", "_chamar_gerador"):
        no = _fn_node(fonte, fn)
        chamadas = {c.func.id for c in ast.walk(no)
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        ok &= check("%s nao CHAMA _analytics_write (write so via _registrar/finally)" % fn,
                    "_analytics_write" not in chamadas)

    print("== FIACAO: instrumentacao nos pontos certos ==")
    fc = _src(fonte, "_classificar")
    ok &= check("classificador grava usage + classif_provedor",
                "_extrair_usage(res)" in fc and 'classif_provedor"]' in fc)
    fg = _src(fonte, "_chamar_gerador")
    ok &= check("gerador SOMA sobre o retry (nao sobrescreve)",
                '(_ev.get("tok_gerador_prompt") or 0) +' in fg)
    fa = _src(fonte, "_gerar_arquivo")
    ok &= check("arquivo mede sistema e anexo (disjuntos)",
                'chars_sistema"] = len(sistema)' in fa and 'chars_anexo"] = len(original' in fa)
    fp = _src(fonte, "_pipe_impl")
    ok &= check("origem_modelo vem do metadata['model_id']",
                'model_id"' in fp and 'origem_modelo"]' in fp)
    ok &= check("historico medido no _pipe_impl",
                "_chars_historico(body.get" in fp)
    ok &= check("acervo medido nas rotas (documentos/geral/arquivo)",
                fp.count('chars_acervo"]') >= 3)
    ok &= check("gerador so soma prompt_tokens quando presente (nao cria 0 espurio)",
                "if p is not None:" in fg and "if c is not None:" in fg)

    print("== ESCOPO: sem nome indefinido nas funcoes novas ==")
    for fn in ("_extrair_usage", "_len_conteudo", "_chars_historico"):
        u = E.nomes_indefinidos(fonte, fn)
        ok &= check("%s: sem nome indefinido" % fn, not u)

    print("\nRESULTADO: " + ("TOKEN 2a OK" if ok else "HOUVE FALHA"))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
