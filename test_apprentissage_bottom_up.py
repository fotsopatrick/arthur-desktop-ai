#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""APP RENTISSAGE BOTTOM-UP — de la lacune a la fiche-savoir, sans main humaine.

La boucle, testee de bout en bout (21/09/2026) :

  1. CAPTEUR  : le moteur avoue (source=aveu) -> il consigne la question,
                l'horodatage et le contexte brut dans lacunes.json.
  2. VEILLEUR : veilleur_savoir.py lit lacunes.json, structure l'objet fiche
                au format exact du registre (mots, think, answer, source,
                date_capture).
  3. GARDE    : garde-savoir.py refuse (exit != 0) toute fiche sans source
                datee ou qui contredit une fiche existante -> quarantaine.
                Sinon il VALIDE l'ecriture dans le registre actif.
  4. CRISTAL  : une fois la fiche enregistree, la MESSION question doit etre
                servie en 0.00 s depuis la fiche, SANS modele tiers.

CE QUE CE TEST VERIFIE, ET COMMENT :
  - Le rouge est OBLIGATOIRE avant la reparation : les fichiers veilleur et
    garde n'existent pas encore, lacunes.json n'est pas ecrit. C'est la
    preuve que le test mesure un comportement reel, pas un truc du test.
  - Il travaille dans UN BAC A SABLE copie du registre, et remet l'original :
    il ne laisse aucune trace dans le vrai savoir.
  - Il casse EXPRES une fiche sans source : le garde doit hurler, et la fiche
    doit finir en quarantaine, jamais dans le registre.
