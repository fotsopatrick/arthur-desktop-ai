# -*- coding: utf-8 -*-
"""CONTROLE : on peut CHOISIR le cerveau de Haichi (nebius vs qwen)."""
import json, sys
p="reglages-maison.json"
orig=open(p,encoding="utf-8").read()
def set_choix(v):
    d=json.load(open(p,encoding="utf-8")); d["cerveau_gros"]=v
    json.dump(d,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
import importlib, nano_moteur_ultra as M
Q="Quelle est la capitale du Cameroun ?"
vert=rouge=0
def dire(ok,t):
    global vert,rouge
    print(("  VERT   " if ok else "  ROUGE  ")+t); 
    globals().__setitem__('vert',vert+1) if ok else globals().__setitem__('rouge',rouge+1)
try:
    set_choix("nebius")
    r=M.nano_moteur_ultra(Q)
    dire(r.get("source")=="nemotron", "mode 'nebius' -> le cerveau Nebius/Nemotron repond (source=%s)"%r.get("source"))
    set_choix("qwen")
    r2=M.nano_moteur_ultra(Q)
    dire(r2.get("source")!="nemotron", "mode 'qwen' -> on n'utilise PAS Nebius (source=%s)"%r2.get("source"))
finally:
    open(p,"w",encoding="utf-8").write(orig)   # on remet le réglage d'origine
print("\n  %d vert, %d rouge"%(vert,rouge))
sys.exit(0 if rouge==0 else 1)
