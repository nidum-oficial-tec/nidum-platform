#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cria o wrapper do 5o motor do ChatND: "NIDUM 1.0 - Identificador de Ambientes"
(visao) via POST /api/v1/models/create (regra 5: wrapper e criado pela API, nunca
renomeando um base). Acopla a tool gerador_de_arquivos_nidum no mesmo payload.

Base do motor: claude-opus-4-8 (decisao 2026-07-14). Prefixo dos relatorios: PLAT_.

SO por variavel de ambiente:
  ADMIN_TOKEN         token de admin do Open WebUI
  OPENWEBUI_BASE_URL  ex.: https://chatnd.nidumbrasil.com.br  (ou --base-url)

Uso (PowerShell):
  $env:ADMIN_TOKEN="COLE_O_TOKEN"
  py _nidum_manutencao/criar_wrapper_ambientes.py --base-url https://chatnd.nidumbrasil.com.br
  # adicione --dry-run para so imprimir o payload, sem criar.
"""
import argparse
import json
import os
import urllib.error
import urllib.request

WRAPPER_ID = "nidum-identificador-ambientes"
BASE_MODEL = "claude-opus-4-8"
TOOL_ID = "gerador_de_arquivos_nidum"

SYSTEM_PROMPT = (
    "Voce e o motor Identificador de Ambientes do ChatND, assistente da Nidum para\n"
    "analise visual de ambientes, materiais e patologias construtivas.\n"
    "\n"
    "ROTEIRO DE ANALISE (siga sempre, nesta ordem):\n"
    "1. Elemento analisado (o que aparece na imagem).\n"
    "2. Material provavel e tipo, citando as evidencias visiveis que sustentam a\n"
    "   hipotese (padrao de veios/cristais, textura, brilho, acabamento, juntas).\n"
    "3. Estado de conservacao e avarias: rachaduras, desgastes, manchas,\n"
    "   infiltracoes - cada uma com localizacao aproximada e severidade estimada.\n"
    "4. Grau de confianca (0-100%) com justificativa, seguindo a rubrica:\n"
    "   - acima de 85%: multiplas evidencias convergentes e boa qualidade de imagem;\n"
    "   - 60-85%: hipotese forte, mas falta angulo, close ou informacao de contexto;\n"
    "   - abaixo de 60%: imagem insuficiente - NAO crave diagnostico; peca material\n"
    "     adicional antes.\n"
    "5. O que reduziria a incerteza (angulos, close de textura, luz natural,\n"
    "   objeto de referencia de tamanho na cena, idade e uso do ambiente).\n"
    "\n"
    "REGRAS DE HONESTIDADE (inviolaveis):\n"
    "- Se uma caracteristica nao for visivel na imagem, declare explicitamente\n"
    "  \"nao e possivel determinar pela foto\". Nunca invente medidas, marcas,\n"
    "  espessuras ou laudos.\n"
    "- Nunca apresente estimativa como certeza. O grau de confianca acompanha\n"
    "  todo diagnostico.\n"
    "- Analise visual assistida por IA orienta, mas nao substitui vistoria\n"
    "  tecnica presencial em decisoes estruturais, juridicas ou de alto valor.\n"
    "  Inclua esta ressalva em todo relatorio final.\n"
    "\n"
    "RELATORIO:\n"
    "Quando o usuario pedir o relatorio, use SEMPRE a ferramenta\n"
    "gerador_de_arquivos_nidum para gerar um PDF (ou DOCX se pedido) com os blocos:\n"
    "Identificacao / Material analisado / Diagnostico / Avarias e estado /\n"
    "Grau de confianca / Ajustes da conversa / Ressalva.\n"
    "Nome do arquivo: PLAT_Relatorio_<Elemento>_<DDMMAAAA>_V<n>.\n"
    "Nao escreva codigo Python. Nao use Code Interpreter.\n"
    "Antes de salvar no SharePoint (ferramenta sharepoint_nidum), confirme com o\n"
    "usuario: \"Posso salvar o relatorio <nome> no SharePoint?\". So salve apos um\n"
    "sim explicito.\n"
)

PAYLOAD = {
    "id": WRAPPER_ID,
    "name": "NIDUM 1.0 - Identificador de Ambientes",
    "base_model_id": BASE_MODEL,
    "meta": {
        "description": "Analisa fotos de ambientes e materiais, aponta avarias e gera relatorio com grau de confianca.",
        "capabilities": {"vision": True, "citations": False, "usage": False},
        "toolIds": [TOOL_ID],
    },
    "params": {"system": SYSTEM_PROMPT},
    "access_control": None,
    "is_active": True,
}


def _req(base, path, token, method="GET", body=None):
    url = base.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("OPENWEBUI_BASE_URL"))
    ap.add_argument("--dry-run", action="store_true", help="so imprime o payload; nao cria")
    args = ap.parse_args()
    base = args.base_url
    if not base:
        raise SystemExit("Faltou --base-url (ou env OPENWEBUI_BASE_URL).")

    print("== Wrapper a criar ==")
    print("  id        :", WRAPPER_ID)
    print("  base_model:", BASE_MODEL)
    print("  tool      :", TOOL_ID)
    print("  vision    : True")
    if args.dry_run:
        print("\n[DRY-RUN] payload:\n" + json.dumps(PAYLOAD, ensure_ascii=False, indent=2))
        return

    token = os.environ.get("ADMIN_TOKEN")
    if not token:
        raise SystemExit("Faltou a variavel de ambiente ADMIN_TOKEN.")

    # Ja existe? (evita erro cego e nao sobrescreve sem querer)
    s, _ = _req(base, "/api/v1/models/model?id=" + WRAPPER_ID, token)
    if s == 200:
        raise SystemExit(
            "O modelo '%s' JA EXISTE. Para ajustar, use /api/v1/models/model/update "
            "(ou edite na UI) - nao recrio para nao sobrescrever cego." % WRAPPER_ID)

    status, raw = _req(base, "/api/v1/models/create", token, method="POST", body=PAYLOAD)
    print("\nPOST /api/v1/models/create -> HTTP", status)
    if status in (200, 201):
        print("OK: wrapper criado.")
        print("Lembrete (regra 4): REPUBLIQUE o pipe ChatND depois de mexer em tools/modelos.")
    else:
        print("Resposta:", raw[:400])
        print("\nSe deu 401/403: token nao e admin. Se 400/409: id ja existe ou payload invalido.")


if __name__ == "__main__":
    main()
