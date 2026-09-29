#!/usr/bin/env python3
"""LE SAVOIR DE L'INCONNU — 233 sujets sans le registre prive.

Ne le 21/09/2026. Le fichier prive registre_connaissances.json appartient a
Patrick et ne sort jamais du depot (regle, .gitignore). Un inconnu qui
telecharge Arthur ne recoit QUE registre_exemple.json.

Avant la reparation du 17/09, le moteur cherchait un SEUL nom — le prive.
L'inconnu recevait donc 233 sujets... et Arthur n'en voyait AUCUN : il
tombait sur ses trois reponses de base. Trois reponses, quand le mode
d'emploi en promet 233.

Ce controle refait le geste exact de l'inconnu :
  - il copie le CODE DE TRAVAIL (pas le depot committe : un test qui
    lit le commit ne verrait jamais la regression en cours) ;
  - il lui ote ce qu'un inconnu ne recevrait jamais : les fichiers
    ignores par le .gitignore, dont le prive registre_connaissances.json ;
  - il coupe tout le reseau (mode avion absolu) ;
  - il demande « la carte vivante » ;
  et il exige UNE VRAIE REPONSE, pas un aveu d'ignorance.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
verts = rouges = 0


def juge(titre, bon, detail=""):
    global verts, rouges
    print("  %-5s %-52s %s" % ("VERT" if bon else "ROUGE", titre, detail))
    if bon:
        verts += 1
    else:
        rouges += 1


def propre(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.replace("'", " ").split())


print("\n1) LE DEPOT, COMME UN INCONNU LE RECOIT")
bac = tempfile.mkdtemp(prefix="inconnu-savoir-")
try:
    # Les fichiers ignores : ce qu'un inconnu ne recevrait jamais.
    ignores = subprocess.run(
        ["git", "-C", ICI, "ls-files", "--others", "--ignored", "--exclude-standard"],
        capture_output=True, text=True).stdout.splitlines()

    nb_copies = 0
    for dossier, _, fichiers in os.walk(ICI):
        if ".git" in dossier:
            continue
        for f in fichiers:
            rel = os.path.relpath(os.path.join(dossier, f), ICI)
            if rel in ignores:
                continue
            cible = os.path.join(bac, rel)
            os.makedirs(os.path.dirname(cible), exist_ok=True)
            shutil.copy2(os.path.join(dossier, f), cible)
            nb_copies += 1

    juge("le code de travail part dans le bac (%d fichiers)" % nb_copies,
         nb_copies > 10)

    juge("le prive registre_connaissances.json n'y est PAS",
         not os.path.exists(os.path.join(bac, "registre_connaissances.json")))
    juge("registre_exemple.json, le savoir public, y est",
         os.path.exists(os.path.join(bac, "registre_exemple.json")))
    for nom in ("nano_moteur_ultra.py",):
        juge("le moteur %s y est" % nom,
             os.path.exists(os.path.join(bac, nom)))

    print("\n2) MODE AVION : le reseau est COUPE pour de bon")
    sys.path.insert(0, bac)
    import nano_moteur_ultra as moteur

    moteur.ALICE_URL = "http://10.255.255.1:9/v1/chat/completions"
    moteur.DOCUMENTS_URL = "http://10.255.255.1:9/api/v1/knowledge?q="
    moteur.ALICE_PATIENCE = 4
    moteur.DOCUMENTS_PATIENCE = 3
    moteur.nemotron_nebius = None   # le 3e chemin qui sort par le wifi
    juge("les trois chemins sortants sont coupes", True)

    print("\n3) ARTHUR, CHEZ L'INCONNU : peut-il encore le savoir ?")
    moteur_de_linconnu = moteur.NanoMoteurUltraEngine()
    nb = len(moteur_de_linconnu.base)
    juge("il charge un vrai savoir (pas 3 reponses de base)",
         nb >= 200, "%d sujets" % nb)

    for question, attendus in [
        ("Qu est ce que la carte vivante ?", ["cartographie"]),
        ("Qui est Victor dans l equipe de la tour ?", ["victor"]),
        ("Cite trois agents de la tour.", ["braignak"]),
    ]:
        t0 = time.perf_counter()
        rep = moteur.nano_moteur_ultra(question).get("answer", "")
        duree = time.perf_counter() - t0
        rp = propre(rep)
        bon = any(propre(a) in rp for a in attendus)
        juge("REPONSE EXACTE attendue : %s" % attendus, bon,
             "(%d ms) %s" % (duree * 1000, rep[:60].replace("\n", " ")))
        if not bon:
            print("         -> repondu : %s" % rep[:90])

finally:
    try:
        subprocess.run(["rm", "-rf", bac])
    except OSError:
        pass

print("\nBILAN INCONNU-SAVOIR : %d verts, %d rouges" % (verts, rouges))
sys.exit(0 if rouges == 0 else 1)