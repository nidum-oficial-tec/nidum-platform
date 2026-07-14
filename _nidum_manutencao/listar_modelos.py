#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lista os modelos do Open WebUI (id, nome, base_model_id, capacidade de visao),
para escolher o BASE_MODEL_VISION do novo motor (regra 7: confirmar via API,
nunca chutar). SO LEITURA - nao cria nem altera nada.

Credenciais SO por variavel de ambiente:
  ADMIN_TOKEN       token de admin do Open WebUI (Bearer)
  OPENWEBUI_BASE_URL  ex.: https://chatnd.nidumbrasil.com.br  (ou passe --base-url)

Uso (PowerShell):
  $env:ADMIN_TOKEN="COLE_O_TOKEN"
  py _nidum_manutencao/listar_modelos.py --base-url https://chatnd.nidumbrasil.com.br
"""
import argparse
import json
import os
import urllib.error
import urllib.request


def _fetch(base, path, token):
    # Devolve (status, texto_cru). Nao explode; deixa o chamador decidir.
    url = base.rstrip("/") + path
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), url


def get(base, token):
    # Tenta os endpoints conhecidos do Open WebUI e devolve a lista de modelos.
    for path in ("/api/v1/models", "/api/models", "/api/v1/models/"):
        status, raw, final = _fetch(base, path, token)
        print("[debug] GET %s -> HTTP %s (url final: %s)" % (path, status, final))
        raw_s = (raw or "").strip()
        if status == 200 and raw_s[:1] in ("{", "["):
            try:
                d = json.loads(raw_s)
            except Exception as e:
                print("[debug]   corpo nao e JSON valido: %s" % e)
                continue
            modelos = d.get("data") if isinstance(d, dict) else d
            if modelos is not None:
                return modelos
            print("[debug]   JSON sem 'data'/lista; chaves: %s" % list(d)[:8])
        else:
            print("[debug]   corpo (200 chars): %s" % raw_s[:200].replace("\n", " "))
    raise SystemExit(
        "Nao consegui obter a lista de modelos. Veja o [debug] acima:\n"
        " - HTTP 401/403 => token sem permissao (use um token de ADMIN).\n"
        " - corpo com '<' (HTML) => a URL redirecionou para uma pagina (base-url errada?\n"
        "   tente sem barra final, ou confirme https://chatnd.nidumbrasil.com.br).\n"
        " - HTTP 200 vazio => endpoint diferente nesta versao; me mande o [debug]."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("OPENWEBUI_BASE_URL"))
    ap.add_argument("--so-visao", action="store_true", help="mostra apenas os com visao=True")
    args = ap.parse_args()
    base = args.base_url
    if not base:
        raise SystemExit("Faltou --base-url (ou env OPENWEBUI_BASE_URL).")
    token = os.environ.get("ADMIN_TOKEN")
    if not token:
        raise SystemExit("Faltou a variavel de ambiente ADMIN_TOKEN.")

    modelos = get(base, token) or []

    print("Total de modelos: %d\n" % len(modelos))
    print("%-40s %-8s %-30s %s" % ("id", "visao", "base_model_id", "nome"))
    print("-" * 110)
    linhas = []
    for m in modelos:
        info = m.get("info") or {}          # /api/models embrulha em 'info'
        mid = m.get("id") or info.get("id") or ""
        nome = m.get("name") or info.get("name") or ""
        base_id = m.get("base_model_id") or info.get("base_model_id") or "(base)"
        meta = m.get("meta") or info.get("meta") or {}
        cap = meta.get("capabilities") or {}
        visao = cap.get("vision")
        if args.so_visao and not visao:
            continue
        linhas.append((str(visao), mid, base_id, nome))
    # visao=True primeiro
    for visao, mid, base_id, nome in sorted(linhas, key=lambda x: (x[0] != "True", x[1])):
        print("%-40s %-8s %-30s %s" % (mid[:40], visao, str(base_id)[:30], nome))

    print("\nDica: o BASE_MODEL_VISION deve ser um modelo com visao=True (ou um base "
          "que voce sabe ter visao). Cole aqui a linha do que voce quer usar.")


if __name__ == "__main__":
    main()
