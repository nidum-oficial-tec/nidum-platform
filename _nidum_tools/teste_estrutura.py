# -*- coding: utf-8 -*-
"""
Checagens ESTRUTURAIS de codigo-fonte, via AST. Para os bancos de prova do pipe/tool.

POR QUE EXISTE: as asserções antigas fixavam trechos LITERAIS do fonte
("if _anexos_recentes(body):" in fonte). Elas quebraram tres vezes SEM regressao real -
duas por reformatacao (uma frase partida em duas linhas; uma assinatura que ganhou
parametro) e uma por renomeacao legitima de variavel. Teste que da alarme falso ensina a
ignorar alarme: na terceira vez que "e so artefato de teste", a quarta - que pode ser real -
passa batido.

O AST resolve as duas causas de ruido de uma vez:
  - CONCATENACAO IMPLICITA: "abc" "def" em linhas separadas vira UMA string. Reformatar o
    fonte deixa de quebrar a asserção sobre o TEXTO.
  - ESTRUTURA vs TEXTO: assinatura, chamada e argumento sao lidos como arvore, nao como
    substring. Renomear uma variavel local quebra so o que realmente depende dela.

Regra de uso: prefira checar COMPORTAMENTO (chame a funcao). Use isto quando o alvo nao e
executavel sem o Open WebUI - assinatura do pipe, fiacao entre funcoes, texto de mensagem
dentro de um metodo async.
"""

import ast


def arvore(fonte):
    return ast.parse(fonte)


def _achar_funcao(no, nome):
    for filho in ast.walk(no):
        if isinstance(filho, (ast.FunctionDef, ast.AsyncFunctionDef)) and filho.name == nome:
            return filho
    return None


def existe(fonte, nome):
    # True se ha funcao/metodo com este nome.
    return _achar_funcao(arvore(fonte), nome) is not None


def assinatura(fonte, nome):
    # Nomes dos parametros da funcao/metodo, na ordem. [] se nao existir.
    fn = _achar_funcao(arvore(fonte), nome)
    if fn is None:
        return []
    a = fn.args
    nomes = [x.arg for x in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)]
    if a.vararg:
        nomes.append(a.vararg.arg)
    if a.kwarg:
        nomes.append(a.kwarg.arg)
    return nomes


def _nome_do_alvo(no):
    # "f(...)" -> "f" ; "obj.m(...)" -> "obj.m" (so o suficiente para casar chamadas).
    alvo = no.func
    if isinstance(alvo, ast.Name):
        return alvo.id
    if isinstance(alvo, ast.Attribute):
        base = alvo.value
        if isinstance(base, ast.Name):
            return base.id + "." + alvo.attr
        return "." + alvo.attr
    return ""


def chamadas(fonte, nome_alvo, dentro=None):
    # Lista de chamadas a 'nome_alvo'. Cada item e a lista de argumentos POSICIONAIS,
    # cada um como texto curto ("_files", "body", "self.valves.X", "<expr>").
    raiz = arvore(fonte)
    if dentro:
        raiz = _achar_funcao(raiz, dentro)
        if raiz is None:
            return []
    saida = []
    for no in ast.walk(raiz):
        if isinstance(no, ast.Call) and _nome_do_alvo(no) == nome_alvo:
            args = []
            for arg in no.args:
                if isinstance(arg, ast.Name):
                    args.append(arg.id)
                elif isinstance(arg, ast.Attribute):
                    args.append(ast.unparse(arg))
                elif isinstance(arg, ast.Constant):
                    args.append(repr(arg.value))
                else:
                    args.append("<expr>")
            saida.append(args)
    return saida


def chamada_com(fonte, nome_alvo, argumento, dentro=None):
    # True se ALGUMA chamada a 'nome_alvo' recebe 'argumento' como posicional.
    return any(argumento in args for args in chamadas(fonte, nome_alvo, dentro))


def nomeados(fonte, nome_alvo, dentro=None):
    # Conjunto dos nomes de argumentos NOMEADOS usados nas chamadas a 'nome_alvo'.
    raiz = arvore(fonte)
    if dentro:
        raiz = _achar_funcao(raiz, dentro)
        if raiz is None:
            return set()
    chaves = set()
    for no in ast.walk(raiz):
        if isinstance(no, ast.Call) and _nome_do_alvo(no) == nome_alvo:
            for kw in no.keywords:
                if kw.arg:
                    chaves.add(kw.arg)
    return chaves


def textos(fonte, nome):
    # TODO o texto literal dentro de uma funcao/metodo, com a concatenacao implicita JA
    # resolvida pelo parser. E isto que acaba com o alarme falso por reformatacao: uma
    # frase partida em cinco linhas vira uma string so aqui.
    fn = _achar_funcao(arvore(fonte), nome)
    if fn is None:
        return ""
    partes = []
    for no in ast.walk(fn):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            partes.append(no.value)
    return "\n".join(partes)


def atribuido_de(fonte, alvo, dentro=None):
    # Texto da EXPRESSAO atribuida a 'alvo' (ex.: "texto") - para checar de ONDE vem um
    # valor sem depender da formatacao da linha.
    raiz = arvore(fonte)
    if dentro:
        raiz = _achar_funcao(raiz, dentro)
        if raiz is None:
            return ""
    for no in ast.walk(raiz):
        if isinstance(no, ast.Assign):
            for t in no.targets:
                if isinstance(t, ast.Name) and t.id == alvo:
                    return ast.unparse(no.value)
    return ""


def campos_de_classe(fonte, nome_classe):
    # Nomes dos atributos anotados de uma classe (ex.: as Valves).
    for no in ast.walk(arvore(fonte)):
        if isinstance(no, ast.ClassDef) and no.name == nome_classe:
            return [
                f.target.id
                for f in no.body
                if isinstance(f, ast.AnnAssign) and isinstance(f.target, ast.Name)
            ]
    return []


def fatia_de(fonte, alvo, dentro=None):
    # True se existe QUALQUER fatiamento (corte) sobre a variavel 'alvo'. Usado para
    # provar a AUSENCIA de truncagem do anexo - a regra que nao pode ser violada.
    raiz = arvore(fonte)
    if dentro:
        raiz = _achar_funcao(raiz, dentro)
        if raiz is None:
            return False
    for no in ast.walk(raiz):
        if isinstance(no, ast.Subscript) and isinstance(no.slice, ast.Slice):
            base = no.value
            if isinstance(base, ast.Name) and base.id == alvo:
                return True
    return False
