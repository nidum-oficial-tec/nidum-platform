"""Prova local do vazamento de memoria do ChatND (threads nativas x arenas do glibc).

Diagnostico (producao, 2026-09-06): 896 threads no PID 1, so 37 sao Python. As
outras sao times OpenMP/BLAS parados em futex para sempre. A RAM NAO esta nas
pilhas (877 pilhas = 0,05 GB) - esta nas ARENAS do glibc: cada thread viva que
alocou ganha uma heap propria de 64 MiB que nunca volta ao SO (105 regioes,
~6 GB). threading.active_count() nao enxerga nada disso; a prova conta
/proc/self/task e heaps alinhadas a 64 MiB.

Duas fases, cada uma medida SEM e COM a variavel de ambiente:
  fase 1  MALLOC_ARENA_MAX=2   -> heaps nao crescem com threads vivas
  fase 2  OMP/OPENBLAS_NUM_THREADS=8 -> times de (8-1) em vez de (nucleos-1)

Uso (Linux; no Windows rode via Docker, ver _nidum_manutencao/RUNBOOK_THREADS_ARENAS.md):
  python prova_threads_arenas.py            # roda as duas fases, sai != 0 se falhar
"""
import ctypes, os, re, subprocess, sys, threading

MB = 1024 * 1024
HEAP = 64 * MB


def heaps_rss():
    n, rss, cur = 0, 0, None
    with open("/proc/self/smaps") as f:
        for line in f:
            m = re.match(r"^([0-9a-f]+)-([0-9a-f]+) (\S+) \S+ \S+ \S+\s*(.*)$", line)
            if m:
                lo, hi = int(m.group(1), 16), int(m.group(2), 16)
                cur = (m.group(3) == "rw-p" and not m.group(4).strip()
                       and lo % HEAP == 0 and 4 * MB <= hi - lo <= HEAP)
                if cur:
                    n += 1
            elif cur and line.startswith("Rss:"):
                rss += int(line.split()[1]) * 1024
    return n, rss


def nthreads():
    return len(os.listdir("/proc/self/task"))


# ---------------------------------------------------------------- fase 1
def _worker_parado(ev):
    # aloca em pedacos < 128 KiB (abaixo do mmap_threshold -> vai para a ARENA da
    # thread), libera metade (fragmenta, a heap nao encolhe) e fica parado, como
    # um worker OpenMP.
    chunks = [ctypes.create_string_buffer(96 * 1024) for _ in range(160)]  # ~15 MB
    for c in chunks:
        ctypes.memset(c, 1, len(c))
    del chunks[::2]
    ev.wait()


def fase1(rodadas=5, por_rodada=16):
    print("fase 1: MALLOC_ARENA_MAX=%s" % os.environ.get("MALLOC_ARENA_MAX"))
    ev = threading.Event()
    n0, r0 = heaps_rss()
    print("  inicio ......... heaps=%3d  rss_heaps=%5d MB  threads=%3d" % (n0, r0 // MB, nthreads()))
    ths = []
    for i in range(1, rodadas + 1):
        novas = [threading.Thread(target=_worker_parado, args=(ev,), daemon=True,
                                  name="omp-worker-fake-%d-%d" % (i, j)) for j in range(por_rodada)]
        for t in novas:
            t.start()
        ths += novas
        import time; time.sleep(0.5)
        n, r = heaps_rss()
        print("  rodada %d ....... heaps=%3d  rss_heaps=%5d MB  threads=%3d" % (i, n, r // MB, nthreads()))
    n1, r1 = heaps_rss()
    ev.set()
    return n1 - n0, (r1 - r0) // MB


# ---------------------------------------------------------------- fase 2
FASE2 = r"""
import os, numpy as np
from sklearn.metrics import pairwise_distances
X = np.random.rand(3000, 128); pairwise_distances(X, X[:300]); (X.T @ X).sum()
print(len(os.listdir("/proc/self/task")))
"""


def fase2():
    def run(env):
        e = dict(os.environ); e.update(env)
        return int(subprocess.check_output([sys.executable, "-c", FASE2], env=e).strip())
    cpus = os.cpu_count()
    sem = run({})
    com = run({k: "8" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
    print("fase 2: nucleos=%d  threads apos numpy+sklearn: SEM teto=%d   COM teto 8=%d" % (cpus, sem, com))
    return sem, com


if __name__ == "__main__":
    falhas = []
    if os.environ.get("MALLOC_ARENA_MAX") is None:
        # roda a si mesmo nas duas condicoes e compara
        env2 = dict(os.environ, MALLOC_ARENA_MAX="2", _FASE1_SO="1")
        print("=== SEM MALLOC_ARENA_MAX ===")
        dh_sem, dr_sem = fase1()
        print("=== COM MALLOC_ARENA_MAX=2 (subprocesso) ===")
        out = subprocess.check_output([sys.executable, __file__], env=env2).decode()
        print(out.rstrip())
        dh_com, dr_com = (int(x) for x in out.strip().splitlines()[-1].split())
        print()
        print("RESULTADO fase 1: heaps novas SEM=%d COM=%d | RSS de heaps SEM=+%d MB COM=+%d MB"
              % (dh_sem, dh_com, dr_sem, dr_com))
        # MALLOC_ARENA_MAX limita ARENAS, e uma arena encadeia varias heaps de 64 MiB
        # quando cresce - por isso a assercao e sobre RSS, nao sobre numero de heaps:
        # sem teto = 1 heap por thread (memoria liberada fica presa por thread);
        # com teto = memoria liberada e reusada entre threads. Medido: +1200 vs +360 MB.
        if not (dh_sem >= 40 and dr_com <= 0.4 * dr_sem):
            falhas.append("fase 1: esperado heaps SEM>=40 e RSS COM <= 40%% do SEM (SEM=+%d COM=+%d MB)" % (dr_sem, dr_com))
        sem, com = fase2()
        if not (com <= 2 * 7 + 3 and sem > com):
            falhas.append("fase 2: esperado COM<=17 e SEM>COM")
        print()
        print("PROVA %s" % ("OK" if not falhas else "FALHOU: " + "; ".join(falhas)))
        sys.exit(1 if falhas else 0)
    else:
        dh, dr = fase1()
        print("%d %d" % (dh, dr))
