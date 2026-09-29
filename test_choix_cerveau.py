# -*- coding: utf-8 -*-
"""CONTROLE : on peut CHOISIR le cerveau de Haichi, et « nebius » n'appelle plus
le cloud.

ABANDON DU 21/09/2026 : la 4e couche cloud (Nebius/Nemotron) est coupee.
Le reglage « nebius » devient un alias du repli local : meme demandé, le
système garde son autonomie et répond avec la maison (Alice/Qwen).
"""
import json, sys
import os as _os
p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "reglages-maison.json")
# (29/09) Sur une machine neuve le reglage n'existe pas : on part d'un {} et
# on le RETIRE a la fin, au lieu de planter (ou d'en laisser un faux).
orig = open(p, encoding="utf-8").read() if _os.path.exists(p) else None
if orig is None:
    open(p, "w", encoding="utf-8").write("{}")

def set_choix(v):
    d = json.load(open(p, encoding="utf-8")); d["cerveau_gros"] = v
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

import importlib, nano_moteur_ultra as M
Q = "Quelle est la capitale du Cameroun ?"
vert = rouge = 0

def dire(ok, t):
    global vert, rouge
    print(("  VERT   " if ok else "  ROUGE  ") + t)
    globals().__setitem__('vert', vert + 1) if ok else globals().__setitem__('rouge', rouge + 1)

try:
    set_choix("nebius")
    r = M.nano_moteur_ultra(Q)
    dire(r.get("source") not in ("nemotron",),
         "mode 'nebius' ne repond PLUS via le cloud (source=%s)" % r.get("source"))
    # REPLI MAÎTRISÉ (21/09/2026) : si Alice est hors ligne, l'aveu propre est valide.
    rep = (r.get("answer") or "").lower()
    dire(rep.find("yaound") >= 0 or "je ne sais pas" in rep,
         "mode 'nebius' replique juste ou avoue proprement via le repli local")

    set_choix("qwen")
    r2 = M.nano_moteur_ultra(Q)
    dire(r2.get("source") != "nemotron",
         "mode 'qwen' -> on n'utilise PAS le cloud (source=%s)" % r2.get("source"))
finally:
    if orig is None:
        _os.remove(p)
    else:
        open(p, "w", encoding="utf-8").write(orig)   # on remet le reglage d'origine

print("\n  %d vert, %d rouge" % (vert, rouge))
sys.exit(0 if rouge == 0 else 1)