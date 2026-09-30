# -*- coding: utf-8 -*-
"""Demarre le traceur de couverture d'Arthur dans CHAQUE processus Python que
lance le lanceur de tests (qualite/lancer.py), sous-processus compris.

Python charge tout seul un module « sitecustomize » trouve sur le chemin :
le lanceur met ce dossier en tete de PYTHONPATH. Sans ARTHUR_COUV_DOSSIER,
ce fichier ne fait rien.
"""
import os
import sys

if os.environ.get("ARTHUR_COUV_DOSSIER"):
    _qualite = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _qualite not in sys.path:
        sys.path.insert(0, _qualite)
    try:
        import traceur as _traceur
        _traceur.demarrer()
    except Exception:
        pass                  # la mesure ne doit jamais empecher un test de tourner
