# -*- coding: utf-8 -*-
"""
Banco de provas da VOZ - ENTRADA (1.54.0). Prova os requisitos DUROS do dono:
  - AUDIO vira TEXTO A MONTANTE: o pedido falado dispara a trava certa (pptx -> arquivo);
  - PRECEDENCIA: texto digitado vem antes do audio;
  - HONESTO: parcial rotula o que falhou; nenhum entendido -> recusa (nao chuta);
  - ACESSO: transcreve so audio do proprio usuario (ou admin);
  - CONTENT-FREE: o TEOR do audio nunca entra em log nem em registro (prova AST);
  - A|B INDEPENDENTE: a transcricao (A) nao toca analytics (B); o write de B esta fora
    do caminho de A (so no _registrar, no finally);
  - DEFENSIVO: detecta audio como file/id E como content-part (base64);
  - sem nome indefinido nas funcoes novas (o verificador de escopo).
USO: python teste_voz.py
"""
import ast
import asyncio
import os
import re
import sys
import types

import teste_estrutura as E

_DIR = os.path.dirname(os.path.abspath(__file__))
CAM = os.path.join(_DIR, "chatnd.py")


def check(nome, cond):
    print(("  OK   " if cond else "  FALHOU  ") + nome)
    return bool(cond)


def _fonte_funcao(fonte, nome):
    # Fonte de uma funcao/metodo pelo nome (desindentada se for metodo), via AST.
    arv = ast.parse(fonte)
    for no in ast.walk(arv):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            linhas = fonte.split("\n")[no.lineno - 1: no.end_lineno]
            # desindenta pelo recuo da primeira linha
            corte = len(linhas[0]) - len(linhas[0].lstrip())
            return "\n".join(l[corte:] if len(l) >= corte else l for l in linhas)
    return ""


def _log_falso():
    return types.SimpleNamespace(exception=lambda *a, **k: None,
                                 error=lambda *a, **k: None,
                                 warning=lambda *a, **k: None,
                                 info=lambda *a, **k: None)


def carregar():
    fonte = open(CAM, encoding="utf-8").read()
    ns = {"re": re, "unicodedata": __import__("unicodedata"), "os": os,
          "asyncio": asyncio, "log": _log_falso()}
    for nome in ("_eh_imagem", "_eh_audio", "_audios_recentes", "_audio_em_partes",
                 "_faixa_audio", "_combinar_voz", "_normalizar_ascii", "_pede_arquivo"):
        m = re.search(r"^def " + nome + r"\(.*?(?=^\S)", fonte, re.M | re.S)
        exec(m.group(0), ns)
    for const in (r"_EXT_AUDIO = \(.*?\)", r"_VERBO_PRODUZIR = \(.*?^\)",
                  r"_SUBST_ARQUIVO = \(.*?^\)", r"_RE_PEDE_ARQUIVO = re\.compile\(.*?^\)"):
        m = re.search(r"^" + const, fonte, re.M | re.S)
        exec(m.group(0), ns)
    return ns, fonte


def files_de(*specs):
    # specs: (nome, mime) -> item como o OWUI entrega em __files__.
    saida = []
    for i, (nome, mime) in enumerate(specs):
        arq = {"data": {"content": ""}, "meta": ({"content_type": mime} if mime else {})}
        saida.append({"type": "file", "id": "f%d" % i, "name": nome, "file": arq})
    return saida


# ----------------------------------------------------------- fakes do open_webui (offline)
def _instalar_fake_openwebui(transcricoes):
    # transcricoes: dict caminho -> texto (ou "" para 'nao entendi').
    mod_ow = types.ModuleType("open_webui")
    mod_r = types.ModuleType("open_webui.routers")
    mod_a = types.ModuleType("open_webui.routers.audio")

    async def transcription_handler(request, caminho, metadata, user):
        return {"text": transcricoes.get(caminho, "")}

    mod_a.transcription_handler = transcription_handler
    sys.modules["open_webui"] = mod_ow
    sys.modules["open_webui.routers"] = mod_r
    sys.modules["open_webui.routers.audio"] = mod_a


def _self_com_caminhos(mapa_id_caminho):
    # self falso com _caminho_audio_storage async (mapeia id -> caminho; "" = inacessivel).
    async def _caminho(self, fid, user):
        return mapa_id_caminho.get(fid, "")
    S = types.SimpleNamespace()
    S._caminho_audio_storage = types.MethodType(_caminho, S)
    return S


