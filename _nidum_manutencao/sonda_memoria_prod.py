import os, re, collections
MB = 1024 * 1024
HEAP = 64 * MB   # HEAP_MAX_SIZE do glibc: heaps nao-principais sao mmap alinhados a 64 MiB

st = {}
with open("/proc/1/status") as f:
    for line in f:
        k = line.split(":")[0]
        if k in ("VmRSS", "RssAnon", "RssFile", "RssShmem", "Threads"):
            st[k] = line.split()[1]
print("status:", st)
with open("/sys/fs/cgroup/memory.stat") as f:
    ms = dict(l.split() for l in f if l.split()[0] in ("anon", "file", "kernel", "shmem", "file_mapped"))
print("cgroup memory.stat (MB):", {k: int(v) // MB for k, v in ms.items()})
print("cgroup memory.current (MB):", int(open("/sys/fs/cgroup/memory.current").read()) // MB)

regs, cur = [], None
with open("/proc/1/smaps") as f:
    for line in f:
        m = re.match(r"^([0-9a-f]+)-([0-9a-f]+) (\S+) \S+ \S+ \S+\s*(.*)$", line)
        if m:
            cur = {"lo": int(m.group(1), 16), "hi": int(m.group(2), 16), "perm": m.group(3),
                   "name": m.group(4).strip(), "rss": 0}
            regs.append(cur)
        elif cur is not None and line.startswith("Rss:"):
            cur["rss"] = int(line.split()[1]) * 1024

futex = set()
for t in os.listdir("/proc/1/task"):
    try:
        sc = open("/proc/1/task/%s/syscall" % t).read().split()
        if sc and sc[0] == "202":
            futex.add(int(sc[1], 16))
    except Exception:
        pass

heaps, big_anon, other_anon = [], [], []
for r in regs:
    if r["name"]:
        continue
    sz = r["hi"] - r["lo"]
    if r["perm"] == "rw-p" and r["lo"] % HEAP == 0 and sz <= HEAP and sz >= 4 * MB:
        r["futex"] = sum(1 for a in futex if r["lo"] <= a < r["hi"])
        heaps.append(r)
    elif r["perm"] == "rw-p" and sz > HEAP:
        big_anon.append(r)
    elif r["perm"] == "rw-p":
        other_anon.append(r)

def gb(x): return x / (1024.0 ** 3)
print()
print("=== ARENAS glibc (anon rw-p alinhadas a 64MiB, <=64MiB) ===")
print("  n=%d  RSS=%.2f GB  (das quais %d hospedam futex de thread parada)"
      % (len(heaps), gb(sum(r["rss"] for r in heaps)), sum(1 for r in heaps if r["futex"])))
print("  RSS das arenas COM futex: %.2f GB   SEM futex: %.2f GB"
      % (gb(sum(r["rss"] for r in heaps if r["futex"])), gb(sum(r["rss"] for r in heaps if not r["futex"]))))
print("=== anon rw-p > 64 MiB (tensores de modelo / buffers grandes) ===")
for r in sorted(big_anon, key=lambda r: -r["rss"])[:8]:
    print("  tam=%6d MB  rss=%6d MB" % ((r["hi"] - r["lo"]) // MB, r["rss"] // MB))
print("  n=%d  RSS=%.2f GB" % (len(big_anon), gb(sum(r["rss"] for r in big_anon))))
print("=== demais anon rw-p (pilhas, pymalloc, heap principal...) ===")
print("  n=%d  RSS=%.2f GB" % (len(other_anon), gb(sum(r["rss"] for r in other_anon))))
heapmain = [r for r in regs if r["name"] == "[heap]"]
print("  [heap] principal RSS=%.2f GB" % gb(sum(r["rss"] for r in heapmain)))
print("=== file-backed RSS (top 10) ===")
fb = collections.Counter()
for r in regs:
    if r["name"] and r["name"].startswith("/"):
        fb[r["name"]] += r["rss"]
for k, v in fb.most_common(10):
    print("  %6d MB  %s" % (v // MB, k[-80:]))
print("  total file-backed RSS=%.2f GB" % gb(sum(fb.values())))
print()
print("--- monitor vivo? ---")
for p in os.listdir("/proc"):
    if p.isdigit():
        try:
            c = open("/proc/%s/cmdline" % p, "rb").read().replace(b"\0", b" ")
            if b"monitor.sh" in c and b"base64" not in c:
                print("  pid", p, c.decode()[:60])
        except Exception:
            pass
print(open("/tmp/mon/monitor.out").read())
print("linhas em threads.log:", sum(1 for _ in open("/tmp/mon/threads.log")))
