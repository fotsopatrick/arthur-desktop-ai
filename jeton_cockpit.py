#!/usr/bin/env python3
"""Le jeton du cockpit (24/09/2026).

Depuis le 23/09, le cockpit refuse toute action POST sans l'en-tête
X-Cockpit-Token (protection CSRF). Arthur — son avatar, ses épreuves — ne
l'envoyait pas : chaque question revenait en 401, et Arthur se taisait.

Le jeton se lit, dans l'ordre :
  1. la variable d'environnement COCKPIT_TOKEN ;
  2. le fichier .env du cockpit (COCKPIT_ENV, sinon ~/cockpit-generique/.env).
Il n'est jamais affiché ni écrit ailleurs.
"""
import os

JSON = {"Content-Type": "application/json"}


def jeton():
    j = os.environ.get("COCKPIT_TOKEN", "").strip()
    if j:
        return j
    chemin = os.environ.get("COCKPIT_ENV") or os.path.expanduser("~/cockpit-generique/.env")
    try:
        with open(chemin, encoding="utf-8") as f:
            for ligne in f:
                cle, _, valeur = ligne.strip().partition("=")
                if cle.strip() == "COCKPIT_TOKEN":
                    return valeur.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def entetes():
    """Les en-têtes d'un POST JSON vers le cockpit, jeton compris s'il existe."""
    e = dict(JSON)
    j = jeton()
    if j:
        e["X-Cockpit-Token"] = j
    return e
