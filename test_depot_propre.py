#!/usr/bin/env python3
"""Le dépôt public est-il propre ? (24/09/2026)

Un juge du hackathon clone le dépôt et le lance chez lui. Ce qui a été trouvé
le 24/09, et qui ne doit pas revenir :
  - des chemins du dossier personnel écrits en dur : chez le juge, ils n'existent pas ;
  - deux fichiers Python qui ne compilaient même pas ;
  - le texte de l'utilisateur glissé dans une commande shell (shell=True) :
    un guillemet dans la question suffisait à lancer n'importe quoi ;
  - la liste des noms de fichiers privés (.livrables_vus.json) publiée.
"""
import os, re, subprocess, sys

ICI = os.path.dirname(os.path.abspath(__file__))
suivis = subprocess.run(["git", "ls-files"], cwd=ICI, capture_output=True, text=True).stdout.split()
rouges = 0; n = 0
def verdict(ok, texte):
    global rouges, n
    n += 1
    print(("  VERT  " if ok else "  ROUGE ") + texte)
    if not ok:
        rouges += 1

code = [f for f in suivis if f.endswith((".py", ".sh", ".html")) and ".avant" not in f]
MAISON_ICI = os.path.expanduser("~") + "/"   # le dossier personnel de la machine, quel qu'il soit
en_dur = [f for f in code if f != "test_depot_propre.py" and MAISON_ICI in open(os.path.join(ICI, f), encoding="utf-8", errors="ignore").read()]
verdict(not en_dur, "aucun chemin du dossier personnel en dur" + (" — " + ", ".join(en_dur) if en_dur else ""))

casses = []
for f in (x for x in suivis if x.endswith(".py")):
    try:
        compile(open(os.path.join(ICI, f), encoding="utf-8").read(), f, "exec")
    except SyntaxError:
        casses.append(f)
verdict(not casses, "tous les fichiers Python compilent" + (" — " + ", ".join(casses) if casses else ""))

injection = []
for f in (x for x in suivis if x.endswith(".py") and x != "test_depot_propre.py"):
    for i, ligne in enumerate(open(os.path.join(ICI, f), encoding="utf-8", errors="ignore"), 1):
        if "shell=True" in ligne and re.search(r'\{(prompt|question|texte|body|q)\w*\}', ligne):
            injection.append("%s:%d" % (f, i))
verdict(not injection, "aucun texte d'utilisateur dans une commande shell" + (" — " + ", ".join(injection) if injection else ""))

verdict(".livrables_vus.json" not in suivis, "la liste des livrables privés n'est pas publiée")

# (24/09) Arthur n'est pas fait pour les médecins : aucune fiche de santé dans le savoir publié
import json
sante = {"sante_prep_indetectable", "labo_vih_docking", "test_dynamique_hepatite_delta", "hepatite_c_epclusa"}
publie = set(json.load(open(os.path.join(ICI, "registre_exemple.json"), encoding="utf-8")))
verdict(not (sante & publie) and "fiches-medicales-retirees.json" not in suivis,
        "aucune fiche de santé dans le dépôt public" + (" — " + ", ".join(sorted(sante & publie)) if sante & publie else ""))

print("BILAN DEPOT : %d rouge(s) sur %d" % (rouges, n))
sys.exit(1 if rouges else 0)
