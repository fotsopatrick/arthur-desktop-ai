#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA SYNCHRO ALICE -> NANO (synchro_alice_vers_nano.py).

Ce qu'on prouve, dans un bac a sable (jamais le vrai registre) :
  - les mots sont normalises (accents, ponctuation, mots courts) ;
  - circuits, garde-fous et lecons exportes entrent dans le registre ;
  - sur un clone neuf, on part du registre d'exemple, pas d'un registre vide ;
  - rien a fusionner : le registre n'est pas touche ;
  - un registre illisible ARRETE tout — il n'est jamais remplace par {}.
"""
import json
import os
import shutil
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import synchro_alice_vers_nano as S  # noqa: E402


@pytest.fixture()
def bac(tmp_path, monkeypatch):
    """ICI, REGISTRE_PATH et DONNEES_DIR pointent dans un dossier jetable."""
    ici = tmp_path / "depot"
    donnees = tmp_path / "donnees"
    ici.mkdir()
    donnees.mkdir()
    monkeypatch.setattr(S, "ICI", str(ici))
    monkeypatch.setattr(S, "REGISTRE_PATH", str(ici / "registre_connaissances.json"))
    monkeypatch.setattr(S, "DONNEES_DIR", str(donnees))
    return ici, donnees


def _ecrire(chemin, obj):
    chemin.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _registre(ici):
    return json.loads((ici / "registre_connaissances.json").read_text(encoding="utf-8"))


def test_normaliser_mots_accents_ponctuation_mots_courts():
    """Accents enleves, ponctuation coupee, mots de 2 lettres ou moins ecartes."""
    mots = S.normaliser_mots("Éléphant, à l'île — où ça? Forêt forêt Côté")
    assert sorted(mots) == ["cote", "elephant", "foret", "ile"]
    assert S.normaliser_mots(None) == []
    assert S.normaliser_mots("") == []


def test_fusion_des_trois_sources(bac, capsys):
    """Circuits, garde-fous et lecons entrent, au bon format, avec leurs cles."""
    ici, donnees = bac
    _ecrire(ici / "registre_connaissances.json",
            {"ancien": {"mots": ["garde"], "think": "t", "answer": "a"}})
    _ecrire(donnees / "circuits.json", [
        {"id": 7, "nom": "Sauvegarde nocturne", "description": "copie des disques"},
        {"code": "C2", "name": "Relance", "detail": "redemarre le service"},
        {"id": "x"},                       # nom et detail par defaut : assez de mots
        {"id": "court", "nom": "a", "description": "b"},  # < 2 mots : ecarte
    ])
    _ecrire(donnees / "garde-fous.json", [
        {"nom": "Jamais bannir", "detail": "verifier son adresse"},
        {"titre": "Pas de secret", "regle": "ne jamais lire une clef"},
        {},
    ])
    _ecrire(donnees / "lecons.json", [
        {"titre": "Montrer la video", "detail": "une page web"},
        {"sujet": "Boutons verts", "contenu": "plus de commandes"},
        {},
    ])
    S.fusionner()
    r = _registre(ici)
    assert "ancien" in r
    assert {"circuit_7", "circuit_C2", "circuit_x"} <= set(r)
    assert "circuit_court" not in r
    assert "Sauvegarde nocturne" in r["circuit_7"]["answer"]
    assert "copie des disques" in r["circuit_7"]["answer"]
    assert "Circuit d'Alice." in r["circuit_x"]["answer"]
    assert set(r["circuit_C2"]["mots"]) >= {"relance", "redemarre", "service"}
    assert "Jamais bannir" in r["garde_fou_0"]["answer"]
    assert "ne jamais lire une clef" in r["garde_fou_1"]["answer"]
    assert "Garde-Fou 2" in r["garde_fou_2"]["think"]
    assert "Montrer la video" in r["lecon_0"]["answer"]
    assert "plus de commandes" in r["lecon_1"]["answer"]
    assert "Leçon apprise." in r["lecon_2"]["answer"]
    for cle in ("circuit_7", "garde_fou_0", "lecon_0"):
        assert set(r[cle]) == {"mots", "think", "answer"}
    assert "FUSION RÉUSSIE" in capsys.readouterr().out


def test_clone_neuf_part_du_registre_exemple(bac):
    """Pas de registre : on part de registre_exemple.json et on y ajoute."""
    ici, donnees = bac
    shutil.copy(os.path.join(REPO, "registre_exemple.json"), ici / "registre_exemple.json")
    exemple = json.load(open(os.path.join(REPO, "registre_exemple.json"), encoding="utf-8"))
    assert "lecon_0" in exemple and "circuit_neuf" not in exemple
    _ecrire(donnees / "lecons.json", [{"titre": "Toujours tester", "detail": "avant de livrer"}])
    _ecrire(donnees / "circuits.json", [{"id": "neuf", "nom": "Circuit neuf", "detail": "tout frais"}])
    S.fusionner()
    r = _registre(ici)
    assert set(exemple) <= set(r)
    assert len(r) == len(exemple) + 1          # seul circuit_neuf est nouveau
    assert "Toujours tester" in r["lecon_0"]["answer"]   # re-synchro : remplace
    assert r["salutations"] == exemple["salutations"]


def test_clone_neuf_sans_exemple_part_de_rien(bac):
    """Ni registre ni exemple : le registre ecrit ne contient que la fusion."""
    ici, donnees = bac
    _ecrire(donnees / "garde-fous.json", [{"nom": "Mur solide", "detail": "refuse tout"}])
    S.fusionner()
    assert list(_registre(ici)) == ["garde_fou_0"]


def test_rien_a_fusionner_ne_touche_pas_le_registre(bac, capsys):
    """Aucune donnee : message clair, registre ni cree ni modifie."""
    ici, donnees = bac
    S.fusionner()
    assert not (ici / "registre_connaissances.json").exists()
    assert "Rien a fusionner" in capsys.readouterr().out

    _ecrire(ici / "registre_connaissances.json", {"a": 1})
    avant = (ici / "registre_connaissances.json").stat().st_mtime_ns
    _ecrire(donnees / "circuits.json", [{"id": 1, "nom": "a", "description": "b"}])
    S.fusionner()
    assert (ici / "registre_connaissances.json").stat().st_mtime_ns == avant
    assert _registre(ici) == {"a": 1}


def test_registre_illisible_arrete_tout_sans_rien_effacer(bac):
    """Registre abime : la fusion leve une erreur, le fichier reste intact."""
    ici, donnees = bac
    abime = '{"ancien": {"mots": ["a"'
    (ici / "registre_connaissances.json").write_text(abime, encoding="utf-8")
    _ecrire(donnees / "lecons.json", [{"titre": "Toujours tester", "detail": "avant"}])
    with pytest.raises(ValueError):
        S.fusionner()
    assert (ici / "registre_connaissances.json").read_text(encoding="utf-8") == abime


def test_donnees_depuis_l_environnement(tmp_path):
    """SYNCHRO_DONNEES choisit le dossier des donnees au chargement du module."""
    import subprocess
    code = "import synchro_alice_vers_nano as S; print(S.DONNEES_DIR)"
    e = dict(os.environ, SYNCHRO_DONNEES=str(tmp_path), HOME=str(tmp_path))
    r = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=e,
                       capture_output=True, text=True, timeout=30)
    assert r.stdout.strip() == str(tmp_path)
