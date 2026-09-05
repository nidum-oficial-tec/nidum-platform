# -*- coding: ascii -*-
# Baixa o fonte PUBLICADO do pipe (function chatnd) e diffa contra origin/main.
# Uso: py _nidum_manutencao/_diff_publicado.py   (dentro de interface-chatnd/)
# Token: NIDUM_API_KEY do .env.local (nunca impresso).
import io, json, re, subprocess, urllib.request

env = dict(re.findall(r"(?m)^([A-Z0-9_]+)=(.*)$", io.open(".env.local", encoding="utf-8").read()))
tok = env["NIDUM_API_KEY"].strip().strip('"').strip("'")
req = urllib.request.Request(
    "https://chatnd.nidumbrasil.com.br/api/v1/functions/id/chatnd",
    headers={"Authorization": "Bearer " + tok})
d = json.load(urllib.request.urlopen(req, timeout=60))
pub = d.get("content") or ""
io.open("_publicado_chatnd.py", "w", encoding="utf-8", newline="").write(pub)
repo = subprocess.run(["git", "show", "origin/main:_nidum_tools/chatnd.py"],
                      capture_output=True).stdout.decode("utf-8")
pl = pub.replace("\r\n", "\n").splitlines()
rl = repo.replace("\r\n", "\n").splitlines()
print("publicado: %d linhas | repo(main): %d linhas" % (len(pl), len(rl)))
print("versao publicada:", [l for l in pl[:8] if "version" in l])
print("versao repo     :", [l for l in rl[:8] if "version" in l])
import difflib
diff = list(difflib.unified_diff(rl, pl, "repo_main", "publicado", lineterm="", n=1))
print("linhas de diff:", len(diff))
io.open("_diff_pub_vs_main.txt", "w", encoding="utf-8").write("\n".join(diff))
