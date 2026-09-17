#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GARDE DE LA VIDEO MONTREE — une video se REGARDE, elle ne se nomme pas.

CE QU IL EMPECHE. Finir un tour en disant « la video est faite, elle
s appelle machin.mp4 ». Patrick ne l a alors jamais vue. Un nom de fichier
ne se regarde pas, ne se juge pas, ne se corrige pas.

NE D UNE FAUTE REELLE (17/09/2026). J ai fabrique une video de 158 secondes
pour son concours. Je lui ai donne son nom et son poids. Il a repondu :
« fait un garde fou qui t oblige a me montrer la video dans une page web ».

CE QU IL FAIT. A la fin du tour, il regarde les videos de ~/livrables/videos.
Si l une a ete fabriquee ou changee DEPUIS la derniere fois que la page des
videos a ete montree, il REFUSE, et il dit quoi lancer.

CE QU IL LAISSE PASSER. Un tour sans video neuve. Une video deja montree.
Une video de moins de deux secondes (un essai, pas un rendu).

Contrat du crochet Stop : sortir 2 = BLOQUER. Ce qui est ecrit sur la sortie
d erreur revient a l agent.
"""
import json
import os
import sys
import time

MAISON = os.path.expanduser("~")
DOSSIER = os.path.join(MAISON, "livrables", "videos")
MARQUE = os.path.join(MAISON, ".claude", "portes", ".videos-montrees")
TROP_VIEUX = 6 * 3600      # on ne reclame pas pour le travail d hier
MINI = 2                   # secondes : en dessous, c est un essai


def duree_rapide(chemin):
    """Sans lancer de programme : un fichier de moins de 200 ko ne peut pas
    porter deux secondes d image et de son. Lancer ffprobe sur chaque video
    a chaque fin de tour couterait plus cher que le garde lui-meme."""
    return 0 if os.path.getsize(chemin) < 200 * 1024 else 99


def main():
    try:
        sys.stdin.read()
    except Exception:
        pass
    if not os.path.isdir(DOSSIER):
        sys.exit(0)

    vues = {}
    try:
        vues = json.load(open(MARQUE, encoding="utf-8"))
    except Exception:
        pass

    maintenant = time.time()
    jamais_vues = []
    for racine, dirs, fichiers in os.walk(DOSSIER):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in fichiers:
            if not f.lower().endswith((".mp4", ".webm")):
                continue
            chemin = os.path.join(racine, f)
            relatif = os.path.relpath(chemin, DOSSIER)
            change = os.path.getmtime(chemin)
            if maintenant - change > TROP_VIEUX:
                continue
            if duree_rapide(chemin) < MINI:
                continue
            if vues.get(relatif, 0) >= change:
                continue
            jamais_vues.append(relatif)

    if not jamais_vues:
        sys.exit(0)

    sys.stderr.write(
        "GARDE DE LA VIDEO MONTREE — REFUS.\n\n"
        "Tu as fabrique " + str(len(jamais_vues)) + " video(s) que Patrick n a "
        "PAS vue(s) :\n  - " + "\n  - ".join(jamais_vues[:6]) + "\n\n"
        "Un nom de fichier ne se regarde pas. Une video se MONTRE.\n"
        "Lance ceci, puis dis-lui l adresse :\n\n"
        "    python3 ~/outils/montrer-la-video.py " + jamais_vues[0] + "\n\n"
        "La page a la YouTube s ouvre sur son ecran, avec toutes ses videos\n"
        "rangees en listes. Reussi quand la sortie dit : VIDEOS MONTREES\n")
    sys.exit(2)


main()
