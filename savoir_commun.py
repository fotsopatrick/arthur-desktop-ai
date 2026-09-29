#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAVOIR COMMUN — les petits mots partages par veilleur_savoir et garde_savoir.

Une seule source de verite pour transformer un texte en liste de mots-cles :
quand le veilleur construit une fiche et que le garde la compare a l'existant,
ils doivent RANGER LES MOTS DE LA MEME FAÇON, sinon le plus petit decalage
fait dire « contredit » a tort (ou « accepte » a tort). C'est le seul fichier
a toucher si on veut changer ce rangement.
"""
import re
import time
from datetime import date as _date

MOTS_VIDES = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "c", "s", "n",
    "et", "ou", "a", "au", "aux", "en", "par", "pour", "sur", "dans", "avec",
    "est", "ce", "cet", "cette", "que", "qu", "qui", "quoi", "quel", "quelle",
    "comment", "pourquoi", "quand", "je", "tu", "il", "elle", "on", "nous",
    "vous", "ils", "elles", "me", "te", "se", "moi", "toi", "mon", "ma",
    "mes", "ton", "ta", "tes", "son", "sa", "ses", "notre", "votre", "leurs",
    "pas", "ne", "plus", "tout", "tous", "toute", "toutes", "y",
    "fait", "faire", "dis", "dit", "veux", "peux", "peut", "sais", "sait",
    "existe", "trouve", "nomme", "nom", "appelle", "appelle", "brille", "animal",
}


def mots_depuis(texte):
    """Decoupe un texte en mots-cles propres : minuscules, sans ponctuation,
    sans les mots vides, sans doublon, dans l'ordre d'apparition."""
    morceaux = re.split(r"[^A-Za-zÀ-ÿ0-9]+", (texte or "").lower())
    vus = []
    for m in morceaux:
        if m and m not in MOTS_VIDES and m not in vus:
            vus.append(m)
    return vus


# Grades de fiabilite par type de source, du plus sur au moins sur.
# La date fraiche apporte +0.1 (sous 30 jours). Tout est borne a 1.0.
_GRADES_SOURCE = [
    ("gouv", 1.0), ("ministere", 1.0), ("insee", 1.0), ("banque mondiale", 1.0),
    ("noaa", 1.0), ("wmo", 1.0), ("pubmed", 1.0), ("census", 1.0),
    ("faostat", 1.0), ("tour", 0.9), ("odoo", 0.9), ("vitrine", 0.9),
    ("wiki", 0.8), ("kaggle", 0.85), ("geonames", 0.85),
    ("wikipedia", 0.8), ("etude", 0.7), ("journal", 0.7), ("article", 0.6),
]


def confiance_sur(source, date_capture):
    """Score deterministe (0.0 a 1.0) d'une fiche selon sa source et sa date.

    Sert au mur de confiance : quand deux fiches se contredisent, la plus
    fiable l'emporte. Pas une opinion : une fonction pure, testable.
    """
    s = (source or "").lower()
    base = 0.5
    trouve = False
    # (29/09) Un marqueur cherche comme simple sous-chaine se trichait :
    # « http://evil.example/gouv » obtenait 1.0. Pour une URL, seul le NOM
    # DE DOMAINE compte (data.gouv.fr -> gouv) ; pour un texte libre, le
    # marqueur doit etre un mot entier (« ministere de ... »).
    hote = ""
    if "://" in s:
        from urllib.parse import urlparse
        hote = (urlparse(s).hostname or "")
    etiquettes = set(hote.split(".")) if hote else set()
    for marqueur, grade in _GRADES_SOURCE:
        if hote:
            bon = marqueur in etiquettes
        else:
            bon = re.search(r"(?<!\w)" + re.escape(marqueur) + r"(?!\w)", s) is not None
        if bon:
            base, trouve = grade, True
            break
    if not trouve:
        # URL web et "site" : plausible mais sans grade reconnu.
        base = 0.6 if ("http" in s or "www" in s or "site" in s or "." in s) else 0.5

    bonus = 0.0
    try:
        champ = (str(date_capture or "") + "T00:00:00")[:10]
        y, m, d = (int(x) for x in champ.split("-"))
        aujourd = _date(*time.localtime()[:3])
        age = (aujourd - _date(y, m, d)).days
        if 0 <= age <= 30:
            bonus = 0.1
    except Exception:
        pass
    return round(min(1.0, base + bonus), 2)