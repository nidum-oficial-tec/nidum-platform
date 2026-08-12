# -*- coding: ascii -*-
"""
Contrato TDD da Fase 3 (dial de rankeamento). VERMELHO ATE A FASE 3 EXISTIR.

Este arquivo escreve as INVARIANTES da Fase 3 como asseracoes offline, ANTES do codigo.
Exercita so funcoes PURAS - nao faz rede, nao busca, nao sobe o OWUI (stub, igual ao
teste_debug_trechos.py). Assim que as 3 funcoes existirem no chatnd.py, as asseracoes
rodam de verdade e viram verde/vermelho reais.

SEMANTICA DE ESTADO (de proposito):
  - Enquanto QUALQUER das 3 funcoes NAO existir: os 9 casos ficam PENDENTES, o arquivo
    IMPRIME o contrato e sai 0 - para NAO poluir a suite offline com falha falsa (o
    trabalho ainda nao venceu). O banner deixa o "vermelho" visivel.
  - Quando as 3 existirem: roda as asseracoes; sai != 0 se qualquer uma falhar.

CONTRATO DAS 3 FUNCOES (assinaturas travadas com o Davi):
  _classificar_trecho(nome, corpo, mapa) -> dict
      {"colecao": "FONTE"|"ACERVOS",
       "assuntos": set[str],           # chaves de assunto do mapa (sigla do NOME U pasta funcional)
       "tipo": "informativo"|"ata"|"registro"|"fonte_doutrina",
       "data": str|None}               # 'modificado' do cabecalho, ou None
  _assuntos_da_pergunta(texto, mapa) -> set[str]
  _selecionar_e_ordenar(sources, assuntos_pergunta, mapa, conceitual) -> list[dict]
      cada item na ORDEM de injecao, com ao menos:
      {"nome":str, "colecao":str, "tipo":str, "assuntos":set, "score":float}

PRINCIPIOS QUE OS CASOS PROVAM:
  - reforcar nunca filtrar / expandir nunca encolher (nenhum candidato sumido);
  - ancora FONTE garantida (minoria), nunca some, teto <=3;
  - dois eixos de boost: assunto (pasta/sigla) e tipo (informativo cross-cutting);
  - diversidade dura p/ status/relacional: informativo + ata + registro juntos;
  - recencia POR-TIPO (informativo/registro sim; FONTE atemporal);
  - trava 5: pergunta conceitual nao promove operacional acima da FONTE.

USO: python _nidum_tools/teste_fase3.py
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


# ------------------------------------------------------------------ mapa-fixture
# Subset do TEC_MapaAssuntos_rascunho_12-08-2026_v1.json, inline para o teste nao
# depender do arquivo real. So os assuntos/tipos que os 9 casos usam.
MAPA = {
    "tipos_de_fonte": {
        "informativo": {
            "deteccao_nome": ["ACA_Informativo_Executivo_", "ACA_Informacoes_Ecossistemas_"],
            "transversal": True,
            "recencia": "so_ultima",
        },
        "ata": {
            "deteccao_nome": ["_Convergencia_", "_Reuniao", "_Conversa", "_Semanal",
                              "ATA_", "GER_", "CTE_", "CT_", "CC_", "CE_"],
            "deteccao_pasta": "Reunioes/Atas",
            "recencia": "recente_pesa_antiga_guarda",
        },
        "registro": {
            "deteccao_nome_exemplos": ["_Cronograma_", "Quadro_de_Pessoas", "Brandbook"],
            "recencia": "versao_ou_data_vence",
        },
        "fonte_doutrina": {"deteccao": "prefixo FONTE > ", "recencia": "atemporal"},
    },
    "assuntos": {
        "academia": {"apelidos": ["academia"], "siglas": ["ACA"],
                     "pastas": ["ACA/", "ACERVOS/Reunioes/Atas"]},
        "fazenda": {"apelidos": ["fazenda", "fazenda fortaleza"], "siglas": ["FAN"],
                    "pastas": ["FAN/",
                               "ACERVOS/Financas e Gestao de Projetos/3.1 EGP/3.1.3 Portfolio de Projetos/1. Projeto Fazenda Fortaleza/",
                               "ACERVOS/Reunioes/Atas"]},
        "nidum_brasil": {"apelidos": ["brasil", "nidum brasil"], "siglas": ["BRA"],
                         "pastas": ["BRA/",
                                    "ACERVOS/Financas e Gestao de Projetos/3.1 EGP/3.1.3 Portfolio de Projetos/2. Projeto MVP Ipanema/",
                                    "ACERVOS/Reunioes/Atas"]},
        "produtos": {"apelidos": ["produtos"], "siglas": ["PROD"],
                     "pastas": ["ACERVOS/Produtos/"]},
        "marketing": {"apelidos": ["marketing"], "siglas": ["MKT"],
                      "pastas": ["MKT/", "ACERVOS/Reunioes/Atas"]},
        "nidum_mundo": {"apelidos": ["mundo", "nidum mundo"], "siglas": ["MUN"],
                        "pastas": ["MUN/", "ACERVOS/Produtos/Nidum Mundo/",
                                   "ACERVOS/Reunioes/Atas"]},
    },
}


# ------------------------------------------------------------------ construtores
def _cab(pasta, modificado=""):
    return ("<!-- origem: sharepoint:x | pasta: %s | modificado: %s | esteira v1 -->"
            % (pasta, modificado))


def _chunk(nome, score, pasta, modificado="", texto="conteudo do trecho"):
    return {"nome": nome, "score": score,
            "corpo": _cab(pasta, modificado) + "\n" + texto}


def _sources(chunks):
    # Formato que o pipe entrega a _selecionar_e_ordenar (uma src, listas paralelas).
    return [{
        "source": {"name": "Base institucional Nidum"},
        "document": [c["corpo"] for c in chunks],
        "metadata": [{"name": c["nome"], "score": c["score"]} for c in chunks],
        "distances": [c["score"] for c in chunks],
    }]


def _nomes(saida):
    return [o.get("nome") for o in (saida or [])]


def _idx(saida, nome):
    ns = _nomes(saida)
    return ns.index(nome) if nome in ns else 10**6


def _por_colecao(saida, col):
    return [o for o in (saida or []) if o.get("colecao") == col]


# ------------------------------------------------------------------ os 9 casos
# Cada caso: (id, descricao, funcao(C)->bool). A funcao so roda quando a Fase 3 existe.

def caso1(C):
    # Ancora FONTE nunca some: pool dominado por ACERVOS -> saida ainda tem >=1 FONTE, teto <=3.
    pool = [
        _chunk("ACERVOS > Reunioes > Atas > ACA_Convergencia_2026-07-20.md", 0.30,
               "3 - Acervos Institucionais/Reunioes/Atas"),
        _chunk("ACERVOS > Academia > ACA_Guia_Integracao.md", 0.20, "3 - Acervos Institucionais/Academia"),
        _chunk("FONTE > Documento Fundador v30.md", 0.90, "1 - Fonte"),
    ]
    out = C._selecionar_e_ordenar(_sources(pool), {"academia"}, MAPA, False)
    fontes = _por_colecao(out, "FONTE")
    return len(fontes) >= 1 and len(fontes) <= 3


def caso2(C):
    # Sem piorar / expandir-nunca-encolher: todo trecho de entrada esta na saida; a
    # ordem relativa ENTRE FONTES e preservada.
    pool = [
        _chunk("FONTE > Documento Fundador v30.md", 0.90, "1 - Fonte"),
        _chunk("FONTE > Empresas Vivas.md", 0.85, "1 - Fonte"),
        _chunk("ACERVOS > Reunioes > Atas > GER_Semanal_27-07-2026.md", 0.10,
               "3 - Acervos Institucionais/Reunioes/Atas"),
    ]
    out = C._selecionar_e_ordenar(_sources(pool), set(), MAPA, False)
    entrada = {c["nome"] for c in pool}
    saida = set(_nomes(out))
    nao_sumiu = entrada.issubset(saida)
    ordem_fonte_ok = _idx(out, "FONTE > Documento Fundador v30.md") < _idx(out, "FONTE > Empresas Vivas.md")
    return nao_sumiu and ordem_fonte_ok


def caso3(C):
    # Boost eixo-assunto (conserta D8): ACA_Convergencia (nota baixa) sobe acima das
    # convergencias de ecossistema ERRADO, para pergunta de Academia.
    pool = [
        _chunk("ACERVOS > Reunioes > Atas > ACA_Convergencia_2026-07-20.md", 0.0055,
               "3 - Acervos Institucionais/Reunioes/Atas"),
        _chunk("ACERVOS > Reunioes > Atas > FAN_Convergencia_2026-07-20.md", 0.10,
               "3 - Acervos Institucionais/Reunioes/Atas"),
        _chunk("ACERVOS > Reunioes > Atas > MKT_Convergencia_2026-07-20.md", 0.12,
               "3 - Acervos Institucionais/Reunioes/Atas"),
        _chunk("ACERVOS > Reunioes > Atas > MUN_Convergencia_2026-07-20.md", 0.11,
               "3 - Acervos Institucionais/Reunioes/Atas"),
    ]
    out = C._selecionar_e_ordenar(_sources(pool), {"academia"}, MAPA, False)
    aca = _idx(out, "ACERVOS > Reunioes > Atas > ACA_Convergencia_2026-07-20.md")
    return all(aca < _idx(out, n) for n in (
        "ACERVOS > Reunioes > Atas > FAN_Convergencia_2026-07-20.md",
        "ACERVOS > Reunioes > Atas > MKT_Convergencia_2026-07-20.md",
        "ACERVOS > Reunioes > Atas > MUN_Convergencia_2026-07-20.md",
    ))


def caso4(C):
    # Sinais SEPARADOS: convergencia com sigla ACA no nome, mas pasta: .../Atas.
    # tipo=ata (pela pasta/nome) E assunto=academia (pela SIGLA do nome, NAO pela pasta).
    nome = "ACERVOS > Academia > ACA_Convergencia_2026-07-20.md"
    corpo = _cab("3 - Acervos Institucionais/Reunioes/Atas", "2026-07-20") + "\nx"
    info = C._classificar_trecho(nome, corpo, MAPA)
    return info.get("tipo") == "ata" and "academia" in (info.get("assuntos") or set())


def caso5(C):
    # Boost eixo-TIPO (informativo cross-cutting): pergunta de Fazenda puxa o
    # ACA_Informativo, que mora em ACA e nao casa pasta/sigla FAN.
    pool = [
        _chunk("ACERVOS > Reunioes > Atas > FAN_Convergencia_2026-07-20.md", 0.10,
               "3 - Acervos Institucionais/Reunioes/Atas"),
        _chunk("ACERVOS > Academia > Informativos Executivos Nidum > ACA_Informativo_Executivo_2026-08-01.md",
               0.02, "3 - Acervos Institucionais/Academia/Informativos Executivos Nidum", "2026-08-01"),
    ]
    out = C._selecionar_e_ordenar(_sources(pool), {"fazenda"}, MAPA, False)
    return "ACERVOS > Academia > Informativos Executivos Nidum > ACA_Informativo_Executivo_2026-08-01.md" in _nomes(out)


def caso6(C):
    # Recencia POR-TIPO:
    #  (a) informativo novo acima do antigo;
    #  (b) registro v3 acima de v1;
    #  (c) FONTE ATEMPORAL: v31 (data mais nova) NAO vence v30 de maior score.
    info_novo = "ACERVOS > Academia > Informativos Executivos Nidum > ACA_Informativo_Executivo_2026-08-01.md"
    info_velho = "ACERVOS > Academia > Informativos Executivos Nidum > ACA_Informativo_Executivo_2026-07-01.md"
    reg_v3 = "ACERVOS > Financas e Gestao de Projetos/3.1 EGP/3.1.3 Portfolio de Projetos/1. Projeto Fazenda Fortaleza > FAN_Cronograma_31-07-2026_v3.md"
    reg_v1 = "ACERVOS > Financas e Gestao de Projetos/3.1 EGP/3.1.3 Portfolio de Projetos/1. Projeto Fazenda Fortaleza > FAN_Cronograma_21-07-2026_v1.md"
    egp = "3 - Acervos Institucionais/Financas e Gestao de Projetos/3.1 EGP/3.1.3 Portfolio de Projetos/1. Projeto Fazenda Fortaleza"
    fonte_v30 = "FONTE > Documento Fundador v30.md"
    fonte_v31 = "FONTE > Documento Fundador v31 rascunho.md"

    a = C._selecionar_e_ordenar(_sources([
        _chunk(info_velho, 0.02, "3 - Acervos Institucionais/Academia/Informativos Executivos Nidum", "2026-07-01"),
        _chunk(info_novo, 0.02, "3 - Acervos Institucionais/Academia/Informativos Executivos Nidum", "2026-08-01"),
    ]), {"academia"}, MAPA, False)
    ok_info = _idx(a, info_novo) < _idx(a, info_velho)

    b = C._selecionar_e_ordenar(_sources([
        _chunk(reg_v1, 0.05, egp, "2026-07-21"),
        _chunk(reg_v3, 0.05, egp, "2026-07-31"),
    ]), {"fazenda"}, MAPA, False)
    ok_reg = _idx(b, reg_v3) < _idx(b, reg_v1)

    # FONTE: v30 score maior; v31 data mais nova. Recencia NAO se aplica -> v30 fica acima.
    c = C._selecionar_e_ordenar(_sources([
        _chunk(fonte_v31, 0.80, "1 - Fonte", "2026-08-10"),
        _chunk(fonte_v30, 0.90, "1 - Fonte", "2026-05-01"),
    ]), set(), MAPA, True)
    ok_fonte = _idx(c, fonte_v30) < _idx(c, fonte_v31)

    return ok_info and ok_reg and ok_fonte


def caso7(C):
    # Diversidade 3-way (status/relacional): informativo + ata + registro do assunto,
    # todos presentes na saida para uma pergunta de Fazenda.
    ata = "ACERVOS > Reunioes > Atas > FAN_Convergencia_2026-07-20.md"
    reg = "ACERVOS > Financas e Gestao de Projetos/3.1 EGP/3.1.3 Portfolio de Projetos/1. Projeto Fazenda Fortaleza > FAN_Cronograma_31-07-2026_v3.md"
    info = "ACERVOS > Academia > Informativos Executivos Nidum > ACA_Informativo_Executivo_2026-08-01.md"
    egp = "3 - Acervos Institucionais/Financas e Gestao de Projetos/3.1 EGP/3.1.3 Portfolio de Projetos/1. Projeto Fazenda Fortaleza"
    out = C._selecionar_e_ordenar(_sources([
        _chunk(ata, 0.10, "3 - Acervos Institucionais/Reunioes/Atas", "2026-07-20"),
        _chunk(reg, 0.05, egp, "2026-07-31"),
        _chunk(info, 0.02, "3 - Acervos Institucionais/Academia/Informativos Executivos Nidum", "2026-08-01"),
    ]), {"fazenda"}, MAPA, False)
    tipos = {o.get("tipo") for o in out}
    return {"informativo", "ata", "registro"}.issubset(tipos)


def caso8(C):
    # Trava 5: pergunta CONCEITUAL nao promove operacional acima da FONTE.
    pool = [
        _chunk("ACERVOS > Reunioes > Atas > ACA_Convergencia_2026-07-20.md", 0.30,
               "3 - Acervos Institucionais/Reunioes/Atas"),
        _chunk("FONTE > Documento Fundador v30.md", 0.90, "1 - Fonte"),
    ]
    out = C._selecionar_e_ordenar(_sources(pool), {"academia"}, MAPA, True)
    # O topo tem de ser FONTE (nao promoveu ACERVOS).
    return bool(out) and out[0].get("colecao") == "FONTE"


def caso9(C):
    # Multi-assunto: MVP Ipanema pertence a nidum_brasil E produtos.
    nome = "ACERVOS > Produtos/Nidum Brasil > BRA_MVP_Ipanema_Etapa2.md"
    corpo = _cab("3 - Acervos Institucionais/Financas e Gestao de Projetos/3.1 EGP/3.1.3 Portfolio de Projetos/2. Projeto MVP Ipanema", "2026-08-01") + "\nx"
    info = C._classificar_trecho(nome, corpo, MAPA)
    ass = info.get("assuntos") or set()
    return "nidum_brasil" in ass and "produtos" in ass


CASOS = [
    ("1", "Ancora FONTE nunca some (teto <=3)", caso1),
    ("2", "Sem piorar / expandir-nunca-encolher; ordem entre FONTES preservada", caso2),
    ("3", "Boost eixo-assunto: ACA sobe acima de eco errado (conserta D8)", caso3),
    ("4", "Sinais separados: tipo=ata via pasta, assunto=academia via sigla do nome", caso4),
    ("5", "Boost eixo-tipo: informativo cross-cutting entra em pergunta de Fazenda", caso5),
    ("6", "Recencia por-tipo: informativo/registro sim; FONTE atemporal (v31 nao vence v30)", caso6),
    ("7", "Diversidade 3-way: informativo + ata + registro juntos", caso7),
    ("8", "Trava 5: pergunta conceitual mantem FONTE no topo", caso8),
    ("9", "Multi-assunto: MVP Ipanema -> nidum_brasil E produtos", caso9),
]

FUNCS_FASE3 = ("_classificar_trecho", "_assuntos_da_pergunta", "_selecionar_e_ordenar")


def main():
    faltando = [f for f in FUNCS_FASE3 if not hasattr(C, f)]
    if faltando:
        print("=" * 70)
        print("FASE 3 PENDENTE (VERMELHO) - funcoes ainda nao existem no chatnd.py:")
        print("   " + ", ".join(faltando))
        print("Contrato aguardando implementacao (9 casos):")
        for cid, desc, _ in CASOS:
            print("  [ ] caso %s: %s" % (cid, desc))
        print("=" * 70)
        print("Saida 0 DE PROPOSITO enquanto pendente (nao e regressao). Implemente a")
        print("Fase 3 e este arquivo passa a rodar as asseracoes de verdade.")
        return 0

    ok = True
    for cid, desc, fn in CASOS:
        try:
            r = bool(fn(C))
        except Exception as e:
            r = False
            print("  ERRO   caso %s: %s (%s: %s)" % (cid, desc, type(e).__name__, e))
            ok = False
            continue
        print(("  OK   " if r else "  FALHOU  ") + "caso %s: %s" % (cid, desc))
        ok = ok and r

    print("\n" + ("FASE 3: TODOS OS 9 CASOS PASSARAM" if ok else "FASE 3: HOUVE FALHA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
