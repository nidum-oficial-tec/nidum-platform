# -*- coding: utf-8 -*-
"""
Banco de provas da ROTA DE IMAGEM do chatnd (1.49.0).

Cobre os dois pontos que ja falharam em producao:
  1. HEX no prompt - o modelo de imagem DESENHA o codigo em vez de usar a cor (visto no
     cartaz de cavaquinho: "#4F71E87", sete digitos, contra os seis do #4F7187 real; ele
     nem copiou direito, tratou como forma a desenhar). Nao basta tirar uma vez: tem que
     ficar impossivel reintroduzir.
  2. SENTINELA SEM_IMAGEM - a guarda de chatnd.py ja foi codigo morto uma vez sem
     ninguem notar. Se a instrucao sair do prompt, o modelo volta a INVENTAR descricao
     em vez de dizer o que falta.
USO: python teste_imagem_prompt.py
"""

import os
import re
import sys

import teste_estrutura as E

_DIR = os.path.dirname(os.path.abspath(__file__))
CAM = os.path.join(_DIR, "chatnd.py")

FUNCOES = ("_imagens_recentes", "_tem_anexo_imagem", "_extrair_imagens_anexo")


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def carregar():
    fonte = open(CAM, encoding="utf-8").read()
    ns = {"re": re}
    for nome in FUNCOES:
        m = re.search(r"^def " + nome + r"\(.*?(?=^\S)", fonte, re.M | re.S)
        exec(m.group(0), ns)
    m = re.search(r"^IMAGEM_PROMPT = \(.*?^\)", fonte, re.M | re.S)
    exec(m.group(0), ns)
    return ns, fonte


def msg_texto(t):
    return {"role": "user", "content": t}


def msg_com_imagem(t, url="data:image/png;base64,AAAA"):
    return {"role": "user", "content": [
        {"type": "text", "text": t},
        {"type": "image_url", "image_url": {"url": url}},
    ]}


