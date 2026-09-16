#!/usr/bin/env python3
"""RIEN DE PRIVE NE SORT DU DEPOT PUBLIC.

Ne le 16/09/2026, juste avant de publier le code d'Arthur pour le hackathon.
En fouillant un clone du depot, j'ai trouve l'adresse du serveur de Patrick
ecrite 4 fois, celle de son PC 5 fois, et celle d'Alice 3 fois.

Donner l'adresse de son serveur au monde entier, c'est dire aux attaquants
ou frapper. Ce controle tourne AVANT chaque publication.

Il verifie deux choses, et les deux comptent :
  - ce qui est prive ne sort pas ;
  - et Arthur marche quand meme avec le registre nettoye. Un nettoyage qui
    casse le programme n'est pas un nettoyage, c'est une panne.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ICI = os.path.expanduser("~/haichi")

# Ce qui ne doit jamais sortir. On ecrit les vraies valeurs ICI, dans un
# fichier qui reste a la maison — c'est le seul endroit ou elles ont le droit
# d'etre, parce que ce fichier n'est pas publie (voir le .gitignore).
INTERDITS = [
    (r"145\.239\.\d+\.\d+",      "l'adresse du serveur de Patrick"),
    (r"192\.168\.1\.\d+",        "une machine de son reseau"),
    (r"ghp_[A-Za-z0-9]{30,}",    "un jeton GitHub"),
    (r"eyJ[A-Za-z0-9_-]{30,}",   "une clef d'API"),
    (r"BEGIN (?:RSA |OPENSSH )?PRIVATE KEY", "une clef privee"),
    (r"07\s?62\s?38\s?89\s?38",  "le telephone de Patrick"),
]

verts, rouges = [], []


def juge(titre, bon, detail=""):
    (verts if bon else rouges).append(titre)
    print("  %-5s %-48s %s" % ("OK" if bon else "RATE", titre, detail))


def fichiers_du_depot(dossier):
    """Ce qu'un inconnu recevrait vraiment, pas ce qui traine sur le disque."""
    sortie = subprocess.run(["git", "-C", dossier, "ls-files"],
                            capture_output=True, text=True)
    return [f for f in sortie.stdout.splitlines() if f.strip()]


print("\n1) ON CLONE, COMME UN INCONNU")
bac = tempfile.mkdtemp()
clone = os.path.join(bac, "arthur")
r = subprocess.run(["git", "clone", "--quiet", ICI, clone], capture_output=True)
juge("le clone reussit", r.returncode == 0)
liste = fichiers_du_depot(clone)
juge("il recoit des fichiers", len(liste) > 10, "%d fichiers" % len(liste))

print("\n2) RIEN DE PRIVE DEDANS")
for motif, quoi in INTERDITS:
    coupables = []
    for nom in liste:
        chemin = os.path.join(clone, nom)
        if not os.path.isfile(chemin):
            continue
        if nom.startswith("test_"):        # un faux secret dans un test est normal
            continue
        try:
            with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
                if re.search(motif, f.read()):
                    coupables.append(nom)
        except OSError:
            pass
    juge("aucune trace de %s" % quoi, not coupables,
         ", ".join(coupables[:2]) if coupables else "rien trouve")

print("\n3) LE COFFRE A CLEFS EST RESTE A LA MAISON")
for interdit in (".secrets", "cle-nebius.txt", ".env", ".cle-nebius"):
    juge("%s n'est pas parti" % interdit,
         not os.path.exists(os.path.join(clone, interdit)))

print("\n4) LE REGISTRE D'EXEMPLE EXISTE ET EST PROPRE")
exemple = os.path.join(ICI, "registre_exemple.json")
juge("il existe", os.path.exists(exemple))
if os.path.exists(exemple):
    contenu = open(exemple, encoding="utf-8").read()
    for motif, quoi in INTERDITS[:2]:
        juge("le registre d'exemple n'a pas %s" % quoi,
             not re.search(motif, contenu))
    try:
        d = json.loads(contenu)
        juge("il reste un JSON valide", True, "%d entrees" % (
            len(d) if isinstance(d, (list, dict)) else 0))
    except json.JSONDecodeError as e:
        juge("il reste un JSON valide", False, str(e)[:40])
    juge("il a garde le savoir", len(contenu) > 100000,
         "%d octets" % len(contenu))

print("\n5) ARTHUR MARCHE QUAND MEME")
code = '''
import os, sys
sys.path.insert(0, %r)
import nano_moteur_ultra as NM
m = NM.NanoMoteurUltraEngine()
r = m.repondre("combien font 17 fois 23 ?")
print("391" in str(r.get("answer","")))
r2 = m.repondre("c'est quoi la PrEP ?")
print(r2.get("source") == "aveu")
''' % clone
out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                     text=True, cwd=clone)
lignes = out.stdout.strip().splitlines()
juge("il demarre depuis le clone", len(lignes) >= 2, out.stderr.strip()[:50])
if len(lignes) >= 2:
    juge("il calcule encore (391)", lignes[0] == "True")
    juge("il refuse encore la sante", lignes[1] == "True")

subprocess.run(["rm", "-rf", bac])
print("\n" + "=" * 70)
print("  %d epreuves passees, %d ratees" % (len(verts), len(rouges)))
for r in rouges:
    print("   RATE : " + r)
print("=" * 70)
sys.exit(1 if rouges else 0)
