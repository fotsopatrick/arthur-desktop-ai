# -*- coding: utf-8 -*-
"""qualite/traceur.py — QUELLES LIGNES D'ARTHUR ONT TOURNE ?

Un traceur de lignes ecrit avec la seule bibliotheque standard (sys.settrace) :
rien a installer, rien qui depende du systeme. Il ne suit QUE le code
d'Arthur (le depot, hors tests, vendor/, archive/ et qualite/) : le reste
est ignore des le premier appel, pour aller vite.

Il est demarre par qualite/amorce/sitecustomize.py dans chaque processus
Python lance par le lanceur — y compris les sous-processus que les tests
lancent eux-memes (serveur MCP, garde-savoir...). A la sortie du processus,
il ecrit ce qu'il a vu dans ARTHUR_COUV_DOSSIER :
    {"test": "<fichier de test>", "lignes": {"<fichier>": [n, ...]}}
"""
import atexit
import json
import os
import sys
import threading

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXCLUS = tuple(os.path.join(RACINE, d) + os.sep
                for d in ("tests", "vendor", "archive", "qualite", ".git"))

_vus = {}           # fichier -> set(lignes)
_garder = {}        # co_filename -> set(lignes) ou None (a ignorer)


def fichier_suivi(chemin):
    """Vrai si ce fichier fait partie du code d'Arthur a mesurer."""
    chemin = os.path.abspath(chemin)
    if not chemin.startswith(RACINE + os.sep) or not chemin.endswith(".py"):
        return False
    if chemin.startswith(_EXCLUS):
        return False
    nom = os.path.basename(chemin)
    return not (nom.startswith("test_") or nom == "conftest.py")


def _ensemble(co_filename):
    try:
        return _garder[co_filename]
    except KeyError:
        s = _vus.setdefault(os.path.abspath(co_filename), set()) \
            if fichier_suivi(co_filename) else None
        _garder[co_filename] = s
        return s


def _local(frame, event, arg):
    if event == "line":
        s = _garder.get(frame.f_code.co_filename)
        if s is not None:
            s.add(frame.f_lineno)
    return _local


def _global(frame, event, arg):
    s = _ensemble(frame.f_code.co_filename)
    if s is None:
        return None                      # pas du code d'Arthur : on ne suit pas
    s.add(frame.f_lineno)
    return _local


def demarrer():
    sys.settrace(_global)
    threading.settrace(_global)
    atexit.register(ecrire)


def ecrire():
    dossier = os.environ.get("ARTHUR_COUV_DOSSIER")
    if not dossier or not _vus:
        return
    try:
        os.makedirs(dossier, exist_ok=True)
        nom = "%d-%d.json" % (os.getpid(), threading.get_ident())
        with open(os.path.join(dossier, nom), "w", encoding="utf-8") as f:
            json.dump({"test": os.environ.get("ARTHUR_COUV_TEST", "?"),
                       "lignes": {k: sorted(v) for k, v in _vus.items() if v}}, f)
    except OSError:
        pass                              # la mesure ne doit jamais casser un test
