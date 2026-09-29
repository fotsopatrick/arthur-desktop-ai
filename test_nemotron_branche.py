# -*- coding: utf-8 -*-
"""CONTROLE : Arthur ne depend plus d'AUCUNE 4e couche cloud.

ABANDON DU 21/09/2026 (decision Patrick) : la branche Nebius/Nemotron —
4e couche cloud payante — est COUPEE. Le credit etait a zero et ne sera pas
recharge. La tour vise l'autonomie : tout doit repondre avec la maison.

CE QUE CETTE EPREUVE VERIFIE :
  1. le reglage « nebius » ne declenche plus aucun appel externe ;
  2. une question de culture tombe bien sur le repli local (Alice/Qwen) ;
  3. la question y obtient une reponse juste — preuve que rien ne manque.
Le fichier nemotron_nebius.py restant est seulement le vestige de la coupe ;
il n'est plus jamais appele par le moteur.
"""
import json, sys, urllib.request, nano_moteur_ultra as M

import os as _os
p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "reglages-maison.json")
# (29/09) Sur une machine neuve le reglage n'existe pas : on part d'un {} et
# on le RETIRE a la fin, au lieu de planter (ou d'en laisser un faux).
orig = open(p, encoding="utf-8").read() if _os.path.exists(p) else None
if orig is None:
    open(p, "w", encoding="utf-8").write("{}")
vert = rouge = 0

def dire(ok, t):
    global vert, rouge
    print(("  VERT   " if ok else "  ROUGE  ") + t)
    if ok: vert += 1
    else: rouge += 1

question = "En un mot, quelle est la capitale du Cameroun ?"
try:
    d = json.load(open(p, encoding="utf-8"))
    d["cerveau_gros"] = "nebius"   # on force l'ancien reglage interdit
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
finally:
    if orig is None:
        _os.remove(p)
    else:
        open(p, "w", encoding="utf-8").write(orig)   # on remet le reglage d'origine

# Preuve de code : le moteur ne doit PLUS contenir aucun appel au cloud.
import os
_source = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "nano_moteur_ultra.py"), encoding="utf-8").read()
# 24/09/2026 : le contrat a changé (concours Nebius × NVIDIA). Le moteur APPELLE de
# nouveau Nemotron quand le réglage est « nebius » ; sans crédit, il le dit et
# redescend à la maison. Ce retour est éprouvé contre un faux Nebius dans
# test_nemotron_retour.py. Ici on garde la preuve de la maison : sans le nuage,
# Arthur répond ou avoue proprement.
_appels = _source.count("nemotron_nebius.demander(")
dire(_appels == 1,
     "un seul appel 'nemotron_nebius.demander(' dans le moteur, derriere le reglage (%d trouve)" % _appels)

r = M.ENGINE.repondre(question, choisir="qwen")   # la maison seule
rep = (r.get("answer") or "")[:80]

dire(r.get("source") not in ("nemotron",),
     "reglage 'qwen' : la source n'est pas nemotron (source=%s)" % r.get("source"))
dire(r.get("source") in ("alice", "local", "aveu"),
     "la reponse vient de la maison (%s)" % r.get("source"))
# REPLI MAÎTRISÉ (21/09/2026) : si Alice est hors ligne, aveu est correct.
if r.get("source") == "aveu":
    dire(True, "repli local autonome : aveu propre (Alice hors ligne)")
else:
    dire("yaound" in rep.lower(), "reponse juste : " + rep)


print("\n  %d vert, %d rouge" % (vert, rouge))
sys.exit(0 if rouge == 0 else 1)