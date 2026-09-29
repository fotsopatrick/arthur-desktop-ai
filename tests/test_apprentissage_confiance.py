#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests du mur de confiance — l'apprentissage bottom-up, format complet.

Apprentissage bottom-up (H2, fiche déterministe, 21-22/09/2026).
Toute nouvelle fiche-savoir porte (mots -> answer + source + date_capture
+ confiance). Le garde doit FORMELLEMENT la rejeter si la source n'est pas
datée, ou si elle contredit une fiche PLUS fiable.

jimmy : au ROUGE d'abord — ces exigences n'existent pas dans garde-savoir.py
(portes 1 et 2 sans comparaison de confiance, fiche sans champ confiance).
On écrit la preuve avant, on la voit échouer, puis on répare jusqu'au vert.

Le matériel travaille dans UN BAC À SABLE (HAICHI_SAVOIR_DIR), jamais dans le
vrai registre.
"""
import json
import os
import shutil
import sys
import tempfile
import importlib.util

HAICHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HAICHI)

import pytest

_garde_path = os.path.join(HAICHI, "garde-savoir.py")


def _charger_garde():  # garde-savoir.py porte un tiret : on le charge par chemin
    spec = importlib.util.spec_from_file_location("garde_savoir_module", _garde_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    G = _charger_garde()
    import veilleur_savoir as V
except Exception as e:  # pragma: no cover
    pytest.fail("imports du banc impossibles : %s" % e)


@pytest.fixture()
def sablier():
    """Registre de départ contrôlé dans un bac à sable jetable."""
    bac = tempfile.mkdtemp(prefix="confiance-bac-")
    registre = {
        "ocean": {
            "mots": ["plus", "grand", "ocean"],
            "think": "legacy",
            "answer": "L'Atlantique",
            "source": "",
            "date_capture": "",
        }
    }
    with open(os.path.join(bac, "registre_connaissances.json"), "w",
              encoding="utf-8") as f:
        json.dump(registre, f, ensure_ascii=False, indent=1)
    os.environ["HAICHI_SAVOIR_DIR"] = bac
    yield bac
    os.environ.pop("HAICHI_SAVOIR_DIR", None)
    shutil.rmtree(bac, ignore_errors=True)


def _registre(bac):
    with open(os.path.join(bac, "registre_connaissances.json"), encoding="utf-8") as f:
        return json.load(f)


def _quarantaine(bac):
    chemin = os.path.join(bac, "quarantaine.json")
    if not os.path.exists(chemin):
        return []
    return json.load(open(chemin, encoding="utf-8"))


def _juge(fiche, bac):
    registre, _ = G._charger_registre()
    return G.juger(fiche, registre, None, os.path.join(bac, "fiches-attente.json"))


# ══════════════════════════════════════════════════════════════════════════
# PORTE 1 — une fiche sans source datée est MOU
# ══════════════════════════════════════════════════════════════════════════

class TestSourceDatee:
    def test_fiche_sans_source_est_bloquee(self, sablier):
        fiche = {
            "mots": ["rhino", "doré"], "think": "", "answer": "rien",
            "source": "", "date_capture": "2026-09-22", "_lacune": "x",
        }
        assert _juge(fiche, sablier) != 0
        assert _quarantaine(sablier) != []

    def test_fiche_source_mal_datee_est_bloquee(self, sablier):
        fiche = {
            "mots": ["rhino", "doré"], "think": "", "answer": "rien",
            "source": "un site serieux", "date_capture": "", "_lacune": "x",
        }
        assert _juge(fiche, sablier) != 0
        assert _quarantaine(sablier) != []


# ══════════════════════════════════════════════════════════════════════════
# FORMAT COMPLET — une fiche saine porte confiance et est stockée AVEC
# ══════════════════════════════════════════════════════════════════════════

class TestFormatComplet:
    def test_fiche_validee_porte_les_quatre_attributs(self, sablier):
        fiche = {
            "mots": ["plus", "grand", "ocean"], "think": "capture",
            "answer": "Le Pacifique est le plus grand océan.",
            "source": "ministere de la transition ecologique",
            "date_capture": "2026-09-22", "_lacune": "ocean",
        }
        assert _juge(fiche, sablier) == 0
        entree = list(_registre(sablier).values())[-1]
        assert entree.get("source") == "ministere de la transition ecologique"
        assert entree.get("date_capture") == "2026-09-22"
        assert isinstance(entree.get("confiance"), (int, float))

    def test_fiche_construite_du_veilleur_porte_confiance(self):
        fiche = V.construire_fiche(
            "Quel est le plus grand ocean ?", "Le Pacifique",
            "geonames", "2026-09-22")
        confiance = fiche.get("confiance")
        assert confiance is not None
        assert 0.0 <= confiance <= 1.0


# ══════════════════════════════════════════════════════════════════════════
# PORTE 2b — la fiabilité départage la contradiction
# ══════════════════════════════════════════════════════════════════════════

class TestConfianceDepartage:
    def test_conflit_avec_fiche_plus_fiable_refuse(self, sablier):
        # La fiche en place est legacy (main humaine, fiable) : Atlantique.
        faible = {
            "mots": ["plus", "grand", "ocean"], "think": "",
            "answer": "Le Pacifique est le plus grand ocean.",
            "source": "un site poubelle", "date_capture": "2026-09-22",
            "_lacune": "ocean",
        }
        assert _juge(faible, sablier) != 0
        assert "fiable" in _quarantaine(sablier)[-1].get("motif_refus", "")
        assert _registre(sablier)["ocean"]["answer"].startswith("L'Atlantique")

    def test_conflit_avec_fiche_moins_fiable_surclasse(self, sablier):
        forte = {
            "mots": ["plus", "grand", "ocean"], "think": "source fiable surclasse",
            "answer": "Le Pacifique est le plus grand ocean.",
            "source": "ministere de la transition ecologique",
            "date_capture": "2026-09-22", "_lacune": "ocean",
        }
        assert _juge(forte, sablier) == 0
        registre = _registre(sablier)
        assert "ocean" not in registre
        valeurs = [v for v in registre.values()
                   if v.get("answer", "").startswith("Le Pacifique")]
        assert valeurs, "la fiche plus fiable doit surclasser la moins fiable"

    def test_conflit_a_egalite_refuse_la_nouvelle(self, sablier):
        # Sur l'existant legacy Atlantique (confiance 0.9), une source "tour"
        # ANCIENNE (au-dela de 30 jours, pas de bonus) tombe a 0.9 aussi :
        # pied d'egalite -> on ne remplace pas le connu sur un pied d'egalite.
        egale = {
            "mots": ["plus", "grand", "ocean"], "think": "",
            "answer": "Le Pacifique est le plus grand ocean.",
            "source": "tour", "date_capture": "2026-07-01",
            "_lacune": "ocean",
        }
        assert _juge(egale, sablier) != 0


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", __file__]))