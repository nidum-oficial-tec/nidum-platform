#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Criacao em massa de usuarios no ChatND (Open WebUI de producao).

PADRAO DE SEGURANCA: este script PREPARA; o humano EXECUTA com a credencial.
Credenciais SO por variavel de ambiente (nunca em arquivo/codigo/.env commitado):
  ADMIN_TOKEN       token de admin da plataforma (Authorization: Bearer)
  SENHA_PROVISORIA  senha provisoria unica e padrao (so no modo real)

O que faz:
  - le um CSV com colunas "nome,email";
  - VALIDA antes de criar:
      * e-mails duplicados dentro do CSV (pula as repeticoes);
      * e-mails fora do dominio da Nidum (rejeita);
      * usuarios que JA existem na plataforma (pula, nao sobrescreve);
    a comparacao de "ja existe"/"duplicado" usa e-mail NORMALIZADO (minusculas, sem espacos);
  - cria cada usuario via API admin, papel "user", com a SENHA_PROVISORIA;
  - relatorio final: criados, pulados, erros;
  - DRY-RUN por padrao (nao cria nada); modo real exige a flag --executar.

Endpoints (Open WebUI):
  GET  /api/v1/users/all           -> lista usuarios (admin)
  GET  /api/v1/auths/admin/config  -> estado do autocadastro (ENABLE_SIGNUP)
  POST /api/v1/auths/add           -> cria usuario (admin) {name,email,password,role}

Uso:
  DRY-RUN (nao cria; so lista o plano; precisa de ADMIN_TOKEN para checar existentes):
    ADMIN_TOKEN=xxxx python criar_usuarios_em_massa.py \
      --csv "TEC_UsuariosChatND_13072026_V1.csv" \
      --base-url https://chatnd.nidumbrasil.com.br

  REAL (cria de fato):
    ADMIN_TOKEN=xxxx SENHA_PROVISORIA=yyyy python criar_usuarios_em_massa.py \
      --csv "TEC_UsuariosChatND_13072026_V1.csv" \
      --base-url https://chatnd.nidumbrasil.com.br \
      --executar
