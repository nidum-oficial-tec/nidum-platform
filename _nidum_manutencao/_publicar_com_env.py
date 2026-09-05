# -*- coding: ascii -*-
# Wrapper: le NIDUM_API_KEY do .env.local (nunca imprime), seta NIDUM_URL/NIDUM_TOKEN
# e executa publicar_pipe.py. Uso: py _nidum_manutencao/_publicar_com_env.py
import io, os, re, runpy, sys
env = dict(re.findall(r"(?m)^([A-Z0-9_]+)=(.*)$", io.open(".env.local", encoding="utf-8").read()))
os.environ["NIDUM_URL"] = "https://chatnd.nidumbrasil.com.br"
os.environ["NIDUM_TOKEN"] = env["NIDUM_API_KEY"].strip().strip('"').strip("'")
sys.argv = ["publicar_pipe.py"]
runpy.run_path("_nidum_manutencao/publicar_pipe.py", run_name="__main__")
