#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le carnet des reponses : ne plus jamais reposer une question deja tranchee.

POURQUOI (17/09/2026). Patrick, excede :
  « j ai deja dit oui... ceci plein de fois »
  « pourquoi tu me reposes la question mille fois »
et la solution, c est lui qui la donne :
  « tu sais pas faire une sauvegarde tes questions => mes reponses »
puis :
  « des qu une reponse apparait tu la memorises dans ton historique »

Il avait raison sur les deux points : je reposais, et je n avais aucun
historique. Chaque question reposee lui coute du temps, et dit toujours la
meme chose : je n ai pas garde sa reponse.

CE QUE FAIT CE CARNET
  · il garde la question, sa reponse, et la date ;
  · il retrouve une reponse meme si la question est reformulee ;
  · une reponse qui change remplace l ancienne, sans faire grossir le carnet.

USAGE
  python3 carnet-des-reponses.py --noter "la question" "la reponse"
  python3 carnet-des-reponses.py --chercher "la question"
  python3 carnet-des-reponses.py --lire
"""
import json, pathlib, re, sys, unicodedata
from datetime import datetime

CARNET = pathlib.Path.home()/".claude"/"portes"/"carnet-des-reponses.json"

# Les mots qui ne portent pas de sens : ils changent d une fois sur l autre,
# et ne doivent pas empecher de reconnaitre la meme question.
MOTS_VIDES = {
    "je", "tu", "on", "le", "la", "les", "un", "une", "des", "du", "de", "a",
    "au", "aux", "et", "ou", "donc", "que", "qui", "quoi", "est", "ce", "ca",
    "sur", "dans", "pour", "avec", "sans", "par", "en", "y", "il", "elle",
    "maintenant", "alors", "aussi", "bien", "tout", "tous", "plus", "moins",
    "veux", "veut", "peux", "peut", "dois", "doit", "fais", "fait",
}


def _cle(question):
    """Rend la forme comparable d une question : sans accent, sans ponctuation,
    sans mots vides, mots ranges dans l ordre.

    Ainsi « Je pose la porte a une heure ? » et « JE POSE DONC LA PORTE A UNE
    HEURE » donnent la meme cle.
    """
    t = unicodedata.normalize("NFD", str(question or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    mots = [m for m in t.split() if m not in MOTS_VIDES and len(m) > 1]
    return " ".join(sorted(set(mots)))


def tout(chemin=None):
    chemin = pathlib.Path(chemin or CARNET)
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except Exception:
        return []


def noter(question, reponse, chemin=None):
    """Garde une reponse. Si la question existe deja, on remplace."""
    chemin = pathlib.Path(chemin or CARNET)
    carnet = tout(chemin)
    cle = _cle(question)
    for x in carnet:
        if x.get("cle") == cle:
            x["reponse"] = reponse
            x["quand"] = datetime.now().astimezone().isoformat(timespec="seconds")
            x["question"] = question
            break
    else:
        carnet.append({
            "cle": cle, "question": question, "reponse": reponse,
            "quand": datetime.now().astimezone().isoformat(timespec="seconds"),
        })
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(carnet, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    return reponse


def deja_repondu(question, chemin=None):
    """Rend la reponse deja donnee, ou None. Tolere les reformulations."""
    cle = _cle(question)
    if not cle:
        return None
    mots = set(cle.split())
    meilleur, score_max = None, 0
    for x in tout(chemin):
        siens = set(str(x.get("cle", "")).split())
        if not siens:
            continue
        if siens == mots:
            return x.get("reponse")
        # Une question reformulee garde l essentiel de ses mots.
        communs = len(mots & siens)
        score = communs / max(len(mots), len(siens))
        if score > score_max:
            meilleur, score_max = x, score
    return meilleur.get("reponse") if meilleur and score_max >= 0.7 else None


def raconter(chemin=None):
    carnet = tout(chemin)
    if not carnet:
        return "Aucune reponse gardee pour l instant."
    lignes = ["%d reponse(s) gardee(s) :\n" % len(carnet)]
    for x in carnet:
        lignes.append("  « %s »" % x.get("question", "?"))
        lignes.append("     -> %s   (%s)" % (x.get("reponse", "?"),
                                             str(x.get("quand", ""))[:16]))
    return "\n".join(lignes)


def main():
    a = sys.argv
    if "--noter" in a:
        i = a.index("--noter")
        print(noter(a[i + 1], a[i + 2]) and "Note.")
        return 0
    if "--chercher" in a:
        r = deja_repondu(a[a.index("--chercher") + 1])
        print(r if r else "(jamais repondu)")
        return 0
    if "--lire" in a:
        print(raconter())
        return 0
    print(__doc__.split("USAGE")[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