def _carregar_metodo(fonte, nome, ns_extra=None):
    ns = {"os": os, "asyncio": asyncio, "log": _log_falso()}
    if ns_extra:
        ns.update(ns_extra)
    exec(_fonte_funcao(fonte, nome), ns)
    return ns[nome]


def run(coro):
    return asyncio.run(coro)


def main():
    ns, fonte = carregar()
    ok = True
    EH = ns["_eh_audio"]
    AUD = ns["_audios_recentes"]
    PARTES = ns["_audio_em_partes"]
    FAIXA = ns["_faixa_audio"]
    COMB = ns["_combinar_voz"]

    print("== deteccao: por mime, por extensao, e NAO confunde doc/imagem ==")
    ok &= check("mime audio/* -> audio", EH({"meta": {"content_type": "audio/mpeg"}}, "x"))
    ok &= check("extensao .wav sem mime -> audio", EH({}, "recado.WAV"))
    ok &= check(".ogg (whatsapp) -> audio", EH({}, "PTT-2026.ogg"))
    ok &= check("docx NAO e audio", EH({}, "contrato.docx") is False)
    ok &= check("png NAO e audio", EH({"meta": {"content_type": "image/png"}}, "a.png") is False)

    print("== _audios_recentes coleta so audio (o que _anexos_recentes descarta) ==")
    fs = files_de(("relatorio.pdf", None), ("recado.mp3", "audio/mpeg"), ("nota.ogg", None))
    got = AUD(fs)
    ok &= check("2 audios detectados (pdf fora)", [a["nome"] for a in got] == ["recado.mp3", "nota.ogg"])
    ok &= check("guarda o id (chave do Storage)", got[0]["id"] == "f1" and got[1]["id"] == "f2")
    ok &= check("sem files -> lista vazia (no-regression)", AUD([]) == [])
    ok &= check("so docs -> lista vazia (no-regression)",
                AUD(files_de(("a.pdf", None), ("b.docx", None))) == [])

    print("== deteccao DEFENSIVA do content-part (base64, sem id) ==")
    ok &= check("parte type 'audio' -> detecta",
                PARTES([{"role": "user", "content": [{"type": "audio", "data": "AAAA"}]}]))
    ok &= check("parte mimeType audio/* -> detecta",
                PARTES([{"role": "user",
                         "content": [{"type": "x", "mimeType": "audio/ogg"}]}]))
    ok &= check("input_audio (openai) -> detecta",
                PARTES([{"role": "user", "content": [{"type": "input_audio"}]}]))
    ok &= check("texto puro -> NAO detecta", PARTES([{"role": "user", "content": "ola"}]) is False)
    ok &= check("imagem em parte -> NAO conta como audio",
                PARTES([{"role": "user", "content": [{"type": "image_url"}]}]) is False)

    print("== faixa de TAMANHO (proxy de carga, content-free) ==")
    ok &= check("<1MB", FAIXA(500 * 1024) == "<1MB")
    ok &= check("1-5MB", FAIXA(3 * 1024 * 1024) == "1-5MB")
    ok &= check(">5MB", FAIXA(9 * 1024 * 1024) == ">5MB")
    ok &= check("zero/None -> None (nada a registrar)", FAIXA(0) is None and FAIXA(None) is None)

    print("== PRECEDENCIA: texto digitado vem ANTES do audio ==")
    comb = COMB("use tom formal", "[Audio 1]\nfaca um resumo")
    ok &= check("digitado primeiro", comb.startswith("use tom formal"))
    ok &= check("audio depois", comb.endswith("[Audio 1]\nfaca um resumo"))
    ok &= check("so audio quando nao ha digitado", COMB("", "[Audio 1]\noi") == "[Audio 1]\noi")
    ok &= check("so audio quando digitado e so espaco", COMB("   ", "[Audio 1]\noi") == "[Audio 1]\noi")

    print("== ROTEAMENTO: 'gere um pptx' FALADO dispara a trava de arquivo ==")
    PEDE = ns["_pede_arquivo"]
    falado = COMB("", "[Audio 1]\ngere um pptx sobre o balanco de vendas")
    ok &= check("pedido falado de pptx -> trava arquivo dispara", PEDE(falado) is True)
    ok &= check("audio de conversa comum NAO dispara arquivo",
                PEDE(COMB("", "[Audio 1]\noi tudo bem por ai")) is False)

    print("== _transcrever_audios: rotula, trata PARCIAL, e da o desfecho certo ==")
    _instalar_fake_openwebui({"/p1": "primeiro audio ok", "/p2": ""})  # p2 vazio = nao entendi
    self_ok = _self_com_caminhos({"a1": "/p1", "a2": "/p2", "a3": ""})  # a3 inacessivel
    TRANS = _carregar_metodo(fonte, "_transcrever_audios", {"_faixa_audio": FAIXA})
    bloco, resumo = run(
        TRANS(self_ok, object(), object(),
              [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}]))
    ok &= check("estado 'parcial' (1 de 3)", resumo["estado"] == "parcial" and resumo["ok"] == 1)
    ok &= check("[Audio 1] traz a transcricao", "[Audio 1]\nprimeiro audio ok" in bloco)
    ok &= check("[Audio 2] marcado 'nao entendi'", "[Audio 2: nao entendi]" in bloco)
    ok &= check("[Audio 3] marcado 'nao consegui acessar'", "[Audio 3: nao consegui acessar]" in bloco)

    _instalar_fake_openwebui({"/x": "tudo certo"})
    self_all = _self_com_caminhos({"a1": "/x", "a2": "/x"})
    b2, r2 = run(
        TRANS(self_all, object(), object(), [{"id": "a1"}, {"id": "a2"}]))
    ok &= check("todos ok -> estado 'ok'", r2["estado"] == "ok" and r2["ok"] == 2)

    _instalar_fake_openwebui({})  # nada transcreve
    self_none = _self_com_caminhos({"a1": ""})
    b3, r3 = run(
        TRANS(self_none, object(), object(), [{"id": "a1"}]))
    ok &= check("nenhum ok -> estado 'falhou'", r3["estado"] == "falhou" and r3["ok"] == 0)

    print("== ACESSO: transcreve so audio do dono (ou admin) ==")
    # fakes de Files/Storage
    mod_ow = sys.modules["open_webui"]
    mod_f = types.ModuleType("open_webui.models.files")
    mod_mods = types.ModuleType("open_webui.models")
    mod_sp = types.ModuleType("open_webui.storage.provider")
    mod_st = types.ModuleType("open_webui.storage")

    class _FO:
        def __init__(self, uid):
            self.user_id = uid
            self.path = "/audio/x.mp3"

    class _Files:
        @staticmethod
        async def get_file_by_id(fid):
            return _FO("dono-123")
    mod_f.Files = _Files
    mod_sp.Storage = types.SimpleNamespace(get_file=lambda p: p)
    sys.modules["open_webui.models"] = mod_mods
    sys.modules["open_webui.models.files"] = mod_f
    sys.modules["open_webui.storage"] = mod_st
    sys.modules["open_webui.storage.provider"] = mod_sp

    CAM_AUD = _carregar_metodo(fonte, "_caminho_audio_storage")
    dono = types.SimpleNamespace(id="dono-123", role="user")
    outro = types.SimpleNamespace(id="intruso-9", role="user")
    admin = types.SimpleNamespace(id="adm-1", role="admin")
    ok &= check("dono acessa o proprio audio", run(CAM_AUD(object(), "fid", dono)) == "/audio/x.mp3")
    ok &= check("outro usuario -> barrado (\"\")", run(CAM_AUD(object(), "fid", outro)) == "")
    ok &= check("admin acessa (gate de suporte)", run(CAM_AUD(object(), "fid", admin)) == "/audio/x.mp3")
    ok &= check("id vazio -> \"\" sem tocar o banco", run(CAM_AUD(object(), "", dono)) == "")

    print("== CONTENT-FREE (prova AST): o TEOR nunca vai a log ==")
    ok &= check("nenhum log em _transcrever_audios recebe a var do teor",
                _log_sem_teor(fonte, "_transcrever_audios", {"texto"}))
    ok &= check("nenhum log no _pipe_impl recebe a transcricao",
                _log_sem_teor(fonte, "_pipe_impl", {"_bloco", "_combinado", "_digitado"}))
    fpi = _fonte_funcao(fonte, "_pipe_impl")
    ok &= check("_ev['audio'] vem do RESUMO (estado), nao do teor",
                '_ev["audio"] = _res.get("estado")' in fpi)
    ok &= check("_ev['audio_faixa'] vem da FAIXA, nao do teor",
                '_ev["audio_faixa"] = _res.get("faixa")' in fpi)

    print("== A|B INDEPENDENTE (estrutural): A nao depende de B ==")
    fta = _fonte_funcao(fonte, "_transcrever_audios")
    # AST (nao substring): o codigo de A nao pode USAR _ev/_registrar/_analytics_* - so os
    # COMENTARIOS os citam (para explicar a separacao), e comentario nao entra na arvore.
    usados_a = _nomes_usados(fonte, "_transcrever_audios")
    ok &= check("_transcrever_audios NAO referencia analytics (AST, nao comentario)",
                not (usados_a & {"_ev", "_registrar", "_analytics_write",
                                 "_analytics_agregar", "_analytics_faixa"}))
    ok &= check("_analytics_write NAO e chamado dentro de _pipe_impl (write so no finally)",
                "_analytics_write(" not in fpi)
    ok &= check("_registrar NAO e chamado dentro de _pipe_impl (e o wrapper no finally)",
                "self._registrar(" not in fpi)
    # a injecao (A) acontece ANTES do despacho /analytics e do roteador
    ok &= check("transcricao roteada A MONTANTE (antes do /analytics)",
                fonte.index("_transcrever_audios(") < fonte.index("_analytics_parse(_ultimo_texto"))

    print("== HONESTO: recusa quando nada transcreve; nao chuta ==")
    ok &= check("recusa honesta presente",
                "Nao consegui entender o audio" in fpi)
    ok &= check("recusa marca desfecho/recusa_cat (registro content-free)",
                'recusa_cat"] = "audio_ininteligivel"' in fpi)
    ok &= check("audio > 20MB avisa em vez de estourar", "muito longo para transcrever" in fta)
    ok &= check("gate de acesso no _caminho_audio_storage",
                'role", "") == "admin"' in _fonte_funcao(fonte, "_caminho_audio_storage")
                and "dono == getattr(user" in _fonte_funcao(fonte, "_caminho_audio_storage"))

    print("== escopo: sem nome indefinido nas funcoes novas ==")
    for fn in ("_eh_audio", "_audios_recentes", "_audio_em_partes", "_faixa_audio",
               "_combinar_voz", "_transcrever_audios", "_caminho_audio_storage"):
        u = E.nomes_indefinidos(fonte, fn)
        ok &= check("%s: sem nome indefinido" % fn, not u)

    print("\nRESULTADO: " + ("VOZ ENTRADA OK" if ok else "HOUVE FALHA"))
    sys.exit(0 if ok else 1)


