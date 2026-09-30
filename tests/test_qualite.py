#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'OUTIL DE MESURE DES TESTS (qualite/) — on mesure la mesure.

Si la couverture annoncee est fausse, tout le tableau de bord ment. On
verifie donc, sur de petits fichiers ecrits pour l'occasion :
  - les lignes executables sont lues dans le code compile (docstrings et
    commentaires ne comptent pas) ;
  - le bloc __main__ et « pragma: no cover » sont exclus, et c'est dit ;
  - les fonctions jamais appelees, partielles, completes sont reconnues ;
  - le verdict couvert / incomplet / sans test suit le seuil ;
  - le traceur ne suit que le code d'Arthur, et ecrit ce qu'il a vu ;
  - le lanceur classe une serie rouge « sautee » seulement quand il manque
    une chose exterieure, et lit les bilans des scripts ;
  - la page du tableau de bord se construit, sans ressource exterieure.
"""
import json
import os
import subprocess
import sys
import textwrap

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUALITE = os.path.join(REPO, "qualite")
sys.path.insert(0, QUALITE)

import analyse  # noqa: E402
import lancer  # noqa: E402
import tableau  # noqa: E402
import traceur  # noqa: E402

EXEMPLE = textwrap.dedent('''\
    """Un module d'exemple."""
    import os


    def appelee(x):
        if x > 0:
            return "positif"
        return "negatif"


    def jamais():
        return 42


    class Boite:
        def methode(self):
            return 1


    def ignoree():  # pragma: no cover
        return "pas mesuree"


    if __name__ == "__main__":
        print(appelee(1))
