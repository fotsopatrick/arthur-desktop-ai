#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ecriture_sure.py — lire et ecrire les fichiers JSON d'Arthur sans jamais
les abimer.

Ne le 29/09/2026, pendant la revue de code. Le registre, la file des lacunes,
les reglages et la quarantaine etaient reecrits « en place » : un plantage au
milieu de l'ecriture laissait un fichier a moitie ecrit, et un fichier
illisible etait souvent remplace par un fichier vide — le savoir disparaissait
sans bruit.

Deux regles, ici et nulle part ailleurs :
  1. on ecrit a cote, puis on remplace d'un seul geste (os.replace) ;
  2. un fichier qui existe mais ne se lit pas n'est JAMAIS traite comme vide :
     on leve FichierAbime, et c'est l'appelant qui decide (s'arreter, le dire).
"""
import json
import os
import tempfile


class FichierAbime(Exception):
    """Le fichier existe, mais son contenu n'est pas du JSON lisible."""


def lire_json(chemin, defaut=None):
    """Le contenu du fichier ; `defaut` s'il n'existe pas ; FichierAbime s'il
    existe mais ne se lit pas."""
    if not os.path.exists(chemin):
        return defaut
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise FichierAbime("%s ne se lit pas : %s" % (chemin, e)) from e


def ecrire_json(chemin, donnees, indent=1):
    """Ecriture atomique : fichier temporaire dans le meme dossier, puis
    os.replace. Les droits du fichier d'origine sont gardes."""
    dossier = os.path.dirname(os.path.abspath(chemin))
    os.makedirs(dossier, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dossier, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=indent)
        try:
            os.chmod(tmp, os.stat(chemin).st_mode)
        except OSError:
            os.chmod(tmp, 0o644)
        os.replace(tmp, chemin)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
