#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LES GREFFONS DE HACHI — ce qu'on lui ajoute sans toucher a son cerveau.

Ne le 16/09/2026, d'une demande de Patrick : « les gens doivent pouvoir le
customiser ». Et d'un exemple qui a tout declenche : un concours exigeait
d'envoyer des messages WhatsApp, et j'avais repondu « laisse tomber ».
Sa reponse : « ne pas prendre les problemes comme des murs infranchissables
mais comme nous meme on le dit : des portes, pas un mur — il nous faut juste
la clef. » Le greffon EST la clef.

COMMENT C'EST FAIT, ET POURQUOI C'EST SIMPLE.
Un greffon, c'est un dossier avec deux fichiers :

    greffons/whatsapp/greffon.json    sa fiche : son nom, ses mots, allume ou non
    greffons/whatsapp/greffon.py      son travail : une seule fonction

La fiche ressemble a ca :

    {"nom": "whatsapp", "titre": "Envoyer un message WhatsApp",
     "mots": ["whatsapp", "envoie un message"], "allume": false,
     "reglages": {"numero": ""}}

Le programme ne contient qu'UNE fonction :

    def repondre(question, reglages):
        return "ce que Hachi doit dire"

CINQ REGLES, toutes nees d'une faute deja payee ailleurs dans ce projet :

  1. UN GREFFON ETEINT N'EXISTE PAS. Il n'est meme pas charge.
  2. UN GREFFON QUI PLANTE NE CASSE PAS HACHI. On attrape sa chute, on le dit,
     et Hachi continue. Un moteur muet bloque toute la file — deja paye.
  3. LES REGLES DE HACHI PASSENT D'ABORD. Un greffon ne vole jamais la place
     d'une reponse que Hachi connait deja.
  4. LES MOTS ENTIERS, JAMAIS LES MORCEAUX. « tour » est ecrit dans
     « detournement » : cette faute a fait repondre le cycle du virus du sida
     a la question « qu'est-ce que la tour ». On ne la refera pas ici.
  5. UN GREFFON NE COUTE RIEN QUAND IL NE SERT PAS. On relit les fiches au
     plus une fois par seconde, pas a chaque question.
"""
import importlib.util
import json
import os
import re
import time
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER_PAR_DEFAUT = os.path.join(ICI, "greffons")

# on garde les fiches en memoire une seconde, pour ne pas relire le disque
# a chaque question. Mesure du 16/09/2026 : sans ca, 200 questions coutaient
# 200 lectures de dossier pour rien.
_CACHE = {"quand": 0.0, "dossier": None, "greffons": []}
_DUREE_CACHE = 1.0


def _normaliser(texte):
    t = unicodedata.normalize("NFD", str(texte or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _mots(texte):
    return [m for m in _normaliser(texte).split(" ") if m]


def lister(dossier=None, relire=False):
    """Rend la liste des greffons poses, allumes ou non."""
    dossier = dossier or DOSSIER_PAR_DEFAUT
    maintenant = time.time()
    if (not relire and _CACHE["dossier"] == dossier
            and maintenant - _CACHE["quand"] < _DUREE_CACHE):
        return _CACHE["greffons"]

    trouves = []
    if os.path.isdir(dossier):
        for nom in sorted(os.listdir(dossier)):
            d = os.path.join(dossier, nom)
            fiche = os.path.join(d, "greffon.json")
            if not os.path.isdir(d) or not os.path.exists(fiche):
                continue
            try:
                f = json.load(open(fiche, encoding="utf-8"))
            except Exception as e:
                trouves.append({"nom": nom, "titre": nom, "mots": [],
                                "allume": False, "reglages": {},
                                "dossier": d, "fiche_cassee": str(e)[:80]})
                continue
            f.setdefault("nom", nom)
            f.setdefault("titre", nom)
            f.setdefault("mots", [])
            f.setdefault("allume", False)
            f.setdefault("reglages", {})
            f["dossier"] = d
            trouves.append(f)

    _CACHE.update({"quand": maintenant, "dossier": dossier, "greffons": trouves})
    return trouves


def _charger_le_programme(greffon):
    chemin = os.path.join(greffon["dossier"], "greffon.py")
    if not os.path.exists(chemin):
        return None
    spec = importlib.util.spec_from_file_location(
        "greffon_" + greffon["nom"], chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _correspond(question_mots, greffon):
    """Les mots du greffon sont-ils dans la question ? MOTS ENTIERS seulement."""
    for cle in greffon.get("mots", []):
        morceaux = _mots(cle)
        if not morceaux:
            continue
        if all(m in question_mots for m in morceaux):
            return cle
    return None


def essayer(question, dossier=None):
    """Un greffon sait-il repondre ? Rend un dictionnaire, ou None.

    Le dictionnaire contient : greffon, titre, reponse, mot, et panne si le
    greffon est tombe.
    """
    greffons = lister(dossier)
    if not greffons:
        return None
    qm = _mots(question)
    if not qm:
        return None

    for g in greffons:
        if not g.get("allume"):
            continue                    # regle 1 : un greffon eteint n'existe pas
        mot = _correspond(qm, g)
        if not mot:
            continue
        try:
            module = _charger_le_programme(g)
            if module is None or not hasattr(module, "repondre"):
                return {"greffon": g["nom"], "titre": g.get("titre", g["nom"]),
                        "mot": mot, "reponse": None,
                        "panne": "ce greffon n'a pas de fonction « repondre »"}
            reponse = module.repondre(question, g.get("reglages", {}))
            return {"greffon": g["nom"], "titre": g.get("titre", g["nom"]),
                    "mot": mot, "reponse": reponse, "panne": None}
        except Exception as e:           # regle 2 : sa chute ne casse pas Hachi
            return {"greffon": g["nom"], "titre": g.get("titre", g["nom"]),
                    "mot": mot, "reponse": None, "panne": str(e)[:160]}
    return None


def basculer(nom, allume, dossier=None):
    """Allume ou eteint un greffon. Rend True si c'est fait."""
    dossier = dossier or DOSSIER_PAR_DEFAUT
    fiche = os.path.join(dossier, nom, "greffon.json")
    if not os.path.exists(fiche):
        return False
    f = json.load(open(fiche, encoding="utf-8"))
    f["allume"] = bool(allume)
    json.dump(f, open(fiche, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    _CACHE["quand"] = 0.0               # on oublie ce qu'on savait
    return True


def regler(nom, reglages, dossier=None):
    """Change les reglages d'un greffon (un numero, une cle, un chemin)."""
    dossier = dossier or DOSSIER_PAR_DEFAUT
    fiche = os.path.join(dossier, nom, "greffon.json")
    if not os.path.exists(fiche):
        return False
    f = json.load(open(fiche, encoding="utf-8"))
    f.setdefault("reglages", {}).update(reglages or {})
    json.dump(f, open(fiche, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    _CACHE["quand"] = 0.0
    return True


if __name__ == "__main__":
    for g in lister():
        etat = "allume" if g.get("allume") else "eteint"
        print(f"  [{etat:>6}] {g['nom']:<16} {g.get('titre','')}")
