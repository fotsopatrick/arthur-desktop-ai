#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP APPRENDRE — apprendre un fait au moteur, mur de confiance compris.

Apprentissage bottom-up (H2, fiche déterministe, 22/09/2026). Un seul
appel pour TOUTE la boucle :
   1. le VEILLEUR structure la fiche au format exact du registre
      (mots -> answer + source + date_capture + confiance) ;
   2. le GARDE (garde-savoir.py, mur de confiance) refuse ou valide
      l'écriture dans le registre actif.

Le mur est réutilisé tel quel (le même binaire que la boucle réelle), jamais
dupliqué : mcp_learn dit ce que le mur a décidé, il ne décide pas à sa place.

Sortie JSON structurée :
  {
    "verdict": "valide" | "refuse",
    "raison": "...",
    "confiance": 0.0-1.0,
    "question": "...",
    "registre_cle": "apprentissage_..." (si valide)
  }

Usage :
  python skills/mcp_learn.py --question "..." --reponse "..." \
      --source "..." --date "AAAA-MM-JJ" [--json]
"""
import importlib.util
import json
import os
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)

if RACINE not in sys.path:
    sys.path.insert(0, RACINE)


def _charger_garde():
    """garde-savoir.py porte un tiret : import par chemin, module nomme."""
    chemin = os.path.join(RACINE, "garde-savoir.py")
    spec = importlib.util.spec_from_file_location("garde_savoir_module", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _charger_veilleur():
    from veilleur_savoir import construire_fiche
    return construire_fiche


def apprendre(question, reponse, source, date_capture):
    """Structure la fiche puis la soumet au mur. Rend le JSON-de-verdict.

    Le veilleur et le garde ecrivent du texte lisible sur stdout ("VALIDE",
    "REFUS", "ATTENTION"). Ici stdout porte le protocole : on redirige ces
    ecrits vers stderr le temps du jugement, puis on restaure."""
    try:
        construire_fiche = _charger_veilleur()
        garde = _charger_garde()
    except Exception as e:
        return {"verdict": "erreur", "raison": "chargement : %s" % str(e)[:120],
                "confiance": None, "question": question}

    fiche = construire_fiche(question, reponse, source, date_capture)

    stdout_sauve = sys.stdout

    def _muet():
        sys.stdout = sys.stderr

    try:
        _muet()
        registre, _ = garde._charger_registre()
        attente = garde._chemin("fiches-attente.json")
        code = garde.juger(fiche, registre, None, attente)
    except Exception as e:
        sys.stdout = stdout_sauve
        return {"verdict": "erreur", "raison": "mur : %s" % str(e)[:120],
                "confiance": fiche.get("confiance"), "question": question}
    finally:
        sys.stdout = stdout_sauve

    retour = {
        "verdict": "valide" if code == 0 else "refuse",
        "raison": "",
        "confiance": fiche.get("confiance"),
        "question": question.strip(),
    }
    if code != 0:
        raison = ""
        try:
            chemin = garde._chemin("quarantaine.json")
            if os.path.exists(chemin):
                quar = json.load(open(chemin, encoding="utf-8"))
                if quar:
                    raison = quar[-1].get("motif_refus", "")
        except Exception:
            raison = ""
        retour["raison"] = raison or "refuse par le mur de confiance"
    return retour


def main(argv):
    def arg(nom, defaut=""):
        for i, a in enumerate(argv):
            if a == nom and i + 1 < len(argv):
                return argv[i + 1]
        return defaut

    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0

    question = arg("--question")
    reponse = arg("--reponse")
    source = arg("--source")
    date_capture = arg("--date")
    if not question or not reponse or not source or not date_capture:
        print(json.dumps({"verdict": "erreur",
                          "raison": "question, reponse, source et date (AAAA-MM-JJ) obligatoires"},
                         ensure_ascii=False))
        return 2

    resultat = apprendre(question, reponse, source, date_capture)
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0 if resultat.get("verdict") == "valide" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))