# -*- coding: ascii -*-
"""
Prova do `conferir_registros` - escrita ANTES das duas classes novas.

CADA CASO AQUI E UM REGISTRO VENCIDO REAL, nao um exemplo inventado. E a
diferenca importa: um teste com fixture inventada prova que o codigo faz o que o
codigo faz. Estes provam que ele pega o que JA PASSOU despercebido - por semanas,
com a suite verde.

OS SEIS CASOS, e o dano que cada um causou:

  valve_fantasma        doc descrevia valve que nao existe. Alguem procura o
                        interruptor no painel e nao acha; conclui que a doc esta
                        certa e o painel, quebrado.
  modelo_revogado       modelo citado na doc que foi revogado/renomeado. O caso
                        do A.2: cinco correcoes de uma vez.
  id_fantasma           id de colecao apagada ainda citado. BASE_CONHECIMENTO_ID
                        apontou para duas colecoes apagadas, e so a valve do
                        painel salvava.
  fixture_vencida       fixture com caminho que a reformulacao renomeou. Custou
                        NOVE de dezenove caminhos do mapa_assuntos mortos, por
                        semanas, com o DIAL_FASE3 ligado e a etiqueta de assunto
                        valendo zero. A suite ficava VERDE.
  frac_catastrofe       FRAC_CATASTROFE fora de 0,25. Nasce do plano de migracao:
                        a rodada B sobe para 0,35 e PRECISA voltar. Um freio
                        afrouxado que ninguem restaurou nao da erro nenhum - ele
                        so deixa de proteger, e a proxima remocao em massa passa.
  base_indevida         base com contagem != 0 que nao devia receber arquivo.
                        Pasta-mae declarada como excluida cujo destino recebeu
                        conteudo assim mesmo: e o unico sintoma observavel de um
                        roteamento errado.

USO: py _nidum_manutencao/teste_conferir_registros.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conferir_registros as CR  # noqa: E402

falhas = []


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    if not cond:
        falhas.append(nome)


def classes(achados):
    return sorted({a["classe"] for a in achados})


def main():
    print("== FRAC_CATASTROFE: o freio que a migracao afrouxa e alguem esquece ==")
    check("0.25 (o valor de desenho) -> nada a relatar",
          CR.conferir_frac_catastrofe("0.25") == [])
    check("0,25 com virgula tambem passa",
          CR.conferir_frac_catastrofe("0,25") == [])
    check("ausente -> nada (o padrao do codigo e 0.25)",
          CR.conferir_frac_catastrofe(None) == [])
    a = CR.conferir_frac_catastrofe("0.35")
    check("0.35 (o valor da rodada B) -> ACUSA", len(a) == 1)
    check("o achado diz o valor encontrado", "0.35" in str(a))
    check("e diz o valor esperado", "0.25" in str(a))
    check("0.10 (mais apertado que o desenho) tambem acusa",
          len(CR.conferir_frac_catastrofe("0.10")) == 1)
    check("lixo nao quebra o conferidor",
          isinstance(CR.conferir_frac_catastrofe("abacaxi"), list))

    print("\n== base que nao devia receber arquivo ==")
    contagens = {"Produtos": 140, "Financas": 0, "Plataformas Regionais": 0}
    vazias = ["Financas", "Plataformas Regionais"]
    check("todas as excluidas em zero -> nada a relatar",
          CR.conferir_bases_vazias(contagens, vazias) == [])
    ruim = dict(contagens, **{"Financas": 3})
    a = CR.conferir_bases_vazias(ruim, vazias)
    check("excluida com 3 arquivos -> ACUSA", len(a) == 1)
    check("o achado NOMEIA a base", "Financas" in str(a))
    check("e diz quantos", "3" in str(a))
    check("base que nao esta na lista de vazias e ignorada",
          CR.conferir_bases_vazias({"Produtos": 140}, vazias) == [])
    check("base vazia AUSENTE da contagem nao acusa (ainda nao criada)",
          CR.conferir_bases_vazias({"Produtos": 1}, ["Financas"]) == [])

    print("\n== o formato do achado e o mesmo das classes antigas ==")
    a = CR.conferir_frac_catastrofe("0.35")[0]
    for campo in ("classe", "detalhe", "onde", "consequencia"):
        check("achado tem '%s'" % campo, campo in a)
    check("a consequencia explica o dano, nao repete o fato",
          len(a["consequencia"]) > 40)

    print("\n== job VERDE ao encontrar (mesma regra do relatorio de orfaos) ==")
    check("achou -> codigo 2 (resultado, nao falha)",
          CR.codigo_de_saida([{"classe": "x"}]) == 2)
    check("nada -> codigo 0", CR.codigo_de_saida([]) == 0)
    check("1 fica reservado para o script quebrar",
          CR.codigo_de_saida([]) != 1 and CR.codigo_de_saida([{"classe": "x"}]) != 1)

    print("")
    if falhas:
        print("CONFERIR REGISTROS: %d FALHA(S)" % len(falhas))
        return 1
    print("CONFERIR REGISTROS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
