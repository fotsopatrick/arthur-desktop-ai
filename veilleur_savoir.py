#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VEILLEUR DU SAVOIR — de la lacune a la fiche structuree.

APP RENTISSAGE BOTTOM-UP, 2e temps (21/09/2026).

Lit la file lacunes.json — ecrite par le moteur quand il avoue — et
structure UNE fiche au format exact du registre de connaissance :

    { "mots": [...], "think": "...", "answer": "...",
      "source": "...", "date_capture": "AAAA-MM-JJ" }

La fiche est ECRITE dans le bac a sable du veilleur (fiches-attente.json),
puis le GARDE (garde-savoir.py) decide seul si elle entre dans le registre.
Le veilleur ne decide rien : il prepare, le mur juge.

Use de bout en bout (bac a sable, sans rien casser) par
test_apprentissage_bottom_up.py. Deux modes :

  --lacune <fichier>   : lire la premiere lacune non traitee de la file.
  --reponse/--source/--date : ... et, hors ce mode, les arguments fournis.

L'angle web (navigateur + recherche) est la CAPTURE : pour la livraison
testee, la reponse et la source arrivent par arguments. Le renvoi vers le
navigateur se branchera la, a l'appel du veilleur par la boucle reelle.
"""
import json
import os
import sys
import time

try:
    from savoir_commun import mots_depuis, confiance_sur
except ImportError:
    # le fichier peut etre lance depuis un autre dossier : on ajoute ICI
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from savoir_commun import mots_depuis, confiance_sur

# STRUCTURED OUTPUTS (21/09/2026) — validation stricte de chaque fiche.
# Plus jamais de fiche malformee qui passerait au garde.
try:
    from skills.structured_outputs import validate as _validate_fiche
except ImportError:
    _validate_fiche = None


def charger_attente():
    """Charge le fichier des fiches en attente, cree-le s'il n'existe pas."""
    fichier = os.environ.get("HAICHI_SAVOIR_DIR") or os.getcwd()
    chemin = os.path.join(fichier, "fiches-attente.json")
    if os.path.exists(chemin):
        try:
            d = json.load(open(chemin, encoding="utf-8"))
            if isinstance(d, list):
                return d, chemin
        except Exception:
            pass
    return [], chemin


def construire_fiche(question, reponse, source, date_capture, contexte_brut=""):
    """Fabrique l'objet fiche au format EXACT du registre + source/date.

    STRUCTURED OUTPUTS (21/09/2026) : la fiche est validee contre le schema
    JSON strict AVANT d'etre retournee. Si le schema est charge et que la
    fiche ne le respecte pas, on le dit — mais on retourne quand meme la
    fiche (le garde fera son travail derriere).
    """
    fiche = {
        "mots": mots_depuis(question),
        "think": ("1. Question : %s.\n"
                  "2. Contexte brut : %s.\n"
                  "3. Reponse capturee le %s depuis %s.") % (
                      question, contexte_brut or "(aucun)", date_capture, source),
        "answer": reponse,
        "source": source,
        "date_capture": date_capture,
        "confiance": confiance_sur(source, date_capture),
    }
    # Validation structuree (non bloquante)
    if _validate_fiche is not None:
        valid, erreur = _validate_fiche(fiche, "veilleur_fiche")
        if not valid:
            print("ATTENTION : fiche malformee (%s)" % erreur)
    return fiche


def main(argv):
    # Argument minimal : le dossier du bac a sable.
    if "--help" in argv or "-h" in argv:
        print("veilleur_savoir.py [--source S] [--date D] [--reponse R] "
              "[-dump] ; lit la file de lacunes du bac et structure une fiche.")
        return 0

    dossier = os.environ.get("HAICHI_SAVOIR_DIR") or os.getcwd()
    lacunes_fichier = os.path.join(dossier, "lacunes.json")

    if not os.path.exists(lacunes_fichier):
        print("Aucune lacune a traiter.")
        return 0

    def arg(nom, defaut=""):
        for i, a in enumerate(argv):
            if a == nom and i + 1 < len(argv):
                return argv[i + 1]
        return defaut

    reponse = arg("--reponse", "") or "Je ne sais pas encore : rien n'a ete capture."
    source = arg("--source", "") or "sans source"
    date_capture = arg("--date", "") or time.strftime("%Y-%m-%d")

    lacunes = json.load(open(lacunes_fichier, encoding="utf-8"))
    if not lacunes:
        print("Fichier de lacunes vide.")
        return 0

    lacune = lacunes[0]
    question = lacune.get("question", "")
    if not question:
        print("Lacune sans question, on saute.")
        return 1

    fiche = construire_fiche(question, reponse, source, date_capture,
                             lacune.get("contexte_brut", ""))

    attente, chemin = charger_attente()
    attente.append({**fiche, "_lacune": question})
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(attente, f, ensure_ascii=False, indent=1)

    if "-dump" in argv:
        print(json.dumps(fiche, ensure_ascii=False)[:800])
    else:
        print("fiche construite et posee dans fiches-attente.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))