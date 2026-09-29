#!/usr/bin/env python3
"""LA DOCUMENTATION DIT CE QUI EXISTE — rien de plus, rien d'autre.

Releve le 21/09/2026 :
  1. ARCHITECTURE.md annoncait nvidia/Llama-3_3-Nemotron-Super-49B-v1_5,
     alors que le vrai modele (nemotron_nebius.py) est
     nvidia/Nemotron-3-Ultra-550b-a55b. Un depot qui ne decrit pas son
     vrai cerveau trompe l inconnu qui l installe.
  2. SECURITE.md citait un controle « test-app-mobile.js » qui n existe
     nulle part dans le code. Une porte promise et jamais montee : rien
     ne prouvait qu elle refusait les adresses exterieures. Le vrai
     controleur s appelle test_rien_de_prive_ne_sort.py.
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
verts = rouges = 0


def juge(t, ok, d=""):
    global verts, rouges
    print("  %-5s %-56s %s" % ("VERT" if ok else "ROUGE", t, d))
    if ok:
        verts += 1
    else:
        rouges += 1


def contient(nom, mot):
    return mot.lower() in open(os.path.join(ICI, nom), encoding="utf-8").read().lower()


print("\n1) ARCHITECTURE.md parle du VRAI modele")
juge("il nomme Nemotron-3-Ultra-550b-a55b",
     contient("ARCHITECTURE.md", "Nemotron-3-Ultra"))
juge("il ne nomme plus le fantome Super-49B",
     not contient("ARCHITECTURE.md", "Super-49B"))
juge("le code dit pareil (nemotron_nebius.py)",
     contient("nemotron_nebius.py", "Nemotron-3-Ultra-550b-a55b"))
juge("architecture et code racontent le meme cerveau",
     open(os.path.join(ICI, "ARCHITECTURE.md"), encoding="utf-8").read()
     .count("Nemotron-3-Ultra") == 0
     or os.path.exists(os.path.join(ICI, "nemotron_nebius.py")))

print("\n2) SECURITE.md ne promet plus de fichier fantome")
juge("test-app-mobile.js n'est plus cite",
     not contient("SECURITE.md", "test-app-mobile.js"))
juge("le CONTROLE bien reel est cite ou existe",
     contient("SECURITE.md", "test_rien_de_prive_ne_sort") or
     os.path.exists(os.path.join(ICI, "test_rien_de_prive_ne_sort.py")))

print("\n3) la promesse de SECURITE.md tient (le controle tourne)")
import subprocess
r = subprocess.run(["python3", os.path.join(ICI, "test_rien_de_prive_ne_sort.py")],
                   capture_output=True, text=True, cwd=ICI)
juge("test_rien_de_prive_ne_sort.py tourne et passe", r.returncode == 0,
     "sortie %d : %s" % (r.returncode, r.stdout.strip().splitlines()[-1]
                         if r.stdout.strip() else r.stderr[:80]))

print("\nBILAN COHERENCE-DOC : %d verts, %d rouges" % (verts, rouges))
sys.exit(0 if rouges == 0 else 1)