def _nomes_usados(fonte, nome_funcao):
    # Conjunto dos nomes (ast.Name) e atributos de metodo (self.X) USADOS no CODIGO da
    # funcao - comentarios/docstrings NAO entram (nao viram Name na arvore).
    arv = ast.parse(fonte)
    alvo = None
    for no in ast.walk(arv):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome_funcao:
            alvo = no
            break
    nomes = set()
    if alvo is None:
        return nomes
    for no in ast.walk(alvo):
        if isinstance(no, ast.Name):
            nomes.add(no.id)
        elif isinstance(no, ast.Attribute):
            nomes.add(no.attr)
    return nomes


def _log_sem_teor(fonte, nome_funcao, proibidos):
    # True se NENHUMA chamada log.* dentro da funcao recebe um dos nomes 'proibidos'
    # (as variaveis que carregam o TEOR). Prova estrutural de content-free.
    arv = ast.parse(fonte)
    alvo = None
    for no in ast.walk(arv):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome_funcao:
            alvo = no
            break
    if alvo is None:
        return False
    for no in ast.walk(alvo):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute):
            base = no.func.value
            if isinstance(base, ast.Name) and base.id == "log":
                for arg in list(no.args) + [k.value for k in no.keywords]:
                    for nn in ast.walk(arg):
                        if isinstance(nn, ast.Name) and nn.id in proibidos:
                            return False
    return True


if __name__ == "__main__":
    main()
