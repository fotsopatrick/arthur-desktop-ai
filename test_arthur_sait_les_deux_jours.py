#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARTHUR DOIT SAVOIR CE QU ON A APPRIS CES DEUX JOURS.

CE QUE L EVEIL A MESURE, LE 17/09/2026 :
  233 sujets, 1 419 mots, nourris le 15 septembre a 22 h 11.
  Il ignorait : le videur, garak, CCBot, Nemotron, la porte unique.
  Cinq sur six. Deux jours de travail dont il ne savait rien.

POURQUOI C EST GRAVE POUR LUI EN PARTICULIER. Arthur promet « je prefere me
taire que dire faux ». Une memoire vieille ne le fait pas mentir — elle le
fait AVOUER a tort. Il dit « je ne sais pas » sur des choses qu on lui a
apprises. C est la promesse tenue, mais le service rendu en moins.

LES DEUX DEVOIRS
  · il connait les sujets des deux derniers jours ;
  · il ne s est pas mis a inventer pour autant — sur ce qu il ignore
    vraiment, il avoue toujours.
"""
import importlib.util
import json
import os
import sys

verts = 0
rouges = 0


def juge(ok, quoi):
    global verts, rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    if ok:
        verts += 1
    else:
        rouges += 1


ICI = os.path.dirname(os.path.abspath(__file__))
REGISTRE = os.path.join(ICI, "registre_connaissances.json")

try:
    d = json.load(open(REGISTRE, encoding="utf-8"))
except Exception as e:
    print("  le registre ne se lit pas : %s" % e)
    sys.exit(1)

print("1) LES SUJETS DES DEUX DERNIERS JOURS SONT-ILS DEDANS ?")
ATTENDUS = {
    "le-videur-du-serveur": ["videur", "fail2ban", "banisseur"],
    "garak-le-juge-exterieur": ["garak", "scanner", "vulnerabilite"],
    "ccbot-et-les-ramasseurs": ["ccbot", "common crawl", "ramasseur"],
    "nemotron-chez-nebius": ["nemotron", "nebius", "grand modele"],
    "la-porte-unique-du-cockpit": ["porte unique", "tout a l ecran"],
    "mes-instruments-mentent": ["instrument", "mesure", "compteur"],
}
for cle, mots in ATTENDUS.items():
    present = cle in d
    juge(present, "il connait « %s »" % cle.replace("-", " "))

print("2) CHAQUE SUJET NEUF EST-IL BIEN FORME ?")
bien = True
for cle in ATTENDUS:
    s = d.get(cle)
    if not isinstance(s, dict) or not all(k in s for k in ("mots", "think", "answer")):
        bien = False
        break
juge(bien, "chaque sujet neuf a ses mots, sa pensee et sa reponse")

print("3) LES 233 ANCIENS SUJETS SONT-ILS TOUJOURS LA ?")
print("        sujets en tout : %d   (233 avant, donc au moins 239 attendus)" % len(d))
juge(len(d) >= 239, "on a AJOUTE, on n a rien efface")

print("4) SON MOTEUR CHARGE-T-IL ENCORE LE REGISTRE SANS PLANTER ?")
try:
    s = importlib.util.spec_from_file_location(
        "m", os.path.join(ICI, "nano_moteur_ultra.py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    a = m.NanoMoteurUltraEngine()
    a.charger()
    juge(True, "le moteur avale le registre nourri sans broncher")
    print("5) AVOUE-T-IL TOUJOURS CE QU IL IGNORE VRAIMENT ?")
    r = a.repondre("De quelle couleur est le chapeau de mon voisin ?")
    rep = (r.get("answer") if isinstance(r, dict) else str(r)) or ""
    print("        il dit : %s" % rep[:80].replace("\n", " "))
    juge("ne sais pas" in rep.lower() or "ne peux pas" in rep.lower(),
         "sur ce qu il ignore, il avoue encore")
except Exception as e:
    juge(False, "le moteur plante : %s" % str(e)[:60])
    juge(False, "sur ce qu il ignore, il avoue encore")

print("")
print("  %d verts, %d rouges" % (verts, rouges))
sys.exit(0 if rouges == 0 else 1)
