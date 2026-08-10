"""
title: POC Audio Render
author: Nidum
version: 0.4.0
description: POC descartavel isolado do ChatND. Testa se audio vira PLAYER no chat e sobrevive ao reload no OWUI 0.9.6. Nao chama TTS, nao toca o pipe medido. Apagar depois de decidir.
"""
# POC ISOLADO da frente "saida de voz". NAO e o ChatND e NAO toca o pipe medido (2a de
# token): e uma Function separada, um MODELO proprio. Instalar/usar este POC nao altera
# nada do ChatND - por isso pode ser testado JA.
#
# Pergunta unica (Q5, empirica): um audio anexado vira PLAYER reproduzivel no chat, e
# SOBREVIVE ao reload? (o bug #24714/#27017 derruba decoracao de outlet -> vamos por
# anexo PERSISTIDO via Files/Storage, nao decoracao.)
#
# Nao chama TTS: gera um WAV de teste em PURO PYTHON (tom 0.3s), so para exercitar o
# RENDER. O formato final (mp3 Azure) NAO muda a pergunta - e a tag <audio>/o anexo que
# tem de renderizar e persistir. ASCII puro (regra do repo).
import asyncio
import inspect
import io
import logging
import math
import struct
import uuid

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


def _wav_teste():
    # WAV minimo (RIFF + PCM 16-bit): tom 440Hz, 0.3s, 8kHz mono. ~5KB, sem dependencia.
    sr, dur = 8000, 0.3
    n = int(sr * dur)
    corpo = bytearray()
    for i in range(n):
        corpo += struct.pack("<h", int(9000 * math.sin(2 * math.pi * 440 * i / sr)))
    data = bytes(corpo)
    cab = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    cab += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16)
    cab += b"data" + struct.pack("<I", len(data))
    return cab + data


async def _salvar(data_bytes, filename, content_type, user_id):
    # MESMO padrao triplo-fallback provado da tool gerador (Storage.upload_file +
    # Files.insert_new_file), para o link nativo /api/v1/files/{id}/content.
    from open_webui.storage.provider import Storage
    from open_webui.models.files import Files, FileForm

    file_id = str(uuid.uuid4())
    stored = file_id + "_" + filename

    def _upload():
        ultimo = None
        for tentar in (
            lambda: Storage.upload_file(io.BytesIO(data_bytes), stored, {}),
            lambda: Storage.upload_file(data_bytes, stored, {}),
            lambda: Storage.upload_file(data_bytes, stored),
        ):
            try:
                return tentar()
            except Exception as e:
                ultimo = e
        raise RuntimeError("upload falhou: " + str(ultimo))

    result = await asyncio.to_thread(_upload)
    path = result[1] if isinstance(result, tuple) and len(result) >= 2 else result
    if not path:
        raise RuntimeError("Storage devolveu caminho vazio")
    meta = {"name": filename, "content_type": content_type, "size": len(data_bytes)}
    form = FileForm(id=file_id, filename=filename, path=path, meta=meta, data={})
    inserted = Files.insert_new_file(user_id, form)
    if inspect.isawaitable(inserted):
        inserted = await inserted
    if inserted is None:
        raise RuntimeError("insert_new_file devolveu None")
    return file_id


def _uid(u):
    if isinstance(u, dict):
        return u.get("id") or u.get("user_id") or ""
    return getattr(u, "id", "") or ""


class Pipe:
    class Valves(BaseModel):
        ATIVO: bool = Field(default=True, description="POC de render ligado.")

    def __init__(self):
        self.valves = self.Valves()

    async def pipe(self, body, __user__=None, __request__=None, **kwargs):
        # Salva o WAV de teste e devolve os metodos de render LADO A LADO, rotulados.
        # String de retorno (como as rotas arquivo/imagem do ChatND) - o conteudo
        # persistido e o que o reload re-renderiza, entao render+reload se testa assim.
        try:
            fid = await _salvar(_wav_teste(), "poc_audio.wav", "audio/wav", _uid(__user__))
        except Exception as e:
            log.exception("POC audio: falha ao salvar o arquivo de teste")
            return ("## POC de render de audio\n\nNao consegui salvar o arquivo de teste "
                    "no Storage: " + str(e) + "\n\n(Isso ja e um dado: o Storage/Files nao "
                    "respondeu como esperado. Me avise que investigo por ai.)")
        url = "/api/v1/files/" + fid + "/content"
        # FORMATO CORRETO (provado no marked@9 + HTMLToken.svelte do 0.9.6): o front so
        # monta o player quando <audio>...</audio> esta num UNICO token HTML de bloco, e
        # le a URL do CONTEUDO INTERNO da tag (nao do src=). 'audio' nao e tag de bloco
        # do CommonMark, entao precisa vir EMBRULHADO num <div> (que E bloco) - senao o
        # marked quebra em tokens inline separados e o player nao aparece. A linha em
        # branco em volta (join por \\n\\n) isola o bloco.
        player = "<div><audio>" + url + "</audio></div>"
        return "\n\n".join([
            "## POC de render de audio (OWUI 0.9.6) - v0.4",
            "Formato provado: `<audio>` com a URL como CONTEUDO, embrulhado em `<div>` "
            "(um so bloco HTML). Toque; depois recarregue (F5) e olhe de novo.",
            "**Player nativo:**",
            player,
            "**Link de download (piso, requisito 3):**",
            "[Baixar/ouvir o audio de teste](" + url + ")",
            "---",
            "**Reporte:** (1) apareceu um PLAYER tocavel agora? (2) depois do F5, "
            "continuou aparecendo? So isso decide o metodo da fatia real.",
        ])
