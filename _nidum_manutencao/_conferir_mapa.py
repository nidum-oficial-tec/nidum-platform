# -*- coding: ascii -*-
# Confere: colecoes existentes (id/nome) vs valve MAPA_COLECOES atual do pipe.
import io, json, re, urllib.request
env = dict(re.findall(r"(?m)^([A-Z0-9_]+)=(.*)$", io.open(".env.local", encoding="utf-8").read()))
tok = env["NIDUM_API_KEY"].strip().strip('"').strip("'")
base = "https://chatnd.nidumbrasil.com.br"
def get(path):
    req = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(req, timeout=60))
kb = get("/api/v1/knowledge/")
itens = kb.get("items") if isinstance(kb, dict) else kb
print("COLECOES NO PAINEL:")
for k in itens:
    print("  %s  %s" % (k.get("id"), (k.get("name") or "")[:44]))
v = get("/api/v1/functions/id/chatnd/valves")
mapa = v.get("MAPA_COLECOES", "(campo ausente)")
print("\nVALVE MAPA_COLECOES ATUAL:")
print("  " + (mapa if isinstance(mapa, str) else json.dumps(mapa)))
print("\nMAX_CHARS_PROJETO na valve:", v.get("MAX_CHARS_PROJETO", "(ausente = default 45000)"))