"""
import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.request

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def norm_email(e):
    return (e or "").strip().lower()


def api(base, path, token, method="GET", body=None, timeout=30):
    """Chama a API. Devolve (status, dado). status 0 = erro de rede."""
    url = base.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(raw)
        except Exception:
            detail = raw
        return e.code, detail
    except Exception as e:
        return 0, str(e)


def get_existing_emails(base, token):
    status, data = api(base, "/api/v1/users/all", token)
    if status != 200:
        raise SystemExit("ERRO ao listar usuarios (HTTP %s): %s" % (status, data))
    users = data.get("users") if isinstance(data, dict) else data
    return set(norm_email(u.get("email")) for u in (users or []) if u.get("email"))


def get_signup_state(base, token):
    status, data = api(base, "/api/v1/auths/admin/config", token)
    if status == 200 and isinstance(data, dict) and "ENABLE_SIGNUP" in data:
        return data.get("ENABLE_SIGNUP")
    return None  # desconhecido


def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader, start=2):  # linha 1 = cabecalho
            nome = (r.get("nome") or "").strip()
            email = (r.get("email") or "").strip()
            if not nome and not email:
                continue  # linha em branco
            rows.append({"linha": i, "nome": nome, "email": email, "norm": norm_email(email)})
    return rows


def parece_email_ja_existe(detalhe):
    d = str(detalhe).lower()
    return any(t in d for t in ("taken", "already", "exist", "registr", "cadastr", "em uso", "in use"))


def parece_erro_de_senha(detalhe):
    d = str(detalhe).lower()
    return any(t in d for t in ("password", "senha"))


def main():
    ap = argparse.ArgumentParser(description="Criacao em massa de usuarios no ChatND (Open WebUI).")
    ap.add_argument("--csv", required=True, help="CSV de entrada com colunas nome,email")
    ap.add_argument("--base-url", default=os.environ.get("OPENWEBUI_BASE_URL"),
                    help="URL da plataforma (ou env OPENWEBUI_BASE_URL). Ex.: https://chatnd.nidumbrasil.com.br")
    ap.add_argument("--dominio", default="nidumbrasil.com.br", help="dominio permitido (rejeita fora dele)")
    ap.add_argument("--executar", action="store_true", help="cria de fato; SEM esta flag e DRY-RUN")
    ap.add_argument("--intervalo", type=float, default=0.3, help="segundos entre criacoes (modo real)")
    args = ap.parse_args()

    base = args.base_url
    if not base:
        raise SystemExit("Faltou --base-url (ou env OPENWEBUI_BASE_URL). Ex.: https://chatnd.nidumbrasil.com.br")
    token = os.environ.get("ADMIN_TOKEN")
    if not token:
        raise SystemExit("Faltou a variavel de ambiente ADMIN_TOKEN (token de admin).")
    senha = os.environ.get("SENHA_PROVISORIA")
    real = args.executar
    if real and not senha:
        raise SystemExit("Modo real (--executar) exige a variavel de ambiente SENHA_PROVISORIA.")

    print("== Criacao em massa de usuarios no ChatND ==")
    print("Plataforma :", base)
    print("Modo       :", "REAL (cria de fato)" if real else "DRY-RUN (nao cria nada)")
    print("Dominio    :", args.dominio)

    signup = get_signup_state(base, token)
    rotulo = {True: "LIGADO", False: "DESLIGADO", None: "desconhecido (sem permissao/endpoint)"}[signup]
    print("Autocadastro (ENABLE_SIGNUP):", rotulo)
    print()

    rows = load_csv(args.csv)
    existentes = get_existing_emails(base, token)
    print("Usuarios ja na plataforma:", len(existentes))
    print("Linhas no CSV            :", len(rows))
    print()

    a_criar, pulados, rejeitados = [], [], []
    vistos = set()
    for r in rows:
        nome, email, ne = r["nome"], r["email"], r["norm"]
        if not nome or not email:
            rejeitados.append((r, "linha incompleta (nome/email vazio)"))
            continue
        if not EMAIL_RE.match(email):
            rejeitados.append((r, "email invalido"))
            continue
        if not ne.endswith("@" + args.dominio.lower()):
            rejeitados.append((r, "fora do dominio " + args.dominio))
            continue
        if ne in vistos:
            pulados.append((r, "duplicado no CSV"))
            continue
        vistos.add(ne)
        if ne in existentes:
            pulados.append((r, "ja existe na plataforma"))
            continue
        a_criar.append(r)

    print("Resumo da validacao:  a criar=%d  pulados=%d  rejeitados=%d"
          % (len(a_criar), len(pulados), len(rejeitados)))
    print()
    if pulados:
        print("-- PULADOS --")
        for r, m in pulados:
            print("  [pular]     %-45s : %s" % (r["email"], m))
        print()
    if rejeitados:
        print("-- REJEITADOS --")
        for r, m in rejeitados:
            print("  [rejeitado] %-45s : %s" % (r["email"] or "(sem email)", m))
        print()

    if not real:
        print("-- SERIAM CRIADOS (DRY-RUN) --")
        for r in a_criar:
            print("  [criar]     %-45s  papel=user  (%s)" % (r["email"], r["nome"]))
        print()
        print("DRY-RUN: NADA foi criado. Para criar de fato: rode com --executar e SENHA_PROVISORIA definida.")
        return

    # -------- MODO REAL --------
    criados, erros = [], []
    for r in a_criar:
        payload = {"name": r["nome"], "email": r["norm"], "password": senha, "role": "user"}
        status, data = api(base, "/api/v1/auths/add", token, method="POST", body=payload)
        detalhe = data.get("detail") if isinstance(data, dict) else data
        if status == 200:
            criados.append(r)
            print("  [ok]     criado: %s" % r["email"])
        elif status == 400 and parece_email_ja_existe(detalhe):
            pulados.append((r, "ja existe (detectado na criacao)"))
            print("  [pular]  ja existe: %s" % r["email"])
        else:
            erros.append((r, "HTTP %s: %s" % (status, detalhe)))
            print("  [ERRO]   %s : HTTP %s: %s" % (r["email"], status, detalhe))
            if status == 400 and parece_erro_de_senha(detalhe):
                print()
                print("!! A SENHA_PROVISORIA nao passou na politica de senha da plataforma.")
                print("   Ajuste a senha e rode de novo. Abortando para nao gerar erro em massa.")
                break
        time.sleep(max(0.0, args.intervalo))

    print()
    print("== RELATORIO FINAL ==")
    print("  criados : %d" % len(criados))
    print("  pulados : %d" % len(pulados))
    print("  erros   : %d" % len(erros))
    if erros:
        print("-- ERROS --")
        for r, m in erros:
            print("  %-45s : %s" % (r["email"], m))
    print()
    print("Lembrete: instrua os usuarios a TROCAR a senha provisoria no primeiro acesso.")


if __name__ == "__main__":
    main()
