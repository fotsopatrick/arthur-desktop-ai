# -*- coding: utf-8 -*-
"""GREFFON VEILLE — trois morceaux de la page Observatoire Uatu entrent dans Arthur.

Ne le 27/09/2026 (demande de Patrick : que nos projets IA utilisent les
parties d'Uatu qui peuvent y entrer). Pour Arthur, trois morceaux :
  - la matrice Beelzebuth & Sage : « a quoi Nvidia est expose ? »
  - les grands actionnaires       : « qui detient Apple ? »
  - les medias                    : « ou lire les nouvelles de la bourse ? »

Les fiches viennent de veille.json, copie de la page du cockpit. Elles sont
ecrites a la main : Arthur le DIT a chaque reponse, et ne comble jamais un
trou (« aucune trace de X dans les N fiches que j'ai lues »).
"""
import json
import os
import re
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
AVERTI = "(Fiches de veille écrites à la main dans le cockpit, pas des mesures.)"


def _n(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9&]+", " ", t).strip()


def _fiches():
    with open(os.path.join(ICI, "veille.json"), encoding="utf-8") as f:
        return json.load(f)


def _geants(v):
    noms = set()
    for m in v["matrice"]:
        noms.update(g.strip() for g in m["geants"].split(",") if g.strip())
    return noms


def _nom_dans(question, noms):
    q = f" {_n(question)} "
    trouves = [n for n in noms if f" {_n(n)} " in q]
    return max(trouves, key=len) if trouves else None


def _sujet_libre(question):
    """Le mot en majuscule que la question nomme, meme s'il n'est dans aucune fiche."""
    mots = re.findall(r"\b([A-Z][\w&.-]+(?:\s+[A-Z][\w&.-]+)*)", question)
    mots = [m for m in mots if _n(m) not in ("a", "qui", "ou", "quels", "quelles", "quel")]
    return mots[-1] if mots else "cette entreprise"


def exposition(question, v):
    nom = _nom_dans(question, _geants(v))
    if not nom:
        return (f"Aucune trace de {_sujet_libre(question)} parmi les géants des {len(v['matrice'])} fiches "
                f"de la matrice que j'ai lues. {AVERTI}")
    crises = [m for m in v["matrice"] if _n(nom) in [_n(g) for g in m["geants"].split(",")]]
    lignes = [f"- {m['probleme']} ({m['criticite']}) : {m.get('impactGeants') or m.get('impact', '')} "
              f"Sage : {m['analyseSage']} Protocole Beelzebuth : {m['protocoleBeelzebuth']}" for m in crises]
    return f"{nom} est exposé(e) à {len(crises)} crise(s) :\n" + "\n".join(lignes) + f"\n{AVERTI}"


def actionnaires(question, v):
    noms = _geants(v) | {m for c in v["capitaux"] for m in re.findall(r"[A-Z][\w&.-]+", c.get("actionnariat", ""))}
    nom = _nom_dans(question, noms)
    if not nom:
        return f"Aucune trace de {_sujet_libre(question)} dans les {len(v['capitaux'])} fiches d'actionnaires. {AVERTI}"
    qui = [c for c in v["capitaux"] if f" {_n(nom)} " in f" {_n(c.get('actionnariat', '') + ' ' + c.get('desc', ''))} "]
    if not qui:
        return f"Aucune des {len(v['capitaux'])} fiches d'actionnaires ne cite {nom}. {AVERTI}"
    return (f"Les fiches citent {len(qui)} grand(s) détenteur(s) de {nom} :\n"
            + "\n".join(f"- {c['nom']} ({c['type']}, {c['pays']}) : {c['actionnariat']}. Mise à jour : {c['frequence']}."
                        for c in qui[:5]) + f"\n{AVERTI}")


def medias(question, v):
    q = _n(question)
    secteur = ("bourse" if re.search(r"\b(bourse|marche|marches|finance|action|actions)\b", q) else
               "tech" if re.search(r"\b(tech|it|ia|informatique|numerique)\b", q) else "")
    liste = [m for m in v["medias"] if not secteur or secteur in _n(m["secteur"])] or v["medias"]
    liste.sort(key=lambda m: m.get("acces") != "open")
    return ("Où lire, d'après les fiches médias (accès libre d'abord) :\n"
            + "\n".join(f"- {m['nom']} ({m['secteur']}, accès {m['acces']}) : {m['vitesse']}." for m in liste[:5])
            + f"\n{AVERTI}")


def repondre(question, reglages):
    v = _fiches()
    q = _n(question)
    if re.search(r"\b(detient|detiennent|actionnaire|actionnaires|possede)\b", q):
        return actionnaires(question, v)
    if re.search(r"\b(ou lire|medias?)\b", q):
        return medias(question, v)
    if re.search(r"\b(crises systemiques|matrice)\b", q) and not re.search(r"\bexpos", q):
        crit = [p for p in v["problemes"] if p["criticite"] == "Critique"]
        return (f"{len(v['problemes'])} crises suivies, dont {len(crit)} critiques :\n"
                + "\n".join(f"- {p['titre']}" for p in crit) + f"\n{AVERTI}")
    return exposition(question, v)
