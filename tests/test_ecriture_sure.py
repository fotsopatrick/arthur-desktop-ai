#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ECRITURE SURE (29/09/2026) — ecriture_sure.py.

Ce qu'on prouve, dans un dossier jetable :
  - un fichier absent rend la valeur par defaut ;
  - un fichier abime n'est JAMAIS traite comme vide : FichierAbime ;
  - l'ecriture est atomique : un plantage au milieu laisse l'ancien fichier
    intact, et aucun fichier temporaire ne traine ;
  - les droits du fichier d'origine sont gardes.
"""
import json
import os
import stat
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import ecriture_sure  # noqa: E402
from ecriture_sure import FichierAbime, ecrire_json, lire_json  # noqa: E402


def test_fichier_absent_rend_le_defaut(tmp_path):
    assert lire_json(str(tmp_path / "rien.json"), defaut=[]) == []
    assert lire_json(str(tmp_path / "rien.json")) is None


def test_aller_retour(tmp_path):
    chemin = str(tmp_path / "sous" / "dossier" / "a.json")   # dossier cree
    ecrire_json(chemin, {"ville": "Yaoundé", "n": [1, 2]})
    assert lire_json(chemin) == {"ville": "Yaoundé", "n": [1, 2]}
    assert "Yaoundé" in open(chemin, encoding="utf-8").read()   # pas d'echappement
    assert os.listdir(os.path.dirname(chemin)) == ["a.json"]


def test_fichier_abime_leve_fichier_abime(tmp_path):
    chemin = tmp_path / "abime.json"
    chemin.write_text("{ pas du json", encoding="utf-8")
    with pytest.raises(FichierAbime) as e:
        lire_json(str(chemin), defaut=[])
    assert "abime.json" in str(e.value)
    assert isinstance(e.value.__cause__, ValueError)


def test_un_dossier_a_la_place_du_fichier_est_abime(tmp_path):
    with pytest.raises(FichierAbime):
        lire_json(str(tmp_path))


def test_nouveau_fichier_en_644(tmp_path):
    chemin = str(tmp_path / "neuf.json")
    ecrire_json(chemin, [1])
    assert stat.S_IMODE(os.stat(chemin).st_mode) == 0o644


def test_les_droits_d_origine_sont_gardes(tmp_path):
    chemin = str(tmp_path / "secret.json")
    ecrire_json(chemin, [1])
    os.chmod(chemin, 0o600)
    ecrire_json(chemin, [1, 2])
    assert stat.S_IMODE(os.stat(chemin).st_mode) == 0o600
    assert lire_json(chemin) == [1, 2]


def test_plantage_au_milieu_l_ancien_reste_intact(tmp_path):
    chemin = str(tmp_path / "registre.json")
    ecrire_json(chemin, {"savoir": "ancien"})
    with pytest.raises(TypeError):
        ecrire_json(chemin, {"savoir": object()})   # impossible a ecrire
    assert lire_json(chemin) == {"savoir": "ancien"}
    assert os.listdir(str(tmp_path)) == ["registre.json"]   # aucun .tmp ne traine


def test_plantage_et_temporaire_impossible_a_effacer(tmp_path, monkeypatch):
    """Meme si le menage echoue, c'est l'erreur d'origine qui remonte."""
    chemin = str(tmp_path / "x.json")

    def refus(_):
        raise OSError("disque en lecture seule")
    monkeypatch.setattr(ecriture_sure.os, "unlink", refus)
    with pytest.raises(TypeError):
        ecrire_json(chemin, {1, 2})                  # un set : pas du JSON
    assert not os.path.exists(chemin)


def test_indentation_reglable(tmp_path):
    chemin = str(tmp_path / "i.json")
    ecrire_json(chemin, {"a": 1}, indent=None)
    assert open(chemin, encoding="utf-8").read() == json.dumps({"a": 1})
