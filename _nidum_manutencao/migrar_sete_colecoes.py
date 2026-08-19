# -*- coding: ascii -*-
"""migrar_sete_colecoes.py -- DRY-RUN da migracao 2->7 colecoes (Fase 1).

SOMENTE --dry-run (padrao e UNICO modo executavel nesta fase): NAO cria colecao,
NAO move/indexa nada, NAO escreve em producao. Le o repo local da esteira +
(opcional, se houver credencial) as colecoes de producao por GET, e imprime o
relatorio de conferencia + o template do MAPA_COLECOES.

USO:
  python _nidum_manutencao/migrar_sete_colecoes.py            (dry-run; salva relatorio)
  python _nidum_manutencao/migrar_sete_colecoes.py --out X.txt

Producao (leitura, opcional): defina NIDUM_URL e NIDUM_TOKEN (admin) no ambiente.
Repo esteira: NIDUM_ESTEIRA_REPO (default: irmao ..\\esteira-conhecimento).

A REGRA de destino vem de colecao_destino.py (fonte unica, do repo da esteira) --
este script nao reimplementa classificacao.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict

_DIR = os.path.dirname(os.path.abspath(__file__))
_ESTEIRA_DEFAULT = os.path.abspath(os.path.join(_DIR, "..", "..", "esteira-conhecimento"))
ESTEIRA = os.environ.get("NIDUM_ESTEIRA_REPO", _ESTEIRA_DEFAULT).rstrip("/\\")
sys.path.insert(0, os.path.join(ESTEIRA, "_scripts"))
try:
    import colecao_destino as CD
except Exception as e:  # noqa: BLE001
    print("ERRO: nao importei colecao_destino de %s/_scripts (%s)." % (ESTEIRA, e))
    print("Defina NIDUM_ESTEIRA_REPO apontando o repo da esteira.")
    sys.exit(2)

INFRA = {"_docs", "_estado", "_scripts", "_teste_local", ".github", ".git"}
RAIZ_MD_INFRA = {"README.md", "FREIOS.md", "HIGIENE.md", "MAPA_REAL.md",
                 "MIGRACAO_DUAS_COLECOES.md"}

# papel -> colecao, para o MAPA_COLECOES (7 papeis).
PAPEL_COLECAO = [("atas", CD.ND_ATAS), ("projetos", CD.ND_PROJETOS),
                 ("fonte", CD.ND_FONTE), ("normas", CD.ND_NORMAS),
                 ("marca", CD.ND_MARCA), ("contratos", CD.ND_CONTRATOS),
                 ("externo", CD.ND_EXTERNO)]


def _carimbo_tipo(texto):
    m = re.search(r"<!--(.*?)-->", texto, re.S)
    if not m:
        return "-"
    m2 = re.search(r"\btipo:\s*([^|\r\n]+)", m.group(1))
    return m2.group(1).strip() if m2 else "-"


def arquivos_repo(raiz):
    for pasta, dirs, files in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in INFRA]
        for f in files:
            if not f.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(pasta, f), raiz)
            if os.sep not in rel and f in RAIZ_MD_INFRA:
                continue
            yield rel


def classificar_repo(raiz):
    porcol = defaultdict(list)
    excluidos, semregra, audit = [], [], []
    total = 0
    for rel in sorted(arquivos_repo(raiz)):
        total += 1
        with open(os.path.join(raiz, rel), encoding="utf-8", errors="replace") as fh:
            texto = fh.read()
        r = CD.avaliar(rel, texto)
        if r.excluido:
            excluidos.append((rel, r.motivo))
            continue
        porcol[r.colecao].append(rel)
        if r.sem_regra:
            semregra.append(rel)
        audit.append((rel, _carimbo_tipo(texto), r.colecao))
    return porcol, excluidos, semregra, audit, total


# ---------------- producao (GET apenas) ----------------
def _get(url, token):
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer %s" % token)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _lista_de(d):
    # Normaliza a resposta paginada do fork: {"items":[...]} (KnowledgeAccessListResponse /
    # KnowledgeFileListResponse), ou {"files":[...]}, ou uma lista crua. Sempre uma lista.
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        return d.get("items") or d.get("files") or []
    return []


def _kbs_producao(base, token):
    # GET /api/v1/knowledge/ e PAGINADO (?page=N, PAGE_ITEM_COUNT por pagina) e devolve
    # {"items":[KB...], "total":N}. Pagina ate esgotar (guarda dura contra loop).
    kbs, page = [], 1
    while page <= 200:
        _st, d = _get("%s/api/v1/knowledge/?page=%d" % (base, page), token)
        itens = _lista_de(d)
        if not itens:
            break
        kbs += [k for k in itens if isinstance(k, dict)]
        total = d.get("total") if isinstance(d, dict) else None
        if total is not None and len(kbs) >= total:
            break
        page += 1
    return kbs


def _arquivos_da_kb(base, token, kid):
    # GET /api/v1/knowledge/{id}/files (paginado) -> nomes por meta.name (mesma leitura
    # que o sincronizar.listar_colecao usa em producao).
    nomes, page = [], 1
    while page <= 500:
        _st, d = _get("%s/api/v1/knowledge/%s/files?limit=1000&page=%d" % (base, kid, page), token)
        itens = _lista_de(d)
        if not itens:
            break
        for f in itens:
            meta = (f or {}).get("meta") or {}
            nomes.append(meta.get("name") or (f or {}).get("filename") or (f or {}).get("id"))
        if len(itens) < 1000:
            break
        page += 1
    return nomes


def ler_producao(base, token):
    """{nome_kb: [nomes_de_arquivo]} de todas as knowledge bases. GET apenas."""
    out = {}
    for kb in _kbs_producao(base, token):
        kid = kb.get("id")
        nome = kb.get("name") or kid or "?"
        try:
            out[nome] = _arquivos_da_kb(base, token, kid) if kid else []
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
            out[nome] = []  # uma KB ilegivel nao derruba o confronto todo
    return out


def _key(nome):
    # Chave CANONICA de caminho. Producao guarda meta.name como a chave da esteira
    # ("PASTA > sub > arquivo.md", separador " > "); o repo usa "/". Normaliza os dois
    # para o MESMO caminho e compara por caminho (nao por basename - que colidiria nomes
    # iguais em pastas diferentes e, pior, nem casava " > " com "/"). Um rename/move
    # aparece dos DOIS lados (e o que queremos: nao sumir com nada).
    s = str(nome).replace("\\", "/").replace(" > ", "/")
    return s.strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--executar", action="store_true",
                    help="BLOQUEADO nesta fase (execucao real desabilitada).")
    ap.add_argument("--out", default=os.path.join(_DIR, "relatorio_migracao_dryrun.txt"))
    args = ap.parse_args()
    if args.executar:
        print("EXECUCAO REAL DESABILITADA nesta fase. So --dry-run (leitura). "
              "Aguarda aprovacao do Davi.")
        return 3

    L = []
    p = L.append
    p("=" * 78)
    p("MIGRACAO 2->7 COLECOES  |  DRY-RUN (leitura apenas; nada criado/movido)")
    p("=" * 78)
    p("Repo esteira: %s" % ESTEIRA)

    porcol, excluidos, semregra, audit, total = classificar_repo(ESTEIRA)
    soma = sum(len(v) for v in porcol.values())

    p("\n## Contagem por colecao (repo)")
    for c in CD.COLECOES:
        p("  %-14s %d" % (c, len(porcol.get(c, []))))
    p("  %-14s %d" % ("EXCLUIDOS", len(excluidos)))

    p("\n## INVARIANTE: classificados + excluidos == total")
    ok = (soma + len(excluidos) == total)
    p("  %d + %d = %d | total varrido = %d | %s"
      % (soma, len(excluidos), soma + len(excluidos), total,
         "OK ZERO PERDIDOS" if ok else "*** FUROU -- ABORTAR ***"))
    if not ok:
        p("\nABORTADO: a invariante nao fechou. Nada a propor ate isso bater.")
        return _emit(L, args.out, 1)

    p("\n## Excluidos (nominal, com motivo) -- nunca indexados; nada sai do repo")
    for rel, mot in excluidos:
        p("  - %s  <== %s" % (rel, mot))

    p("\n## SEM-REGRA (nd-normas sem regra) -- revisar e promover regra nova")
    for rel in (semregra or ["(nenhum)"]):
        p("  - %s" % rel)

    p("\n## Auditoria carimbo-velho (tipo:) x regra-nova (colecao)")
    cross = defaultdict(lambda: defaultdict(int))
    for _rel, tipo, col in audit:
        cross[col][tipo] += 1
    for col in CD.COLECOES:
        if cross.get(col):
            dist = ", ".join("%s=%d" % (t, n) for t, n in sorted(cross[col].items()))
            p("  %-14s <- %s" % (col, dist))
    p("  DIVERGENCIAS de interesse (o carimbo NAO e sinal decisorio; so auditoria):")
    div = [(rel, tipo, col) for rel, tipo, col in audit
           if (tipo == "ata" and col != CD.ND_ATAS)
           or (tipo == "fonte_doutrina" and col != CD.ND_FONTE)]
    for rel, tipo, col in div:
        p("    ! %s  (carimbo=%s -> %s)" % (os.path.basename(rel), tipo, col))
    if not div:
        p("    (nenhuma divergencia forte ata/fonte)")

    p("\n## Confronto repo x producao (GET apenas)")
    base = os.environ.get("NIDUM_URL", "").rstrip("/")
    token = os.environ.get("NIDUM_TOKEN", "").strip()
    if not base or not token:
        p("  SKIPPED: defina NIDUM_URL e NIDUM_TOKEN (admin, SOMENTE LEITURA) e rode de novo.")
        p("  Sem credencial aqui -> confronto com producao PENDENTE (nada decidido).")
    else:
        try:
            prod = ler_producao(base, token)
            prod_keys = set()
            p("  Knowledge bases em producao:")
            for nome, arqs in prod.items():
                p("    - %-30s %d arquivos" % (nome, len(arqs)))
                prod_keys.update(_key(a) for a in arqs)
            repo_keys = set(_key(r) for c in porcol.values() for r in c)
            so_repo = sorted(repo_keys - prod_keys)
            so_prod = sorted(prod_keys - repo_keys)
            p("  So no REPO (ainda nao em producao): %d" % len(so_repo))
            for k in so_repo:
                p("    + %s" % k)
            p("  So na PRODUCAO (nao existe mais no repo; nao some calado): %d" % len(so_prod))
            for k in so_prod:
                p("    - %s" % k)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:  # noqa: BLE001
            p("  ERRO ao ler producao (GET): %s -- confronto pendente, nada decidido." % e)

    p("\n## MAPA_COLECOES (colar no painel; ids placeholder -- colecoes ainda nao existem)")
    mapa = {papel: "COLAR_ID_%s" % col for papel, col in PAPEL_COLECAO}
    p(json.dumps(mapa, indent=2, ensure_ascii=True, sort_keys=True))

    p("\nFim do dry-run. Nada foi criado, movido ou publicado.")
    return _emit(L, args.out, 0)


def _emit(L, out, rc):
    texto = "\n".join(L)
    sys.stdout.write(texto.encode("ascii", "replace").decode("ascii") + "\n")
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(texto + "\n")
        print("\n[relatorio salvo em %s]" % out)
    except OSError as e:  # noqa: BLE001
        print("\n[nao consegui salvar o relatorio: %s]" % e)
    # GitHub Action: espelha o relatorio no summary do job (invariante/contagens/confronto).
    ss = os.environ.get("GITHUB_STEP_SUMMARY")
    if ss:
        try:
            with open(ss, "a", encoding="utf-8") as f:
                f.write("## Dry-run migracao 2->7 colecoes (GET-only)\n\n```\n"
                        + texto + "\n```\n")
        except OSError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
