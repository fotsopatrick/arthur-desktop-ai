# -*- coding: utf-8 -*-
"""Haichi quand la machine est SEULE : plus de reseau, plus d Alice.

Patrick veut debrancher sa carte wifi et parler quand meme a Haichi.
Ce test coupe pour de bon les deux chemins qui sortent de la machine, puis
verifie que Haichi :
  1. repond toujours sur la maison, aussi vite qu avant ;
  2. AVOUE pour le reste au lieu d attendre dans le vide ;
  3. ne fait pas patienter plus de quelques secondes.
"""
import time, sys, unicodedata
sys.path.insert(0, "~/cockpit-generique")
import nano_moteur_ultra as moteur

# On coupe le fil : ces deux adresses ne menent nulle part.
moteur.ALICE_URL = "http://10.255.255.1:9/v1/chat/completions"
moteur.DOCUMENTS_URL = "http://10.255.255.1:9/api/v1/knowledge?q="
moteur.ALICE_PATIENCE = 4          # on n attend pas 90 secondes dans le vide
moteur.DOCUMENTS_PATIENCE = 3

# Le 16/09/2026 : ce test coupait DEUX chemins et se disait « hors ligne ».
# Un troisieme avait ete ouvert entre-temps — Nemotron, chez Nebius, qui sort
# par le meme wifi. Le test passait au vert en etant en ligne. Un controle
# qui ne coupe pas tout ne prouve rien : on coupe aussi celui-la.
moteur.nemotron_nebius = None

def propre(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.replace("'", " ").split())

CAS = [
    ("Qui est Victor dans l equipe de la tour ?", ["victor"],        1.0),
    ("Qu est ce que la carte vivante ?",          ["cartographie"],  1.0),
    ("Cite trois agents de la tour.",             ["braignak"],      1.0),
    ("Qu est ce que Beelzebuth dans la tour ?",   ["gloutonnerie"],  1.0),
    ("Quelle est la capitale du Cameroun ?",      ["je ne sais pas"], 12.0),
    ("Quelle faille touche le noyau Debian ?",    ["je ne sais pas"], 12.0),
]

rouges = 0
for question, attendus, patience_max in CAS:
    t0 = time.perf_counter()
    r = moteur.nano_moteur_ultra(question)
    duree = time.perf_counter() - t0
    rep = propre(r.get("answer", ""))
    bon_texte = any(propre(a) in rep for a in attendus)
    assez_rapide = duree <= patience_max
    bon = bon_texte and assez_rapide
    rouges += 0 if bon else 1
    print(("  VERT  " if bon else "  ROUGE ") +
          f"({duree*1000:7.0f} ms, {r.get('source','?'):<9}) {question[:42]}")
    print("         " + r.get("answer", "")[:92].replace("\n", " "))
    if not bon_texte:    print("         -> on attendait : " + str(attendus))
    if not assez_rapide: print(f"         -> trop long : plus de {patience_max} s d attente")

print("\nBILAN HORS LIGNE : %d rouge(s) sur %d" % (rouges, len(CAS)))
raise SystemExit(1 if rouges else 0)