def main():
    ns, fonte = carregar()
    P = ns["IMAGEM_PROMPT"]
    IMGS = ns["_imagens_recentes"]
    ok = True

    print("== HEX: nenhum #RRGGBB pode chegar ao prompt ==")
    achados = re.findall(r"#[0-9A-Fa-f]{6}", P)
    ok &= check("zero codigos hex no IMAGEM_PROMPT (achados: %s)" % (achados or "nenhum"),
                not achados)
    ok &= check("nem hex de 3 digitos", not re.findall(r"#[0-9A-Fa-f]{3}\b", P))
    ok &= check("a REGRA de cor por nome esta escrita",
                "nunca por codigo hexadecimal" in P)
    ok &= check("explica POR QUE (o modelo desenha o codigo)",
                "desenha o" in P and "codigo como texto" in P)

    print("== a paleta da marca sobreviveu, em palavras ==")
    for cor in ("areia clara", "verde musgo acinzentado", "terracota",
                "azul acinzentado suave", "cinza quente", "quase preto quente"):
        ok &= check("paleta cita %r" % cor, cor in P)
    ok &= check("paleta so quando o usuario pedir a marca",
                "identidade visual da Nidum" in P)

    print("== SENTINELA SEM_IMAGEM (a guarda ja foi codigo morto uma vez) ==")
    ok &= check("instrucao presente no prompt", "SEM_IMAGEM:" in P)
    ok &= check("manda NAO inventar", "NAO invente uma descricao" in P)
    # O contrato com o codigo: chatnd faz refinada.startswith("SEM_IMAGEM:")
    ok &= check("o codigo ainda checa a MESMA string",
                'startswith("SEM_IMAGEM:")' in fonte)
    marcador = re.search(r"^SEM_IMAGEM:", P, re.M)
    ok &= check("o prompt mostra o marcador no INICIO da linha (casa com startswith)",
                bool(marcador))
    # simula a saida do modelo passando pela guarda real
    for saida, esperado in (
        ("SEM_IMAGEM: falta a imagem de referencia", "falta a imagem de referencia"),
        ("  SEM_IMAGEM: pedido vago  ", "pedido vago"),
        ("SEM_IMAGEM: <falta o anexo>", "falta o anexo"),
    ):
        ref = saida.strip()
        bateu = ref.startswith("SEM_IMAGEM:")
        resto = ref[len("SEM_IMAGEM:"):].strip().strip("<>").strip()
        ok &= check("guarda pega %r -> %r" % (saida[:28], resto),
                    bateu and resto == esperado)
    ok &= check("descricao normal NAO aciona a guarda",
                not "um ninho de passaros ao amanhecer".startswith("SEM_IMAGEM:"))

    print("== o prompt nao carrega mais as duas regras que causavam perda ==")
    ok &= check("nao limita a 'uma unica frase'", "unica frase" not in P)
    ok &= check("nao proibe aspas (era o que impedia transcrever texto)",
                "NAO use aspas" not in P)
    ok &= check("texto virou ELEMENTO VISUAL, entre aspas",
                "textos" in P and "transcritos entre aspas" in P)
    ok &= check("comprimento e PROPORCIONAL ao conteudo",
                "proporcional ao conteudo" in P)

    print("== marcas: a proibicao foi REMOVIDA por decisao do dono ==")
    # INVERTIDO DE PROPOSITO. A clausula existia e foi tirada porque atrapalhava o uso
    # mais legitimo: redesenhar material da propria casa (o caso real trazia o logo da
    # Nidum e a regra mandava apaga-lo). Este teste existe para ela nao VOLTAR sem
    # decisao explicita - quem ler o codigo daqui a meses pode achar que foi descuido.
    ok &= check("o prompt NAO proibe reproduzir marcas/logos",
                "NAO reproduza marcas" not in P)
    ok &= check("nao entrou regra nova de marca no lugar",
                "logotipo" not in P.lower() and "emblema" not in P.lower())
    ok &= check("quem governa e 'preserve o restante' (marca sobrevive por padrao)",
                "preserve o restante" in P)

    print("== ASCII (regra do repo) ==")
    ok &= check("IMAGEM_PROMPT e 100% ASCII",
                not [c for c in P if ord(c) > 127])

    print("== PERSISTENCIA do anexo na rota de imagem ==")
    # o bug: anexo num turno, pedido no seguinte -> "Anexe o material original"
    conversa = [
        msg_com_imagem("olha essa arte"),
        {"role": "assistant", "content": "recebi"},
        msg_texto("agora deixa o fundo mais claro"),
    ]
    tem, urls = IMGS(conversa, 5)
    ok &= check("acha o anexo de UM turno atras (o bug real)", tem and len(urls) == 1)

    tem, urls = IMGS([msg_com_imagem("essa aqui")], 5)
    ok &= check("acha na propria mensagem (comportamento antigo preservado)", tem)

    ok &= check("sem anexo nenhum -> (False, [])", IMGS([msg_texto("gere um ninho")], 5) == (False, []))
    ok &= check("conversa vazia nao quebra", IMGS([], 5) == (False, []))
    ok &= check("None nao quebra", IMGS(None, 5) == (False, []))

    # a MAIS RECENTE vence
    duas = [msg_com_imagem("antiga", "data:image/png;base64,OLD"),
            {"role": "assistant", "content": "ok"},
            msg_com_imagem("nova", "data:image/png;base64,NEW")]
    tem, urls = IMGS(duas, 5)
    ok &= check("com duas, vence a MAIS RECENTE", tem and urls == ["data:image/png;base64,NEW"])

    # janela: alem de n mensagens do usuario, para de olhar
    longe = [msg_com_imagem("muito antiga")] + [msg_texto("t%d" % i) for i in range(6)]
    ok &= check("fora da janela de 5 -> nao pega (limite consciente)",
                IMGS(longe, 5) == (False, []))
    ok &= check("dentro de uma janela maior, pega", IMGS(longe, 9)[0] is True)

    print("== fiacao ==")
    ok &= check("a rota de imagem usa a busca em N mensagens",
                E.chamada_com(fonte, "_imagens_recentes", "_msgs"))
    ok &= check("nao usa mais so a ultima mensagem para o anexo de imagem",
                not E.chamada_com(fonte, "_tem_anexo_imagem", "_msg_user"))
    ok &= check("loga quando ha referencia",
                "rota imagem COM referencia" in E.textos(fonte, "pipe"))

    print("\nRESULTADO: " + ("ROTA DE IMAGEM OK" if ok else "HOUVE FALHA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