''')


@pytest.fixture
def exemple(tmp_path):
    chemin = tmp_path / "exemple.py"
    chemin.write_text(EXEMPLE, encoding="utf-8")
    return str(chemin)


def test_lignes_executables_sans_docstring_ni_commentaire(exemple):
    lignes = analyse.lignes_executables(EXEMPLE, exemple)
    assert 2 in lignes and 5 in lignes and 6 in lignes       # import, def, if
    assert 3 not in lignes and 4 not in lignes               # lignes vides


def test_main_et_pragma_sont_exclus_et_dits(exemple, tmp_path):
    m = analyse.analyser_fichier(exemple, str(tmp_path), set())
    pourquoi = " ".join(r["pourquoi"] for r in m["exclusions"])
    assert "__main__" in pourquoi and "pragma" in pourquoi
    assert 26 not in m["manquees"]                           # print dans __main__
    assert 22 not in m["manquees"]                           # corps pragma


def test_fonctions_jamais_partielles_completes(exemple, tmp_path):
    # ce qui a tourne : l'import, les def, et appelee(1) (branche positive)
    vues = {1, 2, 5, 6, 7, 11, 15, 16, 20}
    m = analyse.analyser_fichier(exemple, str(tmp_path), vues)
    etats = {f["nom"]: f["etat"] for f in m["fonctions"]}
    assert etats["appelee"] == "partielle"
    assert etats["jamais"] == "jamais appelee"
    assert etats["Boite.methode"] == "jamais appelee"
    assert "ignoree" not in etats                            # exclue : pas comptee


def test_verdicts_suivent_le_seuil():
    assert analyse.verdict(0.0, set()) == "sans test"
    assert analyse.verdict(10.0, {1}) == "incomplet"
    assert analyse.verdict(analyse.SEUIL_COUVERT, {1}) == "couvert"


def test_tout_couvert_donne_100(exemple, tmp_path):
    tout = analyse.lignes_executables(EXEMPLE, exemple)
    m = analyse.analyser_fichier(exemple, str(tmp_path), tout,
                                 {n: {"test_x"} for n in tout})
    assert m["pourcent"] == 100.0 and m["verdict"] == "couvert"
    assert m["tests"] == ["test_x"] and m["manquees"] == []


def test_fichier_casse_est_signale(tmp_path):
    casse = tmp_path / "casse.py"
    casse.write_text("def f(:\n", encoding="utf-8")
    m = analyse.analyser_fichier(str(casse), str(tmp_path), set())
    assert "syntaxe" in m["erreur"] and m["verdict"] == "sans test"


def test_le_traceur_ne_suit_que_le_code_d_arthur():
    assert traceur.fichier_suivi(os.path.join(REPO, "nano_moteur_ultra.py"))
    assert traceur.fichier_suivi(os.path.join(REPO, "skills", "mcp_eveil.py"))
    for pas_suivi in ("tests/test_infra.py", "test_calcul_arthur.py",
                      "vendor/pytest/__init__.py", "archive/gamma_avatar.py",
                      "qualite/lancer.py", "LISEZ-MOI.md"):
        assert not traceur.fichier_suivi(os.path.join(REPO, pas_suivi)), pas_suivi
    assert not traceur.fichier_suivi(os.__file__)


def test_le_traceur_ecrit_ce_qu_il_a_vu(tmp_path):
    """Un vrai sous-processus, amorce comme le lanceur le fait."""
    env = dict(os.environ, ARTHUR_COUV_DOSSIER=str(tmp_path), ARTHUR_COUV_TEST="essai",
               PYTHONPATH=os.pathsep.join([os.path.join(QUALITE, "amorce"), REPO]))
    subprocess.run([sys.executable, "-c", "import ecriture_sure"], env=env, check=True,
                   cwd=REPO)
    traces = [json.load(open(tmp_path / n)) for n in os.listdir(tmp_path)]
    assert traces and traces[0]["test"] == "essai"
    fichiers = {os.path.basename(f) for t in traces for f in t["lignes"]}
    assert fichiers == {"ecriture_sure.py"}                  # rien d'autre n'est suivi


def test_bilans_des_scripts():
    assert lancer._bilan_rouges("BILAN : 3 verts, 0 rouges") == 0
    assert lancer._bilan_rouges("  24 epreuves passees, 4 ratees") == 4
    assert lancer._bilan_rouges("Ran 2 tests in 0.1s\n\nOK\n") == 0
    assert lancer._bilan_rouges("Ran 2 tests in 0.1s\n\nFAILED (failures=1)\n") == 1
    assert lancer._bilan_rouges("rien de lisible") is None


def test_epreuves_lues_dans_la_sortie():
    ep = lancer._epreuves_texte("  VERT   il calcule\n  ROUGE  il invente\n  OK    ok aussi\n  ~ saute\n")
    assert [e["etat"] for e in ep] == ["vert", "rouge", "vert", "saute"]


def _serie(tmp_path, nom, contenu):
    chemin = tmp_path / nom
    chemin.write_text(contenu, encoding="utf-8")
    return {"id": nom, "type": "script", "chemin": str(chemin), "parallele": False}


def test_serie_verte_rouge_et_sautee(tmp_path):
    verte = lancer.executer(_serie(tmp_path, "t_vert.py",
                                   "print('  VERT   un')\nprint('BILAN 1 vert, 0 rouge')\n"), str(tmp_path))
    rouge = lancer.executer(_serie(tmp_path, "t_rouge.py",
                                   "print('  ROUGE  deux')\nprint('0 vert, 1 rouge')\n"), str(tmp_path))
    sautee = lancer.executer(_serie(tmp_path, "t_saute.py",
                                    "import sys\nprint('[Errno 111] Connection refused')\nsys.exit(1)\n"),
                             str(tmp_path))
    assert (verte["etat"], rouge["etat"], sautee["etat"]) == ("vert", "rouge", "saute")
    assert "cockpit" in sautee["raison"]


def test_une_serie_rouge_sans_raison_exterieure_reste_rouge(tmp_path):
    r = lancer.executer(_serie(tmp_path, "t_bug.py", "raise ValueError('vrai bug')\n"), str(tmp_path))
    assert r["etat"] == "rouge" and r["raison"] == ""


def test_la_page_se_construit_sans_rien_d_exterieur(tmp_path, exemple):
    m = analyse.analyser_fichier(exemple, str(tmp_path), {1, 2})
    m["groupe"] = "coeur"
    donnees = {"date": "2026-09-30T10:00:00", "duree": 1.0, "python": "3", "seuil": 80.0,
               "totaux": {"pourcent": m["pourcent"], "lignes": m["executables"],
                          "couvertes": m["couvertes"], "modules": 1, "couverts": 0,
                          "incomplets": 1, "sans_test": 0, "fonctions": 3,
                          "fonctions_jamais": 3, "series": 0, "series_vertes": 0,
                          "series_rouges": 0, "series_sautees": 0, "epreuves": 0,
                          "epreuves_vertes": 0},
               "modules": [m], "series": [], "historique": []}
    page = open(tableau.ecrire(donnees, str(tmp_path / "index.html")), encoding="utf-8").read()
    assert "exemple.py" in page
    for exterieur in ("http://", "https://", "<link", "@import"):
        assert exterieur not in page.replace("http://www.w3.org/2000/svg", ""), exterieur
    assert "</script>" not in json.dumps(donnees) or "<\\/" in page     # pas d'injection


def test_les_fichiers_d_arthur_sont_trouves():
    noms = {os.path.relpath(f, REPO) for f in analyse.fichiers_d_arthur(REPO)}
    assert "nano_moteur_ultra.py" in noms and os.path.join("skills", "mcp_eveil.py") in noms
    assert not any(n.startswith(("tests", "vendor", "archive", "qualite")) for n in noms)
