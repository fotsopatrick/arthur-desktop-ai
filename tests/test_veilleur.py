#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE VEILLEUR DU SAVOIR (veilleur_savoir.py) — de la lacune a la fiche.

Ce qu'on prouve, dans un bac a sable (HAICHI_SAVOIR_DIR jetable) :
  - sans file de lacunes, ou file vide, il le dit et ne fabrique rien ;
  - il prend la PREMIERE lacune et structure une fiche au format du registre
    (mots, think, answer, source, date_capture, confiance) ;
  - la fiche s'ajoute a fiches-attente.json sans ecraser les precedentes ;
  - un fichier d'attente abime ou mal forme repart d'une liste vide ;
  - une fiche malformee est signalee, mais rendue quand meme (le garde juge) ;
  - le veilleur se charge meme lance depuis un autre dossier.
"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import veilleur_savoir as V  # noqa: E402

CHEMIN = os.path.join(REPO, "veilleur_savoir.py")


@pytest.fixture()
def bac(tmp_path, monkeypatch):
    """Le bac a sable du veilleur : HAICHI_SAVOIR_DIR = un dossier jetable."""
    monkeypatch.setenv("HAICHI_SAVOIR_DIR", str(tmp_path))
    return tmp_path


def _lacunes(bac, lacunes):
    (bac / "lacunes.json").write_text(json.dumps(lacunes, ensure_ascii=False),
                                      encoding="utf-8")


def _attente(bac):
    return json.loads((bac / "fiches-attente.json").read_text(encoding="utf-8"))


def test_aide(capsys):
    """--help et -h : une ligne d'usage, code 0."""
    assert V.main(["--help"]) == 0
    assert V.main(["-h"]) == 0
    assert "veilleur_savoir.py" in capsys.readouterr().out


def test_sans_lacunes(bac, capsys):
    """Pas de lacunes.json : rien a traiter, aucun fichier cree."""
    assert V.main([]) == 0
    assert "Aucune lacune" in capsys.readouterr().out
    assert not (bac / "fiches-attente.json").exists()


def test_file_vide(bac, capsys):
    """File de lacunes vide : on le dit, rien n'est cree."""
    _lacunes(bac, [])
    assert V.main([]) == 0
    assert "vide" in capsys.readouterr().out
    assert not (bac / "fiches-attente.json").exists()


def test_lacune_sans_question(bac, capsys):
    """Lacune sans question : code 1, on saute."""
    _lacunes(bac, [{"contexte_brut": "rien"}])
    assert V.main([]) == 1
    assert "sans question" in capsys.readouterr().out
    assert not (bac / "fiches-attente.json").exists()


def test_fiche_complete_depuis_les_arguments(bac, capsys):
    """Reponse, source et date fournies : la fiche les porte, format exact."""
    _lacunes(bac, [{"question": "Quelle est la capitale du Cameroun ?",
                    "contexte_brut": "moteur muet"},
                   {"question": "Deuxieme lacune"}])
    code = V.main(["--reponse", "Yaounde.", "--source", "https://fr.wikipedia.org/x",
                   "--date", "2026-09-01", "-dump"])
    assert code == 0
    sortie = capsys.readouterr().out
    assert json.loads(sortie)["answer"] == "Yaounde."
    [fiche] = _attente(bac)
    assert fiche["_lacune"] == "Quelle est la capitale du Cameroun ?"
    assert fiche["answer"] == "Yaounde."
    assert fiche["source"] == "https://fr.wikipedia.org/x"
    assert fiche["date_capture"] == "2026-09-01"
    assert "capitale" in fiche["mots"] and "cameroun" in fiche["mots"]
    assert "moteur muet" in fiche["think"]
    assert 0.0 <= fiche["confiance"] <= 1.0


def test_valeurs_par_defaut_et_ajout(bac, capsys):
    """Sans arguments : reponse d'aveu, « sans source », date du jour ; ajout en file."""
    _lacunes(bac, [{"question": "Qui garde la tour ?"}])
    (bac / "fiches-attente.json").write_text('[{"deja": 1}]', encoding="utf-8")
    assert V.main(["--source"]) == 0            # option sans valeur : ignoree
    assert "fiches-attente.json" in capsys.readouterr().out
    attente = _attente(bac)
    assert attente[0] == {"deja": 1}
    fiche = attente[1]
    assert fiche["source"] == "sans source"
    assert fiche["answer"].startswith("Je ne sais pas encore")
    assert len(fiche["date_capture"]) == 10
    assert "(aucun)" in fiche["think"]


@pytest.mark.parametrize("contenu", ["{casse", '{"pas": "une liste"}'])
def test_attente_abimee_repart_de_zero(bac, contenu):
    """fiches-attente.json illisible ou pas une liste : liste vide, meme chemin."""
    (bac / "fiches-attente.json").write_text(contenu, encoding="utf-8")
    attente, chemin = V.charger_attente()
    assert attente == []
    assert chemin == str(bac / "fiches-attente.json")


def test_dossier_courant_par_defaut(tmp_path, monkeypatch):
    """Sans HAICHI_SAVOIR_DIR, le bac a sable est le dossier courant."""
    monkeypatch.delenv("HAICHI_SAVOIR_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    _lacunes(tmp_path, [{"question": "Ou suis-je ?"}])
    assert V.main([]) == 0
    assert _attente(tmp_path)[0]["_lacune"] == "Ou suis-je ?"


def test_fiche_malformee_signalee_mais_rendue(monkeypatch, capsys):
    """Le schema refuse la fiche : ATTENTION imprime, la fiche revient quand meme."""
    monkeypatch.setattr(V, "_validate_fiche", lambda f, nom: (False, "champ manquant"))
    fiche = V.construire_fiche("Question ?", "R", "src", "2026-09-01")
    assert fiche["answer"] == "R"
    assert "fiche malformee (champ manquant)" in capsys.readouterr().out


def test_fiche_valide_sans_avertissement(capsys):
    """Une fiche normale passe le schema sans rien dire."""
    if V._validate_fiche is None:  # pragma: no cover
        pytest.skip("schema structured_outputs absent")
    V.construire_fiche("Quelle heure ?", "Midi.", "https://www.service-public.fr",
                       "2026-09-01")
    assert "ATTENTION" not in capsys.readouterr().out


def test_chargement_hors_du_depot_et_sans_schema(tmp_path, monkeypatch):
    """Lance d'ailleurs : il retrouve savoir_commun ; sans schema, il s'en passe."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", [p for p in sys.path
                                      if os.path.realpath(p or ".") != REPO
                                      and p not in ("", ".")])
    monkeypatch.delitem(sys.modules, "savoir_commun", raising=False)
    monkeypatch.setitem(sys.modules, "skills.structured_outputs", None)
    spec = importlib.util.spec_from_file_location("veilleur_isole", CHEMIN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m._validate_fiche is None
    assert REPO in sys.path
    fiche = m.construire_fiche("Test isole", "ok", "src", "2026-09-01")
    assert fiche["mots"] and fiche["answer"] == "ok"


def test_en_ligne_de_commande(tmp_path):
    """Lance comme un programme : code de sortie et fiche posee dans le bac."""
    _lacunes(tmp_path, [{"question": "Combien de tours ?"}])
    e = dict(os.environ, HAICHI_SAVOIR_DIR=str(tmp_path), HOME=str(tmp_path))
    r = subprocess.run([sys.executable, CHEMIN, "--reponse", "Une."], env=e,
                       cwd=str(tmp_path), capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert _attente(tmp_path)[0]["answer"] == "Une."
