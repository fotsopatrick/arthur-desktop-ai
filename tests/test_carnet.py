#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE CARNET DES REPONSES — outils/carnet-des-reponses.py.

Ce qu'on prouve, dans un HOME de bac a sable (jamais le vrai carnet) :
  - la cle d'une question ignore accents, ponctuation, mots vides et ordre ;
  - les chiffres comptent : « VM 1 » n'est pas « VM 2 » ;
  - noter garde, et remplace sans faire grossir le carnet ;
  - deja_repondu tolere un mot en plus, jamais un mot change ;
  - un carnet absent ou abime se lit comme vide ;
  - la ligne de commande (--noter, --chercher, --lire, aide) dit ce qu'il faut.
"""
import importlib.util
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIER = os.path.join(REPO, "outils", "carnet-des-reponses.py")


@pytest.fixture
def carnet(tmp_path, monkeypatch):
    """Le module charge avec un HOME jetable, son CARNET pointe dans tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    spec = importlib.util.spec_from_file_location("carnet_des_reponses", FICHIER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "CARNET", tmp_path / "portes" / "carnet.json")
    return mod


def test_cle_ignore_accents_ponctuation_mots_vides_et_ordre(carnet):
    """Deux formulations de la meme question donnent la meme cle."""
    a = carnet._cle("Je pose la porte à une heure ?")
    b = carnet._cle("JE POSE DONC LA PORTE A UNE HEURE")
    assert a == b == "heure porte pose"
    assert carnet._cle("Été, forêt !") == "ete foret"


def test_cle_garde_les_chiffres_et_jette_les_lettres_seules(carnet):
    """Un chiffre seul compte ; une lettre seule non."""
    assert carnet._cle("la VM 1") == "1 vm"
    assert carnet._cle("la VM 2") != carnet._cle("la VM 1")
    assert carnet._cle("x b vm") == "vm"


def test_cle_vide_pour_rien(carnet):
    """None, vide, ou que des mots vides : cle vide."""
    assert carnet._cle(None) == ""
    assert carnet._cle("") == ""
    assert carnet._cle("et donc alors ?") == ""


def test_tout_carnet_absent_ou_abime(carnet, tmp_path):
    """Un carnet qui n'existe pas, ou qui n'est pas du JSON, se lit vide."""
    assert carnet.tout() == []
    abime = tmp_path / "abime.json"
    abime.write_text("{pas du json", encoding="utf-8")
    assert carnet.tout(abime) == []


def test_noter_cree_puis_remplace(carnet):
    """Une meme question reformulee remplace la reponse, sans doublon."""
    assert carnet.noter("On pose la porte ?", "oui") == "oui"
    assert carnet.CARNET.exists()
    carnet.noter("ON POSE DONC LA PORTE", "non")
    lu = carnet.tout()
    assert len(lu) == 1
    assert lu[0]["reponse"] == "non"
    assert lu[0]["question"] == "ON POSE DONC LA PORTE"
    assert lu[0]["cle"] == "porte pose"
    assert "T" in lu[0]["quand"]
    carnet.noter("Autre question sur le depot", "peut-etre")
    assert len(carnet.tout()) == 2


def test_noter_chemin_explicite(carnet, tmp_path):
    """On peut ecrire dans un autre carnet que celui par defaut."""
    autre = tmp_path / "a" / "b" / "c.json"
    carnet.noter("question test", "r", chemin=autre)
    assert json.loads(autre.read_text(encoding="utf-8"))[0]["reponse"] == "r"
    assert not carnet.CARNET.exists()


def test_deja_repondu_exact_et_reformule(carnet):
    """La meme question, dans un autre ordre ou avec d'autres mots vides."""
    carnet.noter("Faut-il publier le depot prive sur github ce soir", "oui")
    assert carnet.deja_repondu("ce soir, publier sur github le depot prive, il faut ?") == "oui"


def test_deja_repondu_un_mot_en_plus(carnet):
    """Un mot en plus sur une longue question : la reponse est retrouvee."""
    carnet.noter("publier depot prive github soir demain matin", "oui")
    assert carnet.deja_repondu(
        "publier depot prive github soir demain matin vite") == "oui"
    # un mot en moins aussi
    assert carnet.deja_repondu("publier depot prive github soir demain") == "oui"


def test_deja_repondu_mot_change_refuse(carnet):
    """« depot prive » n'est pas « depot public »."""
    carnet.noter("publier le depot prive sur github", "oui")
    assert carnet.deja_repondu("publier le depot public sur github") is None


def test_deja_repondu_trop_different_ou_vide(carnet):
    """Trop peu de mots communs, question vide, entree sans cle : rien."""
    carnet.noter("publier depot prive github", "oui")
    assert carnet.deja_repondu("publier") is None          # 1/4 < 0.7
    assert carnet.deja_repondu("et donc ?") is None       # cle vide
    carnet.CARNET.write_text(json.dumps([{"cle": "", "reponse": "x"},
                                         {"question": "sans cle"}]), encoding="utf-8")
    assert carnet.deja_repondu("publier depot") is None


def test_deja_repondu_prend_le_meilleur(carnet, tmp_path):
    """Parmi plusieurs candidats, celui qui partage le plus de mots gagne."""
    chemin = tmp_path / "c.json"
    chemin.write_text(json.dumps([
        {"cle": "a1 b1 c1 d1 e1 f1 g1 h1 i1 j1 k1 l1", "reponse": "loin"},
        {"cle": "a1 b1 c1 d1 e1 f1 g1 h1 i1 j1", "reponse": "pres"},
    ]), encoding="utf-8")
    assert carnet.deja_repondu("a1 b1 c1 d1 e1 f1 g1 h1 i1", chemin) == "pres"


def test_raconter_vide_et_plein(carnet):
    """Le recit du carnet : vide, puis avec ses questions et reponses."""
    assert carnet.raconter() == "Aucune reponse gardee pour l instant."
    carnet.noter("On pose la porte ?", "oui")
    txt = carnet.raconter()
    assert txt.startswith("1 reponse(s) gardee(s)")
    assert "« On pose la porte ? »" in txt
    assert "-> oui" in txt


def test_raconter_entrees_incompletes(carnet):
    """Une entree sans question ni reponse s'affiche avec des « ? »."""
    carnet.CARNET.parent.mkdir(parents=True)
    carnet.CARNET.write_text("[{}]", encoding="utf-8")
    assert "« ? »" in carnet.raconter()
    assert "-> ?" in carnet.raconter()


def _cli(carnet, monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["carnet-des-reponses.py", *args])
    code = carnet.main()
    return code, capsys.readouterr().out


def test_cli_noter_chercher_lire(carnet, monkeypatch, capsys):
    """--noter dit « Note. », --chercher retrouve, --lire raconte."""
    code, out = _cli(carnet, monkeypatch, capsys, "--noter", "On pose la porte ?", "oui")
    assert code == 0 and out.strip() == "Note."
    code, out = _cli(carnet, monkeypatch, capsys, "--chercher", "on POSE la porte")
    assert code == 0 and out.strip() == "oui"
    code, out = _cli(carnet, monkeypatch, capsys, "--chercher", "question inconnue")
    assert out.strip() == "(jamais repondu)"
    code, out = _cli(carnet, monkeypatch, capsys, "--lire")
    assert "1 reponse(s)" in out


def test_cli_sans_argument_affiche_usage(carnet, monkeypatch, capsys):
    """Sans option : l'aide (partie USAGE de la docstring)."""
    code, out = _cli(carnet, monkeypatch, capsys)
    assert code == 0
    assert "--noter" in out and "--lire" in out