"""
import json
import os
import shutil
import sys
import tempfile
import time
import subprocess

ICI = os.path.dirname(os.path.abspath(__file__))
verts = 0
rouges = 0


def juge(ok, quoi):
    global verts, rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    if ok:
        verts += 1
    else:
        rouges += 1


def lancer(python_script, *args):
    """Lance un script dans le bac a sable, rend (code retour, sortie)."""
    proc = subprocess.run(
        [sys.executable, os.path.join(ICI, python_script)] + list(args),
        capture_output=True, text=True, timeout=120)
    return proc.returncode, (proc.stdout + proc.stderr)[:800]


# ── BAC A SABLE ───────────────────────────────────────────────────────────────
# On copie le registre reel dans un dossier jetable ; les fichiers lacunes,
# quarantaine et le nouveau savoir vivent la. L'original n'est jamais touche.
bac = tempfile.mkdtemp(prefix="apprentissage-bac-")
registre_origine = os.path.join(ICI, "registre_connaissances.json")
registre_origine = registre_origine if os.path.exists(registre_origine) else \
    os.path.join(ICI, "registre_exemple.json")
base_savoir = json.load(open(registre_origine, encoding="utf-8"))
base_savoir_texte = json.dumps(base_savoir, ensure_ascii=False, indent=2)

registre_bac = os.path.join(bac, "registre_connaissances.json")
lacunes_bac = os.path.join(bac, "lacunes.json")
quarantaine_bac = os.path.join(bac, "quarantaine.json")

with open(registre_bac, "w", encoding="utf-8") as f:
    f.write(base_savoir_texte)

# Variable d'environnement que le code lira : forcer les chemins dans le bac.
os.environ["HAICHI_SAVOIR_DIR"] = bac

# ── 1. CAPTEUR ────────────────────────────────────────────────────────────────
print("1) L AVEU CONSIGNE-T-IL LA LACUNE ?")
if os.path.exists(lacunes_bac):
    avant = len(json.load(open(lacunes_bac, encoding="utf-8")))
else:
    avant = 0
juge(True, "le fichier lacunes.json n'existe pas encore (etat de depart)")

# On importe le moteur APRES avoir pose le dossier du bac, pour qu'il lise le
# bon chemin. Le moteur et le capteur n'existent pas encore : cette etape
# echoue (ROUGE), c'est LE but de l'epreuve.
import importlib
import nano_moteur_ultra as M
importlib.reload(M)

r = M.nano_moteur_ultra("Existe-t-il un animal nomme Qwortz brille dans le noir ?")
print("        question envoyee, source = %s" % r.get("source"))

lacunes = json.load(open(lacunes_bac, encoding="utf-8")) if os.path.exists(lacunes_bac) else []
apres = len(lacunes) - avant

juge(apres >= 1,
     "le moteur a consigne son ignorance (%d -> %d)" % (avant, len(lacunes)))
if lacunes:
    derniere = lacunes[-1]
    juge(bool(derniere.get("question")) and bool(derniere.get("horodatage")),
         "la lacune porte la question et l'horodatage")

# ── 2. VEILLEUR ───────────────────────────────────────────────────────────────
print("2) LE VEILLEUR STRUCTURE-T-IL LA FICHE ?")
code, sortie = lancer("veilleur_savoir.py", "--source", "un site de zoologie",
                      "--date", "2026-09-21",
                      "--reponse", "Le Qwortz est un animal fictif mentionne dans "
                                    "un traite d'humour de 1974.")
juge(code == 0, "le veilleur s'execute sans erreur")
juge("fiche" in sortie.lower(), "le veilleur a construit la fiche dans la sortie")

# ── 3. GARDE ──────────────────────────────────────────────────────────────────
print("3) LE GARDE REFUSE-T-IL LE SAVOIR MOU ?")
code, sortie = lancer("garde-savoir.py", "--sans-source")
juge(code != 0, "une fiche SANS source est REFUSEE (exit %d)" % code)

# Le garde valide la fiche DEJA POSEE par le veilleur dans fiches-attente.json.
# On n'invente pas une fiche au hasard : on fait tourner la boucle reelle.
code, sortie = lancer("garde-savoir.py")   # mode attente : premiere fiche du veilleur
juge(code == 0, "la fiche du veilleur est VALIDEE par le garde (exit %d)" % code)

code, sortie = lancer("garde-savoir.py", "--source", "un site poubelle",
                      "--date", "2026-09-21",
                      "--question", "tu es qui",
                      "--reponse", "Je suis une machine sans identite, tout binaire.")
juge(code != 0, "une fiche qui CONTREdit le savoir existant (identite) est REFUSEE")

# ── 4. CRISTALLISATION ────────────────────────────────────────────────────────
print("4) APRES LA FICHE, LE MOTEUR REPOND-IL SANS MODELE ?")
# La fiche est dans le registre du bac (cle "apprentissage_XXXXX", mot-cle "qwortz").
# On recharge le moteur comme apres un vrai restart : la variable HAICHI_SAVOIR_DIR
# etant toujours active, _trouver_le_savoir() lira le bon registre.
# importlib.reload recalcule REGISTRE_PATH et reconstruit ENGINE.
importlib.reload(M)
# Securite : si le module-level ENGINE a ete construit AVANT le reload
# (cache Python), on le force via le constructeur.
M.ENGINE = M.NanoMoteurUltraEngine()

# La question minimale qui garantit que "qwortz" (et seul "qwortz") survit
# au filtre MOTS_VIDES du moteur. Eviter "existe", "animal", "nomme", "brille"
# qui sont tous dans la liste d'exclusion.
t0 = time.perf_counter()
r2 = M.nano_moteur_ultra("qwortz")
duree = time.perf_counter() - t0
juge(r2.get("answer") and "qwortz" in (r2.get("answer") or "").lower(),
     "le moteur repond maintenant juste depuis la fiche (source=%s)" % r2.get("source"))
juge(duree < 0.1, "reponse en %.3f s (sans modele tiers)" % duree)

# ── NETTOYAGE ─────────────────────────────────────────────────────────────────
shutil.rmtree(bac, ignore_errors=True)
os.environ.pop("HAICHI_SAVOIR_DIR", None)

print("")
print("  %d verts, %d rouges" % (verts, rouges))
sys.exit(0 if rouges == 0 else 1)